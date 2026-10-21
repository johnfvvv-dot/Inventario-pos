/**
 * Servicios de conexión con el backend FastAPI.
 *
 * Para acceder desde otro dispositivo en la misma red WiFi,
 * cambia localhost por la IP de la PC (ej: http://192.168.1.20:8000/api).
 */
export const API_BASE = "http://localhost:8000/api";

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

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
};
