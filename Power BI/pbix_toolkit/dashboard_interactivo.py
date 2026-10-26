#!/usr/bin/env python3
"""Generador de tableros HTML interactivos (con filtros) — desde cero.

Diseño propio: barra de filtros adhesiva, KPIs, gráficos y tablas que se
recalculan en el navegador sin conexión a partir de los datos de detalle
incrustados (contratos y mascotas del modelo .pbix).

El emparejado visual se resuelve de raíz:
  * todo el DOM se construye ANTES de inicializar ECharts,
  * cada gráfico se redimensiona con ResizeObserver.

Uso:
    python3 dashboard_interactivo.py spec.json -o salida.html
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

TOOLKIT = Path(__file__).resolve().parent
ECHARTS_JS = TOOLKIT / "vendor" / "echarts.min.js"
ECHARTS_CDN = "https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"

PLANTILLA = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITULO__</title>
<style>
  :root {
    --fondo: #edf1f8; --tarjeta: #ffffff; --borde: #e2e8f2; --texto: #0f172a;
    --suave: #64748b; --acento: #2563eb;
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--fondo); color: var(--texto);
         font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
  header { padding: 26px 36px 0; }
  h1 { margin: 0 0 5px; font-size: 24px; letter-spacing: -0.02em; }
  .sub { color: var(--suave); margin: 0; font-size: 13.5px; }
  .meta { color: var(--suave); margin: 7px 0 0; font-size: 12px; }
  .barra { position: sticky; top: 0; z-index: 30; display: flex; gap: 12px;
           align-items: flex-end; flex-wrap: wrap; padding: 12px 36px;
           background: rgba(255,255,255,.92); backdrop-filter: blur(8px);
           border-bottom: 1px solid var(--borde); margin-top: 16px; }
  .filtro { display: flex; flex-direction: column; gap: 4px; }
  .filtro label { font-size: 10.5px; text-transform: uppercase; letter-spacing: .07em;
                  color: var(--suave); font-weight: 700; }
  .filtro select { appearance: none; border: 1px solid var(--borde); background-color: #fff;
                   border-radius: 9px; padding: 7px 30px 7px 11px; font-size: 13px;
                   color: var(--texto); min-width: 158px; cursor: pointer;
                   background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='6'><path d='M1 1l4 4 4-4' stroke='%2364748b' fill='none' stroke-width='1.6'/></svg>");
                   background-repeat: no-repeat; background-position: right 10px center; }
  .filtro select:focus { outline: 2px solid #bfd3f7; border-color: #9dbdf3; }
  button.limpiar { border: 1px solid var(--borde); background: #fff; border-radius: 9px;
                   padding: 8px 14px; font-size: 13px; cursor: pointer; color: var(--suave); }
  button.limpiar:hover { color: var(--texto); border-color: #c9d5e6; }
  .estado-filtros { margin-left: auto; font-size: 12.5px; color: var(--suave);
                    padding-bottom: 9px; white-space: nowrap; }
  main { padding: 4px 36px 42px; max-width: 1460px; margin: 0 auto; }
  .kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(196px, 1fr));
          gap: 12px; margin: 16px 0; }
  .kpi { background: var(--tarjeta); border: 1px solid var(--borde); border-radius: 14px;
         padding: 14px 16px; box-shadow: 0 1px 2px rgb(15 23 42 / .05); }
  .kpi .label { font-size: 10.5px; text-transform: uppercase; letter-spacing: .07em;
                color: var(--suave); font-weight: 700; margin-bottom: 6px; }
  .kpi .value { font-size: 26px; font-weight: 700; letter-spacing: -0.02em; }
  .kpi .hint { font-size: 12px; color: var(--suave); margin-top: 5px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(432px, 1fr));
          gap: 12px; }
  .panel { background: var(--tarjeta); border: 1px solid var(--borde); border-radius: 14px;
           padding: 14px 16px 6px; box-shadow: 0 1px 2px rgb(15 23 42 / .05);
           min-width: 0; overflow: hidden; }
  .panel.tabla { grid-column: 1 / -1; }
  .panel-title { font-size: 14px; font-weight: 600; margin: 0 0 6px; }
  .chart { width: 100%; height: 320px; }
  .panel.tabla table { width: 100%; border-collapse: collapse; font-size: 13px;
                       margin-bottom: 10px; }
  .panel.tabla th { text-align: left; color: var(--suave); font-weight: 700; font-size: 11px;
                    text-transform: uppercase; letter-spacing: .05em;
                    border-bottom: 2px solid var(--borde); padding: 7px 8px; }
  .panel.tabla td { border-bottom: 1px solid var(--borde); padding: 7px 8px;
                    font-variant-numeric: tabular-nums; }
  .panel.tabla tr:hover td { background: #f8fafc; }
  footer { text-align: center; color: var(--suave); font-size: 12px; padding: 0 0 30px; }
</style>
</head>
<body>
<header>
  <h1>__TITULO__</h1>
  <p class="sub">__SUBTITULO__</p>
  <p class="meta">__META__</p>
</header>

<div class="barra" id="barra-filtros"></div>

<main>
  <section class="kpis" id="kpis"></section>
  <section class="grid" id="graficos"></section>
</main>
<footer>Generado por pbix_toolkit · datos incrustados del modelo del .pbix · funciona sin conexión</footer>
__ECHARTS_TAG__
<script>
"use strict";
const SPEC = __SPEC__;
const DATOS = SPEC.datos;
const PALETA = ["#2563eb", "#f59e0b", "#10b981", "#8b5cf6", "#14b8a6", "#ef4444", "#f97316", "#64748b"];
const NF = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 2 });
const NF0 = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 0 });
const NFE = new Intl.NumberFormat("es-CO", { notation: "compact", maximumFractionDigits: 1 });
const estado = {};           // id de filtro -> valor seleccionado ("" = todos)
const grafs = [];            // {el, inst, spec}

function fmt(v, formato) {
  if (v === null || v === undefined || (typeof v === "number" && isNaN(v))) return "—";
  if (typeof v === "string") return v;
  if (formato === "money") return "$ " + NF.format(v);
  if (formato === "money0") return "$ " + NF0.format(v);
  if (formato === "int") return NF0.format(v);
  if (formato === "pct") return (v * 100).toFixed(1).replace(".", ",") + "%";
  if (formato === "compact") return "$ " + NFE.format(v);
  return NF.format(v);
}

/* --------------------------- filtrado --------------------------- */
function cumple(fila, filtro) {
  if (!filtro) return true;
  for (const campo in filtro) {
    let ok = false;
    for (const r of filtro[campo]) {
      const valor = String(fila[campo]);
      if (typeof r === "string" && r.charAt(0) === "!") { if (valor !== r.slice(1)) ok = true; }
      else if (valor === String(r)) ok = true;
    }
    if (!ok) return false;
  }
  return true;
}

function contratosFiltrados() {
  let cs = DATOS.contratos;
  if (estado.sucursal) cs = cs.filter(c => c.s === estado.sucursal);
  if (estado.familia) cs = cs.filter(c => c.fam === estado.familia);
  if (estado.tipo) cs = cs.filter(c => (c.tipos || []).indexOf(estado.tipo) >= 0);
  return cs;
}

function mascotasFiltradas(cs) {
  cs = cs || contratosFiltrados();
  const ids = {};
  cs.forEach(c => { ids[c.c] = true; });
  let ms = DATOS.mascotas.filter(m => ids[m.c]);
  if (estado.tipo) ms = ms.filter(m => m.t === estado.tipo);
  return ms;
}

/* --------------------------- agregación --------------------------- */
function agrupar(filas, dim, series) {
  const cats = [];
  const mapa = {};
  filas.forEach(f => { const k = f[dim]; if (!(k in mapa)) { mapa[k] = true; cats.push(k); } });
  const vals = series.map(s => {
    const acc = {};
    cats.forEach(k => { acc[k] = { n: 0, suma: 0 }; });
    filas.forEach(f => {
      const k = f[dim];
      if (!(k in acc)) return;
      if (!cumple(f, s.filtro)) return;
      acc[k].n += 1;
      if (s.medida) acc[k].suma += Number(f[s.medida]) || 0;
    });
    return cats.map(k => s.agg === "sum" ? acc[k].suma
                      : s.agg === "avg" ? (acc[k].n ? acc[k].suma / acc[k].n : 0)
                      : acc[k].n);
    });
  return { cats, vals };
}

/* --------------------------- KPIs --------------------------- */
function valorKPI(k) {
  const base = k.base === "mascotas" ? mascotasFiltradas() : contratosFiltrados();
  const filas = base.filter(f => cumple(f, k.filtro));
  if (k.agg === "sum") return filas.reduce((t, f) => t + (Number(f[k.medida]) || 0), 0);
  if (k.agg === "avg") return filas.length ? filas.reduce((t, f) => t + (Number(f[k.medida]) || 0), 0) / filas.length : 0;
  return filas.length;
}

function pistaKPI(k) {
  if (!k.pista) return "";
  if (k.pista === "auto:pctActivos") {
    const tot = valorKPI({ base: "contratos", agg: "count" });
    const act = valorKPI({ base: "contratos", agg: "count", filtro: { e: ["ACT"] } });
    return tot ? act + " de " + tot + " (" + Math.round(100 * act / tot) + "%)" : "sin contratos";
  }
  if (k.pista === "auto:perrosGatos") {
    const ms = mascotasFiltradas();
    const p = ms.filter(m => m.t === "PERRO").length;
    const g = ms.filter(m => m.t === "GATO").length;
    return p + " perros · " + g + " gatos";
  }
  if (k.pista === "auto:activos") {
    const f = contratosFiltrados().filter(c => cumple(c, k.filtro)).filter(c => c.e === "ACT").length;
    return f + " contratos activos";
  }
  return k.pista;
}

/* --------------------------- gráficos --------------------------- */
function colorDe(nombre, i) {
  const c = SPEC.colores || {};
  return c[nombre] || PALETA[i % PALETA.length];
}

function opcionGrafico(g, cs, ms) {
  const base = (g.series || []).some(s => s.base === "mascotas") ? ms : cs;
  const formatoSerie = (g.series.find(s => s.formato) || {}).formato || "int";
  const tooltip = { trigger: g.tipo === "dona" ? "item" : "axis",
                    valueFormatter: v => fmt(v, formatoSerie) };

  if (g.tipo === "dona") {
    const ag = agrupar(base, g.dim, g.series);
    let pares = ag.cats.map((c, i) => ({ name: c, value: ag.vals[0][i] }))
                      .filter(p => p.value > 0)
                      .sort((a, b) => b.value - a.value);
    return {
      color: pares.map((p, i) => colorDe(p.name, i)),
      tooltip: tooltip,
      legend: { bottom: 0, type: "scroll" },
      series: [{
        type: "pie", radius: ["46%", "70%"], center: ["50%", "45%"],
        itemStyle: { borderRadius: 6, borderColor: "#fff", borderWidth: 2 },
        label: { formatter: "{b}\\n{per|{d}%}", lineHeight: 17,
                 rich: { per: { color: "#64748b", fontSize: 11 } } },
        data: pares
      }]
    };
  }

  const ag = agrupar(base, g.dim, g.series);
  let orden = ag.cats.map((_, i) => i).sort((a, b) =>
      (ag.vals[0][b] - ag.vals[0][a]) || String(ag.cats[a]).localeCompare(String(ag.cats[b])));
  let cats = orden.map(i => ag.cats[i]);
  let vals = g.series.map((s, si) => orden.map(i => ag.vals[si][i]));
  if (g.limite) { cats = cats.slice(0, g.limite); vals = vals.map(v => v.slice(0, g.limite)); }

  const horizontal = g.tipo === "barras-h";
  const apilado = g.tipo === "barras-apiladas";
  const ejesValor = [{ type: "value", splitLine: { lineStyle: { color: "#eef2f7" } },
                       axisLabel: { hideOverlap: true,
                                    formatter: v => fmt(v, formatoSerie.indexOf("money") === 0 ? "compact" : "int") } }];
  const ejeCat = { type: "category", data: cats,
                   axisLabel: { interval: 0, rotate: horizontal ? 0 : (g.rotar || 0) },
                   axisTick: { show: false } };
  const series = g.series.map((s, si) => {
    const d = { name: s.nombre, type: "bar", data: vals[si], barMaxWidth: 30 };
    if (apilado) d.stack = "total";
    d.itemStyle = { borderRadius: horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0],
                    color: s.color || undefined };
    return d;
  });

  return {
    color: PALETA,
    tooltip: tooltip,
    legend: { bottom: 0, type: "scroll" },
    grid: { left: 6, right: 20, top: 14, bottom: 42, containLabel: true },
    xAxis: horizontal ? ejesValor : ejeCat,
    yAxis: horizontal ? Object.assign({ inverse: true }, ejeCat) : ejesValor,
    series: series
  };
}

/* --------------------------- tablas --------------------------- */
function renderTabla(t, cs, ms) {
  const panel = document.getElementById(t._id);
  const tabla = panel.querySelector("table");
  const claves = [];
  const vistos = {};
  cs.forEach(c => {
    const k = c[t.dim] + "\\u0001" + (t.dim2 ? c[t.dim2] : "");
    if (!(k in vistos)) { vistos[k] = true; claves.push([c[t.dim], t.dim2 ? c[t.dim2] : null]); }
  });
  const filas = claves.map(par => {
    const extra = {}; extra[t.dim] = [par[0]];
    if (t.dim2) extra[t.dim2] = [par[1]];
    const valores = {};
    const salida = t.columnas.map(col => {
      if (col.campo === "dim") return par[0];
      if (col.campo === "dim2") return par[1];
      const base = col.base === "mascotas" ? ms : cs;
      const f = Object.assign({}, col.filtro || {}, extra);
      const sub = base.filter(x => cumple(x, f));
      let v;
      if (col.agg === "sum") v = sub.reduce((tt, x) => tt + (Number(x[col.medida]) || 0), 0);
      else if (col.agg === "avg") v = sub.length ? sub.reduce((tt, x) => tt + (Number(x[col.medida]) || 0), 0) / sub.length : 0;
      else v = sub.length;
      if (col.id) valores[col.id] = v;
      return v;
    });
    return { par, salida, valores };
  });
  // cálculos especiales por fila (p. ej. % activos)
  filas.forEach(fila => {
    fila.salida = fila.salida.map((v, i) => {
      const col = t.columnas[i];
      if (col.calculo === "pctActivos") {
        const act = fila.valores.activos || 0, tot = fila.valores.total || 0;
        return tot ? act / tot : 0;
      }
      return v;
    });
  });
  filas.sort((a, b) => (b.valores.total || b.salida[1] || 0) - (a.valores.total || a.salida[1] || 0));
  const cuerpo = document.createElement("tbody");
  filas.forEach(fila => {
    const tr = document.createElement("tr");
    fila.salida.forEach((v, i) => {
      const td = document.createElement("td");
      td.textContent = (typeof v === "number" && t.columnas[i].formato)
        ? fmt(v, t.columnas[i].formato) : (v === null || v === undefined ? "—" : String(v));
      tr.appendChild(td);
    });
    cuerpo.appendChild(tr);
  });
  const viejo = tabla.querySelector("tbody");
  if (viejo) viejo.remove();
  tabla.appendChild(cuerpo);
}
</script>
__COMPORTAMIENTO__
</body>
</html>
"""


def renderizar(spec: dict | str | Path, salida: str | Path) -> Path:
    """Renderiza un spec v2 (dict o ruta JSON) a un HTML autocontenido."""
    if isinstance(spec, (str, Path)):
        spec = json.loads(Path(spec).read_text(encoding="utf-8"))

    titulo = spec.get("titulo", "Tablero")
    subtitulo = spec.get("subtitulo", "")
    meta = spec.get("meta", "Fuente: modelo tabular del .pbix")

    if ECHARTS_JS.exists():
        contenido = ECHARTS_JS.read_text(encoding="utf-8").replace("</script>", "<\\/script>")
        echarts_tag = f"<script>{contenido}</script>"
    else:
        echarts_tag = f'<script src="{ECHARTS_CDN}"></script>'

    html = (
        PLANTILLA.replace("__TITULO__", str(titulo))
        .replace("__SUBTITULO__", str(subtitulo))
        .replace("__META__", str(meta))
        .replace("__SPEC__", json.dumps(spec, ensure_ascii=False))
        .replace("__COMPORTAMIENTO__", COMPORTAMIENTO)
        .replace("__ECHARTS_TAG__", echarts_tag)
    )

    destino = Path(salida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(html, encoding="utf-8")
    return destino


COMPORTAMIENTO = """
<script>
"use strict";
/* --------------------------- construcción de la interfaz --------------------------- */
(function () {
  /* barra de filtros */
  const barra = document.getElementById("barra-filtros");
  (SPEC.filtros || []).forEach(function (f) {
    estado[f.id] = "";
    const caja = document.createElement("div"); caja.className = "filtro";
    const lab = document.createElement("label"); lab.textContent = f.etiqueta;
    const sel = document.createElement("select"); sel.id = "campos-" + f.id;
    const opTodos = document.createElement("option");
    opTodos.value = ""; opTodos.textContent = f.todos || "Todos";
    sel.appendChild(opTodos);
    (f.valores || []).forEach(function (v) {
      const op = document.createElement("option");
      op.value = v; op.textContent = (f.etiquetas && f.etiquetas[v]) || v;
      sel.appendChild(op);
    });
    sel.addEventListener("change", function () { estado[f.id] = sel.value; actualizar(); });
    caja.appendChild(lab); caja.appendChild(sel); barra.appendChild(caja);
  });
  /* filtros iniciales desde la URL (p. ej. ?sucursal=Cali%20Sur&tipo=PERRO) */
  try {
    const q = new URLSearchParams(window.location.search);
    (SPEC.filtros || []).forEach(function (f) {
      const v = q.get(f.id);
      if (v && (f.valores || []).indexOf(v) >= 0) {
        estado[f.id] = v;
        const sel = document.getElementById("campos-" + f.id);
        if (sel) sel.value = v;
      }
    });
  } catch (e) { /* URL sin filtros iniciales */ }
  const btn = document.createElement("button");
  btn.className = "limpiar"; btn.textContent = "Limpiar filtros";
  btn.addEventListener("click", function () {
    (SPEC.filtros || []).forEach(function (f) {
      estado[f.id] = "";
      const sel = document.getElementById("campos-" + f.id);
      if (sel) sel.value = "";
    });
    actualizar();
  });
  barra.appendChild(btn);
  const marca = document.createElement("div");
  marca.className = "estado-filtros"; marca.id = "estado-filtros";
  barra.appendChild(marca);

  /* KPIs */
  const contK = document.getElementById("kpis");
  (SPEC.kpis || []).forEach(function (k, i) {
    const div = document.createElement("div"); div.className = "kpi";
    const l = document.createElement("div"); l.className = "label"; l.textContent = k.etiqueta;
    const v = document.createElement("div"); v.className = "value"; v.id = "kpi-v-" + i;
    const h = document.createElement("div"); h.className = "hint"; h.id = "kpi-h-" + i;
    div.appendChild(l); div.appendChild(v); div.appendChild(h);
    contK.appendChild(div);
  });

  /* Gráficos y tablas: TODO el DOM primero, sin inicializar ECharts todavía */
  const contG = document.getElementById("graficos");
  (SPEC.graficos || []).forEach(function (g, i) {
    const panel = document.createElement("div");
    if (g.tipo === "tabla") {
      panel.className = "panel tabla";
      panel.id = "panel-" + i;
      const t = document.createElement("p"); t.className = "panel-title"; t.textContent = g.titulo;
      const tabla = document.createElement("table");
      const thead = document.createElement("thead"); const trh = document.createElement("tr");
      (g.columnas || []).forEach(function (col) {
        const th = document.createElement("th"); th.textContent = col.titulo; trh.appendChild(th);
      });
      thead.appendChild(trh); tabla.appendChild(thead);
      panel.appendChild(t); panel.appendChild(tabla);
      contG.appendChild(panel);
      g._tipoDOM = "tabla"; g._id = panel.id;
    } else {
      panel.className = "panel";
      const t = document.createElement("p"); t.className = "panel-title"; t.textContent = g.titulo;
      const div = document.createElement("div"); div.className = "chart"; div.id = "graf-" + i;
      panel.appendChild(t); panel.appendChild(div);
      contG.appendChild(panel);
      g._tipoDOM = "chart"; g._ids = div.id;
    }
  });

  /* recién ahora se inicializan los gráficos (el grid ya tiene su tamaño final) */
  requestAnimationFrame(function () {
    (SPEC.graficos || []).forEach(function (g, i) {
      if (g._tipoDOM !== "chart") return;
      const el = document.getElementById("graf-" + i);
      const inst = echarts.init(el);
      grafs.push({ el: el, inst: inst, spec: g });
      if (window.ResizeObserver) {
        new ResizeObserver(function () { inst.resize(); }).observe(el);
      }
    });
    window.addEventListener("resize", function () { grafs.forEach(function (gr) { gr.inst.resize(); }); });
    actualizar();
  });

  function actualizar() {
    const cs = contratosFiltrados();
    const ms = mascotasFiltradas(cs);
    document.getElementById("estado-filtros").textContent =
      cs.length + " contratos · " + ms.length + " mascotas";
    (SPEC.kpis || []).forEach(function (k, i) {
      document.getElementById("kpi-v-" + i).textContent = fmt(valorKPI(k), k.formato);
      const p = document.getElementById("kpi-h-" + i);
      const texto = pistaKPI(k);
      p.textContent = texto || "";
      p.style.display = texto ? "" : "none";
    });
    grafs.forEach(function (gr) {
      gr.inst.setOption(opcionGrafico(gr.spec, cs, ms), true);
    });
    (SPEC.graficos || []).forEach(function (g) {
      if (g._tipoDOM === "tabla") renderTabla(g, cs, ms);
    });
  }
})();
</script>
"""


def main() -> None:
    p = argparse.ArgumentParser(description="Spec v2 JSON -> tablero HTML interactivo")
    p.add_argument("spec", help="Ruta del spec JSON")
    p.add_argument("-o", "--salida", required=True, help="Ruta del HTML de salida")
    args = p.parse_args()
    destino = renderizar(args.spec, args.salida)
    print(f"Tablero generado: {destino}")


if __name__ == "__main__":
    main()
