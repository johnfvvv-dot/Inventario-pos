/** Pantalla de Reportes - Administrador. Gráficos + exportación CSV. */

import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  type ChartOptions,
} from "chart.js";
import { Line, Doughnut } from "react-chartjs-2";
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

/* -------------------- ICONOS (SVG inline) -------------------- */

type NombreIcono =
  | "actualizar"
  | "descargar"
  | "info"
  | "limpiar"
  | "ventas"
  | "ganancias"
  | "operaciones"
  | "ticket"
  | "productos"
  | "stock";

const ICONOS: Record<NombreIcono, ReactNode> = {
  actualizar: (
    <>
      <path d="M23 4v6h-6" />
      <path d="M1 20v-6h6" />
      <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10" />
      <path d="M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
    </>
  ),
  descargar: (
    <>
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </>
  ),
  info: (
    <>
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="16" x2="12" y2="12" />
      <line x1="12" y1="8" x2="12.01" y2="8" />
    </>
  ),
  limpiar: (
    <>
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </>
  ),
  ventas: (
    <>
      <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
      <polyline points="17 6 23 6 23 12" />
    </>
  ),
  ganancias: (
    <>
      <line x1="12" y1="1" x2="12" y2="23" />
      <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
    </>
  ),
  operaciones: (
    <>
      <path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z" />
      <line x1="3" y1="6" x2="21" y2="6" />
      <path d="M16 10a4 4 0 0 1-8 0" />
    </>
  ),
  ticket: (
    <>
      <path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1Z" />
      <line x1="8" y1="7" x2="16" y2="7" />
      <line x1="8" y1="11" x2="16" y2="11" />
      <line x1="8" y1="15" x2="12" y2="15" />
    </>
  ),
  productos: (
    <>
      <line x1="16.5" y1="9.4" x2="7.5" y2="4.21" />
      <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
      <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
      <line x1="12" y1="22.08" x2="12" y2="12" />
    </>
  ),
  stock: (
    <>
      <polygon points="12 2 2 7 12 12 22 7 12 2" />
      <polyline points="2 17 12 22 22 17" />
      <polyline points="2 12 12 17 22 12" />
    </>
  ),
};

function Icono({ nombre }: { nombre: NombreIcono }) {
  return (
    <svg
      className="reportes-icono"
      viewBox="0 0 24 24"
      width="18"
      height="18"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {ICONOS[nombre]}
    </svg>
  );
}

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

  const comparativoPorDia = useMemo(() => {
    if (!serie) return { etiquetas: [], series: [] };
    return {
      etiquetas: serie.etiquetas.map((e: string) => e.slice(5)), // solo mes-día
      series: [
        {
          label: "Ventas",
          data: serie.serie.map((s: any) => s.total),
          borderColor: "#3498db",
          backgroundColor: "rgba(52,152,219,0.10)",
          pointBackgroundColor: "#3498db",
          pointBorderColor: "#3498db",
          borderWidth: 2.5,
          pointRadius: 2.5,
          pointHoverRadius: 5,
          fill: true,
          tension: 0.35,
        },
        {
          label: "Ganancias",
          data: serie.serie.map((s: any) => s.ganancia || 0),
          borderColor: "#27ae60",
          backgroundColor: "rgba(39,174,96,0.10)",
          pointBackgroundColor: "#27ae60",
          pointBorderColor: "#27ae60",
          borderWidth: 2.5,
          pointRadius: 2.5,
          pointHoverRadius: 5,
          fill: true,
          tension: 0.35,
        },
      ],
    };
  }, [serie]);

  const maxCantidadTop = useMemo(
    () =>
      topProductos.reduce(
        (maximo: number, p: any) => Math.max(maximo, Number(p.cantidad) || 0),
        0
      ),
    [topProductos]
  );

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

  const totalFormasPago = useMemo(
    () => formasPago.datos.reduce((suma, valor) => suma + valor, 0),
    [formasPago]
  );

  // Métricas calculadas con los datos ya disponibles en la vista.
  const ticketPromedio =
    totales && totales.operaciones > 0
      ? totales.total / totales.operaciones
      : 0;

  const margenGanancia =
    totales && totales.total > 0 ? (ganancia / totales.total) * 100 : 0;

  const valorInventario = useMemo(
    () =>
      productos.reduce(
        (suma, p) => suma + Number(p.precio || 0) * Number(p.stock || 0),
        0
      ),
    [productos]
  );

  const maxStock = useMemo(
    () =>
      productos.reduce(
        (maximo, p) => Math.max(maximo, Number(p.stock) || 0),
        0
      ),
    [productos]
  );

  const opcionesComparativo: ChartOptions<"line"> = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: {
        position: "top",
        align: "end",
        labels: {
          usePointStyle: true,
          boxWidth: 8,
          boxHeight: 8,
          padding: 16,
          font: { size: 11, weight: 600 },
        },
      },
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
        border: { display: false },
        grid: { color: "rgba(44, 62, 80, 0.07)" },
        ticks: {
          callback: (valor: any) => formatearNumero(Number(valor)),
        },
      },
      x: {
        grid: { display: false },
        ticks: { maxRotation: 0, autoSkipPadding: 12 },
      },
    },
  };

  const opcionesDona: ChartOptions<"doughnut"> = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: "68%",
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (ctx: any) => {
            const valor = Number(ctx.parsed) || 0;
            const porcentaje =
              totalFormasPago > 0 ? (valor / totalFormasPago) * 100 : 0;
            return `${ctx.label}: ${formatearPrecio(valor)} (${Math.round(
              porcentaje
            )}%)`;
          },
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
    <div className="page reportes-page">
      <header className="reportes-head">
        <div className="reportes-head-texto">
          <h2>Reportes de ventas e inventario</h2>
          <p className="reportes-subtitulo">
            <span>
              Mostrando <strong>{filtro.etiqueta}</strong>
            </span>
            {modo === "rango" && rango === "turno_ayer" && turnoAyer && (
              <span>
                Abrió {formatearFechaHora(turnoAyer.fecha_apertura)} · Cerró{" "}
                {turnoAyer.fecha_cierre
                  ? formatearFechaHora(turnoAyer.fecha_cierre)
                  : "aún en curso"}
              </span>
            )}
            {modo === "rango" && rango === "turno_ayer" && !turnoAyer && (
              <span className="filtros-alerta">
                No hay turno registrado ayer
              </span>
            )}
          </p>
        </div>

        <div className="reportes-head-acciones">
          {/*
            "Actualizar" sí tiene una función real: fuerza una nueva consulta
            de inventario, años con ventas, turno de ayer y reportes.
          */}
          <button
            type="button"
            className="btn-secondary reportes-btn"
            onClick={() => setRecarga((n) => n + 1)}
          >
            <Icono nombre="actualizar" />
            Actualizar
          </button>
          <span
            className="reportes-info"
            tabIndex={0}
            aria-describedby="reportes-info-tooltip"
          >
            <Icono nombre="info" />
            <span
              id="reportes-info-tooltip"
              className="reportes-info-tooltip"
              role="tooltip"
            >
              «Actualizar» vuelve a consultar inventario, opciones de año,
              turnos y reportes.
            </span>
          </span>
          <button
            type="button"
            className="btn-primary reportes-btn"
            onClick={exportarCSV}
            disabled={exportando}
          >
            <Icono nombre="descargar" />
            {exportando ? "Exportando..." : "Exportar CSV"}
          </button>
        </div>
      </header>

      {error && <p className="error-msg">{error}</p>}

      {/* Filtros en una sola barra horizontal y compacta */}
      <div className="filtros-barra reportes-filtros">
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

        <div className="reportes-filtros-fin">
          <button
            type="button"
            className="reportes-quitar"
            onClick={quitarFiltros}
          >
            <Icono nombre="limpiar" />
            Quitar filtros
          </button>
        </div>
      </div>

      {/* KPIs del período + inventario completo (sin filtros de fecha) */}
      <div className="reportes-kpis">
        <article className="reportes-kpi reportes-kpi--ventas">
          <span className="reportes-kpi-icono">
            <Icono nombre="ventas" />
          </span>
          <p className="reportes-kpi-label">Ventas</p>
          <p className="reportes-kpi-valor">
            {formatearPrecio(totales?.total ?? 0)}
          </p>
          <p className="reportes-kpi-detalle">{filtro.etiqueta}</p>
        </article>

        <article className="reportes-kpi reportes-kpi--ganancias">
          <span className="reportes-kpi-icono">
            <Icono nombre="ganancias" />
          </span>
          <p className="reportes-kpi-label">Ganancias</p>
          <p className="reportes-kpi-valor">{formatearPrecio(ganancia)}</p>
          <div className="reportes-kpi-detalle-fila">
            <p className="reportes-kpi-detalle">{filtro.etiqueta}</p>
            <span
              className="reportes-margen"
              title="Margen de ganancia sobre las ventas"
            >
              {margenGanancia.toFixed(1)}%
            </span>
          </div>
        </article>

        <article className="reportes-kpi reportes-kpi--operaciones">
          <span className="reportes-kpi-icono">
            <Icono nombre="operaciones" />
          </span>
          <p className="reportes-kpi-label">Operaciones</p>
          <p className="reportes-kpi-valor">{totales?.operaciones ?? 0}</p>
          <p className="reportes-kpi-detalle">transacciones del periodo</p>
        </article>

        <article className="reportes-kpi reportes-kpi--ticket">
          <span className="reportes-kpi-icono">
            <Icono nombre="ticket" />
          </span>
          <p className="reportes-kpi-label">Ticket promedio</p>
          <p className="reportes-kpi-valor">
            {formatearPrecio(ticketPromedio)}
          </p>
          <p className="reportes-kpi-detalle">Ventas / operaciones</p>
        </article>

        <article className="reportes-kpi reportes-kpi--productos">
          <span className="reportes-kpi-icono">
            <Icono nombre="productos" />
          </span>
          <p className="reportes-kpi-label">Productos</p>
          <p className="reportes-kpi-valor">{totalProductos}</p>
          <p className="reportes-kpi-detalle">en catálogo</p>
        </article>

        <article className="reportes-kpi reportes-kpi--stock">
          <span className="reportes-kpi-icono">
            <Icono nombre="stock" />
          </span>
          <p className="reportes-kpi-label">Stock total</p>
          <p className="reportes-kpi-valor">{stockTotal}</p>
          <p className="reportes-kpi-detalle">unidades disponibles</p>
        </article>
      </div>

      {/* Comparativo unificado de ventas y ganancias */}
      <section className="panel">
        <div className="reportes-panel-head">
          <div>
            <h3>Ventas y ganancias por día</h3>
            <p className="muted small">Comparativo del periodo · {filtro.etiqueta}</p>
          </div>
          <div className="reportes-chips">
            <span className="reportes-chip">
              <span
                className="reportes-punto"
                style={{ background: "#3498db" }}
              />
              Ventas {formatearPrecio(totales?.total ?? 0)}
            </span>
            <span className="reportes-chip">
              <span
                className="reportes-punto"
                style={{ background: "#27ae60" }}
              />
              Ganancias {formatearPrecio(ganancia)}
            </span>
          </div>
        </div>

        {comparativoPorDia.etiquetas.length > 0 ? (
          <div className="chart-wrap reportes-chart">
            <Line
              data={{
                labels: comparativoPorDia.etiquetas,
                datasets: comparativoPorDia.series,
              }}
              options={opcionesComparativo}
            />
          </div>
        ) : (
          <p className="empty-state">Sin ventas en el periodo.</p>
        )}
      </section>

      <div className="reportes-grid">
        {/* Formas de pago */}
        <section className="panel">
          <div className="reportes-panel-head">
            <div>
              <h3>Formas de pago</h3>
              <p className="muted small">Distribución de los cobros del periodo</p>
            </div>
            <span className="reportes-chip">
              Total {formatearPrecio(totalFormasPago)}
            </span>
          </div>

          {formasPago.datos.length > 0 ? (
            <>
              <div className="reportes-dona">
                <Doughnut
                  data={{
                    labels: formasPago.etiquetas,
                    datasets: [
                      {
                        data: formasPago.datos,
                        backgroundColor: formasPago.colores,
                        borderWidth: 0,
                        hoverOffset: 4,
                      },
                    ],
                  }}
                  options={opcionesDona}
                />
                <div className="reportes-dona-centro" aria-hidden="true">
                  <span>Total</span>
                  <strong>{formatearPrecio(totalFormasPago)}</strong>
                </div>
              </div>

              <ul className="reportes-leyenda">
                {formasPago.etiquetas.map((etiqueta, indice) => {
                  const valor = formasPago.datos[indice];
                  const porcentaje =
                    totalFormasPago > 0
                      ? (valor / totalFormasPago) * 100
                      : 0;
                  return (
                    <li key={etiqueta}>
                      <span
                        className="reportes-punto"
                        style={{ background: formasPago.colores[indice] }}
                      />
                      <span className="reportes-leyenda-nombre">{etiqueta}</span>
                      <span className="reportes-leyenda-valor">
                        {formatearPrecio(valor)}
                      </span>
                      <span className="reportes-leyenda-pct">
                        {Math.round(porcentaje)}%
                      </span>
                    </li>
                  );
                })}
              </ul>
            </>
          ) : (
            <p className="empty-state">Sin cobros en el periodo.</p>
          )}
        </section>

        {/* Top de productos con unidades al final de cada barra */}
        <section className="panel">
          <div className="reportes-panel-head">
            <div>
              <h3>Productos más vendidos</h3>
              <p className="muted small">Unidades vendidas en el periodo</p>
            </div>
          </div>

          {topProductos.length > 0 ? (
            <ul className="reportes-top">
              {topProductos.map((p: any, indice: number) => {
                const cantidad = Number(p.cantidad) || 0;
                const ancho =
                  maxCantidadTop > 0 ? (cantidad / maxCantidadTop) * 100 : 0;
                return (
                  <li
                    className="reportes-top-item"
                    key={`${p.nombre}-${indice}`}
                  >
                    <span className="reportes-top-nombre" title={p.nombre}>
                      {p.nombre}
                    </span>
                    <div className="reportes-top-barra" aria-hidden="true">
                      <span
                        className="reportes-top-fill"
                        style={{ width: `${ancho}%` }}
                      />
                    </div>
                    <span className="reportes-top-unidades">
                      {formatearNumero(cantidad)} u.
                    </span>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="empty-state">Sin ventas en el periodo.</p>
          )}
        </section>
      </div>

      {/* Estado del inventario (completo, independiente de los filtros) */}
      <section className="panel">
        <div className="reportes-panel-head">
          <div>
            <h3>Estado del inventario</h3>
            <p className="muted small">
              Inventario actual, independiente del periodo seleccionado
            </p>
          </div>
          <div className="reportes-inv-total">
            <span>Valor total en stock</span>
            <strong>{formatearPrecio(valorInventario)}</strong>
          </div>
        </div>

        <div className="table-wrap">
          <table className="reportes-inv-tabla">
            <thead>
              <tr>
                <th>Producto</th>
                <th>Precio</th>
                <th>Stock</th>
                <th>Valor en stock</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {productos.map((p) => {
                const porcentajeStock =
                  maxStock > 0 ? (p.stock / maxStock) * 100 : 0;
                const claseStock =
                  p.stock === 0 ? "agotado" : p.stock < 10 ? "bajo" : "ok";
                return (
                  <tr key={p.id}>
                    <td>{p.nombre}</td>
                    <td>{formatearPrecio(p.precio)}</td>
                    <td>
                      <div className="reportes-stock-celda">
                        <span className="reportes-stock-numero">{p.stock}</span>
                        <div
                          className="reportes-stock-barra"
                          aria-hidden="true"
                        >
                          <span
                            className={`reportes-stock-fill reportes-stock-fill--${claseStock}`}
                            style={{
                              width: `${porcentajeStock}%`,
                              minWidth: p.stock > 0 ? 4 : 0,
                            }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="reportes-valor-stock">
                      {formatearPrecio(p.precio * p.stock)}
                    </td>
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
                        {p.stock === 0
                          ? "Agotado"
                          : p.stock < 10
                          ? "Bajo"
                          : "OK"}
                      </span>
                    </td>
                  </tr>
                );
              })}
              {productos.length === 0 && (
                <tr>
                  <td colSpan={5} className="empty-state">
                    No hay productos registrados.
                  </td>
                </tr>
              )}
            </tbody>
            {productos.length > 0 && (
              <tfoot>
                <tr className="reportes-inv-pie">
                  <td colSpan={3}>Total inventario</td>
                  <td>{formatearPrecio(valorInventario)}</td>
                  <td></td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      </section>
    </div>
  );
}
