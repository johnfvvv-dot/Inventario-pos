/** Pantalla de Reportes - Administrador. Gráficos + exportación CSV. */

import { useEffect, useMemo, useState } from "react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";
import { Bar, Line, Doughnut } from "react-chartjs-2";
import { api } from "../services/api";
import {
  fechaParaArchivo,
  formatearFechaHora,
  formatearNumero,
  formatearPrecio,
} from "../utils/format";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

interface Producto {
  id: number;
  nombre: string;
  precio: number;
  stock: number;
}

interface TotalPorForma {
  etiqueta: string;
  valor: number;
  color: string;
}

interface Totales {
  efectivo: number;
  tarjeta: number;
  transferencia: number;
  total: number;
  operaciones: number;
}

interface Turno {
  id: number;
  usuario_nombre: string;
  fecha_apertura: string;
  fecha_cierre: string | null;
  estado: string;
  totales: Totales;
  ganancia: number;
}

type Rango = "dia" | "turno_ayer" | "semana" | "mes";

/** Origen del filtro activo. Los filtros son mutuamente excluyentes. */
type Modo = "rango" | "mes" | "fecha";

interface FiltroReporte {
  desde: string;
  hasta: string;
  etiqueta: string;
  /** true cuando el filtro no puede consultar datos (ej. no hay turno ayer). */
  vacio?: boolean;
}

const RANGOS: Record<Rango, { dias: number; etiqueta: string }> = {
  dia: { dias: 1, etiqueta: "hoy" },
  turno_ayer: { dias: 1, etiqueta: "turno de ayer" },
  semana: { dias: 7, etiqueta: "últimos 7 días" },
  mes: { dias: 30, etiqueta: "últimos 30 días" },
};

const MESES = [
  "enero",
  "febrero",
  "marzo",
  "abril",
  "mayo",
  "junio",
  "julio",
  "agosto",
  "septiembre",
  "octubre",
  "noviembre",
  "diciembre",
];

const dosDigitos = (n: number) => String(n).padStart(2, "0");

const capitalizar = (texto: string) =>
  texto.charAt(0).toUpperCase() + texto.slice(1);

/** Fecha local en ISO sin zona (la que espera el backend). */
const isoLocal = (d: Date, finDelDia = false) =>
  `${d.getFullYear()}-${dosDigitos(d.getMonth() + 1)}-${dosDigitos(
    d.getDate()
  )}T${finDelDia ? "23:59:59.999999" : "00:00:00"}`;

const isoAhora = () => {
  const d = new Date();
  // Incluye milisegundos: si una venta se cierra en el mismo segundo en que
  // se carga Reportes, truncar a segundos dejaría la venta fuera del rango.
  return `${d.getFullYear()}-${dosDigitos(d.getMonth() + 1)}-${dosDigitos(
    d.getDate()
  )}T${dosDigitos(d.getHours())}:${dosDigitos(d.getMinutes())}:${dosDigitos(
    d.getSeconds()
  )}.${String(d.getMilliseconds()).padStart(3, "0")}`;
};

/** Rango del período seleccionado (día / semana / mes). */
const rangoActual = (rango: Rango) => {
  const ahora = new Date();
  const inicio = new Date(ahora.getFullYear(), ahora.getMonth(), ahora.getDate());
  inicio.setDate(inicio.getDate() - (RANGOS[rango].dias - 1));
  return { desde: isoLocal(inicio), hasta: isoAhora() };
};

export default function ReportesPage() {
  const [productos, setProductos] = useState<Producto[]>([]);
  const [totalProductos, setTotalProductos] = useState(0);
  const [stockTotal, setStockTotal] = useState(0);
  const [totales, setTotales] = useState<Totales | null>(null);
  const [ganancia, setGanancia] = useState(0);
  const [serie, setSerie] = useState<any>(null);
  const [anios, setAnios] = useState<number[]>([]);
  const [turnoAyer, setTurnoAyer] = useState<Turno | null>(null);

  // Filtros. Por defecto: Semana (7 días).
  const [modo, setModo] = useState<Modo>("rango");
  const [rango, setRango] = useState<Rango>("semana");
  const [mesTexto, setMesTexto] = useState("");
  const [anioTexto, setAnioTexto] = useState("");
  const [fechaTexto, setFechaTexto] = useState("");

  const [recarga, setRecarga] = useState(0);
  const [exportando, setExportando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Inventario independiente de los filtros de tiempo: Productos y Stock
  // total muestran siempre el estado completo y actual del inventario.
  useEffect(() => {
    let vigente = true;

    const cargarInventario = async () => {
      try {
        // Solo se carga el inventario que muestran los KPIs y la tabla.
        // El detalle de pedidos para el CSV se consulta al exportar.
        const inv: any = await api.getProductos({ limite: 500 });
        if (!vigente) return;

        setProductos(inv.items);
        setTotalProductos(
          typeof inv.total === "number" ? inv.total : inv.items.length
        );
        setStockTotal(
          typeof inv.stock_total === "number"
            ? inv.stock_total
            : inv.items.reduce(
                (suma: number, p: Producto) => suma + p.stock,
                0
              )
        );
        setError(null);
      } catch (err: any) {
        if (vigente) setError(err.message);
      }
    };

    cargarInventario();
    return () => {
      vigente = false;
    };
  }, [recarga]);

  // Años con ventas (opciones del listado de año) y turno de ayer.
  useEffect(() => {
    let vigente = true;

    const cargarCatalogos = async () => {
      try {
        const [listaAnios, datosTurnoAyer]: any = await Promise.all([
          api.getAniosVentas(),
          api.getTurnoAyer(),
        ]);
        if (!vigente) return;
        setAnios(Array.isArray(listaAnios) ? listaAnios : []);
        setTurnoAyer(datosTurnoAyer ?? null);
      } catch (err: any) {
        if (vigente) setError(err.message);
      }
    };

    cargarCatalogos();
    return () => {
      vigente = false;
    };
  }, [recarga]);

  // Si hay un mes elegido sin año, refleja el año más reciente con ventas
  // (por ejemplo cuando las opciones de año terminan de cargar).
  useEffect(() => {
    if (modo === "mes" && mesTexto && !anioTexto && anios.length) {
      setAnioTexto(String(anios[0]));
    }
  }, [modo, mesTexto, anioTexto, anios]);

  const mesNumero = mesTexto ? Number(mesTexto) : null;
  const anioSeleccionado = anioTexto ? Number(anioTexto) : null;

  // Rango efectivo según el filtro activo (mes/año, fecha o rango rápido).
  const filtro: FiltroReporte = useMemo(() => {
    if (modo === "mes") {
      if (mesNumero !== null || anioSeleccionado !== null) {
        // Sin año explícito se usa el año más reciente con ventas.
        const anio = anioSeleccionado ?? anios[0] ?? new Date().getFullYear();

        // Solo año: todo el año calendario.
        if (mesNumero === null) {
          return {
            desde: `${anio}-01-01T00:00:00`,
            hasta: `${anio}-12-31T23:59:59.999999`,
            etiqueta: `Año ${anio}`,
          };
        }

        // Mes + año: mes calendario completo.
        const inicio = new Date(anio, mesNumero - 1, 1);
        const fin = new Date(anio, mesNumero, 0);
        return {
          desde: isoLocal(inicio),
          hasta: isoLocal(fin, true),
          etiqueta: `${capitalizar(MESES[mesNumero - 1])} de ${anio}`,
        };
      }
    }

    if (modo === "fecha" && fechaTexto) {
      const [anio, mes, dia] = fechaTexto.split("-").map(Number);
      if (anio && mes && dia) {
        const fecha = new Date(anio, mes - 1, dia);
        return {
          desde: isoLocal(fecha),
          hasta: isoLocal(fecha, true),
          etiqueta: `Día ${dosDigitos(dia)}/${dosDigitos(mes)}/${anio}`,
        };
      }
    }

    if (modo === "rango" && rango === "turno_ayer") {
      if (turnoAyer) {
        return {
          desde: turnoAyer.fecha_apertura.slice(0, 19),
          hasta: turnoAyer.fecha_cierre
            ? turnoAyer.fecha_cierre.slice(0, 19)
            : isoAhora(),
          etiqueta: `Turno de ayer #${turnoAyer.id}`,
        };
      }
      return {
        desde: "",
        hasta: "",
        etiqueta: "sin turno ayer",
        vacio: true,
      };
    }

    // Filtro por defecto (u otro rango rápido). `recarga` refresca "hasta".
    return { ...rangoActual(rango), etiqueta: RANGOS[rango].etiqueta };
  }, [
    modo,
    rango,
    mesNumero,
    anioSeleccionado,
    anios,
    fechaTexto,
    turnoAyer,
    recarga,
  ]);

  // Reporte de ventas/ganancias: depende del filtro activo.
  useEffect(() => {
    let vigente = true;

    if (filtro.vacio) {
      setTotales(null);
      setGanancia(0);
      setSerie({ etiquetas: [], serie: [], top_productos: [] });
      setError(null);
      return () => {
        vigente = false;
      };
    }

    const cargarReporte = async () => {
      try {
        const [res, dia]: any = await Promise.all([
          api.getResumenCaja(1, 0, filtro.desde, filtro.hasta),
          api.getVentasPorDia(1, 0, filtro.desde, filtro.hasta),
        ]);
        if (!vigente) return;

        setTotales(res.totales);
        setGanancia(Number(res.ganancia) || 0);
        setSerie(dia);
        setError(null);
      } catch (err: any) {
        if (vigente) setError(err.message);
      }
    };

    cargarReporte();
    return () => {
      vigente = false;
    };
  }, [filtro.desde, filtro.hasta, filtro.vacio, recarga]);

  const cambiarMes = (valor: string) => {
    setMesTexto(valor);
    setFechaTexto("");
    if (!valor && !anioTexto) {
      setModo("rango");
      setRango("semana");
    } else {
      setModo("mes");
      // Si elige un mes sin año, se usa el año más reciente con ventas.
      if (valor && !anioTexto && anios[0]) {
        setAnioTexto(String(anios[0]));
      }
    }
  };

  const cambiarAnio = (valor: string) => {
    setAnioTexto(valor);
    setFechaTexto("");
    if (!valor) {
      // Sin año no hay filtro por mes: se vuelve al rango por defecto.
      setMesTexto("");
      setModo("rango");
      setRango("semana");
    } else {
      setModo("mes");
    }
  };

  const cambiarFecha = (valor: string) => {
    setFechaTexto(valor);
    setMesTexto("");
    setAnioTexto("");
    if (!valor) {
      setModo("rango");
      setRango("semana");
    } else {
      setModo("fecha");
    }
  };

  const cambiarFiltro = (valor: string) => {
    if (valor === "personalizado") return;
    setRango(valor as Rango);
    setModo("rango");
    setMesTexto("");
    setAnioTexto("");
    setFechaTexto("");
  };

  /** Restablece el filtro por defecto: Semana (7 días). */
  const quitarFiltros = () => {
    setModo("rango");
    setRango("semana");
    setMesTexto("");
    setAnioTexto("");
    setFechaTexto("");
  };

  // --- Datos derivados ---
  const topProductos = useMemo(() => {
    if (!serie?.top_productos?.length) return [];
    return serie.top_productos;
  }, [serie]);

  const ventasPorDia = useMemo(() => {
    if (!serie) return { etiquetas: [], series: [] };
    return {
      etiquetas: serie.etiquetas.map((e: string) => e.slice(5)), // solo mes-día
      series: [
        {
          label: "Ventas",
          data: serie.serie.map((s: any) => s.total),
          borderColor: "#3498db",
          backgroundColor: "rgba(52,152,219,0.15)",
          fill: true,
          tension: 0.3,
        },
      ],
    };
  }, [serie]);

  const gananciasPorDia = useMemo(() => {
    if (!serie) return { etiquetas: [], series: [] };
    return {
      etiquetas: serie.etiquetas.map((e: string) => e.slice(5)),
      series: [
        {
          label: "Ganancia",
          data: serie.serie.map((s: any) => s.ganancia || 0),
          borderColor: "#27ae60",
          backgroundColor: "rgba(39,174,96,0.15)",
          fill: true,
          tension: 0.3,
        },
      ],
    };
  }, [serie]);

  const formasPago = useMemo(() => {
    if (!totales) {
      return { etiquetas: [], datos: [], colores: [] };
    }

    // Etiqueta y valor se filtran juntos: si una forma de pago está en cero
    // no debe desplazar las etiquetas de las demás en la gráfica.
    const pares: TotalPorForma[] = [
      { etiqueta: "Efectivo", valor: totales.efectivo, color: "#27ae60" },
      { etiqueta: "Tarjeta", valor: totales.tarjeta, color: "#3498db" },
      {
        etiqueta: "Transferencia",
        valor: totales.transferencia,
        color: "#f39c12",
      },
    ].filter((p) => p.valor > 0);

    return {
      etiquetas: pares.map((p) => p.etiqueta),
      datos: pares.map((p) => p.valor),
      colores: pares.map((p) => p.color),
    };
  }, [totales]);

  const opcionesGrafico = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: true },
      tooltip: {
        callbacks: {
          label: (ctx: any) =>
            `${ctx.dataset.label}: ${formatearPrecio(ctx.parsed.y)}`,
        },
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          callback: (valor: any) => formatearNumero(Number(valor)),
        },
      },
    },
  };

  // --- Exportar CSV ---
  const exportarCSV = async () => {
    setExportando(true);
    setError(null);
    try {
      // El detalle se pide al exportar y se recorren todas las páginas del
      // filtro activo. Antes se cargaban todos los pedidos al abrir la
      // pantalla y el CSV solo incluía los que ya estaban en memoria.
      const detalle: any[] = [];
      const limite = 500;
      let offset = 0;

      while (true) {
        const data: any = await api.getHistorial({
          desde: filtro.desde || undefined,
          hasta: filtro.hasta || undefined,
          limite,
          offset,
        });
        const items = Array.isArray(data.items) ? data.items : [];
        detalle.push(...items);
        if (
          items.length === 0 ||
          detalle.length >= Number(data.total || 0) ||
          offset > 20000
        ) {
          break;
        }
        offset += limite;
      }

      const filas: string[][] = [];
      filas.push(["REPORTE DE VENTAS Y GANANCIAS - Inventario POS"]);
      filas.push(["Generado", formatearFechaHora(new Date())]);
      filas.push(["Periodo", filtro.etiqueta]);
      filas.push([]);
      filas.push(["=== VENTAS POR FORMA DE PAGO ==="]);
      filas.push(["Forma de pago", "Total"]);
      if (totales) {
        filas.push(["Efectivo", String(totales.efectivo)]);
        filas.push(["Tarjeta", String(totales.tarjeta)]);
        filas.push(["Transferencia", String(totales.transferencia)]);
        filas.push(["TOTAL VENTAS", String(totales.total)]);
        filas.push(["GANANCIA", String(ganancia)]);
      }
      filas.push([]);
      filas.push(["=== TOP PRODUCTOS ==="]);
      filas.push(["Producto", "Cantidad", "Total"]);
      topProductos.forEach((p: any) =>
        filas.push([p.nombre, String(p.cantidad), String(p.total)])
      );
      filas.push([]);
      filas.push(["=== PEDIDOS DETALLADOS ==="]);
      filas.push(["Pedido", "Mesa", "Fecha", "Estado", "Total", "Productos"]);
      detalle.forEach((p: any) =>
        filas.push([
          String(p.id),
          p.mesa_etiqueta || (p.mesa_numero != null ? `Mesa ${p.mesa_numero}` : "-"),
          formatearFechaHora(p.fecha),
          p.estado,
          String(p.total),
          (p.productos || []).join(" | "),
        ])
      );

      const csv = filas
        .map((f) => f.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(";"))
        .join("\n");

      const blob = new Blob(["\ufeff" + csv], {
        type: "text/csv;charset=utf-8;",
      });
      const url = URL.createObjectURL(blob);
      const enlace = document.createElement("a");
      enlace.href = url;
      enlace.download = `reporte-ventas-${fechaParaArchivo()}.csv`;
      enlace.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(err.message || "No se pudo exportar el CSV");
    } finally {
      setExportando(false);
    }
  };

  return (
    <div className="page">
      <div className="page-head">
        <h2>Reportes de ventas e inventario</h2>
      </div>

      {/* Panel de filtros con el mismo estilo que Historial */}
      <div className="filtros-barra">
        <div className="form-group">
          <label htmlFor="reporte-calendario">Calendario</label>
          <input
            id="reporte-calendario"
            type="date"
            value={fechaTexto}
            onChange={(e) => cambiarFecha(e.target.value)}
          />
        </div>

        <div className="form-group">
          <label htmlFor="reporte-mes">Mes</label>
          <select
            id="reporte-mes"
            value={mesTexto}
            onChange={(e) => cambiarMes(e.target.value)}
          >
            <option value="">Todos los meses</option>
            {MESES.map((mes, indice) => (
              <option key={mes} value={indice + 1}>
                {capitalizar(mes)}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="reporte-anio">Año</label>
          <select
            id="reporte-anio"
            value={anioTexto}
            onChange={(e) => cambiarAnio(e.target.value)}
          >
            <option value="">Todos los años</option>
            {anios.map((anio) => (
              <option key={anio} value={anio}>
                {anio}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="reporte-filtro">Filtro personalizado</label>
          <select
            id="reporte-filtro"
            value={modo === "rango" ? rango : "personalizado"}
            onChange={(e) => cambiarFiltro(e.target.value)}
          >
            {modo !== "rango" && (
              <option value="personalizado" disabled>
                Personalizado
              </option>
            )}
            <option value="dia">Día (hoy)</option>
            <option value="turno_ayer">Ult turno (ayer)</option>
            <option value="semana">Semana (7 días)</option>
            <option value="mes">Mes (30 días)</option>
          </select>
        </div>

        <div className="filtros-acciones">
          <button className="btn-secondary" onClick={quitarFiltros}>
            Quitar Filtros
          </button>
          <button
            className="btn-primary"
            onClick={exportarCSV}
            disabled={exportando}
          >
            {exportando ? "Exportando..." : "Exportar CSV"}
          </button>
          {/*
            "Actualizar" sí tiene una función real: fuerza una nueva consulta
            de inventario, años con ventas, turno de ayer y reportes.
          */}
          <button
            className="btn-secondary"
            onClick={() => setRecarga((n) => n + 1)}
          >
            Actualizar
          </button>
        </div>
      </div>

      <p className="muted small filtros-nota">
        «Actualizar» vuelve a consultar inventario, opciones de año, turnos y
        reportes.
      </p>

      <div className="filtros-resumen">
        <span className="muted small">
          Mostrando: <strong>{filtro.etiqueta}</strong>
        </span>
        {modo === "rango" && rango === "turno_ayer" && turnoAyer && (
          <span className="muted small">
            · Abrió {formatearFechaHora(turnoAyer.fecha_apertura)} · Cerró{" "}
            {turnoAyer.fecha_cierre
              ? formatearFechaHora(turnoAyer.fecha_cierre)
              : "aún en curso"}
          </span>
        )}
        {modo === "rango" && rango === "turno_ayer" && !turnoAyer && (
          <span className="filtros-alerta small">
            · No hay turno registrado ayer
          </span>
        )}
      </div>

      {error && <p className="error-msg">{error}</p>}

      {/* KPIs del período + inventario completo (sin filtros de fecha) */}
      <div className="kpis">
        <div className="kpi-card">
          <h3>Ventas ({filtro.etiqueta})</h3>
          <h2>{formatearPrecio(totales?.total ?? 0)}</h2>
        </div>
        <div className="kpi-card kpi-ganancia">
          <h3>Ganancias ({filtro.etiqueta})</h3>
          <h2>{formatearPrecio(ganancia)}</h2>
        </div>
        <div className="kpi-card">
          <h3>Operaciones</h3>
          <h2>{totales?.operaciones ?? 0}</h2>
        </div>
        <div className="kpi-card">
          <h3>Productos</h3>
          <h2>{totalProductos}</h2>
        </div>
        <div className="kpi-card">
          <h3>Stock total</h3>
          <h2>{stockTotal}</h2>
        </div>
      </div>

      {/* Gráfico de ventas por día */}
      <section className="panel">
        <h3>Ventas por día · {filtro.etiqueta}</h3>
        {ventasPorDia.etiquetas.length > 0 ? (
          <div className="chart-wrap">
            <Line
              data={{
                labels: ventasPorDia.etiquetas,
                datasets: ventasPorDia.series,
              }}
              options={opcionesGrafico}
            />
          </div>
        ) : (
          <p className="empty-state">Sin ventas en el periodo.</p>
        )}
      </section>

      {/* Gráfico de ganancias por día */}
      <section className="panel">
        <h3>Ganancias por día · {filtro.etiqueta}</h3>
        {gananciasPorDia.etiquetas.length > 0 ? (
          <div className="chart-wrap">
            <Line
              data={{
                labels: gananciasPorDia.etiquetas,
                datasets: gananciasPorDia.series,
              }}
              options={opcionesGrafico}
            />
          </div>
        ) : (
          <p className="empty-state">Sin ganancias en el periodo.</p>
        )}
      </section>

      <div className="report-grid">
        {/* Formas de pago */}
        <section className="panel">
          <h3>Formas de pago</h3>
          {formasPago.datos.length > 0 ? (
            <div className="chart-wrap chart-wrap-small">
              <Doughnut
                data={{
                  labels: formasPago.etiquetas,
                  datasets: [
                    {
                      data: formasPago.datos,
                      backgroundColor: formasPago.colores,
                      borderWidth: 0,
                    },
                  ],
                }}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  plugins: {
                    legend: { position: "bottom" },
                    tooltip: {
                      callbacks: {
                        label: (ctx: any) =>
                          `${ctx.label}: ${formatearPrecio(Number(ctx.parsed))}`,
                      },
                    },
                  },
                }}
              />
            </div>
          ) : (
            <p className="empty-state">Sin cobros en el periodo.</p>
          )}
        </section>

        {/* Top de productos */}
        <section className="panel">
          <h3>Productos más vendidos</h3>
          {topProductos.length > 0 ? (
            <div className="chart-wrap">
              <Bar
                data={{
                  labels: topProductos.map((p: any) => p.nombre),
                  datasets: [
                    {
                      label: "Unidades",
                      data: topProductos.map((p: any) => p.cantidad),
                      backgroundColor: "#3498db",
                    },
                  ],
                }}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  indexAxis: "y",
                  plugins: { legend: { display: false } },
                  scales: { x: { beginAtZero: true } },
                }}
              />
            </div>
          ) : (
            <p className="empty-state">Sin ventas en el periodo.</p>
          )}
        </section>
      </div>

      {/* Estado del inventario (completo, independiente de los filtros) */}
      <section className="panel">
        <h3>Estado del inventario</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Producto</th>
                <th>Precio</th>
                <th>Stock</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {productos.map((p) => (
                <tr key={p.id}>
                  <td>{p.nombre}</td>
                  <td>{formatearPrecio(p.precio)}</td>
                  <td>{p.stock}</td>
                  <td>
                    <span
                      className={
                        p.stock === 0
                          ? "badge badge-danger"
                          : p.stock < 10
                          ? "badge badge-warning"
                          : "badge badge-success"
                      }
                    >
                      {p.stock === 0 ? "Agotado" : p.stock < 10 ? "Bajo" : "OK"}
                    </span>
                  </td>
                </tr>
              ))}
              {productos.length === 0 && (
                <tr>
                  <td colSpan={4} className="empty-state">
                    No hay productos registrados.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
