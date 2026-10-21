/** Pantalla de Inventario - Administrador. Búsqueda, paginación y categorías. */

import { FormEvent, useEffect, useState } from "react";
import { api } from "../services/api";

interface Producto {
  id: number;
  nombre: string;
  descripcion?: string;
  precio: number;
  stock: number;
  categoria_id?: number | null;
}

interface Categoria {
  id: number;
  nombre: string;
  activa: boolean;
  total_productos: number;
}

const POR_PAGINA = 20;

/**
 * Convierte lo que escribe el usuario a número.
 * Acepta formato español: "2,50" -> 2.50  |  "2.500,00" -> 2500
 * y formato inglés: "2.50" -> 2.50
 */
const parseNumero = (valor: string): number => {
  if (!valor) return 0;
  let texto = valor.trim().replace(/\s/g, "");
  if (texto.includes(",")) {
    texto = texto.replace(/\./g, "").replace(",", ".");
  }
  const numero = Number(texto);
  return isNaN(numero) ? 0 : numero;
};

export default function InventarioPage() {
  // El Bartender solo consulta: no puede crear, editar ni eliminar
  const usuario = JSON.parse(localStorage.getItem("user") || "{}");
  const soloLectura = usuario?.rol !== "admin";

  const [productos, setProductos] = useState<Producto[]>([]);
  const [categorias, setCategorias] = useState<Categoria[]>([]);
  const [total, setTotal] = useState(0);
  const [pagina, setPagina] = useState(0);
  const [buscar, setBuscar] = useState("");
  const [categoriaFiltro, setCategoriaFiltro] = useState<number | "">("");
  const [mostrarForm, setMostrarForm] = useState(false);
  const [mostrarCategorias, setMostrarCategorias] = useState(false);
  const [editando, setEditando] = useState<Producto | null>(null);
  const [nuevoProducto, setNuevoProducto] = useState({
    nombre: "",
    descripcion: "",
    precio: "",
    stock: "",
    categoria_id: "" as number | "",
  });
  const [nuevaCategoria, setNuevaCategoria] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);

  const cargar = async () => {
    try {
      const data: any = await api.getProductos({
        buscar: buscar || undefined,
        categoria_id: categoriaFiltro || undefined,
        limite: POR_PAGINA,
        offset: pagina * POR_PAGINA,
      });
      setProductos(data.items);
      setTotal(data.total);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const cargarCategorias = async () => {
    try {
      const data: any = await api.getCategorias();
      setCategorias(data);
    } catch (err: any) {
      setError(err.message);
    }
  };

  useEffect(() => {
    cargar();
  }, [pagina, categoriaFiltro]);

  useEffect(() => {
    cargarCategorias();
  }, []);

  // Búsqueda con retardo (evita una petición por cada tecla)
  useEffect(() => {
    const t = setTimeout(() => {
      setPagina(0);
      cargar();
    }, 350);
    return () => clearTimeout(t);
  }, [buscar]);

  const guardarProducto = async (e: FormEvent) => {
    e.preventDefault();
    try {
      const datos = {
        nombre: nuevoProducto.nombre.trim(),
        descripcion: nuevoProducto.descripcion.trim() || undefined,
        precio: parseNumero(nuevoProducto.precio),
        stock: parseNumero(nuevoProducto.stock || "0"),
        categoria_id: nuevoProducto.categoria_id || null,
      };
      if (editando) {
        await api.updateProducto(editando.id, datos as any);
        setMensaje(`Producto "${datos.nombre}" actualizado`);
      } else {
        await api.createProducto(datos as any);
        setMensaje(`Producto "${datos.nombre}" agregado`);
      }
      setNuevoProducto({
        nombre: "",
        descripcion: "",
        precio: "",
        stock: "",
        categoria_id: "",
      });
      setMostrarForm(false);
      setEditando(null);
      await Promise.all([cargar(), cargarCategorias()]);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const abrirEdicion = (p: Producto) => {
    setEditando(p);
    setNuevoProducto({
      nombre: p.nombre,
      descripcion: p.descripcion || "",
      precio: String(p.precio),
      stock: String(p.stock),
      categoria_id: p.categoria_id || "",
    });
    setMostrarForm(true);
  };

  const eliminar = async (id: number) => {
    if (!window.confirm("¿Eliminar este producto?")) return;
    try {
      await api.deleteProducto(id);
      await Promise.all([cargar(), cargarCategorias()]);
    } catch (err: any) {
      setError(err.message);
    }
  };

  /** Guarda el stock ingresado manualmente en la casilla */
  const guardarStock = async (id: number, stock: number) => {
    try {
      await api.updateProductoStock(id, stock);
      await cargar();
    } catch (err: any) {
      setError(err.message);
      await cargar();
    }
  };

  const ajustarStock = async (id: number, stockActual: number, delta: number) => {
    try {
      await api.updateProductoStock(id, Math.max(0, stockActual + delta));
      await cargar();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const crearCategoria = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await api.createCategoria(nuevaCategoria.trim());
      setNuevaCategoria("");
      await cargarCategorias();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const eliminarCategoria = async (id: number) => {
    if (!window.confirm("¿Eliminar la categoría? Los productos quedan sin categoría.")) return;
    try {
      await api.eliminarCategoria(id);
      await Promise.all([cargarCategorias(), cargar()]);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const paginas = Math.max(1, Math.ceil(total / POR_PAGINA));
  const nombreCategoria = (id?: number | null) =>
    categorias.find((c) => c.id === id)?.nombre || "—";

  return (
    <div className="page">
      <div className="page-head">
        <h2>Inventario de productos</h2>
        <div className="filters">
          {!soloLectura && (
            <button
              className="btn-secondary"
              onClick={() => setMostrarCategorias(true)}
            >
              Categorías ({categorias.length})
            </button>
          )}
          {soloLectura && <span className="badge badge-warning">Solo lectura</span>}
          {!soloLectura && (
          <button
            className="btn-primary"
            onClick={() => {
              setEditando(null);
              setNuevoProducto({
                nombre: "",
                descripcion: "",
                precio: "",
                stock: "",
                categoria_id: "",
              });
              setMostrarForm(true);
            }}
          >
            + Añadir producto
          </button>
          )}
        </div>
      </div>

      {error && <p className="error-msg">{error}</p>}
      {mensaje && <p className="success-msg">{mensaje}</p>}

      {/* Filtros */}
      <div className="filtros-barra">
        <input
          type="search"
          className="input-busqueda"
          placeholder="Buscar producto..."
          value={buscar}
          onChange={(e) => setBuscar(e.target.value)}
        />
        <select
          value={categoriaFiltro}
          onChange={(e) => {
            setCategoriaFiltro(e.target.value ? Number(e.target.value) : "");
            setPagina(0);
          }}
        >
          <option value="">Todas las categorías</option>
          {categorias.map((c) => (
            <option key={c.id} value={c.id}>
              {c.nombre} ({c.total_productos})
            </option>
          ))}
        </select>
        <span className="muted small">
          {total} producto{total !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Tabla */}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Nombre</th>
              <th>Categoría</th>
              <th>Precio</th>
              <th>Stock</th>
              {!soloLectura && <th>Acciones</th>}
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
                <td className="muted small">{nombreCategoria(p.categoria_id)}</td>
                <td>${p.precio.toFixed(2)}</td>
                <td>
                  {soloLectura ? (
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
                  ) : (
                    <div className="stock-editor">
                      <input
                        type="number"
                        min="0"
                        className="stock-input"
                        defaultValue={p.stock}
                        onBlur={(e) => {
                          const valor = Math.max(0, parseNumero(e.target.value));
                          if (valor !== p.stock) {
                            guardarStock(p.id, valor);
                          }
                        }}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") (e.target as HTMLInputElement).blur();
                        }}
                      />
                      <div className="stock-acciones">
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
                      </div>
                    </div>
                  )}
                </td>
                {!soloLectura && (
                  <td className="actions">
                    <button
                      className="btn-icon"
                      title="Editar"
                      onClick={() => abrirEdicion(p)}
                    >
                      ✎
                    </button>
                    <button
                      className="btn-icon danger"
                      title="Eliminar"
                      onClick={() => eliminar(p.id)}
                    >
                      ×
                    </button>
                  </td>
                )}
              </tr>
            ))}
            {productos.length === 0 && (
              <tr>
                <td colSpan={soloLectura ? 5 : 6} className="empty-state">
                  {buscar || categoriaFiltro
                    ? "Sin resultados para el filtro aplicado."
                    : "No hay productos registrados."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Paginación */}
      {paginas > 1 && (
        <div className="paginacion">
          <button
            className="btn-secondary btn-small"
            disabled={pagina === 0}
            onClick={() => setPagina((p) => p - 1)}
          >
            ‹ Anterior
          </button>
          <span className="muted small">
            Página {pagina + 1} de {paginas}
          </span>
          <button
            className="btn-secondary btn-small"
            disabled={pagina >= paginas - 1}
            onClick={() => setPagina((p) => p + 1)}
          >
            Siguiente ›
          </button>
        </div>
      )}

      {/* Formulario */}
      {mostrarForm && (
        <div className="modal-overlay" onClick={() => setMostrarForm(false)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <h3>{editando ? `Editar: ${editando.nombre}` : "Nuevo producto"}</h3>
              <button className="btn-icon" onClick={() => setMostrarForm(false)}>
                ×
              </button>
            </div>
            <form onSubmit={guardarProducto}>
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
                  <label>Stock</label>
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
                <label>Categoría</label>
                <select
                  value={nuevoProducto.categoria_id}
                  onChange={(e) =>
                    setNuevoProducto((p) => ({
                      ...p,
                      categoria_id: e.target.value ? Number(e.target.value) : "",
                    }))
                  }
                >
                  <option value="">Sin categoría</option>
                  {categorias.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.nombre}
                    </option>
                  ))}
                </select>
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
                  onClick={() => {
                    setMostrarForm(false);
                    setEditando(null);
                  }}
                >
                  Cancelar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Categorías */}
      {mostrarCategorias && (
        <div className="modal-overlay" onClick={() => setMostrarCategorias(false)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <h3>Categorías</h3>
              <button className="btn-icon" onClick={() => setMostrarCategorias(false)}>
                ×
              </button>
            </div>

            <form className="inline-form" onSubmit={crearCategoria}>
              <div className="form-group">
                <label>Nueva categoría</label>
                <input
                  value={nuevaCategoria}
                  onChange={(e) => setNuevaCategoria(e.target.value)}
                  placeholder="Ej: Bebidas"
                />
              </div>
              <button type="submit" className="btn-primary">
                + Crear
              </button>
            </form>

            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Categoría</th>
                    <th>Productos</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {categorias.map((c) => (
                    <tr key={c.id}>
                      <td>{c.nombre}</td>
                      <td>{c.total_productos}</td>
                      <td className="actions">
                        <button
                          className="btn-icon danger"
                          title="Eliminar"
                          onClick={() => eliminarCategoria(c.id)}
                        >
                          ×
                        </button>
                      </td>
                    </tr>
                  ))}
                  {categorias.length === 0 && (
                    <tr>
                      <td colSpan={3} className="empty-state">
                        Todavía no hay categorías.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
