/** Pantalla de Reportes - Administrador. */

import { useEffect, useMemo, useState } from "react";
import { api } from "../services/api";

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
  mesa?: { numero: number } | null;
  items: {
    producto_id: number;
    producto_nombre: string;
    cantidad: number;
    subtotal: number;
  }[];
}

export default function ReportesPage() {
  const [productos, setProductos] = useState<Producto[]>([]);
  const [pedidos, setPedidos] = useState<Pedido[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [filtro, setFiltro] = useState<"hoy" | "todos">("todos");

  const cargar = async () => {
    try {
      const [p, ped]: any = await Promise.all([
        api.getProductos(),
        api.getPedidos(),
      ]);
      setProductos(p);
      setPedidos(ped);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    }
  };

  useEffect(() => {
    cargar();
  }, []);

  const pedidosFiltrados = useMemo(() => {
    const cerrados = pedidos.filter((p) => p.estado === "cerrado");
    if (filtro === "todos") return cerrados;
    const hoy = new Date().toDateString();
    return cerrados.filter(
      (p: any) => new Date(p.fecha).toDateString() === hoy
    );
  }, [pedidos, filtro]);

  const resumen = useMemo(() => {
    const totalVentas = pedidosFiltrados.reduce((s, p) => s + (p.total || 0), 0);
    const mesas = new Set(
      pedidosFiltrados.map((p) => p.mesa?.numero).filter(Boolean)
    );
    const unidades = pedidosFiltrados.reduce(
      (s, p) => s + p.items.reduce((x, i) => x + i.cantidad, 0),
      0
    );

    const ventasPorProducto: Record<string, number> = {};
    pedidosFiltrados.forEach((p) =>
      p.items.forEach((i) => {
        ventasPorProducto[i.producto_nombre] =
          (ventasPorProducto[i.producto_nombre] || 0) + i.cantidad;
      })
    );

    const top = Object.entries(ventasPorProducto)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);

    return {
      totalVentas,
      mesasAtendidas: mesas.size,
      unidades,
      promedio: mesas.size ? totalVentas / mesas.size : 0,
      top,
    };
  }, [pedidosFiltrados]);

  return (
    <div className="page">
      <div className="page-head">
        <h2>Reportes de ventas e inventario</h2>
        <div className="filters">
          <select
            value={filtro}
            onChange={(e) => setFiltro(e.target.value as "hoy" | "todos")}
          >
            <option value="todos">Todo el historial</option>
            <option value="hoy">Solo hoy</option>
          </select>
          <button className="btn-secondary" onClick={cargar}>
            Actualizar
          </button>
        </div>
      </div>

      {error && <p className="error-msg">{error}</p>}

      <div className="kpis">
        <div className="kpi-card">
          <h3>Total ventas</h3>
          <h2>${resumen.totalVentas.toFixed(2)}</h2>
        </div>
        <div className="kpi-card">
          <h3>Mesas atendidas</h3>
          <h2>{resumen.mesasAtendidas}</h2>
        </div>
        <div className="kpi-card">
          <h3>Unidades vendidas</h3>
          <h2>{resumen.unidades}</h2>
        </div>
        <div className="kpi-card">
          <h3>Promedio por mesa</h3>
          <h2>${resumen.promedio.toFixed(2)}</h2>
        </div>
      </div>

      <div className="report-grid">
        <section className="panel">
          <h3>Top productos vendidos</h3>
          {resumen.top.length === 0 ? (
            <p className="empty-state">Aún no hay ventas registradas.</p>
          ) : (
            <ul className="ranking">
              {resumen.top.map(([nombre, cantidad]) => (
                <li key={nombre}>
                  <span>{nombre}</span>
                  <strong>{cantidad} und.</strong>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="panel">
          <h3>Estado del inventario</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Producto</th>
                  <th>Stock</th>
                  <th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {productos.map((p) => (
                  <tr key={p.id}>
                    <td>{p.nombre}</td>
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
    </div>
  );
}
