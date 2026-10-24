/** Pantalla de Historial de Ventas - Administrador. Filtros por fecha, mesa, producto y forma de pago. */

import { useEffect, useState } from "react";
import { api } from "../services/api";

interface PedidoHistorial {
  id: number;
  fecha: string | null;
  estado: string;
  forma_pago: string;
  total: number;
  mesa_numero: number | null;
  mesa_etiqueta: string | null;
  usuario_nombre: string;
  productos: string[];
}

interface Producto {
  id: number;
  nombre: string;
}

interface Mesa {
  id: number;
  numero: number;
  tipo?: string;
  grupo?: string | null;
}

const POR_PAGINA = 25;

const etiquetaMesa = (m: Mesa) =>
  m.tipo === "barra" ? `Barra ${m.numero}` : `Mesa ${m.numero}`;

export default function HistorialPage() {
  const [items, setItems] = useState<PedidoHistorial[]>([]);
  const [total, setTotal] = useState(0);
  const [pagina, setPagina] = useState(0);
  const [productos, setProductos] = useState<Producto[]>([]);
  const [mesas, setMesas] = useState<Mesa[]>([]);
  const [filtros, setFiltros] = useState({
    desde: "",
    hasta: "",
    mesa: "" as number | "",
    producto: "" as number | "",
    forma_pago: "" as string | "",
  });
  const [error, setError] = useState<string | null>(null);

  const cargar = async () => {
    try {
      const data: any = await api.getHistorial({
        desde: filtros.desde || undefined,
        hasta: filtros.hasta || undefined,
        mesa: filtros.mesa || undefined,
        producto: filtros.producto || undefined,
        forma_pago: filtros.forma_pago || undefined,
        limite: POR_PAGINA,
        offset: pagina * POR_PAGINA,
      });
      setItems(data.items);
      setTotal(data.total);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    }
  };

  useEffect(() => {
    cargar();
  }, [pagina]);

  useEffect(() => {
    (async () => {
      try {
        const [p, m]: any = await Promise.all([
          api.getProductos({ limite: 500 }),
          api.getMesas(),
        ]);
        setProductos(p.items);
        setMesas(m);
      } catch (err: any) {
        setError(err.message);
      }
    })();
  }, []);

  const aplicar = () => {
    setPagina(0);
    cargar();
  };

  const limpiar = () => {
    setFiltros({ desde: "", hasta: "", mesa: "", producto: "", forma_pago: "" });
    setPagina(0);
  };

  const exportarCSV = () => {
    const filas: string[][] = [
      ["HISTORIAL DE VENTAS"],
      ["Pedido", "Fecha", "Mesa / Barra", "Usuario", "Forma de pago", "Total", "Productos"],
      ...items.map((p) => [
        String(p.id),
        p.fecha || "",
        p.mesa_etiqueta || "-",
        p.usuario_nombre,
        p.forma_pago,
        String(p.total),
        p.productos.join(" | "),
      ]),
    ];
    const csv = filas
      .map((f) => f.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(";"))
      .join("\n");
    const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const enlace = document.createElement("a");
    enlace.href = url;
    enlace.download = `historial-ventas-${new Date().toISOString().slice(0, 10)}.csv`;
    enlace.click();
    URL.revokeObjectURL(url);
  };

  const paginas = Math.max(1, Math.ceil(total / POR_PAGINA));

  return (
    <div className="page">
      <div className="page-head">
        <h2>Historial de ventas</h2>
        <div className="filters">
          <button className="btn-secondary" onClick={aplicar}>
            Aplicar filtros
          </button>
          <button className="btn-secondary" onClick={limpiar}>
            Limpiar
          </button>
          <button className="btn-primary" onClick={exportarCSV}>
            ⬇ Exportar CSV
          </button>
        </div>
      </div>

      {error && <p className="error-msg">{error}</p>}

      {/* Filtros */}
      <div className="filtros-barra">
        <div className="form-group">
          <label>Desde</label>
          <input
            type="date"
            value={filtros.desde}
            onChange={(e) => setFiltros((f) => ({ ...f, desde: e.target.value }))}
          />
        </div>
        <div className="form-group">
          <label>Hasta</label>
          <input
            type="date"
            value={filtros.hasta}
            onChange={(e) => setFiltros((f) => ({ ...f, hasta: e.target.value }))}
          />
        </div>
        <div className="form-group">
          <label>Mesa / Barra</label>
          <select
            value={filtros.mesa}
            onChange={(e) =>
              setFiltros((f) => ({ ...f, mesa: e.target.value ? Number(e.target.value) : "" }))
            }
          >
            <option value="">Todas</option>
            {mesas.map((m) => (
              <option key={m.id} value={m.id}>
                {etiquetaMesa(m)}
              </option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label>Producto</label>
          <select
            value={filtros.producto}
            onChange={(e) =>
              setFiltros((f) => ({
                ...f,
                producto: e.target.value ? Number(e.target.value) : "",
              }))
            }
          >
            <option value="">Todos</option>
            {productos.map((p) => (
              <option key={p.id} value={p.id}>
                {p.nombre}
              </option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label>Forma de pago</label>
          <select
            value={filtros.forma_pago}
            onChange={(e) => setFiltros((f) => ({ ...f, forma_pago: e.target.value }))}
          >
            <option value="">Todas</option>
            <option value="efectivo">Efectivo</option>
            <option value="tarjeta">Tarjeta</option>
            <option value="transferencia">Transferencia</option>
          </select>
        </div>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Fecha</th>
              <th>Mesa / Barra</th>
              <th>Usuario</th>
              <th>Forma de pago</th>
              <th>Productos</th>
              <th>Total</th>
            </tr>
          </thead>
          <tbody>
            {items.map((p) => (
              <tr key={p.id}>
                <td>{p.id}</td>
                <td>{p.fecha ? new Date(p.fecha).toLocaleString("es") : "-"}</td>
                <td>{p.mesa_etiqueta || "-"}</td>
                <td>{p.usuario_nombre}</td>
                <td>
                  <span className="badge badge-success">{p.forma_pago}</span>
                </td>
                <td className="muted small">{p.productos.join(", ")}</td>
                <td>
                  <strong>${p.total.toFixed(2)}</strong>
                </td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr>
                <td colSpan={7} className="empty-state">
                  No hay ventas que coincidan con los filtros.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="paginacion">
        <button
          className="btn-secondary btn-small"
          disabled={pagina === 0}
          onClick={() => setPagina((p) => p - 1)}
        >
          ‹ Anterior
        </button>
        <span className="muted small">
          Página {pagina + 1} de {paginas} · {total} ventas
        </span>
        <button
          className="btn-secondary btn-small"
          disabled={pagina >= paginas - 1}
          onClick={() => setPagina((p) => p + 1)}
        >
          Siguiente ›
        </button>
      </div>
    </div>
  );
}
