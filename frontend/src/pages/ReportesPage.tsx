/** Pantalla de Reportes - Administrador */
import { useEffect, useState } from "react";
import { api } from "../services/api";
import { Link } from "react-router-dom";

export default function ReportesPage() {
  const [ventas, setVentas] = useState({
    totalVentas: 0,
    totalProductos: 0,
    mesasAtendidas: 0,
    promedioPorMesa: 0,
  });
  const [topProductos, setTopProductos] = useState<any[]>([]);
  const [inventoryState, setInventoryState] = useState<any[]>([]);
  const [periodo, setPeriodo] = useState({ inicio: "", fin: "" });
  const [error, setError] = useState<string | null>(null);

  // Cargar reportes al inicializar
  useEffect(() => {
    fetchReportes();
  }, []);

  const fetchReportes = async () => {
    try {
      // Obtener datos combinados
      const [productos, pedidos] = await Promise.all([
        api.getProductos(),
        api.getPedidos(),
      ]);

      // Calcular estadísticas
      let totalVentas = 0;
      let totalProductos = 0;
      const mapaVentas: any = {};
      let mesasAtendidas = new Set();

      // Procesar pedidos cerrados
      const pedidosCerrados = pedidos.filter((p: any) => p.estado === "cerrado");
      
      pedidosCerrados.forEach((pedido: any) => {
        totalVentas += pedido.total || 0;
        mesasAtendidas.add(pedido.mesa?.numero || 0);
        
        // Contar productos vendidos
        pedido.items?.forEach(((item: any) => {
          const prodId = item.producto_id || item.id;
          mapaVentas[prodId] = (mapaVentas[prodId] || 0) + (item.cantidad || 1);
          totalProductos += item.cantidad || 1;
        }));
      });

      // Calcular promedio
      const promedio = mesasAtendidas.size > 0 ? totalVentas / mesasAtendidas.size : 0;

      // Top productos
      const top = Object.entries(mapaVentas)
        .sort((a: any, b: any) => b[1] - a[1])
        .slice(0, 5)
        .map(([nombre, cantidad]) => ({
          nombre,
          cantidad,
        }));

      setVentas({
        totalVentas: totalVentas.toFixed(2),
        totalProductos,
        mesasAtendidas: mesasAtendidas.size,
        promedioPorMesa: promedio.toFixed(2),
      });
      setTopProductos(top);

      // Estado actual de inventario
      setInventoryState(productos.map((p: any) => ({
        nombre: p.nombre,
        stockActual: p.stock,
        ventasHoy: mapaVentas[p.id] || 0,
      })));

    } catch (err: any) {
      setError("Error al generar reportes: " + err.message);
    }
  };

  return (
    <div className="reportes-page">
      <h2>REPORTES - VENTAS E INVENTARIO</h2>

      {/* Selector de período simplificado */}
      <div className="period-select">
        <label>Periodo:</label>
        <select
          value={periodo.inicio}
          onChange={(e) => setPeriodo({ ...periodo, inicio: e.target.value })}
        >
          <option value="hoy">Hoy</option>
          <option value="this-week">Esta Semana</option>
          <option value="this-month">Este Mes</option>
          <option value="custom">Personalizado</option>
        </select>
        <select
          value={periodo.fin}
          onChange={(e) => setPeriodo({ ...periodo, fin: e.target.value })}
        >
          <option value="hoy">Hoy</option>
          <option value="this-week">Esta Semana</option>
          <option value="this-month">Este Mes</option>
        </select>
        <button onClick={fetchReportes} className="btn-small">
          Actualizar
        </button>
      </div>

      {/* Errores */}
      {error && <p className="error-msg">{error}</p>}

      {/* KPIs Principales */}
      <div className="kpis">
        <div className="kpi-card">
          <h3>Total Ventas</h3>
          <h2>${ventas.totalVentas}</h2>
        </div>
        <div className="kpi-card">
          <h3>Productos Vendidos</h3>
          <h2>{ventas.totalProductos} und.</h2>
        </div>
        <div className="kpi-card">
          <h3>Mesas Atendidas</h3>
          <h2>{ventas.mesasAtendidas}</h2>
        </div>
        <div className="kpi-card">
          <h3>Promedio/Mesa</h3>
          <h2>${ventas.promedioPorMesa}</h2>
        </div>
      </div>

      {/* Top Productos Más Vendidos */}
      <div className="top-productos-section">
        <h3>Top Productos Más Vendidos</h3>
        {topProductos.length === 0 ? (
          <p>No hay datos de ventas</p>
        ) : (
          <ul>
            {topProductos.map((producto: any, index: number) => (
              <li key={index}>
                {producto.nombre}: {producto.cantidad} unidad{"es".repeat(producto.cantidad > 1)}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Estado de Inventario */}
      <div className="inventario-estado">
        <h3>Estado Actual de Inventario</h3>
        {inventoryState.length === 0 ? (
          <p>Cargando...</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Producto</th>
                <th>Stock Actual</th>
                <th>Ventas Hoy</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {inventoryState.map((item: any) => (
                <tr key={item.nombre}>
                  <td>{item.nombre}</td>
                  <td>{item.stockActual}</td>
                  <td>{item.ventasHoy}</td>
                  <td>
                    <span
                      className={
                        item.stockActual <= 0
                          ? "stock-agotado"
                        : item.stockActual < 10
                          ? "stock-bajo"
                          : "stock-bien"
                      }
                    >
                      {item.stockActual <= 0 ? "Agotado" : item.stockActual < 10 ? "Bajo" : "Bien"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}