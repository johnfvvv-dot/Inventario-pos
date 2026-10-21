/**
 * Servicios de conexión con el backend FastAPI.
 *
 * IMPORTANTE: en el celular NUNCA uses "localhost", porque ahí apunta al
 * propio teléfono. Se usa la IP local de la PC (obténla con `ipconfig`).
 * Puedes sobrescribirla con la variable de entorno REACT_APP_API_URL.
 */
const PC_IP = "192.168.1.6"; // actualizar si cambia la IP de la PC

export const API_BASE =
  process.env.REACT_APP_API_URL || `http://${PC_IP}:8000/api`;

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
        `Revisa que el servidor esté levantado y que la IP ${PC_IP} sea correcta.`
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

export const api = {
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

  closePedido: (pedidoId: number) =>
    request(`/pedidos/${pedidoId}/cerrar`, { method: "PUT" }),

  // ---------- Cuentas de mesa ----------
  getCuentaMesa: (mesaId: number) => request(`/cuentas/mesa/${mesaId}`),

  /** Cierra la cuenta; con liberarMesa=true la mesa queda disponible */
  cerrarCuentaMesa: (mesaId: number, liberarMesa = false) =>
    request(
      `/cuentas/mesa/${mesaId}/cerrar${liberarMesa ? "?liberar_mesa=true" : ""}`,
      { method: "POST" }
    ),

  /** Transfiere la cuenta abierta a otra mesa */
  transferirCuenta: (mesaId: number, destinoId: number) =>
    request(`/cuentas/mesa/${mesaId}/transferir?destino_id=${destinoId}`, {
      method: "POST",
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

  pagarDivision: (divisionId: number) =>
    request(`/cuentas/division/${divisionId}/pagar`, { method: "POST" }),

  /** Cierra solo la cuenta de un alias (el cliente paga su parte) */
  pagarParticipante: (participanteId: number) =>
    request(`/cuentas/participante/${participanteId}/pagar`, { method: "POST" }),
};
