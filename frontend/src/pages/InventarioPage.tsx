/** Pantalla de Inventario - Administrador. */

import { FormEvent, useEffect, useState } from "react";
import { api } from "../services/api";

interface Producto {
  id: number;
  nombre: string;
  descripcion?: string;
  precio: number;
  stock: number;
}

export default function InventarioPage() {
  const [productos, setProductos] = useState<Producto[]>([]);
  const [mostrarForm, setMostrarForm] = useState(false);
  const [nuevoProducto, setNuevoProducto] = useState({
    nombre: "",
    descripcion: "",
    precio: "",
    stock: "",
  });
  const [error, setError] = useState<string | null>(null);

  const cargarProductos = async () => {
    try {
      const data: any = await api.getProductos();
      setProductos(data);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    }
  };

  useEffect(() => {
    cargarProductos();
  }, []);

  const crearProducto = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await api.createProducto({
        nombre: nuevoProducto.nombre.trim(),
        descripcion: nuevoProducto.descripcion.trim() || undefined,
        precio: Number(nuevoProducto.precio),
        stock: Number(nuevoProducto.stock || 0),
      });
      setNuevoProducto({ nombre: "", descripcion: "", precio: "", stock: "" });
      setMostrarForm(false);
      await cargarProductos();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const eliminarProducto = async (id: number) => {
    if (!window.confirm("¿Eliminar este producto?")) return;
    try {
      await api.deleteProducto(id);
      await cargarProductos();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const ajustarStock = async (id: number, stockActual: number, delta: number) => {
    const nuevo = Math.max(0, stockActual + delta);
    try {
      await api.updateProductoStock(id, nuevo);
      await cargarProductos();
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className="page">
      <div className="page-head">
        <h2>Inventario de productos</h2>
        <button className="btn-primary" onClick={() => setMostrarForm(true)}>
          + Añadir producto
        </button>
      </div>

      {error && <p className="error-msg">{error}</p>}

      {mostrarForm && (
        <div className="modal-overlay">
          <div className="modal-box">
            <h3>Nuevo producto</h3>
            <form onSubmit={crearProducto}>
              <div className="form-group">
                <label>Nombre *</label>
                <input
                  value={nuevoProducto.nombre}
                  onChange={(e) =>
                    setNuevoProducto((p) => ({ ...p, nombre: e.target.value }))
                  }
                  required
                />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Precio *</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    value={nuevoProducto.precio}
                    onChange={(e) =>
                      setNuevoProducto((p) => ({ ...p, precio: e.target.value }))
                    }
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Stock inicial</label>
                  <input
                    type="number"
                    min="0"
                    value={nuevoProducto.stock}
                    onChange={(e) =>
                      setNuevoProducto((p) => ({ ...p, stock: e.target.value }))
                    }
                  />
                </div>
              </div>
              <div className="form-group">
                <label>Descripción</label>
                <input
                  value={nuevoProducto.descripcion}
                  onChange={(e) =>
                    setNuevoProducto((p) => ({ ...p, descripcion: e.target.value }))
                  }
                />
              </div>
              <div className="modal-actions">
                <button type="submit" className="btn-primary">
                  Guardar
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setMostrarForm(false)}
                >
                  Cancelar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Nombre</th>
              <th>Precio</th>
              <th>Stock</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {productos.map((p) => (
              <tr key={p.id}>
                <td>{p.id}</td>
                <td>
                  <strong>{p.nombre}</strong>
                  {p.descripcion && <div className="muted small">{p.descripcion}</div>}
                </td>
                <td>${p.precio.toFixed(2)}</td>
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
                    {p.stock}
                  </span>
                </td>
                <td className="actions">
                  <button
                    className="btn-icon"
                    title="Restar 1"
                    onClick={() => ajustarStock(p.id, p.stock, -1)}
                  >
                    −
                  </button>
                  <button
                    className="btn-icon"
                    title="Sumar 1"
                    onClick={() => ajustarStock(p.id, p.stock, +1)}
                  >
                    +
                  </button>
                  <button
                    className="btn-icon danger"
                    title="Eliminar"
                    onClick={() => eliminarProducto(p.id)}
                  >
                    ×
                  </button>
                </td>
              </tr>
            ))}
            {productos.length === 0 && (
              <tr>
                <td colSpan={5} className="empty-state">
                  No hay productos registrados.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
