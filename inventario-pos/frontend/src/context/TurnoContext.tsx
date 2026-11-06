/**
 * Estado compartido del turno de caja.
 *
 * Consulta el turno actual al entrar al panel y abre automáticamente el modal
 * de apertura cuando no hay ninguno. Las páginas operativas usan este estado
 * para bloquear mesas y pedidos hasta que exista un turno abierto.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { ReactNode } from "react";
import AvisoTurnoModal from "../components/AvisoTurnoModal";
import { api } from "../services/api";
import type { TurnoCaja } from "../types/turno";

export const MENSAJE_TURNO_REQUERIDO =
  "Operación no permitida: Debe abrir un turno de caja antes de atender mesas o tomar pedidos";

interface TurnoContexto {
  turno: TurnoCaja | null;
  cargando: boolean;
  error: string | null;
  recargar: () => Promise<TurnoCaja | null>;
  abrirTurno: (fondoInicial: number) => Promise<TurnoCaja>;
  solicitarApertura: () => void;
}

const ContextoTurno = createContext<TurnoContexto | null>(null);

function usuarioActualId(): number {
  try {
    const usuario = JSON.parse(localStorage.getItem("user") || "{}");
    return Number(usuario?.id) || 1;
  } catch {
    return 1;
  }
}

export function TurnoProvider({ children }: { children: ReactNode }) {
  const [turno, setTurno] = useState<TurnoCaja | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mostrarApertura, setMostrarApertura] = useState(false);

  const consultar = useCallback(async (): Promise<TurnoCaja | null> => {
    setCargando(true);
    try {
      const actual = (await api.getTurnoActual()) as TurnoCaja | null;
      setTurno(actual ?? null);
      setError(null);
      return actual ?? null;
    } catch (err: any) {
      setError(err?.message || "No se pudo consultar el turno actual.");
      return null;
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    let vigente = true;

    const revisar = async () => {
      setCargando(true);
      try {
        const actual = (await api.getTurnoActual()) as TurnoCaja | null;
        if (!vigente) return;
        setTurno(actual ?? null);
        setError(null);
        // Solo en la carga inicial: si no hay turno, se guía la apertura.
        if (!actual) setMostrarApertura(true);
      } catch (err: any) {
        if (vigente) {
          setError(err?.message || "No se pudo consultar el turno actual.");
        }
      } finally {
        if (vigente) setCargando(false);
      }
    };

    revisar();
    return () => {
      vigente = false;
    };
  }, []);

  const recargar = useCallback(async () => {
    const actual = await consultar();
    return actual;
  }, [consultar]);

  const abrirTurno = useCallback(
    async (fondoInicial: number): Promise<TurnoCaja> => {
      try {
        const respuesta: any = await api.abrirTurno(
          usuarioActualId(),
          fondoInicial
        );
        const nuevo: TurnoCaja | null = respuesta?.turno ?? null;
        if (!nuevo) {
          throw new Error("El servidor no devolvió el turno abierto.");
        }
        setTurno(nuevo);
        setMostrarApertura(false);
        setError(null);
        return nuevo;
      } catch (err: any) {
        // Si otro navegador abrió el turno, se sincroniza el estado y se
        // cierra el modal en lugar de dejar un error sin salida.
        if (String(err?.message || "").includes("Ya hay un turno")) {
          const actual = await consultar();
          if (actual) setMostrarApertura(false);
        }
        throw err;
      }
    },
    [consultar]
  );

  const solicitarApertura = useCallback(() => setMostrarApertura(true), []);

  const valor = useMemo<TurnoContexto>(
    () => ({
      turno,
      cargando,
      error,
      recargar,
      abrirTurno,
      solicitarApertura,
    }),
    [turno, cargando, error, recargar, abrirTurno, solicitarApertura]
  );

  return (
    <ContextoTurno.Provider value={valor}>
      {children}
      {mostrarApertura && (
        <AvisoTurnoModal
          onCancelar={() => setMostrarApertura(false)}
          onAbierto={(nuevo) => {
            setTurno(nuevo);
            setMostrarApertura(false);
          }}
          abrirTurno={abrirTurno}
        />
      )}
    </ContextoTurno.Provider>
  );
}

export function useTurno(): TurnoContexto {
  const contexto = useContext(ContextoTurno);
  if (!contexto) {
    throw new Error("useTurno debe usarse dentro de TurnoProvider");
  }
  return contexto;
}
