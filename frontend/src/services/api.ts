/**
 * Servicios de conexión con el backend FastAPI.
 *
 * La URL base se deduce del host con el que se abrió la app:
 *  - Desarrollo (React :3000) → http://localhost:8000/api
 *  - Ejecutable (.exe)         → http://localhost:8000/api
 *  - Móvil / APK               → http://192.168.1.6:8000/api
 * Para fijar una IP concreta: REACT_APP_API_URL=http://IP:8000/api
 */
const detectApiBase = (): string => {
  const envUrl = process.env.REACT_APP_API_URL;
  if (envUrl) return envUrl;

  if (typeof window !== "undefined" && window.location.hostname) {
    return `http://${window.location.hostname}:8000/api`;
  }
  return "http://localhost:8000/api";
};

export const API_BASE = detectApiBase();

/** Timeout de la petición: evita que la interfaz se quede cargando eternamente */
const REQUEST_TIMEOUT_MS = 10000;

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${url}`, {
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      ...options,
    });
  } catch (err: any) {
    if (err?.name === "AbortError") {
      throw new Error(
        `El backend no respondió en ${REQUEST_TIMEOUT_MS / 1000}s. ` +
          `Verifica que esté corriendo en ${API_BASE}`
      );
    }
    throw new Error(
      `No se pudo conectar con el backend (${API_BASE}). ` +
        `Revisa que el servidor esté levantado y que la IP ${API_BASE} sea correcta.`
    );
  } finally {
    clearTimeout(timer);
  }

  if (!response.ok) {
    let detail = `Error ${response.status}`;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      /* respuesta sin JSON */
    }
    throw new Error(detail);
  }

  return response.json() as Promise<T>;
}

export const FORMAS_PAGO = [
  { id: "efectivo", label: "Efectivo" },
  { id: "tarjeta", label: "Tarjeta" },
  { id: "transferencia", label: "Transferencia" },
];

export const api = {
  // ---------- Configuración ----------
  getConfig: () => request("/config"),

  // ---------- Usuarios ----------
  login: (alias: string, password: string) =>
    request("/usuarios/login", {
      method: "POST",
      body: JSON.stringify({ alias, password }),
    }),

  getUsuarios: () => request("/usuarios/"),

  createUsuario: (datos: {
    alias: string;
    nombre?: string;
    password?: string;
    rol: string;
  }) =>
    request("/usuarios/", {
      method: "POST",
      body: JSON.stringify(datos),
    }),

  updateUsuario: (
    usuarioId: number,
    datos: { alias?: string; nombre?: string; rol?: string; activo?: boolean }
  ) =>
    request(`/usuarios/${usuarioId}`, {
      method: "PUT",
      body: JSON.stringify(datos),
    }),

  cambiarClave: (usuarioId: number, password: string) =>
    request(`/usuarios/${usuarioId}/clave`, {
      method: "PUT",
      body: JSON.stringify({ password }),
    }),

  deleteUsuario: (usuarioId: number) =>
    request(`/usuarios/${usuarioId}`, { method: "DELETE" }),

  // ---------- Mesas ----------
  getMesas: () => request("/mesas/"),

  createMesa: (numero: number, capacidad: number) =>
    request("/mesas/", {
      method: "POST",
      body: JSON.stringify({ numero, capacidad, estado: "disponible" }),
    }),

  updateMesaEstado: (mesaId: number, nuevo_estado: string) =>
    request(`/mesas/${mesaId}/estado`, {
      method: "PUT",
      body: JSON.stringify({ nuevo_estado }),
    }),

  /** Libera la mesa solo si no tiene cuentas pendientes */
  liberarMesa: (mesaId: number) =>
    request(`/mesas/${mesaId}/liberar`, { method: "POST" }),

  /** Elimina una mesa o puesto de barra (mesas eventuales) */
  deleteMesa: (mesaId: number) =>
    request(`/mesas/${mesaId}`, { method: "DELETE" }),

  /** Crea una barra con varias cuentas independientes */
  createBarra: (numero: number, capacidad: number, cuentas: number) =>
    request("/mesas/barra", {
      method: "POST",
      body: JSON.stringify({ numero, capacidad, cuentas }),
    }),

  // ---------- Cuentas de mesa ----------
  getCuentaMesa: (mesaId: number) => request(`/cuentas/mesa/${mesaId}`),

  /** Cierra la cuenta; con liberarMesa=true la mesa queda disponible */
  cerrarCuentaMesa: (mesaId: number, liberarMesa = false, formaPago = "efectivo") =>
    request(
      `/cuentas/mesa/${mesaId}/cerrar?liberar_mesa=${liberarMesa}&forma_pago=${formaPago}`,
      { method: "POST" }
    ),

  /** Transfiere la cuenta abierta a otra mesa */
  transferirCuenta: (mesaId: number, destinoId: number) =>
    request(`/cuentas/mesa/${mesaId}/transferir?destino_id=${destinoId}`, {
      method: "POST",
    }),

  // ---------- Inventario ----------
  /** Inventario con búsqueda, filtro por categoría y paginación */
  getProductos: (filtros: {
    buscar?: string;
    categoria_id?: number | null;
    limite?: number;
    offset?: number;
  } = {}) => {
    const params = new URLSearchParams();
    if (filtros.buscar) params.append("buscar", filtros.buscar);
    if (filtros.categoria_id) params.append("categoria_id", String(filtros.categoria_id));
    params.append("limite", String(filtros.limite ?? 50));
    params.append("offset", String(filtros.offset ?? 0));
    return request(`/inventario/?${params.toString()}`);
  },

  createProducto: (datos: {
    nombre: string;
    descripcion?: string;
    precio: number;
    stock: number;
  }) =>
    request("/inventario/", {
      method: "POST",
      body: JSON.stringify(datos),
    }),

  updateProductoStock: (productoId: number, nuevo_stock: number) =>
    request(`/inventario/${productoId}/stock`, {
      method: "PUT",
      body: JSON.stringify({ nuevo_stock }),
    }),

  deleteProducto: (productoId: number) =>
    request(`/inventario/${productoId}`, { method: "DELETE" }),

  updateProducto: (productoId: number, datos: {
    nombre: string;
    descripcion?: string;
    precio: number;
    stock: number;
    categoria_id?: number | null;
  }) =>
    request(`/inventario/${productoId}`, {
      method: "PUT",
      body: JSON.stringify(datos),
    }),

  // ---------- Categorias ----------
  getCategorias: () => request("/categorias/"),

  createCategoria: (nombre: string) =>
    request("/categorias/", {
      method: "POST",
      body: JSON.stringify({ nombre }),
    }),

  actualizarCategoria: (categoriaId: number, nombre: string) =>
    request(`/categorias/${categoriaId}`, {
      method: "PUT",
      body: JSON.stringify({ nombre }),
    }),

  eliminarCategoria: (categoriaId: number) =>
    request(`/categorias/${categoriaId}`, { method: "DELETE" }),

  // ---------- Pedidos ----------
  getPedidos: () => request("/pedidos/"),

  getPedidosMesa: (mesaId: number) => request(`/pedidos/mesa/${mesaId}`),

  createPedido: (datos: {
    mesa_id: number;
    usuario_id: number;
    items: { producto_id: number; cantidad: number }[];
  }) =>
    request("/pedidos/", {
      method: "POST",
      body: JSON.stringify(datos),
    }),

  /** Ajusta la cantidad de una línea de un pedido abierto (0 = eliminar) */
  ajustarItemPedido: (pedidoId: number, itemId: number, cantidad: number) =>
    request(`/pedidos/${pedidoId}/items/${itemId}`, {
      method: "PUT",
      body: JSON.stringify({ cantidad }),
    }),

  closePedido: (pedidoId: number, formaPago = "efectivo") =>
    request(`/pedidos/${pedidoId}/cerrar?forma_pago=${formaPago}`, {
      method: "PUT",
    }),

  // ---------- División de cuenta ----------
  dividirCuenta: (datos: {
    mesa_id: number;
    usuario_id: number;
    participantes: { alias: string; items: { producto_id: number; cantidad: number }[] }[];
  }) =>
    request("/cuentas/dividir", {
      method: "POST",
      body: JSON.stringify(datos),
    }),

  getDivisionesMesa: (mesaId: number) =>
    request(`/cuentas/mesa/${mesaId}/divisiones`),

  pagarDivision: (divisionId: number, formaPago = "efectivo") =>
    request(`/cuentas/division/${divisionId}/pagar?forma_pago=${formaPago}`, {
      method: "POST",
    }),

  /** Cierra solo la cuenta de un alias (el cliente paga su parte) */
  pagarParticipante: (participanteId: number, formaPago = "efectivo") =>
    request(`/cuentas/participante/${participanteId}/pagar?forma_pago=${formaPago}`, {
      method: "POST",
    }),

  // ---------- Corte de caja ----------
  getTurnoActual: () => request("/caja/turno-actual"),

  abrirTurno: (usuarioId = 1) =>
    request(`/caja/abrir?usuario_id=${usuarioId}`, { method: "POST" }),

  cerrarTurno: (observaciones?: string) =>
    request("/caja/cerrar", {
      method: "POST",
      body: JSON.stringify({ observaciones: observaciones || null }),
    }),

  getTurnos: (limite = 20) => request(`/caja/turnos?limite=${limite}`),

  getResumenCaja: (dias = 1) => request(`/caja/resumen?dias=${dias}`),

  getVentasPorDia: (dias = 14) => request(`/caja/ventas-por-dia?dias=${dias}`),

  /** Historial de ventas con filtros */
  getHistorial: (filtros: {
    desde?: string;
    hasta?: string;
    mesa?: number | null;
    producto?: number | null;
    forma_pago?: string | null;
    limite?: number;
    offset?: number;
  } = {}) => {
    const params = new URLSearchParams();
    if (filtros.desde) params.append("desde", filtros.desde);
    if (filtros.hasta) params.append("hasta", filtros.hasta);
    if (filtros.mesa) params.append("mesa", String(filtros.mesa));
    if (filtros.producto) params.append("producto", String(filtros.producto));
    if (filtros.forma_pago) params.append("forma_pago", filtros.forma_pago);
    params.append("limite", String(filtros.limite ?? 50));
    params.append("offset", String(filtros.offset ?? 0));
    return request(`/caja/historial?${params.toString()}`);
  },
};
