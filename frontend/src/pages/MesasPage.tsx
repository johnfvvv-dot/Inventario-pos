/** Pantalla de Gestión de Mesas - Administrador */
import { useEffect, useState } from "react";
import { api } from "../services/api";
import { Link } from "react-router-dom";

export default function MesasPage() {
  const [mesas, setMesas] = useState<any[]>([]);
  const [nuevaMesa, setNuevaMesa] = useState({ numero: "", capacidad: "4" });
  const [error, setError] = useState<string | null>(null);

  // Cargar mesas al inicializar
  useEffect(() => {
    fetchMesas();
  }, []);

  const fetchMesas = async () => {
    try {
      const data = await api.getMesas();
      setMesas(data);
    } catch (err: any) {
      setError("Error al cargar mesas: " + err.message);
    }
  };

  const handleCreateMesa = async (e: React.FormEvent) => {
    e.preventDefault();
    const { numero, capacidad } = nuevaMesa;
    if (!numero || !capacidad) {
      setError("Por favor completa todos los campos");
      return;
    }
    try {
      await api.createMesa(Number(numero), Number(capacidad));
      setMesas((prev) => [...prev, { id: prev.length + 1, numero: Number(numero), capacidad: Number(capacidad), estado: "disponible" }]);
      setNuevaMesa({ numero: "", capacidad: "4" });
      setError(null);
    } catch (err: any) {
      setError("Error al crear mesa: " + err.message);
    }
  };

  const handleUpdateEstado = async (mesaId: number, nuevoEstado: string) => {
    try {
      await api.updateMesaEstado(mesaId, nuevoEstado);
      // Actualizar estado en la lista local
      setMesas((prev) =>
        prev.map((m) => (m.id === mesaId ? { ...m, estado: nuevoEstado } : m))
      );
    } catch (err: any) {
      setError("Error al actualizar estado: " + err.message);
    }
  };

  return (
    <div className="mesas-page">
      <h2>GESTIÓN DE MESAS</h2>

      <div className="mesas-actions">
        <h3>Nueva Mesa</h3>
        <form onSubmit={handleCreateMesa}>
          <div className="form-group">
            <label>Número de Mesa *</label>
            <input
              type="number"
              value={nuevaMesa.numero}
              onChange={(e) =>
                setNuevaMesa((prev) => ({ ...prev, numero: e.target.value }))
              }
              required
            />
          </div>
          <div className="form-group">
            <label>Capacidad *</label>
            <input
              type="number"
              value={nuevaMesa.capacidad}
              onChange={(e) =>
                setNuevaMesa((prev) => ({ ...prev, capacidad: e.target.value }))
              }
              required
            />
          </div>
          <button type="submit" className="btn-primary">
            Crear Mesa
          </button>
        </form>
      </div>

      {/* Tabla de mesas */}
      {error && <p className="error-msg">{error}</p>}

      <table>
        <thead>
          <tr>
            <th>Número</th>
            <th>Capacidad</th>
            <th>Estado</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {mesas.map((mesa: any) => (
            <tr key={mesa.id}>
              <td>{mesa.numero}</td>
              <td>{mesa.capacidad}</td>
              <td>
                <span
                  className={
                    mesa.estado === "disponible"
                      ? "status-disponible"
                    : mesa.estado === "ocupada"
                      ? "status-ocupada"
                    : "status-cerrada"
                  }
                >
                  {mesa.estado}
                </span>
              </td>
              <td>
                <button
                  onClick={() => console.log("Ver detalles", mesa.id)}
                  title="Ver/Editar"
                  className="btn-action"
                >
                  👁️
                </button>
                <button
                  onClick={() => handleUpdateEstado(mesa.id, "ocupada")}
                  title="Ocupar Mesa"
                  className="btn-action"
                >
                  Ocupar
                </button>
              </td>
            </tr>
          ))}
          {mesas.length === 0 && (
            <tr>
              <td colSpan={5} className="empty-state">
                No hay mesas registradas
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}