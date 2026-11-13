/** Pantalla de Historial de Ventas - Administrador. Filtros por fecha, mesa, producto y forma de pago. */

import { useEffect, useState } from "react";
import { api } from "../services/api";
import {
  fechaParaArchivo,
  formatearFechaHora,
  formatearPrecio,
} from "../utils/format";
import Icon from "../components/Icon";

interface PedidoHistorial {
  id: number;
  fecha: string | null;
  estado: string;
  forma_pago: string;
  total: number;
  mesa_numero: number | null;
  mesa_etiqueta: string | null;
  usuario_nombre: string;
  usuario_cierre_nombre?: string;
  alias?: string | null;
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
const FILTROS_VACIOS = {
  desde: "",
  hasta: "",
  mesa: "" as number | "",
  producto: "" as number | "",
  forma_pago: "" as string | "",
};
type Filtros = typeof FILTROS_VACIOS;

const etiquetaMesa = (m: Mesa) =>
  m.tipo === "barra" ? `Barra ${m.numero}` : `Mesa ${m.numero}`;

/** Color semántico de la píldora según la forma de pago. */
const claseFormaPago = (forma: string): string => {
  const texto = (forma || "").toLowerCase();
  if (texto.includes("efectivo")) return "badge badge-pago-efectivo";
  if (texto.includes("transfer")) return "badge badge-pago-transferencia";
  if (texto.includes("tarjeta")) return "badge badge-pago-tarjeta";
  return "badge badge-neutral";
};

/**
 * Devuelve siempre el origen del pedido ("Mesa N" / "Barra N").
 * Usa la etiqueta guardada y, si falta, la reconstruye desde el número
 * histórico (las plazas de barra se codifican como N*100 + posición).
 */
const etiquetaOrigen = (p: PedidoHistorial): string => {
  if (p.mesa_etiqueta) return p.mesa_etiqueta;
  if (p.mesa_numero != null) {
    const posicion = p.mesa_numero % 100;
    if (p.mesa_numero >= 100 && posicion >= 1 && posicion <= 20) {
      return `Barra ${Math.floor(p.mesa_numero / 100)}`;
    }
    return `Mesa ${p.mesa_numero}`;
  }
  return "—";
};

export default function HistorialPage() {
  const [items, setItems] = useState<PedidoHistorial[]>([]);
  const [total, setTotal] = useState(0);
  const [pagina, setPagina] = useState(0);
  const [productos, setProductos] = useState<Producto[]>([]);
  const [mesas, setMesas] = useState<Mesa[]>([]);
  const [filtros, setFiltros] = useState<Filtros>({ ...FILTROS_VACIOS });
  // Filtros que están aplicados a la tabla (pueden diferir del formulario).
  const [aplicados, setAplicados] = useState<Filtros>({ ...FILTROS_VACIOS });
  const [exportando, setExportando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const cargar = async () => {
    try {
      const data: any = await api.getHistorial({
        desde: aplicados.desde || undefined,
        hasta: aplicados.hasta || undefined,
        mesa: aplicados.mesa || undefined,
        producto: aplicados.producto || undefined,
        forma_pago: aplicados.forma_pago || undefined,
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
  }, [aplicados, pagina]);

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
    // Un objeto nuevo dispara la consulta aunque los valores no cambien.
    setAplicados({ ...filtros });
  };

  const limpiar = () => {
    const vacios = { ...FILTROS_VACIOS };
    setFiltros(vacios);
    setPagina(0);
    // Siempre se vuelve a consultar, incluso si ya se estaba en la página 0.
    setAplicados({ ...vacios });
  };

  const exportarCSV = async () => {
    setExportando(true);
    setError(null);
    try {
      // Se exportan TODAS las ventas del filtro aplicado, no solo la página
      // visible. Se recorre el endpoint por bloques de 500.
      const todos: PedidoHistorial[] = [];
      const limite = 500;
      let offset = 0;

      while (true) {
        const data: any = await api.getHistorial({
          desde: aplicados.desde || undefined,
          hasta: aplicados.hasta || undefined,
          mesa: aplicados.mesa || undefined,
          producto: aplicados.producto || undefined,
          forma_pago: aplicados.forma_pago || undefined,
          limite,
          offset,
        });
        const bloque = Array.isArray(data.items) ? data.items : [];
        todos.push(...bloque);
        if (
          bloque.length === 0 ||
          todos.length >= Number(data.total || 0) ||
          offset > 20000
        ) {
          break;
        }
        offset += limite;
      }

      const filas: string[][] = [
        ["HISTORIAL DE VENTAS"],
        [
          "Pedido",
          "Fecha",
          "Mesa / Barra",
          "Cliente",
          "Usuario creador",
          "Cobrado por",
          "Forma de pago",
          "Total",
          "Productos",
        ],
        ...todos.map((p) => [
          String(p.id),
          formatearFechaHora(p.fecha),
          etiquetaOrigen(p),
          p.alias || "Cuenta general",
          p.usuario_nombre,
          p.usuario_cierre_nombre || "",
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
      enlace.download = `historial-ventas-${fechaParaArchivo()}.csv`;
      enlace.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(err.message || "No se pudo exportar el CSV");
    } finally {
      setExportando(false);
    }
  };

  const paginas = Math.max(1, Math.ceil(total / POR_PAGINA));

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h2>Historial de ventas</h2>
          <p className="page-subtitulo">
            Registro detallado de transacciones cobradas, responsables y
            desglose de productos
          </p>
        </div>
        <div className="filters page-head-acciones">
          <button className="btn-secondary" onClick={aplicar}>
            <Icon nombre="filtrar" size={16} />
            Aplicar filtros
          </button>
          <button className="btn-secondary" onClick={limpiar}>
            <Icon nombre="cerrar" size={16} />
            Limpiar
          </button>
          <button
            className="btn-primary"
            onClick={exportarCSV}
            disabled={exportando}
          >
            <Icon nombre="descargar" size={16} />
            {exportando ? "Exportando..." : "Exportar CSV"}
          </button>
        </div>
      </div>

      {error && <p className="error-msg">{error}</p>}

      {/* Filtros */}
      <div className="filtros-barra historial-filtros">
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

      <div className="panel tabla-card">
        <div className="table-wrap">
          <table className="historial-tabla">
            <thead>
              <tr>
                <th>#</th>
                <th>Fecha</th>
                <th>Mesa / Barra</th>
                <th>Cliente</th>
                <th>Usuario creador</th>
                <th>Cobrado por</th>
                <th>Forma de pago</th>
                <th>Productos</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody>
              {items.map((p) => (
                <tr key={p.id}>
                  <td>{p.id}</td>
                  <td>{formatearFechaHora(p.fecha)}</td>
                  <td>{etiquetaOrigen(p)}</td>
                  <td>
                    {p.alias ? (
                      <span className="badge badge-warning">{p.alias}</span>
                    ) : (
                      <span className="muted small">Cuenta general</span>
                    )}
                  </td>
                  <td>{p.usuario_nombre}</td>
                  <td>{p.usuario_cierre_nombre || "—"}</td>
                  <td>
                    <span className={claseFormaPago(p.forma_pago)}>
                      {p.forma_pago}
                    </span>
                  </td>
                  <td className="muted small historial-productos">
                    {p.productos.join(", ")}
                  </td>
                  <td className="historial-total">
                    <strong>{formatearPrecio(p.total)}</strong>
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td colSpan={9} className="empty-state">
                    No hay ventas que coincidan con los filtros.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
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
