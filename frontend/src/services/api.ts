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
  login: (email: string, password: string) =>
    request("/usuarios/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  getUsuarios: () => request("/usuarios/"),

  createUsuario: (datos: {
    nombre: string;
    email: string;
    password: string;
    rol: string;
  }) =>
    request("/usuarios/", {
      method: "POST",
      body: JSON.stringify(datos),
    }),

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
  getProductos: () => request("/inventario/"),

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
};
