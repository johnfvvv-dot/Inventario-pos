/** Pantalla de Inventario - Administrador */
import { useEffect, useState } from "react";
import { api } from "../services/api";
import { Link } from "react-router-dom";

export default function InventarioPage() {
  const [productos, setProductos] = useState<any[]>([]);
  const [nuevoProducto, setNuevoProducto] = useState({
    nombre: "",
    descripcion: "",
    precio: 0,
    stock: 0,
  });
  const [error, setError] = useState<string | null>(null);
  const [mostrarForm, setMostrarForm] = useState(false);

  // Cargar productos al inicializar
  useEffect(() => {
    fetchProductos();
  }, []);

  const fetchProductos = async () => {
    try {
      const data = await api.getProductos();
      setProductos(data);
    } catch (err: any) {
      setError("Error al cargar productos: " + err.message);
    }
  };

  const handleCreateProducto = async () => {
    try {
      const data = await api.createProducto(nuevoProducto);
      setProductos((prev) => [...prev, data]);
      setNuevoProducto({ nombre: "", descripcion: "", precio: 0, stock: 0 });
      setMostrarForm(false);
    } catch (err: any) {
      setError("Error al crear producto: " + err.message);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("¿Eliminar este producto?")) return;
    try {
      await fetch(`${api.api.defaults.baseURL}/inventario/${id}`, {
        method: "DELETE",
      });
      setProductos((prev) => prev.filter((p: any) => p.id !== id));
    } catch (err: any) {
      setError("Error al eliminar: " + err.message);
    }
  };

  return (
    <div className="inventario-page">
      <h2>INVENTARIO DE PRODUCTOS</h2>

      {/* Barra de acciones */}
      <div className="page-actions">
        <Link to="/admin/pedidos" className="btn-secondary">
          ← Volver a Pedidos
        </Link>
        <button
          onClick={() => setMostrarForm(true)}
          className="btn-primary"
        >
          Añadir Nuevo Producto
        </button>
      </div>

      {/* Formulario para añadir producto */}
      {mostrarForm && (
        <div className="modal-overlay">
          <div className="modal-box">
            <h3>Añadir Producto</h3>
            <form
              onSubmit={async (e: React.FormEvent) => {
                e.preventDefault();
                await handleCreateProducto();
              }}
            >
              <div className="form-row">
                <div className="form-group">
                  <label>Nombre *</label>
                  <input
                    type="text"
                    value={nuevoProducto.nombre}
                    onChange={(e) =>
                      setNuevoProducto((prev) => ({ ...prev, nombre: e.target.value }))
                    }
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Precio *</label>
                  <input
                    type="number"
                    value={nuevoProducto.precio}
                    onChange={(e) =>
                      setNuevoProducto(
                        (prev) => ({ ...prev, precio: Number(e.target.value) })
                      )
                    }
                    required
                  />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Stock Inicial</label>
                  <input
                    type="number"
                    value={nuevoProducto.stock}
                    onChange={(e) =>
                      setNuevoProducto(
                        (prev) => ({ ...prev, stock: Number(e.target.value) })
                      )
                    }
                  />
                </div>
                <div className="form-group">
                  <label>Descripción</label>
                  <input
                    type="text"
                    value={nuevoProducto.descripcion}
                    onChange={(e) =>
                      setNuevoProducto(
                        (prev) => ({ ...prev, descripcion: e.target.value })
                      )
                    }
                  />
                </div>
              </div>

              <div className="-actions">
                <button type="submit" className="btn-save">
                  Guardar Producto
                </button>
                <button
                  type="button"
                  onClick={() => setMostrarForm(false)}
                  className="btn-cancel"
                >
                  Cancelar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Tabla de productos */}
      {error && <p className="error-msg">{error}</p>}

      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Nombre</th>
            <th>Precio</th>
            <th>Stock Actual</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {productos.map((producto: any) => (
            <tr key={producto.id}>
              <td>{producto.id}</td>
              <td>{producto.nombre}</td>
              <td>${producto.precio.toFixed(2)}</td>
              <td>
                <span
                  className={
                    producto.stock <= 0
                      ? "stock-agotado"
                      : producto.stock < 10
                      ? "stock-bajo"
                      : "stock-bien"
                  }
                >
                  {producto.stock}
                </span>
              </td>
              <td>
                <button
                  onClick={() => console.log("Editar", producto.id)}
                  title="Editar"
                  className="btn-action"
                >
                  ✎
                </button>
                <button
                  onClick={handleDelete}
                  onClick={() => console.log("Eliminar", producto.id)}
                  title="Eliminar"
                  className="btn-delete"
                >
                  ×
                </button>
              </td>
            </tr>
          ))}
          {productos.length === 0 && (
            <tr>
              <td colSpan={5} className="empty-state">
                No hay productos en inventario
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}