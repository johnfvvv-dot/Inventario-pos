# pbix_toolkit — Consultas y dashboards automáticos para .pbix

Toolkit para cargar el modelo de datos de un archivo **.pbix** (Power BI Desktop),
exponer su esquema (tablas, columnas, medidas y relaciones) y responder a prompts
generando **dashboards HTML** con datos reales del modelo.

El archivo original **nunca se modifica**: se abre sobre una copia en `runtime/`.

---

## Arquitectura

```
                       Windows                                          WSL (Linux)
┌─────────────────────────────────────────────┐        ┌──────────────────────────────────┐
│  Power BI Desktop (copia del .pbix)         │        │  query.py   (puente/CLI)         │
│      └─ msmdsrv.exe  ── puerto local ─────┐ │        │  dashboard.py (spec -> HTML)     │
│                                           │ │        │  demos/generar_dashboards.py     │
│  engine.py ── ADOMD (.NET) ───────────────┘ │  ◄──── │                                  │
│    · open / status / close                  │        │  Dashboards HTML con ECharts     │
│    · schema  -> runtime/schema.json         │        │  embebido (sin internet)         │
│    · query   -> JSON (DAX/DMV/MDX)          │        │                                  │
└─────────────────────────────────────────────┘        └──────────────────────────────────┘
```

- **engine.py** (corre con el Python de Windows): lanza Power BI Desktop con una copia
  del .pbix, localiza el puerto del motor tabular local, se conecta vía ADOMD
  (`Microsoft.PowerBI.AdomdClient.dll`, incluida en Power BI Desktop) y expone
  comandos. El esquema viene de las DMV `$SYSTEM.TMSCHEMA_*` y las consultas de DAX.
- **query.py** (puente WSL→Windows): ejecuta el engine y devuelve JSON o una
  tabla legible en consola.
- **dashboard.py**: convierte un *spec* JSON (KPIs, gráficos, tablas) en un HTML
  autocontenido con ECharts embebido.
- **demos/generar_dashboards.py**: muestra la tubería completa
  *prompt → DAX → spec → dashboard HTML*.

## Requisitos (ya verificados en esta máquina)

| Componente | Estado |
|---|---|
| Power BI Desktop (`C:\Program Files\Microsoft Power BI Desktop`) | ✓ instalado |
| Python 3.13 en Windows con `pandas`, `pyadomd`, `pythonnet` | ✓ instalado |
| Python 3 en WSL (para los puentes y dashboards) | ✓ |

## Uso rápido

Todos los comandos se ejecutan desde esta carpeta
(`C:\Users\XR-18\Desktop\Python\Power BI\pbix_toolkit` o su ruta `/mnt/c/...` en WSL).

```bash
# 1. Abrir el modelo (lanza Power BI Desktop sobre una copia segura)
python3 query.py open "C:\Users\XR-18\Desktop\Python\Power BI\Visión Ejecutiva - Portafolio de Mascotas1.pbix"
#    → en WSL, si la ruta con acentos diera problemas, usa la ruta /mnt/c/... completa

# 2. Estado de la sesión
python3 query.py status

# 3. Esquema del modelo (tablas, columnas, medidas, relaciones)
python3 query.py schema --summary          # resumen de texto
python3 query.py schema                    # JSON completo (cacheado en runtime/schema.json)
python3 query.py schema --refresh          # forzar reconstrucción

# 4. Consultas DAX (devuelve JSON)
python3 query.py query "EVALUATE 'Cttes'" --table
cat consulta.dax | python3 query.py query --table     # también admite stdin/--file

# 5. Dashboards de ejemplo (prompts ya resueltos)
python3 demos/generar_dashboards.py
#    → dashboards/tablero_kpis_sucursal.html
#    → dashboards/tablero_planes_petamigo_petfiel.html

# 6. Cerrar (cierra el Power BI Desktop lanzado por el toolkit)
python3 query.py close
```

Abrir un dashboard en el navegador desde WSL:

```bash
explorer.exe "C:\Users\XR-18\Desktop\Python\Power BI\pbix_toolkit\dashboards\tablero_kpis_sucursal.html"
```

## Prompts soportados

El flujo es: **prompt → (agente/LLM) consultas DAX → spec JSON → dashboard HTML**.
Ejemplos ya resueltos en `demos/generar_dashboards.py`:

- *"Genera un tablero de KPIs de ventas por región"* → KPIs por sucursal
  (contratos, activos, prima mensual activa, mascotas) + gráficos.
- *"Muestra la distribución de planes Petamigo vs Petfiel"* → KPIs por familia,
  donuts de contratos/mascotas y detalle por plan.

Para crear un tablero nuevo: escribe un spec (mira
`dashboards/spec_kpis_sucursal.json` como plantilla) y renderízalo:

```bash
python3 dashboard.py dashboards/mi_spec.json -o dashboards/mi_tablero.html
```

Formato del spec:

```json
{
  "title": "…", "subtitle": "…", "meta": "…",
  "kpis": [ {"label": "Contratos", "value": 30, "format": "int|money|compact|text", "hint": "…"} ],
  "charts": [
    {"type": "bar", "horizontal": true, "title": "…", "categories": ["…"], "series": [{"name": "…", "data": [1]}]},
    {"type": "line", "…": "igual que bar"},
    {"type": "pie", "donut": true, "title": "…", "data": [{"name": "…", "value": 1}]},
    {"type": "table", "title": "…", "columns": ["…"], "formats": ["int", "money", null], "rows": [[1, 2, "x"]]}
  ]
}
```

## Modelo actual (V1.0)

- **Cttes** (30 filas): contratos. Columnas clave: `Numero Contrato`, `Nombre Plan`,
  `Codigo plan`, `Sucursal`, `Estado del Contrato`, `Valor Mensual`, `Proteccion`,
  `Fecha creacion SAP`, `Nombre Convenio`, `Mobile Phone`, `E-Mail`.
- **Beneficiarios** (57 filas): mascotas. `DocEntry`, `Nombre Beneficiario`,
  `Tipo de Beneficiario` (PERRO/GATO), `Parentesco`, `Edad`, `Valor Mensual` (prima
  asignada), `Sucursal`, `Proteccion`…
- **Estados** (11 filas): catálogo `Estado del Contrato` → `Nombre` / `Tipificacion`.
- Relaciones activas (integridad preservada del original):
  - `Beneficiarios[DocEntry] → Cttes[Doc entry actual]` (Muchos→Uno)
  - `Cttes[Estado del Contrato] → Estados[Estado del Contrato]` (Muchos→Uno)
  - `Cttes[Fecha creacion SAP] → tabla de fechas automática` (Muchos→Uno)
- **No hay medidas definidas en el modelo**; los KPIs se calculan con DAX en las
  consultas (p. ej. `CALCULATE(SUM('Cttes'[Valor Mensual]), 'Cttes'[Estado del Contrato] = "ACT")`).
  Tip: usa `COALESCE(…, 0)` para evitar `BLANK`.

## Seguridad y buenas prácticas

- **Original intacto**: `open` copia el .pbix a `runtime/model.pbix` y abre la copia;
  el toolkit nunca guarda cambios.
- La copia se refresca al detectar cambios en el original (`status`/`open` lo
  reportan como `staleSource`: cierra y vuelve a abrir).
- El motor local escucha solo en `localhost`; la conexión es ADOMD local (sin nube).

## Solución de problemas

| Síntoma | Acción |
|---|---|
| `No hay sesión abierta` | `python3 query.py open "<ruta.pbix>"` |
| `close` no cierra | Espera: hace `taskkill /T` y escala a `/F` a los 15 s |
| Power BI Desktop tarda la primera vez | Normal (30–120 s); el timeout por defecto es 240 s |
| Error de ruta por acentos | Usa la ruta absoluta `/mnt/c/Users/...` dentro de WSL |
| El modelo no responde tras suspender el PC | `python3 query.py close` y vuelve a `open` |

## Estructura

```
pbix_toolkit/
├─ engine.py            # motor (Windows): open/status/close/schema/query
├─ adomd.py             # wrapper ADOMD (.NET via pythonnet)
├─ model_schema.py      # esquema desde DMVs ($SYSTEM.TMSCHEMA_*)
├─ query.py             # puente WSL -> Windows (CLI)
├─ dashboard.py         # spec JSON -> HTML autocontenido (ECharts embebido)
├─ demos/
│  └─ generar_dashboards.py
├─ dashboards/          # HTML generados + specs
├─ vendor/echarts.min.js
├─ runtime/             # copia de trabajo, state.json, schema.json
└─ dev/                 # scripts de exploración/diagnóstico
```

## Hoja de ruta

- Integrar el endpoint `/generate_dashboard` del `server.py` (FastAPI) con
  `query.py` para servir dashboards vía API REST.
- Soporte multi-archivo .pbix (sesiones por archivo).
- Plantillas de prompts predefinidas (ventas, cartera, siniestralidad).
