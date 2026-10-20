/** Pantalla de Pedido por Mesa - Mesero/Administrador */
import { useEffect, useState } from "react";
import { api } from "../services/api";
import { Link, useParams } from "react-router-dom";

export default function PedidoMesaPage() {
  const { mesaId } = useParams<{ mesaId: string }>();
  const [productos, setProductos] = useState<any[]>([]);
  const [pedidoActual, setPedidoActual] = useState({
    mesaId: Number(mesaId) || 1,
    items: [] as any[],
    total: 0,
  });
  const [error, setError] = useState<string | null>(null);
  const [buscandoProducto, setBuscandoProducto] = useState("");

  // Cargar mesas y estado inicial
  useEffect(() => {
    // Cargar productos disponibles
    fetchProductosDisponibles();
  }, [mesaId]);

  const fetchProductosDisponibles = async () => {
    try {
      const data = await api.getProductos();
      setProductos(data);
    } catch (err: any) {
      setError("Error al cargar productos: " + err.message);
    }
  };

  // Calcular total del pedido
  const calcularTotal = (items: any[]) =>
    items.reduce((sum: number, item: any) => sum + item.subtotal, 0);

  // Agregar producto al pedido
  const handleAgregarProducto = async (productoId: number) => {
    const producto = productos.find((p: any) => p.id === productoId);
    if (!producto) return;

    // Verificar stock
    if (producto.stock <= 0) {
      setError("Producto sin stock disponible");
      return;
    }

    // Crear item para el pedido
    const nuevoItem = {
      producto_id: producto.id,
      producto_nombre: producto.nombre,
      cantidad: 1,
      precio_unitario: producto.precio,
      subtotal: producto.precio,
    };

    // Actualizar pedido actual
    const itemExistente = pedidoActual.items.find(
      (item: any) => item.producto_id === productoId
    );

    if (itemExistente) {
      // Incrementar cantidad si ya existe
      const actualizado = pedidoActual.items.map((item: any) => {
        if (item.producto_id === productoId) {
          item.cantidad += 1;
          item.subtotal = item.precio_unitario * item.cantidad;
        }
        return item;
      });
      setPedidoActual({ ...pedidoActual, items: actualizado });
    } else {
      setPedidoActual({
        ...pedidoActual,
        items: [...pedidoActual.items, nuevoItem],
      });
    }
  };

  // Quitar item del pedido
  const handleQuitarItem = (productoId: number) => {
    const actualizado = pedidoActual.items.filter(
      (item: any) => item.producto_id !== productoId
    );
    setPedidoActual({ ...pedidoActual, items: actualizado });
  };

  // Cerrar pedido
  const handleCerrarPedido = async () => {
    if (pedidoActual.items.length === 0) {
      setError("El pedido está vacío");
      return;
    }

    try {
      const pedidoData = {
        mesa_id: pedidoActual.mesaId,
        usuario_id: 1, // TODO: obtener del usuario logueado
        items: pedidoActual.items.map((item: any) => ({
          producto_id: item.producto_id,
          cantidad: item.cantidad,
        })),
      };

      const response = await api.closePedido(pedidoActual.mesaId);
      setError(null);
      // Resetear pedido
      setPedidoActual({
        mesaId: pedidoActual.mesaId,
        items: [],
        total: 0,
      });
      // Recargar mesas para actualizar estado
      fetchProductosDisponibles();
    } catch (err: any) {
      setError("Error al cerrar pedido: " + err.message);
    }
  };

  if (!mesaId) {
    return <div>ID de mesa no especificado</div>;
  }

  return (
    <div className="pedido-mesa-page">
      <h2>MESA NÚMERO {mesaId}</h2>

      {/* Información de la mesa */}
      <div className="mesa-info">
        <p>Estado: <span id="mesa-estado">Cargando...</span></p>
        <p>Total Pedido: <strong>${pedidoActual.total.toFixed(2)}</strong></p>
      </div>

      {/* Lista de productos disponibles */}
      <div className="productos-disponibles">
        <h3>Productos Disponibles</h3>
        <table>
          <thead>
            <tr>
              <th>Producto</th>
              <th>Precio</th>
              <th>Stock</th>
              <th>Añadir</th>
            </tr>
          </thead>
          <tbody>
            {productos.map((producto: any) => (
              <tr key={producto.id}>
                <td>{producto.nombre}</td>
                <td>${producto.precio.toFixed(2)}</td>
                <td>{producto.stock > 0 ? producto.stock : "🚫"}</td>
                <td>
                  <button
                    onClick={() => handleAgregarProducto(producto.id)}
                    disabled={producto.stock <= 0}
                    className="btn-add"
                  >
                    +
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Resumen del pedido actual */}
      <div className="pedido-resumen">
        <h3>Resumen del Pedido</h3>
        {pedidoActual.items.length === 0 ? (
          <p>El pedido está vacío</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Producto</th>
                <th>Cantidad</th>
                <th>Precio Unit.</th>
                <th>Subtotal</th>
                <th>Quitar</th>
              </tr>
            </thead>
            <tbody>
              {pedidoActual.items.map((item: any) => (
                <tr key={item.producto_id}>
                  <td>{item.producto_nombre}</td>
                  <td>{item.cantidad}</td>
                  <td>${item.precio_unitario.toFixed(2)}</td>
                  <td>${item.subtotal.toFixed(2)}</td>
                  <td>
                    <button
                      onClick={() => handleQuitarItem(item.producto_id)}
                      className="btn-delete-small"
                    >
                      ×
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan={4} style={{ textAlign: "right" }}>
                  <strong>Total: ${pedidoActual.total.toFixed(2)}</strong>
                </td>
              </tr>
            </tfoot>
          </table>
        )}
      </div>

      {/* Acciones */}
      <div className="pedido-acciones">
        {pedidoActual.items.length > 0 && (
          <button
            onClick={handleCerrarPedido}
            disabled={pedidoActual.estado === "cerrado"}
            className="btn-cerrar-pedido"
          >
            Cerrar Pedido
          </button>
        )}
        <Link to={`/mesas`} className="btn-regresar">
          ← Regresar a Mesas
        </Link>
      </div>
    </div>
  );
}