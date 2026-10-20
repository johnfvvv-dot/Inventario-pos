/** Servicios API para conectar frontend con backend FastAPI */

/* Configuración de URL de la API
 * - Desarrollo local: http://localhost:8000
 * - Desde red local: http://192.168.1.xxx:8000
 * - Producción/nube: tu-dominio.com o dirección IP
 */

const API_BASE = "http://localhost:8000/api";

export const api = {
  // Usuarios
  login: (email: string, password: string) =>
    fetch(`${API_BASE}/usuarios/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    }).then((r) => r.json()),

  register: (userData) =>
    fetch(`${API_BASE}/usuarios/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(userData),
    }).then((r) => r.json()),

  // Mesas
  getMesas: () => fetch(`${API_BASE}/mesas/`).then((r) => r.json()),
  createMesa: (numero: number, capacidad: number) =>
    fetch(`${API_BASE}/mesas/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ numero, capacidad }),
    }).then((r) => r.json()),
  updateMesaEstado: (mesaId: number, estado: string) =>
    fetch(`${API_BASE}/mesas/${mesaId}/estado`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nuevo_estado: estado }),
    }).then((r) => r.json()),

  // Productos Inventario
  getProductos: () => fetch(`${API_BASE}/inventario/`).then((r) => r.json()),
  createProducto: (datos) =>
    fetch(`${API_BASE}/inventario/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(datos),
    }).then((r) => r.json()),
  updateProductoStock: (id: number, stock: number) =>
    fetch(`${API_BASE}/inventario/${id}/stock`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nuevo_stock: stock }),
    }).then((r) => r.json()),

  // Pedidos/Ventas
  getPedidos: () => fetch(`${API_BASE}/pedidos/`).then((r) => r.json()),
  createPedido: (pedidoData) =>
    fetch(`${API_BASE}/pedidos/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(pedidoData),
    }).then((r) => r.json()),
  getPedidosMesa: (mesaId: number) =>
    fetch(`${API_BASE}/pedidos/mesa/${mesaId}`).then((r) => r.json()),
  closePedido: (pedidoId: number) =>
    fetch(`${API_BASE}/pedidos/${pedidoId}/cerrar`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
    }).then((r) => r.json()),
};