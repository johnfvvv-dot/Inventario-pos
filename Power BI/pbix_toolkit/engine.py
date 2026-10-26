"""Motor de acceso a modelos .pbix a través de Power BI Desktop + ADOMD.

Uso (desde el Python de Windows):
    python engine.py open "Ruta\\Archivo.pbix"      -> abre el modelo (sobre una copia)
    python engine.py status                         -> estado de la sesión
    python engine.py schema [--refresh]             -> esquema (tablas/medidas/relaciones)
    python engine.py query "EVALUATE ..." [--max N] -> consulta DAX/DMV/MDX -> JSON
    python engine.py query --stdin                  -> idem, leyendo la consulta de stdin
    python engine.py close                          -> cierra el Power BI Desktop lanzado

El archivo original NUNCA se modifica: se trabaja sobre una copia en runtime/.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

TOOLKIT = Path(__file__).resolve().parent
RUNTIME = TOOLKIT / "runtime"
STATE_FILE = RUNTIME / "state.json"
SCHEMA_FILE = RUNTIME / "schema.json"
SCHEMA_TXT = RUNTIME / "schema_summary.txt"
COPY_FILE = RUNTIME / "model.pbix"

PBIDESKTOP = Path(r"C:\Program Files\Microsoft Power BI Desktop\bin\PBIDesktop.exe")
WS_ROOTS = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Power BI Desktop" / "AnalysisServicesWorkspaces",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Power BI Desktop Store App" / "AnalysisServicesWorkspaces",
]

sys.path.insert(0, str(TOOLKIT))
import adomd  # noqa: E402
import model_schema  # noqa: E402


# ---------------------------------------------------------------- utilidades
def log(*args) -> None:
    print(*args, file=sys.stderr, flush=True)


def salida(obj) -> None:
    json.dump(obj, sys.stdout, ensure_ascii=False, default=str)
    print()


def cargar_estado() -> dict | None:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def guardar_estado(estado: dict) -> None:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ------------------------------------------------- descubrimiento de puerto
def _archivos_puerto():
    for raiz in WS_ROOTS:
        if raiz.exists():
            yield from raiz.glob("*/Data/msmdsrv.port.txt")


def _puerto_desde_archivos(desde_ts: float) -> int | None:
    mejor = None
    for pf in _archivos_puerto():
        try:
            mt = pf.stat().st_mtime
        except OSError:
            continue
        if mt >= desde_ts - 5 and (mejor is None or mt > mejor[0]):
            mejor = (mt, pf)
    if mejor:
        try:
            return int(mejor[1].read_text(encoding="utf-8-sig").strip())
        except (ValueError, OSError):
            return None
    return None


def _pids_hijos_msmdsrv(pid_padre: int) -> list[int]:
    try:
        out = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_Process -Filter \"Name='msmdsrv.exe'\" | "
                f"Where-Object {{$_.ParentProcessId -eq {pid_padre}}} | "
                "Select-Object -ExpandProperty ProcessId",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        return [int(x) for x in out.split() if x.strip().isdigit()]
    except Exception:
        return []


def _puerto_desde_netstat(pids: list[int]) -> int | None:
    if not pids:
        return None
    try:
        out = subprocess.run(
            ["netstat", "-ano"], capture_output=True, text=True, timeout=30
        ).stdout
    except Exception:
        return None
    for linea in out.splitlines():
        partes = linea.split()
        if len(partes) >= 5 and partes[0].upper() == "TCP" and partes[3].upper() == "LISTENING":
            try:
                pid = int(partes[4])
            except ValueError:
                continue
            if pid in pids:
                host, _, puerto = partes[1].rpartition(":")
                if puerto.isdigit():
                    return int(puerto)
    return None


def _pids_pbidesktop_con_archivo(fragmento: str) -> list[int]:
    """PIDs de Power BI Desktop que tienen abierto un archivo (por CommandLine).

    Power BI Desktop usa un proceso lanzador que delega en otro proceso la
    ventana real; este método encuentra el proceso verdadero para poder
    cerrarlo correctamente.
    """
    frag = fragmento.replace("'", "''")
    comando = (
        "Get-CimInstance Win32_Process -Filter \"Name='PBIDesktop.exe'\" | "
        f"Where-Object {{ $_.CommandLine -like '*{frag}*' }} | "
        "Select-Object -ExpandProperty ProcessId"
    )
    try:
        out = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", comando],
            capture_output=True,
            text=True,
            timeout=40,
        ).stdout
        return [int(x) for x in out.split() if x.strip().isdigit()]
    except Exception:
        return []


def esperar_puerto(pid: int, desde_ts: float, timeout: float) -> int:
    """Espera a que aparezca el puerto del motor local (workspace)."""
    limite = time.time() + timeout
    mientras_fallback = desde_ts + 25
    log(f"[open] esperando puerto del motor (PID {pid}, máx {int(timeout)}s)...")
    while time.time() < limite:
        puerto = _puerto_desde_archivos(desde_ts)
        if puerto:
            log(f"[open] puerto detectado en workspace: {puerto}")
            return puerto
        if time.time() > mientras_fallback:
            hijos = _pids_hijos_msmdsrv(pid)
            puerto = _puerto_desde_netstat(hijos)
            if puerto:
                log(f"[open] puerto detectado vía netstat (msmdsrv PID {hijos}): {puerto}")
                return puerto
        time.sleep(2)
    raise TimeoutError("No se detectó el puerto del motor local en el tiempo esperado.")


def esperar_conexion(puerto: int, timeout: float) -> str:
    """Espera a que el motor acepte consultas y devuelve el catálogo."""
    limite = time.time() + timeout
    log("[open] esperando a que el modelo esté listo para consultas...")
    ultimo_error = None
    while time.time() < limite:
        try:
            catalogo = adomd.probe(puerto, timeout_s=5)
            if catalogo is not None:
                log(f"[open] modelo listo. Catálogo: {catalogo or '(sin nombre)'}")
                return catalogo
        except Exception as exc:  # pragma: no cover
            ultimo_error = exc
        time.sleep(3)
    raise TimeoutError(f"El motor no respondió: {ultimo_error}")


# ----------------------------------------------------------------- comandos
def cmd_open(args) -> None:
    origen = Path(args.pbix).resolve()
    if not origen.exists():
        salida({"ok": False, "error": f"No existe el archivo: {origen}"})
        sys.exit(1)

    if not PBIDESKTOP.exists():
        salida({"ok": False, "error": f"No se encontró Power BI Desktop: {PBIDESKTOP}"})
        sys.exit(1)

    # ¿Ya hay una sesión viva?
    estado = cargar_estado()
    if estado and estado.get("port"):
        catalogo = adomd.probe(int(estado["port"]), timeout_s=4)
        if catalogo is not None:
            desactualizada = False
            if estado.get("source") != str(origen):
                desactualizada = True
            else:
                try:
                    e = estado.get("sourceStat") or {}
                    st = origen.stat()
                    desactualizada = (st.st_mtime_ns != e.get("mtimeNs")) or (st.st_size != e.get("size"))
                except OSError:
                    pass
            salida(
                {
                    "ok": True,
                    "reused": True,
                    "staleSource": desactualizada,
                    "port": estado["port"],
                    "catalog": catalogo,
                    "source": estado.get("source"),
                    "copy": estado.get("copy"),
                    "pid": estado.get("pid"),
                    "mensaje": (
                        "Sesión ya activa." if not desactualizada
                        else "Sesión activa pero el original cambió: usa close y vuelve a abrir."
                    ),
                }
            )
            return

    RUNTIME.mkdir(parents=True, exist_ok=True)

    # Copiar SIEMPRE a runtime/ (el original no se toca jamás)
    shutil.copy2(origen, COPY_FILE)
    fuente_stat = origen.stat()
    log(f"[open] copia de trabajo: {COPY_FILE}")

    lanzado = time.time()
    proc = subprocess.Popen([str(PBIDESKTOP), str(COPY_FILE)])

    puerto = esperar_puerto(proc.pid, lanzado, timeout=args.timeout)
    catalogo = esperar_conexion(puerto, timeout=max(60, args.timeout - 60))
    pids_pbi = _pids_pbidesktop_con_archivo(str(COPY_FILE))
    log(f"[open] procesos Power BI Desktop con el modelo abierto: {pids_pbi or [proc.pid]}")

    estado = {
        "source": str(origen),
        "copy": str(COPY_FILE),
        "pid": proc.pid,
        "pidsPBI": pids_pbi,
        "port": puerto,
        "catalog": catalogo,
        "launchedAt": lanzado,
        "sourceStat": {
            "mtimeNs": fuente_stat.st_mtime_ns,
            "size": fuente_stat.st_size,
        },
        "engineVersion": "1.0",
    }
    guardar_estado(estado)

    salida(
        {
            "ok": True,
            "reused": False,
            "port": puerto,
            "catalog": catalogo,
            "pid": proc.pid,
            "source": str(origen),
            "copy": str(COPY_FILE),
            "mensaje": "Modelo abierto y listo para consultas.",
        }
    )


def cmd_status(_args) -> None:
    estado = cargar_estado()
    if not estado:
        salida({"open": False, "mensaje": "No hay ninguna sesión registrada."})
        return
    catalogo = adomd.probe(int(estado["port"]), timeout_s=4)
    vivo = catalogo is not None
    salida(
        {
            "open": vivo,
            "port": estado.get("port"),
            "catalog": catalogo if vivo else None,
            "source": estado.get("source"),
            "copy": estado.get("copy"),
            "pid": estado.get("pid"),
            "launchedAt": estado.get("launchedAt"),
            "mensaje": "Motor activo." if vivo else "El proceso ya no responde (usa open de nuevo).",
        }
    )


def _proceso_vivo(pid: int) -> bool:
    try:
        out = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True,
            text=True,
            timeout=20,
        ).stdout
        return str(pid) in out
    except Exception:
        return False


def cmd_close(_args) -> None:
    estado = cargar_estado()
    pids: set[int] = set()
    if estado:
        if estado.get("pid"):
            pids.add(int(estado["pid"]))
        pids.update(int(p) for p in (estado.get("pidsPBI") or []))

    # Rastreo por línea de comandos: encuentra la ventana real aunque el lanzador haya cambiado
    pids.update(_pids_pbidesktop_con_archivo(str(RUNTIME)))

    if not pids:
        try:
            STATE_FILE.unlink(missing_ok=True)
        except OSError:
            pass
        salida({"ok": True, "mensaje": "No había sesión que cerrar."})
        return

    log(f"[close] cerrando procesos: {sorted(pids)}")
    for pid in sorted(pids):
        subprocess.run(["taskkill", "/PID", str(pid), "/T"], capture_output=True, timeout=30)

    limite = time.time() + 20
    while time.time() < limite:
        restantes = set(_pids_pbidesktop_con_archivo(str(RUNTIME)))
        restantes |= {p for p in pids if _proceso_vivo(p)}
        if not restantes:
            break
        time.sleep(1)
    else:
        forzar = pids | set(_pids_pbidesktop_con_archivo(str(RUNTIME)))
        log(f"[close] forzando cierre de: {sorted(forzar)}")
        for pid in sorted(forzar):
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, timeout=30)
        time.sleep(2)

    try:
        STATE_FILE.unlink(missing_ok=True)
    except OSError:
        pass

    restantes = _pids_pbidesktop_con_archivo(str(RUNTIME))
    if restantes:
        salida({"ok": False, "mensaje": f"No se pudieron cerrar los procesos: {restantes}"})
    else:
        salida({"ok": True, "mensaje": "Sesión cerrada."})


def _conectar_estado(estado: dict):
    if not estado or not estado.get("port"):
        raise RuntimeError("No hay sesión abierta. Ejecuta primero: engine.py open <archivo.pbix>")
    return adomd.connect(int(estado["port"]))


def cmd_schema(args) -> None:
    if SCHEMA_FILE.exists() and not args.refresh:
        datos = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
        resumen = SCHEMA_TXT.read_text(encoding="utf-8") if SCHEMA_TXT.exists() else model_schema.resumen_texto(datos)
        salida({"ok": True, "cached": True, "schema": datos, "summary": resumen})
        return

    estado = cargar_estado()
    conn = _conectar_estado(estado)
    try:
        esquema = model_schema.build(conn)
    finally:
        conn.Close()

    esquema["generatedAt"] = time.strftime("%Y-%m-%d %H:%M:%S")
    esquema["pbixSource"] = (estado or {}).get("source")

    RUNTIME.mkdir(parents=True, exist_ok=True)
    SCHEMA_FILE.write_text(json.dumps(esquema, ensure_ascii=False, indent=2), encoding="utf-8")
    resumen = model_schema.resumen_texto(esquema)
    SCHEMA_TXT.write_text(resumen, encoding="utf-8")

    salida({"ok": True, "cached": False, "schema": esquema, "summary": resumen})


def cmd_query(args) -> None:
    if args.stdin:
        consulta = sys.stdin.read()
    elif args.consulta:
        consulta = args.consulta
    else:
        salida({"ok": False, "error": "Falta la consulta (argumento o --stdin)."})
        sys.exit(1)

    consulta = consulta.strip()
    if not consulta:
        salida({"ok": False, "error": "Consulta vacía."})
        sys.exit(1)

    # Prefijo generoso para DAX: si no es EVALUATE/DEFINE/SELECT, se asume tabla o expresión DAX
    primera = consulta.upper()
    if not (primera.startswith("EVALUATE") or primera.startswith("DEFINE") or primera.startswith("SELECT") or primera.startswith("{")):
        import re as _re

        if _re.fullmatch(r"[\wáéíóúÁÉÍÓÚñÑ .\-]+", consulta):
            consulta = f"EVALUATE '{consulta.replace(chr(39), chr(39) * 2)}'"
        else:
            consulta = "EVALUATE " + consulta

    estado = cargar_estado()
    conn = _conectar_estado(estado)
    inicio = time.time()
    try:
        res = adomd.query(conn, consulta, max_rows=args.max)
    finally:
        conn.Close()

    salida(
        {
            "ok": True,
            "consulta": consulta,
            "elapsedMs": int((time.time() - inicio) * 1000),
            **_vars_consulta(res),
        }
    )


def _vars_consulta(res: dict) -> dict:
    return {
        "columns": res["columns"],
        "types": res["types"],
        "rows": res["rows"],
        "rowCount": res["rowCount"],
    }


# --------------------------------------------------------------------- main
def main() -> None:
    for flujo in (sys.stdout, sys.stderr, sys.stdin):
        try:
            flujo.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except Exception:
            pass

    parser = argparse.ArgumentParser(prog="engine.py", description="Motor .pbix (Power BI Desktop + ADOMD)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_open = sub.add_parser("open", help="Abre un .pbix (sobre copia) y prepara el motor")
    p_open.add_argument("pbix")
    p_open.add_argument("--timeout", type=int, default=240, help="Segundos máximos de espera")
    p_open.set_defaults(func=cmd_open)

    p_status = sub.add_parser("status", help="Estado de la sesión")
    p_status.set_defaults(func=cmd_status)

    p_close = sub.add_parser("close", help="Cierra el Power BI Desktop lanzado")
    p_close.set_defaults(func=cmd_close)

    p_schema = sub.add_parser("schema", help="Esquema del modelo")
    p_schema.add_argument("--refresh", action="store_true")
    p_schema.set_defaults(func=cmd_schema)

    p_query = sub.add_parser("query", help="Consulta DAX/DMV/MDX")
    p_query.add_argument("consulta", nargs="?", default=None)
    p_query.add_argument("--stdin", action="store_true", help="Leer la consulta de stdin")
    p_query.add_argument("--max", type=int, default=200000, help="Máximo de filas devueltas")
    p_query.set_defaults(func=cmd_query)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
