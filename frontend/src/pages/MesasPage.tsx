/** Pantalla de Gestión de Mesas - Administrador. Mesas eventuales y barras. */

import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../services/api";
import ConfirmModal from "../components/ConfirmModal";
import CuentaModal from "../components/CuentaModal";
import DivisionModal from "../components/DivisionModal";
import TransferirModal from "../components/TransferirModal";

interface Posicion {
  id: number;
  estado: string;
  total_cuenta: number;
}

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
  posiciones?: Posicion[];
}

/** Formatea el total con separador de miles y sin decimales .00. */
const formatearTotal = (total: number): string =>
  total.toLocaleString("es-CO", {
    minimumFractionDigits: Number.isInteger(total) ? 0 : 2,
    maximumFractionDigits: Number.isInteger(total) ? 0 : 2,
  });

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
  const [barraCuenta, setBarraCuenta] = useState<number | null>(null);
  const [mesaDivision, setMesaDivision] = useState<number | null>(null);
  const [barraDivision, setBarraDivision] = useState<number | null>(null);
  const [mesaTransferir, setMesaTransferir] = useState<number | null>(null);
  const [barraTransferir, setBarraTransferir] = useState<number | null>(null);

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

  /** Asigna un cliente: en una mesa la ocupa, en una barra toma un puesto libre */
  const ocupar = async (mesa: Mesa) => {
    try {
      if (mesa.tipo === "barra") {
        const res: any = await api.ocuparMesa(mesa.id);
        await cargarMesas();
        navigate(`/admin/pedidos?mesa=${res.mesa_id}`);
      } else {
        await cambiarEstado(mesa, "ocupada");
      }
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
    mesa.tipo === "barra" ? `Barra ${mesa.numero}` : `Mesa ${mesa.numero}`;

  const cuentasBarra = (grupo: string) =>
    mesas.filter((m) => m.grupo === grupo).length;

  const barraTieneCuenta = (numero: number) =>
    mesas.some(
      (m) =>
        m.tipo === "barra" &&
        m.numero === numero &&
        m.tiene_cuenta_pendiente
    );

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
            <div className="muted small">{mesa.capacidad} plazas</div>
            <div className="mesa-estado-fila">
              <span className={claseEstado(mesa.estado)}>{mesa.estado}</span>
              {mesa.tipo === "barra" && (
                <span className="badge barra-tag">Barra</span>
              )}
            </div>

            {mesa.tiene_cuenta_pendiente && (
              <div className="mesa-pendiente-valor">
                ${formatearTotal(mesa.total_cuenta || 0)}
              </div>
            )}

            <div className="mesa-acciones">
              {mesa.estado === "disponible" && (
                <button
                  className="btn-secondary btn-small"
                  onClick={() => ocupar(mesa)}
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
                onClick={() =>
                  mesa.tipo === "barra"
                    ? setBarraCuenta(mesa.numero)
                    : setMesaCuenta(mesa.id)
                }
                title={`Ver la cuenta de ${etiquetaMesa(mesa)}`}
              >
                Cuenta
              </button>
              <button
                className="btn-icon danger"
                title={
                  mesa.tipo === "barra"
                    ? "Eliminar barra completa"
                    : "Eliminar mesa"
                }
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
          titulo={
            porEliminar.tipo === "barra"
              ? "Eliminar barra"
              : "Eliminar mesa"
          }
          mensaje={
            porEliminar.tipo === "barra"
              ? `¿Eliminar la barra ${porEliminar.numero}?`
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
                    const numero = porEliminar.numero;
                    const esBarra = porEliminar.tipo === "barra";
                    setPorEliminar(null);
                    setErrorEliminar(null);
                    if (esBarra) {
                      setBarraCuenta(numero);
                    } else {
                      setMesaCuenta(id);
                    }
                  }}
                >
                  Ver la cuenta
                </button>
                <button
                  className="btn-secondary btn-small"
                  onClick={() => {
                    const id =
                      porEliminar.tipo === "barra"
                        ? (porEliminar.posiciones?.find(
                            (p) => p.total_cuenta > 0
                          )?.id ?? porEliminar.id)
                        : porEliminar.id;
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

      {/* Ventana de cuenta agregada de la barra */}
      {barraCuenta !== null && (
        <CuentaModal
          mesaId={barraCuenta}
          barraNumero={barraCuenta}
          onClose={() => setBarraCuenta(null)}
          onDividir={() => {
            setBarraCuenta(null);
            setBarraDivision(barraCuenta);
          }}
          onTransferir={
            barraTieneCuenta(barraCuenta)
              ? () => {
                  setBarraCuenta(null);
                  setBarraTransferir(barraCuenta);
                }
              : undefined
          }
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

      {/* Ventana de división de una barra completa */}
      {barraDivision !== null && (
        <DivisionModal
          barraNumero={barraDivision}
          onClose={() => setBarraDivision(null)}
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

      {/* Ventana de transferencia desde una barra */}
      {barraTransferir !== null && (
        <TransferirModal
          barraNumero={barraTransferir}
          onClose={() => setBarraTransferir(null)}
          onTransferido={() => {
            setBarraTransferir(null);
            cargarMesas();
          }}
        />
      )}
    </div>
  );
}
