/** Pantalla de Gestión de Mesas - Administrador. Mesas eventuales y barras. */

import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../services/api";
import ConfirmModal from "../components/ConfirmModal";
import CuentaModal from "../components/CuentaModal";
import DivisionModal from "../components/DivisionModal";
import TransferirModal from "../components/TransferirModal";

interface Mesa {
  id: number;
  numero: number;
  capacidad: number;
  estado: string;
  tipo: string;
  grupo: string | null;
  posicion: number;
  total_cuenta?: number;
  tiene_cuenta_pendiente?: boolean;
  detalle_pendiente?: string;
}

export default function MesasPage() {
  const navigate = useNavigate();
  const [mesas, setMesas] = useState<Mesa[]>([]);
  const [nuevaMesa, setNuevaMesa] = useState({ numero: "", capacidad: "4" });
  const [nuevaBarra, setNuevaBarra] = useState({ numero: "", capacidad: "2" });
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<{ mesaId: number; texto: string } | null>(null);
  const [porEliminar, setPorEliminar] = useState<Mesa | null>(null);
  const [errorEliminar, setErrorEliminar] = useState<string | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);

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

  /* Sincronización en vivo: refresca el estado de las mesas periódicamente */
  useEffect(() => {
    const intervalo = setInterval(cargarMesas, 15000);
    return () => clearInterval(intervalo);
  }, []);

  const crearMesa = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await api.createMesa(Number(nuevaMesa.numero), Number(nuevaMesa.capacidad));
      setNuevaMesa({ numero: "", capacidad: "4" });
      setMensaje("Mesa creada");
      await cargarMesas();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const crearBarra = async (e: FormEvent) => {
    e.preventDefault();
    try {
      const res: any = await api.createBarra(
        Number(nuevaBarra.numero),
        Number(nuevaBarra.capacidad)
      );
      setNuevaBarra({ numero: "", capacidad: "2" });
      setMensaje(
        `${res[0]?.grupo || "Barra"} creada con ${res.length} cuenta(s) para clientes`
      );
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

  const eliminarMesa = async () => {
    if (!porEliminar) return;
    setErrorEliminar(null);
    try {
      const res: any = await api.deleteMesa(porEliminar.id);
      setMensaje(res.message || "Mesa eliminada");
      setPorEliminar(null);
      await cargarMesas();
    } catch (err: any) {
      // El modal permanece abierto con el motivo del rechazo
      setErrorEliminar(err.message);
    }
  };

  const abrirPedido = (mesa: Mesa) => {
    navigate(`/admin/pedidos?mesa=${mesa.id}`);
  };

  const claseEstado = (estado: string) =>
    estado === "disponible"
      ? "badge badge-success"
      : estado === "ocupada"
      ? "badge badge-warning"
      : "badge badge-danger";

  const etiquetaMesa = (mesa: Mesa) =>
    mesa.tipo === "barra"
      ? `${mesa.grupo} · Cliente ${mesa.posicion}`
      : `Mesa ${mesa.numero}`;

  const cuentasBarra = (grupo: string) =>
    mesas.filter((m) => m.grupo === grupo).length;

  return (
    <div className="page">
      <div className="page-head">
        <h2>Gestión de mesas</h2>
        <button className="btn-secondary" onClick={cargarMesas}>
          Actualizar
        </button>
      </div>

      {error && <p className="error-msg">{error}</p>}
      {mensaje && <p className="success-msg">{mensaje}</p>}

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

      {/* Crear mesa */}
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

      {/* Crear barra */}
      <form className="inline-form" onSubmit={crearBarra}>
        <div className="form-group">
          <label>Número de barra</label>
          <input
            type="number"
            min="1"
            value={nuevaBarra.numero}
            onChange={(e) => setNuevaBarra((b) => ({ ...b, numero: e.target.value }))}
            placeholder="Ej: 2"
            required
          />
        </div>
        <div className="form-group">
          <label>Capacidad (clientes)</label>
          <input
            type="number"
            min="1"
            max="20"
            value={nuevaBarra.capacidad}
            onChange={(e) => setNuevaBarra((b) => ({ ...b, capacidad: e.target.value }))}
            required
          />
        </div>
        <button type="submit" className="btn-primary">
          + Crear barra
        </button>
        <span className="muted small">
          Cada plaza de la barra es una cuenta independiente.
        </span>
      </form>

      <div className="mesas-grid">
        {mesas.map((mesa) => (
          <div
            key={mesa.id}
            className={`mesa-card mesa-${mesa.estado} ${mesa.tipo === "barra" ? "mesa-barra" : ""}`}
          >
            <div className="mesa-numero">{etiquetaMesa(mesa)}</div>
            <div className="muted small">
              {mesa.tipo === "barra"
                ? `Cliente ${mesa.posicion} de ${cuentasBarra(mesa.grupo || "")} · 1 plaza`
                : `${mesa.capacidad} plazas`}
            </div>
            <span className={claseEstado(mesa.estado)}>{mesa.estado}</span>
            {mesa.tipo === "barra" && (
              <span className="badge badge-info barra-tag">Barra</span>
            )}

            {mesa.tiene_cuenta_pendiente && (
              <div className="mesa-pendiente-valor">
                ${(mesa.total_cuenta || 0).toFixed(2)}
              </div>
            )}

            <div className="mesa-acciones">
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
                  Liberar
                </button>
              )}
              <button
                className="btn-primary btn-small"
                onClick={() => abrirPedido(mesa)}
                title={`Abrir el pedido de ${etiquetaMesa(mesa)}`}
              >
                Pedido
              </button>
              <button
                className="btn-secondary btn-small"
                onClick={() => setMesaCuenta(mesa.id)}
                title={`Ver la cuenta de ${etiquetaMesa(mesa)}`}
              >
                Cuenta
              </button>
              <button
                className="btn-icon danger"
                title="Eliminar mesa"
                onClick={() => {
                  setErrorEliminar(null);
                  setPorEliminar(mesa);
                }}
              >
                ×
              </button>
            </div>
          </div>
        ))}
        {mesas.length === 0 && <p className="empty-state">No hay mesas registradas.</p>}
      </div>

      {/* Confirmación de borrado */}
      {porEliminar && (
        <ConfirmModal
          titulo="Eliminar mesa"
          mensaje={
            porEliminar.tipo === "barra"
              ? `¿Eliminar la cuenta ${porEliminar.posicion} de ${porEliminar.grupo}?`
              : `¿Eliminar la mesa ${porEliminar.numero}?`
          }
          aceptar="Aceptar"
          cancelar="Cancelar"
          onConfirmar={eliminarMesa}
          onCancelar={() => {
            setPorEliminar(null);
            setErrorEliminar(null);
          }}
          error={errorEliminar}
          accionesExtra={
            errorEliminar ? (
              <>
                <button
                  className="btn-secondary btn-small"
                  onClick={() => {
                    const id = porEliminar.id;
                    setPorEliminar(null);
                    setErrorEliminar(null);
                    setMesaCuenta(id);
                  }}
                >
                  Ver la cuenta
                </button>
                <button
                  className="btn-secondary btn-small"
                  onClick={() => {
                    const id = porEliminar.id;
                    setPorEliminar(null);
                    setErrorEliminar(null);
                    navigate(`/admin/pedidos?mesa=${id}`);
                  }}
                >
                  Ver el pedido abierto
                </button>
              </>
            ) : null
          }
        />
      )}

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
          onActualizado={() => cargarMesas()}
        />
      )}

      {/* Ventana de división */}
      {mesaDivision !== null && (
        <DivisionModal
          mesaId={mesaDivision}
          onClose={() => setMesaDivision(null)}
          onConfirmado={() => cargarMesas()}
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
