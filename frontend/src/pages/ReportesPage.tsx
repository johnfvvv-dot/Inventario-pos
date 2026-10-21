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

interface Pedido {
  id: number;
  total: number;
  estado: string;
  fecha: string;
  mesa?: { numero: number } | null;
  items: {
    producto_id: number;
    producto_nombre: string;
    cantidad: number;
    subtotal: number;
  }[];
}

interface Totales {
  efectivo: number;
  tarjeta: number;
  transferencia: number;
  total: number;
  operaciones: number;
}

export default function ReportesPage() {
  const [productos, setProductos] = useState<Producto[]>([]);
  const [pedidos, setPedidos] = useState<Pedido[]>([]);
  const [totales, setTotales] = useState<Totales | null>(null);
  const [serie, setSerie] = useState<any>(null);
  const [periodo, setPeriodo] = useState(14);
  const [error, setError] = useState<string | null>(null);

  const cargar = async () => {
    try {
      const [inv, ped, res, dia]: any = await Promise.all([
        api.getProductos({ limite: 500 }),
        api.getPedidos(),
        api.getResumenCaja(periodo),
        api.getVentasPorDia(periodo),
      ]);
      setProductos(inv.items);
      setPedidos(ped);
      setTotales(res.totales);
      setSerie(dia);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    }
  };

  useEffect(() => {
    cargar();
  }, [periodo]);

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
          label: "Total",
          data: serie.serie.map((s: any) => s.total),
          borderColor: "#3498db",
          backgroundColor: "rgba(52,152,219,0.15)",
          fill: true,
          tension: 0.3,
        },
      ],
    };
  }, [serie]);

  const formasPago = useMemo(() => {
    if (!totales) return { etiquetas: [], datos: [] };
    return {
      etiquetas: ["Efectivo", "Tarjeta", "Transferencia"],
      datos: [totales.efectivo, totales.tarjeta, totales.transferencia].filter(
        (v) => v > 0
      ),
    };
  }, [totales]);

  // --- Exportar CSV ---
  const exportarCSV = () => {
    const filas: string[][] = [];
    filas.push(["REPORTE DE VENTAS - Inventario POS"]);
    filas.push(["Generado", new Date().toLocaleString("es")]);
    filas.push(["Periodo (dias)", String(periodo)]);
    filas.push([]);
    filas.push(["=== VENTAS POR FORMA DE PAGO ==="]);
    filas.push(["Forma de pago", "Total"]);
    if (totales) {
      filas.push(["Efectivo", String(totales.efectivo)]);
      filas.push(["Tarjeta", String(totales.tarjeta)]);
      filas.push(["Transferencia", String(totales.transferencia)]);
      filas.push(["TOTAL", String(totales.total)]);
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
    pedidos
      .filter((p) => p.estado === "cerrado")
      .forEach((p) =>
        filas.push([
          String(p.id),
          p.mesa ? String(p.mesa.numero) : "-",
          p.fecha,
          p.estado,
          String(p.total),
          p.items.map((i) => `${i.cantidad}x ${i.producto_nombre}`).join(" | "),
        ])
      );

    const csv = filas
      .map((f) => f.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(";"))
      .join("\n");

    const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const enlace = document.createElement("a");
    enlace.href = url;
    enlace.download = `reporte-ventas-${new Date().toISOString().slice(0, 10)}.csv`;
    enlace.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="page">
      <div className="page-head">
        <h2>Reportes de ventas e inventario</h2>
        <div className="filters">
          <select value={periodo} onChange={(e) => setPeriodo(Number(e.target.value))}>
            <option value={7}>Últimos 7 días</option>
            <option value={14}>Últimos 14 días</option>
            <option value={30}>Últimos 30 días</option>
            <option value={90}>Últimos 90 días</option>
          </select>
          <button className="btn-secondary" onClick={cargar}>
            Actualizar
          </button>
          <button className="btn-primary" onClick={exportarCSV}>
            ⬇ Exportar CSV
          </button>
        </div>
      </div>

      {error && <p className="error-msg">{error}</p>}

      {/* KPIs */}
      <div className="kpis">
        <div className="kpi-card">
          <h3>Ventas totales</h3>
          <h2>${(totales?.total ?? 0).toFixed(2)}</h2>
        </div>
        <div className="kpi-card">
          <h3>Operaciones</h3>
          <h2>{totales?.operaciones ?? 0}</h2>
        </div>
        <div className="kpi-card">
          <h3>Productos</h3>
          <h2>{productos.length}</h2>
        </div>
        <div className="kpi-card">
          <h3>Stock total</h3>
          <h2>{productos.reduce((s, p) => s + p.stock, 0)}</h2>
        </div>
      </div>

      {/* Gráfico de ventas por día */}
      <section className="panel">
        <h3>Ventas por día</h3>
        {ventasPorDia.etiquetas.length > 0 ? (
          <div className="chart-wrap">
            <Line
              data={{
                labels: ventasPorDia.etiquetas,
                datasets: ventasPorDia.series,
              }}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: true } },
                scales: { y: { beginAtZero: true } },
              }}
            />
          </div>
        ) : (
          <p className="empty-state">Sin ventas en el periodo.</p>
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
                  labels: formasPago.etiquetas.slice(0, formasPago.datos.length),
                  datasets: [
                    {
                      data: formasPago.datos,
                      backgroundColor: ["#27ae60", "#3498db", "#f39c12"],
                      borderWidth: 0,
                    },
                  ],
                }}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  plugins: { legend: { position: "bottom" } },
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

      {/* Estado del inventario */}
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
                  <td>${p.precio.toFixed(2)}</td>
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
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
