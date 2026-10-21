/** Pantalla de Gestión de Mesas - Administrador. */

import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../services/api";
import CuentaModal from "../components/CuentaModal";
import DivisionModal from "../components/DivisionModal";
import TransferirModal from "../components/TransferirModal";

interface Mesa {
  id: number;
  numero: number;
  capacidad: number;
  estado: string;
  total_cuenta?: number;
  tiene_cuenta_pendiente?: boolean;
  detalle_pendiente?: string;
}

interface Aviso {
  mesaId: number;
  texto: string;
}

export default function MesasPage() {
  const navigate = useNavigate();
  const [mesas, setMesas] = useState<Mesa[]>([]);
  const [nuevaMesa, setNuevaMesa] = useState({ numero: "", capacidad: "4" });
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<Aviso | null>(null);

  // Modales
  const [mesaCuenta, setMesaCuenta] = useState<number | null>(null);
  const [mesaDivision, setMesaDivision] = useState<number | null>(null);
  const [mesaTransferir, setMesaTransferir] = useState<number | null>(null);

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

  /**
   * Libera la mesa. Si tiene cuentas pendientes, el backend lo rechaza y
   * se muestra el aviso con la opción de ver el pedido abierto.
   */
  const liberarMesa = async (mesa: Mesa) => {
    setAviso(null);
    try {
      await api.liberarMesa(mesa.id);
      await cargarMesas();
    } catch (err: any) {
      setAviso({ mesaId: mesa.id, texto: err.message });
    }
  };

  /** Abre el pedido con la mesa ya seleccionada */
  const abrirPedido = (mesa: Mesa) => {
    navigate(`/admin/pedidos?mesa=${mesa.id}`);
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

      {/* Aviso de mesa con cuenta pendiente */}
      {aviso && (
        <div className="aviso-panel">
          <div className="aviso-texto">
            <strong>Aviso:</strong> {aviso.texto}
          </div>
          <div className="aviso-acciones">
            <button
              className="btn-secondary btn-small"
              onClick={() => {
                const mesa = mesas.find((m) => m.id === aviso.mesaId);
                setAviso(null);
                if (mesa) abrirPedido(mesa);
              }}
            >
              Ver el pedido abierto
            </button>
            <button
              className="btn-secondary btn-small"
              onClick={() => {
                setAviso(null);
                setMesaCuenta(aviso.mesaId);
              }}
            >
              Ver la cuenta
            </button>
            <button className="btn-icon" onClick={() => setAviso(null)} title="Cerrar aviso">
              ×
            </button>
          </div>
        </div>
      )}

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

            {mesa.tiene_cuenta_pendiente && (
              <div className="mesa-pendiente">
                <strong>${(mesa.total_cuenta || 0).toFixed(2)}</strong> pendiente
                <span className="muted small">{mesa.detalle_pendiente}</span>
              </div>
            )}

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
                  onClick={() => liberarMesa(mesa)}
                >
                  Liberar mesa
                </button>
              )}
              <button
                className="btn-primary btn-small"
                onClick={() => abrirPedido(mesa)}
                title={`Abrir el pedido de la mesa ${mesa.numero}`}
              >
                Pedido
              </button>
              <button
                className="btn-secondary btn-small"
                onClick={() => setMesaCuenta(mesa.id)}
                title={`Ver la cuenta de la mesa ${mesa.numero}`}
              >
                Cuenta
              </button>
              {mesa.tiene_cuenta_pendiente && (
                <button
                  className="btn-secondary btn-small"
                  onClick={() => setMesaTransferir(mesa.id)}
                  title="Mover la cuenta a otra mesa"
                >
                  Transferir
                </button>
              )}
            </div>
          </div>
        ))}
        {mesas.length === 0 && <p className="empty-state">No hay mesas registradas.</p>}
      </div>

      {/* Ventana de cuenta */}
      {mesaCuenta !== null && (
        <CuentaModal
          mesaId={mesaCuenta}
          onClose={() => setMesaCuenta(null)}
          onDividir={() => {
            setMesaCuenta(null);
            setMesaDivision(mesaCuenta);
          }}
          onTransferir={() => {
            setMesaCuenta(null);
            setMesaTransferir(mesaCuenta);
          }}
        />
      )}

      {/* Ventana de división */}
      {mesaDivision !== null && (
        <DivisionModal
          mesaId={mesaDivision}
          onClose={() => setMesaDivision(null)}
          onConfirmado={() => {
            cargarMesas();
          }}
        />
      )}

      {/* Ventana de transferencia */}
      {mesaTransferir !== null && (
        <TransferirModal
          mesaId={mesaTransferir}
          onClose={() => setMesaTransferir(null)}
          onTransferido={() => {
            setMesaTransferir(null);
            cargarMesas();
          }}
        />
      )}
    </div>
  );
}
