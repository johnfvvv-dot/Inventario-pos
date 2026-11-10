/** Pantalla de Pedido por Mesa - POS para mesero/administrador. */

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../services/api";
import { formatearPrecio } from "../utils/format";
import {
  MENSAJE_TURNO_REQUERIDO,
  useTurno,
} from "../context/TurnoContext";
import CuentaModal from "../components/CuentaModal";
import DivisionModal from "../components/DivisionModal";
import TransferirModal from "../components/TransferirModal";
import CobroModal from "../components/CobroModal";
import TurnoRequeridoAviso from "../components/TurnoRequeridoAviso";
import AsignarPedidoModal, {
  type DestinoPedido,
} from "../components/AsignarPedidoModal";

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
  participante_id?: number | null;
  alias?: string | null;
  items: {
    id?: number;
    producto_id?: number;
    producto_nombre: string;
    cantidad: number;
    subtotal: number;
  }[];
}

interface ParticipanteCuenta {
  id: number;
  alias: string;
  subtotal: number;
  pagado: boolean;
  items: { producto_nombre: string; cantidad: number; subtotal: number }[];
}

interface DivisionCuenta {
  id: number;
  total: number;
  total_pendiente: number;
  estado: string;
  participantes: ParticipanteCuenta[];
}

interface CuentaData {
  total: number;
  total_general: number;
  total_divisiones: number;
  pedidos: Pedido[];
  divisiones: DivisionCuenta[];
}

export default function PedidoMesaPage() {
  const [searchParams] = useSearchParams();
  const { turno, cargando: cargandoTurno, solicitarApertura } = useTurno();
  const sinTurno = !cargandoTurno && !turno;
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

  // Cuenta actual y destinos posibles para el nuevo pedido
  const [cuenta, setCuenta] = useState<CuentaData | null>(null);
  const [destinos, setDestinos] = useState<DestinoPedido[]>([]);
  const [mostrarAsignacion, setMostrarAsignacion] = useState(false);
  const [errorAsignacion, setErrorAsignacion] = useState<string | null>(null);
  const [procesandoAsignacion, setProcesandoAsignacion] = useState(false);

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

  const etiquetaCuenta = barraNumero
    ? `Barra ${barraNumero}`
    : mesaSeleccionada
    ? `Mesa ${mesaSeleccionada.numero}`
    : "la cuenta";

  const aliasActivos = destinos.filter((d) => !d.esGeneral && !d.pagado);

  // Los pedidos asignados a un alias se ocultan cuando ese cliente ya pagó:
  // siguen guardados para el historial, pero ya no forman parte de la cuenta.
  const pedidosVisibles = pedidos.filter((p) => {
    if (p.estado === "abierto") return true;
    if (p.estado !== "dividido" || p.participante_id == null) return false;
    return destinos.some(
      (d) => d.participanteId === p.participante_id && !d.pagado
    );
  });

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

  const cargarPedidos = async (id: number, barra?: number | null) => {
    try {
      const data: any = barra
        ? await api.getPedidosBarra(barra)
        : await api.getPedidosMesa(id);
      // La cuenta general son los pedidos abiertos. Los pedidos asignados a
      // un alias quedan "dividido" y se muestran solo como información.
      setPedidos(
        data.filter(
          (p: Pedido) =>
            p.estado === "abierto" ||
            (p.estado === "dividido" && p.participante_id != null)
        )
      );
    } catch (err: any) {
      setError(err.message);
    }
  };

  const destinosDesdeCuenta = (data: CuentaData): DestinoPedido[] => {
    const deAlias: DestinoPedido[] = (data.divisiones || []).flatMap((d) =>
      (d.participantes || []).map((p) => ({
        participanteId: p.id,
        alias: p.alias,
        divisionId: d.id,
        subtotal: p.subtotal,
        pagado: p.pagado,
        itemsCount: p.items?.length || 0,
      }))
    );
    return [
      ...deAlias,
      {
        participanteId: null,
        alias: barraNumero
          ? "Cuenta General de la Barra"
          : "Cuenta General de la Mesa",
        subtotal: data.total_general || 0,
        pagado: false,
        itemsCount: data.pedidos?.length || 0,
        esGeneral: true,
      },
    ];
  };

  const cargarCuenta = async (): Promise<CuentaData | null> => {
    if (mesaId === "") return null;
    try {
      const data: any = barraNumero
        ? await api.getCuentaBarra(barraNumero)
        : await api.getCuentaMesa(Number(mesaId));
      setCuenta(data);
      setDestinos(destinosDesdeCuenta(data));
      return data;
    } catch (err: any) {
      setError(err.message);
      return null;
    }
  };

  const crearPedido = async (
    participanteId: number | null,
    etiquetaDestino: string,
    desdeModal = false
  ) => {
    if (!mesaId) return;
    setProcesandoAsignacion(true);
    if (desdeModal) setErrorAsignacion(null);
    try {
      await api.createPedido({
        mesa_id: Number(mesaId),
        usuario_id: usuarioId,
        participante_id: participanteId,
        items: carrito.map((i) => ({
          producto_id: i.producto_id,
          cantidad: i.cantidad,
        })),
      });
      setCarrito([]);
      setCantidades({});
      setMostrarAsignacion(false);
      setErrorAsignacion(null);
      setError(null);
      setMensaje(`Pedido agregado a ${etiquetaDestino}.`);
      await Promise.all([
        cargarCatalogos(),
        cargarPedidos(Number(mesaId), barraNumero),
        cargarCuenta(),
      ]);
    } catch (err: any) {
      if (desdeModal) {
        setErrorAsignacion(err.message);
        // El alias pudo pagar mientras se confirmaba: refrescar opciones.
        await Promise.all([
          cargarCuenta(),
          cargarPedidos(Number(mesaId), barraNumero),
        ]);
      } else {
        setError(err.message);
      }
    } finally {
      setProcesandoAsignacion(false);
    }
  };

  // Mesa seleccionada automáticamente al venir desde el panel de Mesas
  useEffect(() => {
    const mesaParam = searchParams.get("mesa");
    if (mesaParam) {
      setMesaId(Number(mesaParam));
      setCarrito([]);
      setCantidades({});
      setMensaje(null);
      setError(null);
      setMostrarAsignacion(false);
      setErrorAsignacion(null);
    }
  }, [searchParams]);

  useEffect(() => {
    if (mesaId) {
      cargarPedidos(Number(mesaId), barraNumero);
      cargarCuenta();
    } else {
      setPedidos([]);
      setCuenta(null);
      setDestinos([]);
    }
  }, [mesaId, barraNumero]);

  useEffect(() => {
    cargarCatalogos();
  }, [categoriaFiltro]);

  const agregarCantidad = (producto: Producto, cantidad: number): boolean => {
    setError(null);
    setMensaje(null);

    if (!turno) {
      setError(MENSAJE_TURNO_REQUERIDO);
      return false;
    }

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
    if (!turno) {
      setError(MENSAJE_TURNO_REQUERIDO);
      return;
    }
    if (!mesaId) {
      setError("Selecciona una mesa");
      return;
    }
    if (carrito.length === 0) {
      setError("Agrega al menos un producto");
      return;
    }

    setError(null);
    // Se consulta la cuenta justo antes de confirmar para no asignar a un
    // alias que acaba de pagar o a una división ya cerrada.
    const data = await cargarCuenta();
    if (!data) return;

    const opciones = destinosDesdeCuenta(data);
    const activos = opciones.filter((d) => !d.esGeneral && !d.pagado);
    if (activos.length === 0) {
      await crearPedido(null, "la cuenta general");
      return;
    }

    setDestinos(opciones);
    setErrorAsignacion(null);
    setMostrarAsignacion(true);
  };

  const confirmarAsignacion = (participanteId: number | null) => {
    const destino = destinos.find((d) =>
      participanteId === null
        ? d.esGeneral
        : d.participanteId === participanteId
    );
    crearPedido(participanteId, destino?.alias || "la cuenta general", true);
  };

  /** Ajusta la cantidad de una linea de un pedido abierto */
  const ajustarLinea = async (pedidoId: number, itemId: number, cantidad: number) => {
    if (!turno) {
      setError(MENSAJE_TURNO_REQUERIDO);
      return;
    }
    try {
      await api.ajustarItemPedido(pedidoId, itemId, cantidad);
      await Promise.all([
        cargarPedidos(Number(mesaId), barraNumero),
        cargarCatalogos(),
        cargarCuenta(),
      ]);
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
        mesaId
          ? cargarPedidos(Number(mesaId), barraNumero)
          : Promise.resolve(),
        mesaId ? cargarCuenta() : Promise.resolve(),
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
              setMostrarAsignacion(false);
              setErrorAsignacion(null);
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

      {sinTurno && <TurnoRequeridoAviso onAbrir={solicitarApertura} />}

      {aliasActivos.length > 0 && (
        <div className="aviso-clientes">
          <div className="aviso-clientes-texto">
            <strong>
              {etiquetaCuenta} tiene {aliasActivos.length} cliente
              {aliasActivos.length > 1 ? "s" : ""} activo
              {aliasActivos.length > 1 ? "s" : ""}.
            </strong>{" "}
            Al confirmar el pedido podrás elegir a quién asignarlo.
          </div>
          <div className="aviso-clientes-detalle">
            {aliasActivos.map((d) => (
              <span key={d.participanteId}>
                {d.alias}: <strong>{formatearPrecio(d.subtotal)}</strong>
              </span>
            ))}
            <span>
              Cuenta general:{" "}
              <strong>{formatearPrecio(cuenta?.total_general || 0)}</strong>
            </span>
          </div>
        </div>
      )}

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
                          disabled={p.stock === 0 || !turno}
                        />
                        <button
                          className="btn-success btn-small"
                          disabled={p.stock === 0 || !turno}
                          onClick={() => agregarDesdeInput(p)}
                          title={
                            !turno
                              ? MENSAJE_TURNO_REQUERIDO
                              : `Agregar la cantidad indicada de ${p.nombre}`
                          }
                        >
                          Agregar
                        </button>
                        <button
                          className="btn-primary btn-small"
                          disabled={p.stock === 0 || !turno}
                          onClick={() => agregar(p)}
                          title={
                            !turno
                              ? MENSAJE_TURNO_REQUERIDO
                              : `Agregar una unidad de ${p.nombre}`
                          }
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

          <button
            className="btn-primary btn-block"
            onClick={confirmarPedido}
            disabled={!turno || cargandoTurno}
            title={!turno ? MENSAJE_TURNO_REQUERIDO : undefined}
          >
            Confirmar pedido
          </button>
        </section>
      </div>

      <section className="panel">
        <h3>Pedidos de {etiquetaCuenta}</h3>
        {pedidosVisibles.length === 0 ? (
          <p className="empty-state">No hay pedidos abiertos.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Productos</th>
                  <th>Total</th>
                  <th>Destino</th>
                </tr>
              </thead>
              <tbody>
                {pedidosVisibles.map((p) => {
                  const asignado =
                    p.estado === "dividido" && p.participante_id != null;
                  return (
                    <tr key={p.id}>
                      <td>{p.id}</td>
                      <td>
                        {p.items.map((i) => (
                          <div key={i.producto_id} className="linea-pedido">
                            <span>
                              {i.cantidad} × {i.producto_nombre}
                            </span>
                            {!asignado && i.id !== undefined && (
                              <span className="linea-acciones">
                                <button
                                  className="btn-icon"
                                  title="Quitar una unidad"
                                  disabled={!turno}
                                  onClick={() =>
                                    ajustarLinea(p.id, i.id as number, i.cantidad - 1)
                                  }
                                >
                                  −
                                </button>
                                <button
                                  className="btn-icon"
                                  title="Añadir una unidad"
                                  disabled={!turno}
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
                        {asignado ? (
                          <span className="badge badge-warning badge-cliente">
                            Asignado a {p.alias}
                          </span>
                        ) : (
                          <button
                            className="btn-primary btn-small"
                            onClick={() => setPedidoACobrar(p)}
                          >
                            Cobrar / cerrar
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        <p className="muted small">
          Los pedidos asignados a un alias se cobran desde la cuenta, con
          "Cerrar división". No se pueden cobrar por separado.
        </p>
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

      {/* Ventana de asignación del pedido a un alias o a la cuenta general */}
      {mostrarAsignacion && (
        <AsignarPedidoModal
          etiquetaCuenta={etiquetaCuenta}
          totalPedido={total}
          cantidadItems={carrito.reduce((s, i) => s + i.cantidad, 0)}
          destinos={destinos}
          procesando={procesandoAsignacion}
          error={errorAsignacion}
          onConfirmar={confirmarAsignacion}
          onClose={() => {
            if (procesandoAsignacion) return;
            setMostrarAsignacion(false);
            setErrorAsignacion(null);
          }}
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
            cargarPedidos(Number(mesaId), barraNumero);
            cargarCatalogos();
            cargarCuenta();
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
            cargarPedidos(Number(mesaId), barraNumero);
            cargarCatalogos();
            cargarCuenta();
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
            cargarPedidos(Number(mesaId), barraNumero);
            cargarCatalogos();
            cargarCuenta();
          }}
        />
      )}
    </div>
  );
}
