/** Pantalla de Pedido por Mesa - POS para mesero/administrador. */

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../services/api";
import { formatearPrecio } from "../utils/format";
import CuentaModal from "../components/CuentaModal";
import DivisionModal from "../components/DivisionModal";
import TransferirModal from "../components/TransferirModal";
import CobroModal from "../components/CobroModal";

interface Mesa {
  id: number;
  numero: number;
  capacidad: number;
  estado: string;
  tipo?: string;
  grupo?: string | null;
  posiciones?: { id: number; posicion: number; estado: string }[];
}

interface Producto {
  id: number;
  nombre: string;
  precio: number;
  stock: number;
  categoria_id?: number | null;
}

interface Categoria {
  id: number;
  nombre: string;
  total_productos: number;
}

interface ItemCarrito {
  producto_id: number;
  nombre: string;
  precio: number;
  cantidad: number;
}

interface Pedido {
  id: number;
  mesa?: { numero: number } | null;
  total: number;
  estado: string;
  items: {
    id?: number;
    producto_id?: number;
    producto_nombre: string;
    cantidad: number;
    subtotal: number;
  }[];
}

export default function PedidoMesaPage() {
  const [searchParams] = useSearchParams();
  const [mesas, setMesas] = useState<Mesa[]>([]);
  const [productos, setProductos] = useState<Producto[]>([]);
  const [pedidos, setPedidos] = useState<Pedido[]>([]);
  const [mesaId, setMesaId] = useState<number | "">("");
  const [carrito, setCarrito] = useState<ItemCarrito[]>([]);
  const [cantidades, setCantidades] = useState<Record<number, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);

  // Modales de cuenta, división y transferencia
  const [mostrarCuenta, setMostrarCuenta] = useState(false);
  const [mostrarDivision, setMostrarDivision] = useState(false);
  const [mostrarTransferir, setMostrarTransferir] = useState(false);
  const [pedidoACobrar, setPedidoACobrar] = useState<Pedido | null>(null);
  const [categorias, setCategorias] = useState<Categoria[]>([]);
  const [categoriaFiltro, setCategoriaFiltro] = useState<number | "">("");

  const usuario = JSON.parse(localStorage.getItem("user") || "{}");
  const usuarioId: number = usuario?.id || 1;

  const total = useMemo(
    () => carrito.reduce((sum, item) => sum + item.precio * item.cantidad, 0),
    [carrito]
  );

  /**
   * Mesa o barra seleccionada en el desplegable.
   *
   * En una barra, el desplegable usa el id de la plaza activa. Si la URL
   * trae el id de otra plaza, se busca dentro de `posiciones` para saber a
   * qué barra pertenece.
   */
  const mesaSeleccionada = useMemo(() => {
    const directa = mesas.find((m) => m.id === mesaId);
    if (directa?.tipo === "barra") return directa;

    const barra = mesas.find(
      (m) =>
        m.tipo === "barra" &&
        (m.posiciones || []).some((p) => p.id === mesaId)
    );
    return barra || directa || null;
  }, [mesas, mesaId]);

  /**
   * Número de barra cuando la selección es una barra.
   * El backend lista la barra como una sola tarjeta con el número de barra,
   * aunque internamente los pedidos se guarden por plaza.
   */
  const barraNumero =
    mesaSeleccionada?.tipo === "barra" ? mesaSeleccionada.numero : null;

  const etiquetaMesa = (m: Mesa) =>
    m.tipo === "barra" ? `Barra ${m.numero}` : `Mesa ${m.numero}`;

  const cargarCatalogos = async () => {
    try {
      const [m, inv, cats]: any = await Promise.all([
        api.getMesas(),
        api.getProductos({ limite: 500, categoria_id: categoriaFiltro || undefined }),
        api.getCategorias(),
      ]);
      setMesas(m);
      setProductos(inv.items);
      setCategorias(cats);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const cargarPedidos = async (id: number) => {
    try {
      const data: any = await api.getPedidosMesa(id);
      setPedidos(data.filter((p: Pedido) => p.estado === "abierto"));
    } catch (err: any) {
      setError(err.message);
    }
  };

  useEffect(() => {
    cargarCatalogos();
  }, []);

  // Mesa seleccionada automáticamente al venir desde el panel de Mesas
  useEffect(() => {
    const mesaParam = searchParams.get("mesa");
    if (mesaParam) {
      setMesaId(Number(mesaParam));
      setCarrito([]);
      setCantidades({});
      setMensaje(null);
      setError(null);
    }
  }, [searchParams]);

  useEffect(() => {
    if (mesaId) cargarPedidos(Number(mesaId));
    else setPedidos([]);
  }, [mesaId]);

  useEffect(() => {
    cargarCatalogos();
  }, [categoriaFiltro]);

  const agregarCantidad = (producto: Producto, cantidad: number): boolean => {
    setError(null);
    setMensaje(null);

    if (!Number.isInteger(cantidad) || cantidad <= 0) {
      setError("Ingresá una cantidad válida mayor a cero");
      return false;
    }

    const enCarrito =
      carrito.find((i) => i.producto_id === producto.id)?.cantidad || 0;
    if (enCarrito + cantidad > producto.stock) {
      const disponible = Math.max(producto.stock - enCarrito, 0);
      setError(
        `Stock insuficiente de ${producto.nombre}. Disponible: ${disponible}`
      );
      return false;
    }

    setCarrito((actual) => {
      const existe = actual.find((i) => i.producto_id === producto.id);
      if (existe) {
        return actual.map((i) =>
          i.producto_id === producto.id
            ? { ...i, cantidad: i.cantidad + cantidad }
            : i
        );
      }
      return [
        ...actual,
        {
          producto_id: producto.id,
          nombre: producto.nombre,
          precio: producto.precio,
          cantidad,
        },
      ];
    });
    return true;
  };

  const agregar = (producto: Producto) => {
    agregarCantidad(producto, 1);
  };

  /** Solo admite digitos en el cuadro de cantidad. */
  const actualizarCantidad = (productoId: number, valor: string) => {
    const soloNumeros = valor.replace(/\D/g, "");
    setCantidades((actual) => ({ ...actual, [productoId]: soloNumeros }));
  };

  const agregarDesdeInput = (producto: Producto) => {
    const cantidad = Number(cantidades[producto.id] || 0);
    if (agregarCantidad(producto, cantidad)) {
      setCantidades((actual) => ({ ...actual, [producto.id]: "" }));
    }
  };

  const quitar = (productoId: number) => {
    setCarrito((actual) =>
      actual
        .map((i) =>
          i.producto_id === productoId ? { ...i, cantidad: i.cantidad - 1 } : i
        )
        .filter((i) => i.cantidad > 0)
    );
  };

  const confirmarPedido = async () => {
    if (!mesaId) {
      setError("Selecciona una mesa");
      return;
    }
    if (carrito.length === 0) {
      setError("Agrega al menos un producto");
      return;
    }

    try {
      await api.createPedido({
        mesa_id: Number(mesaId),
        usuario_id: usuarioId,
        items: carrito.map((i) => ({
          producto_id: i.producto_id,
          cantidad: i.cantidad,
        })),
      });
      setCarrito([]);
      setCantidades({});
      setMensaje("Pedido registrado correctamente");
      setError(null);
      await Promise.all([cargarCatalogos(), cargarPedidos(Number(mesaId))]);
    } catch (err: any) {
      setError(err.message);
    }
  };

  /** Ajusta la cantidad de una linea de un pedido abierto */
  const ajustarLinea = async (pedidoId: number, itemId: number, cantidad: number) => {
    try {
      await api.ajustarItemPedido(pedidoId, itemId, cantidad);
      await Promise.all([cargarPedidos(Number(mesaId)), cargarCatalogos()]);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const cerrarPedido = async (pedidoId: number, formaPago = "efectivo") => {
    try {
      await api.closePedido(pedidoId, formaPago);
      setPedidoACobrar(null);
      setMensaje(`Pedido #${pedidoId} cerrado y cobrado (${formaPago})`);
      await Promise.all([
        cargarCatalogos(),
        mesaId ? cargarPedidos(Number(mesaId)) : Promise.resolve(),
      ]);
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className="page">
      <div className="page-head">
        <h2>Pedido por mesa</h2>
        <div className="filters">
          <select
            className="select-mesa"
            value={mesaId}
            onChange={(e) => {
              setMesaId(e.target.value ? Number(e.target.value) : "");
              setCarrito([]);
              setCantidades({});
              setMensaje(null);
            }}
          >
            <option value="">— Seleccionar mesa o barra —</option>
            {mesas.map((m) => (
              <option key={m.id} value={m.id}>
                {etiquetaMesa(m)} ({m.estado})
              </option>
            ))}
          </select>
          <select
            className="select-categoria"
            value={categoriaFiltro}
            onChange={(e) =>
              setCategoriaFiltro(e.target.value ? Number(e.target.value) : "")
            }
          >
            <option value="">Todas las categorías</option>
            {categorias.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nombre}
              </option>
            ))}
          </select>
          {mesaId !== "" && (
            <button
              className="btn-secondary"
              onClick={() => setMostrarCuenta(true)}
            >
              Ver cuenta
            </button>
          )}
        </div>
      </div>

      {error && <p className="error-msg">{error}</p>}
      {mensaje && <p className="success-msg">{mensaje}</p>}

      <div className="pos-grid">
        <section className="panel">
          <h3>Productos disponibles</h3>
          <div className="table-wrap productos-scroll">
            <table>
              <thead>
                <tr>
                  <th>Producto</th>
                  <th>Precio</th>
                  <th>Stock</th>
                  <th>Agregar</th>
                </tr>
              </thead>
              <tbody>
                {productos.map((p) => (
                  <tr key={p.id}>
                    <td>{p.nombre}</td>
                    <td>{formatearPrecio(p.precio)}</td>
                    <td>{p.stock}</td>
                    <td>
                      <div className="producto-acciones">
                        <input
                          type="text"
                          inputMode="numeric"
                          pattern="[0-9]*"
                          className="cantidad-input"
                          placeholder="Cant."
                          aria-label={`Cantidad de ${p.nombre}`}
                          value={cantidades[p.id] ?? ""}
                          onChange={(e) =>
                            actualizarCantidad(p.id, e.target.value)
                          }
                          onKeyDown={(e) => {
                            if (e.key === "Enter") {
                              e.preventDefault();
                              agregarDesdeInput(p);
                            }
                          }}
                          disabled={p.stock === 0}
                        />
                        <button
                          className="btn-success btn-small"
                          disabled={p.stock === 0}
                          onClick={() => agregarDesdeInput(p)}
                          title={`Agregar la cantidad indicada de ${p.nombre}`}
                        >
                          Agregar
                        </button>
                        <button
                          className="btn-primary btn-small"
                          disabled={p.stock === 0}
                          onClick={() => agregar(p)}
                          title={`Agregar una unidad de ${p.nombre}`}
                        >
                          +
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="panel">
          <h3>Pedido actual</h3>
          {carrito.length === 0 ? (
            <p className="empty-state">Sin productos seleccionados.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Producto</th>
                    <th>Cant.</th>
                    <th>Subtotal</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {carrito.map((i) => (
                    <tr key={i.producto_id}>
                      <td>{i.nombre}</td>
                      <td>{i.cantidad}</td>
                      <td>{formatearPrecio(i.precio * i.cantidad)}</td>
                      <td>
                        <button
                          className="btn-icon danger"
                          onClick={() => quitar(i.producto_id)}
                        >
                          ×
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="total-row">
            <span>Total</span>
            <strong>{formatearPrecio(total)}</strong>
          </div>

          <button className="btn-primary btn-block" onClick={confirmarPedido}>
            Confirmar pedido
          </button>
        </section>
      </div>

      <section className="panel">
        <h3>Pedidos abiertos de la mesa</h3>
        {pedidos.length === 0 ? (
          <p className="empty-state">No hay pedidos abiertos.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Productos</th>
                  <th>Total</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {pedidos.map((p) => (
                  <tr key={p.id}>
                    <td>{p.id}</td>
                    <td>
                      {p.items.map((i) => (
                        <div key={i.producto_id} className="linea-pedido">
                          <span>
                            {i.cantidad} × {i.producto_nombre}
                          </span>
                          {i.id !== undefined && (
                            <span className="linea-acciones">
                              <button
                                className="btn-icon"
                                title="Quitar una unidad"
                                onClick={() =>
                                  ajustarLinea(p.id, i.id as number, i.cantidad - 1)
                                }
                              >
                                −
                              </button>
                              <button
                                className="btn-icon"
                                title="Añadir una unidad"
                                onClick={() =>
                                  ajustarLinea(p.id, i.id as number, i.cantidad + 1)
                                }
                              >
                                +
                              </button>
                            </span>
                          )}
                        </div>
                      ))}
                    </td>
                    <td>{formatearPrecio(p.total)}</td>
                    <td>
                      <button
                        className="btn-primary btn-small"
                        onClick={() => setPedidoACobrar(p)}
                      >
                        Cobrar / cerrar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Ventana de cobro de un pedido */}
      {pedidoACobrar && (
        <CobroModal
          titulo={`Cobrar pedido #${pedidoACobrar.id}`}
          total={pedidoACobrar.total}
          error={error}
          onClose={() => setPedidoACobrar(null)}
          confirmar={(formaPago) => cerrarPedido(pedidoACobrar.id, formaPago)}
        />
      )}

      {/* Ventana de cuenta de la mesa */}
      {mostrarCuenta && mesaId !== "" && (
        <CuentaModal
          mesaId={Number(mesaId)}
          barraNumero={barraNumero}
          onClose={() => setMostrarCuenta(false)}
          onDividir={() => {
            setMostrarCuenta(false);
            setMostrarDivision(true);
          }}
          onTransferir={() => {
            setMostrarCuenta(false);
            setMostrarTransferir(true);
          }}
          onActualizado={() => {
            cargarPedidos(Number(mesaId));
            cargarCatalogos();
          }}
        />
      )}

      {/* Ventana de división de cuenta */}
      {mostrarDivision && mesaId !== "" && (
        <DivisionModal
          mesaId={Number(mesaId)}
          barraNumero={barraNumero}
          onClose={() => setMostrarDivision(false)}
          onConfirmado={() => {
            cargarPedidos(Number(mesaId));
            cargarCatalogos();
          }}
        />
      )}

      {/* Ventana de transferencia de cuenta */}
      {mostrarTransferir && mesaId !== "" && (
        <TransferirModal
          mesaId={Number(mesaId)}
          barraNumero={barraNumero ?? undefined}
          onClose={() => setMostrarTransferir(false)}
          onTransferido={() => {
            setMostrarTransferir(false);
            cargarPedidos(Number(mesaId));
            cargarCatalogos();
          }}
        />
      )}
    </div>
  );
}
