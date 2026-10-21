/** Pantalla de Gestión de Mesas - Administrador. */

import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api";

interface Mesa {
  id: number;
  numero: number;
  capacidad: number;
  estado: string;
}

export default function MesasPage() {
  const [mesas, setMesas] = useState<Mesa[]>([]);
  const [nuevaMesa, setNuevaMesa] = useState({ numero: "", capacidad: "4" });
  const [error, setError] = useState<string | null>(null);

  const cargarMesas = async () => {
    try {
      const data: any = await api.getMesas();
      setMesas(data);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    }
  };

  useEffect(() => {
    cargarMesas();
  }, []);

  const crearMesa = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await api.createMesa(Number(nuevaMesa.numero), Number(nuevaMesa.capacidad));
      setNuevaMesa({ numero: "", capacidad: "4" });
      await cargarMesas();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const cambiarEstado = async (mesa: Mesa, estado: string) => {
    try {
      await api.updateMesaEstado(mesa.id, estado);
      await cargarMesas();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const claseEstado = (estado: string) =>
    estado === "disponible"
      ? "badge badge-success"
      : estado === "ocupada"
      ? "badge badge-warning"
      : "badge badge-danger";

  return (
    <div className="page">
      <div className="page-head">
        <h2>Gestión de mesas</h2>
        <button className="btn-secondary" onClick={cargarMesas}>
          Actualizar
        </button>
      </div>

      {error && <p className="error-msg">{error}</p>}

      <form className="inline-form" onSubmit={crearMesa}>
        <div className="form-group">
          <label>Número de mesa</label>
          <input
            type="number"
            min="1"
            value={nuevaMesa.numero}
            onChange={(e) => setNuevaMesa((m) => ({ ...m, numero: e.target.value }))}
            required
          />
        </div>
        <div className="form-group">
          <label>Capacidad</label>
          <input
            type="number"
            min="1"
            value={nuevaMesa.capacidad}
            onChange={(e) => setNuevaMesa((m) => ({ ...m, capacidad: e.target.value }))}
            required
          />
        </div>
        <button type="submit" className="btn-primary">
          Crear mesa
        </button>
      </form>

      <div className="mesas-grid">
        {mesas.map((mesa) => (
          <div key={mesa.id} className={`mesa-card mesa-${mesa.estado}`}>
            <div className="mesa-numero">Mesa {mesa.numero}</div>
            <div className="muted small">{mesa.capacidad} plazas</div>
            <span className={claseEstado(mesa.estado)}>{mesa.estado}</span>

            <div className="mesa-actions">
              {mesa.estado === "disponible" && (
                <button
                  className="btn-secondary btn-small"
                  onClick={() => cambiarEstado(mesa, "ocupada")}
                >
                  Ocupar
                </button>
              )}
              {mesa.estado === "ocupada" && (
                <button
                  className="btn-secondary btn-small"
                  onClick={() => cambiarEstado(mesa, "disponible")}
                >
                  Liberar
                </button>
              )}
              <Link className="btn-primary btn-small" to="/admin/pedidos">
                Pedido
              </Link>
            </div>
          </div>
        ))}
        {mesas.length === 0 && <p className="empty-state">No hay mesas registradas.</p>}
      </div>
    </div>
  );
}
