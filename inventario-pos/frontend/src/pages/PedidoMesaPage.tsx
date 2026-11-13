/** Pantalla de Pedido por Mesa - POS para mesero/administrador. */

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../services/api";
import { formatearFechaHora, formatearPrecio } from "../utils/format";
import {
  MENSAJE_TURNO_REQUERIDO,
  useTurno,
} from "../context/TurnoContext";
import CuentaModal from "../components/CuentaModal";
import DivisionModal from "../components/DivisionModal";
import TransferirModal from "../components/TransferirModal";
import CrearAliasModal from "../components/CrearAliasModal";
import TurnoRequeridoAviso from "../components/TurnoRequeridoAviso";
import AsignarPedidoModal, {
  type DestinoPedido,
} from "../components/AsignarPedidoModal";
import Icon from "../components/Icon";

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

interface LineaItem {
  id?: number;
  producto_id?: number;
  producto_nombre: string;
  cantidad: number;
  subtotal: number;
  participante_item_id?: number | null;
  pedido_id?: number | null;
}

interface Pedido {
  id: number;
  mesa?: { numero: number } | null;
  total: number;
  estado: string;
  participante_id?: number | null;
  alias?: string | null;
  items: LineaItem[];
}

interface ParticipanteCuenta {
  id: number;
  alias: string;
  subtotal: number;
  pagado: boolean;
  forma_pago?: string | null;
  fecha_pago?: string | null;
  items: LineaItem[];
}

interface DivisionCuenta {
  id: number;
  total: number;
  total_pendiente: number;
  estado: string;
  participantes: ParticipanteCuenta[];
}

interface CuentaData {
  mesa_id: number;
  mesa_numero: number;
  estado_mesa: string;
  total: number;
  total_general: number;
  total_divisiones: number;
  pedidos: Pedido[];
  divisiones: DivisionCuenta[];
}

/** El Administrador siempre puede; el Bartender necesita el permiso. */
const leerPermisoCantidades = (): boolean => {
  try {
    const usuario = JSON.parse(localStorage.getItem("user") || "{}");
    return usuario?.rol === "admin" || Boolean(usuario?.editar_cantidades);
  } catch {
    return false;
  }
};

export default function PedidoMesaPage() {
  const [searchParams] = useSearchParams();
  const { turno, cargando: cargandoTurno, solicitarApertura } = useTurno();
  const sinTurno = !cargandoTurno && !turno;
  const [mesas, setMesas] = useState<Mesa[]>([]);
  const [productos, setProductos] = useState<Producto[]>([]);
  const [mesaId, setMesaId] = useState<number | "">("");
  const [carrito, setCarrito] = useState<ItemCarrito[]>([]);
  const [cantidades, setCantidades] = useState<Record<number, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);

  // Modales de cuenta, división y transferencia
  const [mostrarCuenta, setMostrarCuenta] = useState(false);
  const [mostrarDivision, setMostrarDivision] = useState(false);
  const [mostrarTransferir, setMostrarTransferir] = useState(false);
  const [mostrarCrearAlias, setMostrarCrearAlias] = useState(false);
  const [ajustando, setAjustando] = useState<string | null>(null);
  const [categorias, setCategorias] = useState<Categoria[]>([]);
  const [categoriaFiltro, setCategoriaFiltro] = useState<number | "">("");

  // Cuenta actual y destinos posibles para el nuevo pedido
  const [cuenta, setCuenta] = useState<CuentaData | null>(null);
  const [destinos, setDestinos] = useState<DestinoPedido[]>([]);
  const [mostrarAsignacion, setMostrarAsignacion] = useState(false);
  const [errorAsignacion, setErrorAsignacion] = useState<string | null>(null);
  const [procesandoAsignacion, setProcesandoAsignacion] = useState(false);
  const [permisoEditar, setPermisoEditar] = useState<boolean>(
    leerPermisoCantidades
  );

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

  // Cada cliente es un bloque independiente, sin agrupar por división.
  const clientes = cuenta
    ? cuenta.divisiones.flatMap((division) =>
        division.participantes.map((participante) => ({
          ...participante,
          divisionId: division.id,
        }))
      )
    : [];

  // La Cuenta General también se muestra como líneas planas para que su
  // estructura sea idéntica a la de cada cuenta de cliente.
  const lineasGenerales = cuenta
    ? cuenta.pedidos.flatMap((pedido) =>
        pedido.items.map((item, indice) => ({
          ...item,
          pedidoId: pedido.id,
          indice,
        }))
      )
    : [];

  // Refresca los permisos desde el servidor y cuando el Administrador los
  // cambia, para que una sesión abierta del Bartender no quede desactualizada.
  useEffect(() => {
    let activo = true;

    const actualizar = async () => {
      if (!usuarioId) return;
      try {
        const datos: any = await api.getUsuario(usuarioId);
        if (!activo || !datos) return;
        const sesion = JSON.parse(localStorage.getItem("user") || "{}");
        localStorage.setItem(
          "user",
          JSON.stringify({ ...sesion, ...datos })
        );
      } catch {
        // Sin conexión se conserva el permiso guardado en la sesión.
      }
      if (activo) setPermisoEditar(leerPermisoCantidades());
    };

    actualizar();
    window.addEventListener("usuario-actualizado", actualizar);
    window.addEventListener("storage", actualizar);
    return () => {
      activo = false;
      window.removeEventListener("usuario-actualizado", actualizar);
      window.removeEventListener("storage", actualizar);
    };
  }, [usuarioId]);

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
      await Promise.all([cargarCatalogos(), cargarCuenta()]);
    } catch (err: any) {
      if (desdeModal) {
        setErrorAsignacion(err.message);
        // El alias pudo pagar mientras se confirmaba: refrescar opciones.
        await cargarCuenta();
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
      cargarCuenta();
    } else {
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

  /**
   * Crea el alias y le asigna el pedido actual en una sola operación.
   *
   * Reutiliza "Dividir Cuenta" en el backend: `nuevo_alias` crea la división
   * y el participante, y el pedido nace directamente asignado a ese cliente.
   */
  const crearAliasConPedido = async (alias: string): Promise<void> => {
    if (!turno) throw new Error(MENSAJE_TURNO_REQUERIDO);
    if (mesaId === "") throw new Error("Seleccioná una mesa o barra.");
    if (carrito.length === 0) {
      throw new Error("Agregá al menos un producto antes de crear el alias.");
    }

    setError(null);
    setMensaje(null);
    await api.createPedido({
      mesa_id: Number(mesaId),
      usuario_id: usuarioId,
      nuevo_alias: alias,
      items: carrito.map((i) => ({
        producto_id: i.producto_id,
        cantidad: i.cantidad,
      })),
    });

    setCarrito([]);
    setCantidades({});
    setMensaje(
      `Alias "${alias}" creado. El pedido quedó asignado a esa cuenta de cliente.`
    );
    await Promise.all([cargarCatalogos(), cargarCuenta()]);
  };

  /** Ajusta una línea de la Cuenta General (0 = eliminar). */
  const ajustarLineaGeneral = async (
    pedidoId: number,
    itemId: number,
    cantidad: number
  ) => {
    if (!turno) {
      setError(MENSAJE_TURNO_REQUERIDO);
      return;
    }
    if (!permisoEditar) {
      setError(
        "No tenés permiso para editar pedidos. El Administrador debe habilitarlo desde Usuarios."
      );
      return;
    }
    setError(null);
    setAjustando(`general-${itemId}`);
    try {
      await api.ajustarItemPedido(pedidoId, itemId, cantidad, usuarioId);
      await Promise.all([cargarCuenta(), cargarCatalogos()]);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setAjustando(null);
    }
  };

  /** Ajusta una línea de la cuenta de un alias (0 = eliminar). */
  const ajustarLineaAlias = async (
    participanteItemId: number,
    cantidad: number
  ) => {
    if (!turno) {
      setError(MENSAJE_TURNO_REQUERIDO);
      return;
    }
    if (!permisoEditar) {
      setError(
        "No tenés permiso para editar pedidos. El Administrador debe habilitarlo desde Usuarios."
      );
      return;
    }
    setError(null);
    setAjustando(`alias-${participanteItemId}`);
    try {
      await api.ajustarLineaAlias(participanteItemId, cantidad, usuarioId);
      await Promise.all([cargarCuenta(), cargarCatalogos()]);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setAjustando(null);
    }
  };

  const puedeEditar = permisoEditar;

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h2>Pedido por mesa</h2>
          <p className="page-subtitulo">
            Toma de comandas rápidas y asignación a cuenta general o por
            cliente
          </p>
        </div>
        <div className="filters pos-cabecera-filtros">
          <div className="form-group">
            <label htmlFor="pedido-mesa">Mesa / barra</label>
            <select
              id="pedido-mesa"
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
          </div>
          <div className="form-group">
            <label htmlFor="pedido-categoria">Categoría</label>
            <select
              id="pedido-categoria"
              className="select-categoria"
              value={categoriaFiltro}
              onChange={(e) =>
                setCategoriaFiltro(
                  e.target.value ? Number(e.target.value) : ""
                )
              }
            >
              <option value="">Todas las categorías</option>
              {categorias.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nombre}
                </option>
              ))}
            </select>
          </div>
          {mesaId !== "" && (
            <button
              className="btn-secondary pos-ver-cuenta"
              onClick={() => setMostrarCuenta(true)}
            >
              <Icon nombre="recibo" size={16} />
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
          <div className="aviso-clientes-icono">
            <Icon nombre="usuarios" size={18} />
          </div>
          <div className="aviso-clientes-contenido">
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
        </div>
      )}

      <div className="pos-grid">
        <section className="panel pos-panel pos-panel--productos">
          <h3>
            <Icon nombre="inventario" size={15} />
            Productos disponibles
          </h3>
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
                          className="btn-primary btn-small btn-agregar-pedido"
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
                          <Icon nombre="mas" size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="panel pos-panel pos-panel--actual">
          <h3>
            <Icon nombre="pedidos" size={15} />
            Pedido actual
          </h3>
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

          <div className="total-row pos-total">
            <span>Total</span>
            <strong>{formatearPrecio(total)}</strong>
          </div>

          <div className="pedido-actual-acciones">
            <button
              className="btn-secondary"
              onClick={() => setMostrarCrearAlias(true)}
              disabled={
                !turno || cargandoTurno || mesaId === "" || carrito.length === 0
              }
              title={
                !turno
                  ? MENSAJE_TURNO_REQUERIDO
                  : mesaId === ""
                  ? "Seleccioná una mesa o barra"
                  : carrito.length === 0
                  ? "Agregá productos para crear la cuenta del cliente"
                  : "Crear un alias y asignarle este pedido"
              }
            >
              <Icon nombre="usuario" size={16} />
              Crear alias
            </button>
            <button
              className="btn-primary"
              onClick={confirmarPedido}
              disabled={!turno || cargandoTurno}
              title={!turno ? MENSAJE_TURNO_REQUERIDO : undefined}
            >
              <Icon nombre="check" size={16} />
              Confirmar pedido
            </button>
          </div>
        </section>
      </div>

      <section className="panel pedido-cuenta-panel">
        <div className="cuenta-panel-head">
          <div>
            <h3>
              <Icon nombre="recibo" size={15} />
              Pedidos de {etiquetaCuenta}
            </h3>
            <span className="muted small">
              Cuenta General y cuentas de clientes activas.
            </span>
          </div>
        </div>

        {!cuenta ? (
          <p className="empty-state">
            {mesaId === ""
              ? "Seleccioná una mesa o barra para ver su cuenta."
              : "Cargando la cuenta..."}
          </p>
        ) : (
          <>
            <div className="cuenta-grupo cuenta-grupo--general">
              <div className="cuenta-grupo-head">
                <div>
                  <h4>Cuenta General</h4>
                  <span className="muted small">
                    {cuenta.pedidos.length} pedido(s)
                  </span>
                </div>
                <strong>{formatearPrecio(cuenta.total_general)}</strong>
              </div>

              {lineasGenerales.length === 0 ? (
                <p className="muted small">Sin pedidos en la Cuenta General.</p>
              ) : (
                lineasGenerales.map((item) => (
                  <div
                    className="linea-pedido"
                    key={`general-${item.pedidoId}-${
                      item.id ?? `${item.producto_id ?? item.indice}-${item.indice}`
                    }`}
                  >
                    <span>
                      {item.cantidad} × {item.producto_nombre}{" "}
                      <span className="muted small">
                        · {formatearPrecio(item.subtotal)}
                      </span>
                    </span>
                    {puedeEditar && item.id !== undefined && (
                      <span className="linea-acciones">
                        <button
                          className="btn-icon"
                          title="Quitar una unidad"
                          disabled={ajustando !== null}
                          onClick={() =>
                            ajustarLineaGeneral(
                              item.pedidoId,
                              item.id as number,
                              item.cantidad - 1
                            )
                          }
                        >
                          −
                        </button>
                        <button
                          className="btn-icon"
                          title="Añadir una unidad"
                          disabled={ajustando !== null}
                          onClick={() =>
                            ajustarLineaGeneral(
                              item.pedidoId,
                              item.id as number,
                              item.cantidad + 1
                            )
                          }
                        >
                          +
                        </button>
                      </span>
                    )}
                  </div>
                ))
              )}
            </div>

            {clientes.map((cliente) => (
              <div
                key={`cliente-${cliente.id}`}
                className="cuenta-grupo cuenta-grupo--cliente"
              >
                <div className="cuenta-grupo-head">
                  <div>
                    <h4>
                      Cuenta de cliente {cliente.alias}{" "}
                      {cliente.pagado && (
                        <span className="badge badge-success">pagado</span>
                      )}
                    </h4>
                    <span className="muted small">
                      {cliente.items.length} producto(s)
                    </span>
                  </div>
                  <strong>{formatearPrecio(cliente.subtotal)}</strong>
                </div>

                {cliente.pagado && (
                  <span className="cuenta-pago-info">
                    Pagado con {cliente.forma_pago || "—"}
                    {cliente.fecha_pago
                      ? ` · ${formatearFechaHora(cliente.fecha_pago)}`
                      : ""}
                  </span>
                )}

                {cliente.items.length === 0 ? (
                  <p className="muted small">
                    Sin productos en esta cuenta de cliente.
                  </p>
                ) : (
                  cliente.items.map((item, indice) => (
                    <div
                      className="linea-pedido"
                      key={
                        item.participante_item_id ??
                        `${cliente.id}-${
                          item.producto_id ?? indice
                        }-${indice}`
                      }
                    >
                      <span>
                        {item.cantidad} × {item.producto_nombre}{" "}
                        <span className="muted small">
                          · {formatearPrecio(item.subtotal)}
                        </span>
                      </span>
                      {puedeEditar &&
                        !cliente.pagado &&
                        item.participante_item_id != null && (
                          <span className="linea-acciones">
                            <button
                              className="btn-icon"
                              title="Quitar una unidad"
                              disabled={ajustando !== null}
                              onClick={() =>
                                ajustarLineaAlias(
                                  item.participante_item_id as number,
                                  item.cantidad - 1
                                )
                              }
                            >
                              −
                            </button>
                            <button
                              className="btn-icon"
                              title="Añadir una unidad"
                              disabled={ajustando !== null}
                              onClick={() =>
                                ajustarLineaAlias(
                                  item.participante_item_id as number,
                                  item.cantidad + 1
                                )
                              }
                            >
                              +
                            </button>
                          </span>
                        )}
                    </div>
                  ))
                )}
              </div>
            ))}
          </>
        )}
      </section>

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

      {/* Ventana para crear un alias y asignarle el pedido actual */}
      {mostrarCrearAlias && mesaId !== "" && (
        <CrearAliasModal
          titulo="Crear alias para este pedido"
          descripcion={`Se creará una cuenta de cliente en ${etiquetaCuenta} y el pedido actual se asignará a ese alias.`}
          onCrear={crearAliasConPedido}
          onClose={() => setMostrarCrearAlias(false)}
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
            cargarCatalogos();
            cargarCuenta();
          }}
        />
      )}
    </div>
  );
}
