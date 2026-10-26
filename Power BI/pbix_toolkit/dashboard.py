#!/usr/bin/env python3
"""Generador de dashboards HTML autocontenidos a partir de un spec JSON.

El spec describe KPIs, gráficos y tablas ya "hidratados" con datos
(obtenidos de las consultas DAX vía query.py). El HTML resultante
incluye ECharts embebido: funciona sin internet y sin dependencias.

Uso:
    python3 dashboard.py spec.json -o salida.html
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TOOLKIT = Path(__file__).resolve().parent
ECHARTS_JS = TOOLKIT / "vendor" / "echarts.min.js"
ECHARTS_CDN = "https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"

PLANTILLA = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITULO__ · pbix_toolkit</title>
<style>
  :root {
    --fondo: #f1f5f9; --tarjeta: #ffffff; --borde: #e2e8f0;
    --texto: #0f172a; --suave: #64748b; --acento: #2563eb;
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--fondo); color: var(--texto);
         font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
  header { padding: 28px 32px 8px; }
  h1 { margin: 0 0 4px; font-size: 26px; letter-spacing: -0.02em; }
  .sub { color: var(--suave); margin: 0 0 6px; font-size: 14px; }
  .meta { color: var(--suave); font-size: 12px; margin: 0; }
  main { padding: 16px 32px 40px; max-width: 1400px; margin: 0 auto; }
  .kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
          gap: 14px; margin-bottom: 18px; }
  .kpi { background: var(--tarjeta); border: 1px solid var(--borde); border-radius: 12px;
         padding: 16px 18px; box-shadow: 0 1px 2px rgb(15 23 42 / .04); }
  .kpi .label { font-size: 12px; text-transform: uppercase; letter-spacing: .06em;
                color: var(--suave); margin-bottom: 6px; }
  .kpi .value { font-size: 26px; font-weight: 700; letter-spacing: -0.02em; }
  .kpi .hint { font-size: 12px; color: var(--suave); margin-top: 4px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(430px, 1fr));
          gap: 14px; }
  .panel { background: var(--tarjeta); border: 1px solid var(--borde); border-radius: 12px;
           padding: 14px 16px 8px; box-shadow: 0 1px 2px rgb(15 23 42 / .04); }
  .panel.tabla { grid-column: 1 / -1; }
  .panel-title { font-size: 14px; font-weight: 600; margin: 0 0 8px; }
  .chart { width: 100%; height: 340px; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 10px; }
  th { text-align: left; color: var(--suave); font-weight: 600; font-size: 12px;
       text-transform: uppercase; letter-spacing: .05em;
       border-bottom: 2px solid var(--borde); padding: 6px 8px; }
  td { border-bottom: 1px solid var(--borde); padding: 6px 8px; font-variant-numeric: tabular-nums; }
  tr:hover td { background: #f8fafc; }
  footer { text-align: center; color: var(--suave); font-size: 12px; padding: 0 0 28px; }
</style>
</head>
<body>
<header>
  <h1>__TITULO__</h1>
  <p class="sub">__SUBTITULO__</p>
  <p class="meta">__META__</p>
</header>
<main>
  <section class="kpis" id="kpis"></section>
  <section class="grid" id="graficos"></section>
</main>
<footer>Generado por pbix_toolkit · datos en vivo del modelo del .pbix · ECharts embebido</footer>
__ECHARTS_TAG__
<script>
"use strict";
const SPEC = __SPEC__;
const PALETA = ["#2563eb", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6", "#14b8a6", "#f97316", "#64748b"];
const NF = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 2 });
const NFE = new Intl.NumberFormat("es-CO", { notation: "compact", maximumFractionDigits: 1 });

function fmtNum(v, fmt) {
  if (v === null || v === undefined) return "—";
  if (typeof v === "string") return v;
  if (fmt === "money") return "$ " + NF.format(v);
  if (fmt === "int") return NF.format(Math.round(v));
  if (fmt === "compact") return "$ " + NFE.format(v);
  return NF.format(v);
}

/* ---------- KPIs ---------- */
const contKpi = document.getElementById("kpis");
(SPEC.kpis || []).forEach(function (k) {
  const div = document.createElement("div");
  div.className = "kpi";
  const l = document.createElement("div"); l.className = "label"; l.textContent = k.label || "";
  const v = document.createElement("div"); v.className = "value"; v.textContent = fmtNum(k.value, k.format);
  div.appendChild(l); div.appendChild(v);
  if (k.hint) { const h = document.createElement("div"); h.className = "hint"; h.textContent = k.hint; div.appendChild(h); }
  contKpi.appendChild(div);
});

/* ---------- Gráficos ---------- */
const contChart = document.getElementById("graficos");
const instancias = [];
const pendientes = [];
(SPEC.charts || []).forEach(function (c, idx) {
  if (c.type === "table") { contChart.appendChild(tablaHTML(c)); return; }
  const panel = document.createElement("div"); panel.className = "panel";
  const titulo = document.createElement("p"); titulo.className = "panel-title"; titulo.textContent = c.title || "";
  const div = document.createElement("div"); div.className = "chart"; div.id = "ch-" + idx;
  panel.appendChild(titulo); panel.appendChild(div); contChart.appendChild(panel);

  let option = {
    color: PALETA,
    tooltip: { trigger: c.type === "pie" ? "item" : "axis",
               valueFormatter: function (v) { return fmtNum(v, c.format); } },
    legend: { bottom: 0, type: "scroll" },
    grid: { left: 10, right: 18, top: 32, bottom: 44, containLabel: true },
  };

  if (c.type === "pie") {
    option.series = [{
      type: "pie",
      radius: c.donut ? ["42%", "68%"] : "62%",
      center: ["50%", "46%"],
      itemStyle: { borderRadius: 6, borderColor: "#fff", borderWidth: 2 },
      label: { formatter: "{b}\\n{per|{d}%}", lineHeight: 18,
               rich: { per: { color: "#64748b", fontSize: 11 } } },
      data: c.data || [],
    }];
  } else {
    const horizontal = !!c.horizontal;
    const conDer = (c.series || []).some(function (s) { return s.axis === "right"; });
    const ejes = [{ type: "value", splitLine: { lineStyle: { color: "#eef2f7" } } }];
    if (conDer) ejes.push({ type: "value", position: "right", splitLine: { show: false } });
    const cat = { type: "category", data: c.categories || [],
                  axisLabel: { interval: 0, rotate: horizontal ? 0 : (c.rotate || 0) },
                  axisTick: { show: false } };
    option.xAxis = horizontal ? ejes : cat;
    option.yAxis = horizontal ? cat : ejes;
    option.series = (c.series || []).map(function (s, i) {
      const base = { name: s.name, type: c.type === "line" ? "line" : "bar", data: s.data || [] };
      if (c.type === "line") { base.smooth = true; base.symbolSize = 7; }
      if (s.stack) base.stack = s.stack === true ? "total" : s.stack;
      if (horizontal) { if (s.axis === "right") base.xAxisIndex = 1; }
      else if (s.axis === "right") base.yAxisIndex = 1;
      if (c.type === "bar") base.barMaxWidth = 34;
      base.itemStyle = { borderRadius: horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0] };
      return base;
    });
  }

  pendientes.push({ div: div, option: option });
});

/* Inicializar recién cuando TODAS las tarjetas existen en el documento: así
   cada gráfico mide el ancho definitivo de su tarjeta y no un ancho transitorio
   (causa de lienzos desbordados cuando se inicializaba dentro del bucle). */
requestAnimationFrame(function () {
  pendientes.forEach(function (p) {
    const graf = echarts.init(p.div);
    graf.setOption(p.option);
    instancias.push(graf);
    if (window.ResizeObserver) {
      new ResizeObserver(function () { graf.resize(); }).observe(p.div);
    }
  });
});

function tablaHTML(c) {
  const panel = document.createElement("div"); panel.className = "panel tabla";
  const titulo = document.createElement("p"); titulo.className = "panel-title"; titulo.textContent = c.title || "";
  panel.appendChild(titulo);
  const t = document.createElement("table");
  const thead = document.createElement("thead"); const trh = document.createElement("tr");
  (c.columns || []).forEach(function (col) { const th = document.createElement("th"); th.textContent = col; trh.appendChild(th); });
  thead.appendChild(trh); t.appendChild(thead);
  const tbody = document.createElement("tbody");
  (c.rows || []).forEach(function (fila) {
    const tr = document.createElement("tr");
    fila.forEach(function (celda, i) {
      const td = document.createElement("td");
      td.textContent = (c.formats && c.formats[i]) ? fmtNum(celda, c.formats[i]) : fmtNum(celda, c.format);
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  t.appendChild(tbody); panel.appendChild(t);
  return panel;
}

window.addEventListener("resize", function () { instancias.forEach(function (g) { g.resize(); }); });
</script>
</body>
</html>
"""


def renderizar(spec: dict | str | Path, salida: str | Path) -> Path:
    """Renderiza un spec (dict o ruta JSON) a un HTML autocontenido."""
    if isinstance(spec, (str, Path)):
        spec = json.loads(Path(spec).read_text(encoding="utf-8"))

    titulo = spec.get("title", "Dashboard")
    subtitulo = spec.get("subtitle", "")
    meta = spec.get("meta", "Fuente: modelo tabular del archivo .pbix (Power BI Desktop)")

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
        .replace("__ECHARTS_TAG__", echarts_tag)
    )

    destino = Path(salida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(html, encoding="utf-8")
    return destino


def main() -> None:
    p = argparse.ArgumentParser(description="Spec JSON -> dashboard HTML autocontenido")
    p.add_argument("spec", help="Ruta del spec JSON")
    p.add_argument("-o", "--salida", required=True, help="Ruta del HTML de salida")
    args = p.parse_args()

    destino = renderizar(args.spec, args.salida)
    print(f"Dashboard generado: {destino}")


if __name__ == "__main__":
    main()
