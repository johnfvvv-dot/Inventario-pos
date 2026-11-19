/** Pantalla de Gestión de Mesas - Administrador. Mesas eventuales y barras. */

import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../services/api";
import { formatearPrecio } from "../utils/format";
import {
  MENSAJE_TURNO_REQUERIDO,
  useTurno,
} from "../context/TurnoContext";
import ConfirmModal from "../components/ConfirmModal";
import CuentaModal from "../components/CuentaModal";
import DivisionModal from "../components/DivisionModal";
import TransferirModal from "../components/TransferirModal";
import TurnoRequeridoAviso from "../components/TurnoRequeridoAviso";
import Icon from "../components/Icon";

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
  nombre?: string | null;
  total_cuenta?: number;
  tiene_cuenta_pendiente?: boolean;
  en_bolirana?: boolean;
  bolirana_nombre?: string | null;
  posiciones?: Posicion[];
}

export default function MesasPage() {
  const navigate = useNavigate();
  const usuario = JSON.parse(localStorage.getItem("user") || "{}");
  // El panel de mesas lo comparten Administrador y Bartender; cada uno debe
  // volver a su propia ruta de pedidos, no siempre a /admin.
  const basePedidos = usuario?.rol === "bartender" ? "/bartender" : "/admin";
  const { turno, cargando: cargandoTurno, solicitarApertura } = useTurno();
  const sinTurno = !cargandoTurno && !turno;
  const [mesas, setMesas] = useState<Mesa[]>([]);
  const [nuevaMesa, setNuevaMesa] = useState({ numero: "", capacidad: "4" });
  const [nuevaBarra, setNuevaBarra] = useState({ numero: "", capacidad: "2" });
  const [nuevoCliente, setNuevoCliente] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<{ mesaId: number; texto: string } | null>(null);
  const [avisoBolirana, setAvisoBolirana] = useState<Mesa | null>(null);
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

  const crearCliente = async (e: FormEvent) => {
    e.preventDefault();
    const nombre = nuevoCliente.trim();
    if (!nombre) return;
    if (!turno) {
      setError(MENSAJE_TURNO_REQUERIDO);
      return;
    }
    try {
      await api.crearClienteIndividual(nombre);
      setNuevoCliente("");
      setMensaje(`Cliente individual "${nombre}" creado`);
      await cargarMesas();
    } catch (err: any) {
      setError(err.message);
    }
  };

  /** Asigna un cliente: en una mesa la ocupa, en una barra toma un puesto libre.
   *  Solo cambia el estado; no abre la ventana de pedidos. */
  const ocupar = async (mesa: Mesa) => {
    if (!turno) {
      setError(MENSAJE_TURNO_REQUERIDO);
      return;
    }

    try {
      if (mesa.tipo === "barra") {
        // La tarjeta agregada usa la posicion activa; el backend asigna la
        // primera plaza libre del grupo y no redirige.
        await api.ocuparMesa(mesa.id);
      } else {
        await api.updateMesaEstado(mesa.id, "ocupada");
      }
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
    if (mesa.en_bolirana) {
      // La tarjeta no se bloquea: se explica el motivo en un modal claro.
      setAvisoBolirana(mesa);
      return;
    }
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
    navigate(`${basePedidos}/pedidos?mesa=${mesa.id}`);
  };

  const claseEstado = (estado: string) =>
    estado === "disponible"
      ? "badge badge-success"
      : estado === "ocupada"
      ? "badge badge-warning"
      : "badge badge-danger";

  const etiquetaMesa = (mesa: Mesa) =>
    mesa.tipo === "barra"
      ? `Barra ${mesa.numero}`
      : mesa.tipo === "individual"
      ? mesa.nombre || "Cliente individual"
      : `Mesa ${mesa.numero}`;

  const individuales = mesas.filter((m) => m.tipo === "individual");
  // Orden estricto de la cuadrícula: mesas, barras y clientes individuales.
  const mesasOrdenadas = mesas
    .filter((m) => m.tipo !== "barra" && m.tipo !== "individual")
    .slice()
    .sort((a, b) => a.numero - b.numero);
  const barrasOrdenadas = mesas
    .filter((m) => m.tipo === "barra")
    .slice()
    .sort((a, b) => a.numero - b.numero);
  const mesasYBarras = [...mesasOrdenadas, ...barrasOrdenadas];

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
        <div>
          <h2>Gestión de mesas</h2>
          <p className="page-subtitulo">
            Control de ocupación, pedidos activos y cobro de cuentas en salón y
            barra
          </p>
        </div>
        <button className="btn-secondary" onClick={cargarMesas}>
          <Icon nombre="actualizar" size={16} />
          Actualizar
        </button>
      </div>

      {error && <p className="error-msg">{error}</p>}
      {mensaje && <p className="success-msg">{mensaje}</p>}

      {sinTurno && <TurnoRequeridoAviso onAbrir={solicitarApertura} />}

      {/* Aviso de mesa con cuenta pendiente */}
      {aviso && (
        <div className="aviso-panel">
          <span className="aviso-icono">
            <Icon nombre="alerta" size={18} />
          </span>
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
              <Icon nombre="pedidos" size={14} />
              Ver el pedido abierto
            </button>
            <button
              className="btn-secondary btn-small"
              onClick={() => {
                setAviso(null);
                setMesaCuenta(aviso.mesaId);
              }}
            >
              <Icon nombre="recibo" size={14} />
              Ver la cuenta
            </button>
            <button className="btn-icon" onClick={() => setAviso(null)} title="Cerrar aviso">
              <Icon nombre="cerrar" size={15} />
            </button>
          </div>
        </div>
      )}

      {/* Crear mesa y barra */}
      <div className="mesas-creacion-grid">
        <form className="panel mesas-form" onSubmit={crearMesa}>
          <div className="mesas-form-head">
            <span className="mesas-form-icono">
              <Icon nombre="mesa" size={18} />
            </span>
            <div>
              <h3>Crear mesa</h3>
              <p>Mesas para el salón</p>
            </div>
          </div>
          <div className="mesas-form-campos">
            <div className="form-group">
              <label>Número de mesa</label>
              <input
                type="number"
                min="1"
                value={nuevaMesa.numero}
                onChange={(e) =>
                  setNuevaMesa((m) => ({ ...m, numero: e.target.value }))
                }
                placeholder="Ej: 1"
                required
              />
            </div>
            <div className="form-group">
              <label>Capacidad</label>
              <input
                type="number"
                min="1"
                value={nuevaMesa.capacidad}
                onChange={(e) =>
                  setNuevaMesa((m) => ({ ...m, capacidad: e.target.value }))
                }
                required
              />
            </div>
            <button type="submit" className="btn-primary">
              <Icon nombre="mas" size={15} />
              Crear mesa
            </button>
          </div>
        </form>

        <form className="panel mesas-form" onSubmit={crearBarra}>
          <div className="mesas-form-head">
            <span className="mesas-form-icono mesas-form-icono--barra">
              <Icon nombre="barra" size={18} />
            </span>
            <div>
              <h3>Crear barra</h3>
              <p>Barras para servicio rápido</p>
            </div>
          </div>
          <div className="mesas-form-campos">
            <div className="form-group">
              <label>Número de barra</label>
              <input
                type="number"
                min="1"
                value={nuevaBarra.numero}
                onChange={(e) =>
                  setNuevaBarra((b) => ({ ...b, numero: e.target.value }))
                }
                placeholder="Ej: 2"
                required
              />
            </div>
            <div className="form-group">
              <label>Capacidad</label>
              <input
                type="number"
                min="1"
                max="20"
                value={nuevaBarra.capacidad}
                onChange={(e) =>
                  setNuevaBarra((b) => ({ ...b, capacidad: e.target.value }))
                }
                required
              />
            </div>
            <button type="submit" className="btn-primary">
              <Icon nombre="mas" size={15} />
              Crear barra
            </button>
          </div>
        </form>

        <form
          className="panel mesas-form mesas-form--individual"
          onSubmit={crearCliente}
        >
          <div className="mesas-form-head">
            <span className="mesas-form-icono mesas-form-icono--individual">
              <Icon nombre="usuario" size={18} />
            </span>
            <div>
              <h3>Crear cliente individual</h3>
              <p>Cuentas personales sin mesa asignada</p>
            </div>
          </div>
          <div className="mesas-form-campos mesas-form-campos--individual">
            <div className="form-group">
              <label>Nombre / alias del cliente</label>
              <input
                type="text"
                value={nuevoCliente}
                onChange={(e) => setNuevoCliente(e.target.value)}
                placeholder="Ej: Carlos"
                maxLength={60}
                required
              />
            </div>
            <button
              type="submit"
              className="btn-primary"
              disabled={!turno || cargandoTurno}
              title={!turno ? MENSAJE_TURNO_REQUERIDO : undefined}
            >
              <Icon nombre="mas" size={15} />
              Crear cliente
            </button>
          </div>
        </form>
      </div>

      <div className="mesas-grid">
        {mesasYBarras.map((mesa) => (
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

            {mesa.en_bolirana && (
              <span
                className="badge badge-bolirana"
                title={`En partida en ${mesa.bolirana_nombre}. La cuenta se puede consultar, pero no cobrar ni cerrar hasta liquidarla.`}
              >
                <Icon nombre="bolirana" size={12} />
                <span className="badge-bolirana-nombre">
                  {mesa.bolirana_nombre || "Bolirana"}
                </span>
                <Icon nombre="candado" size={12} />
              </span>
            )}

            {mesa.tiene_cuenta_pendiente && (
              <div className="mesa-pendiente-valor">
                {formatearPrecio(mesa.total_cuenta || 0)}
              </div>
            )}

            <div className="mesa-acciones">
              {mesa.estado === "disponible" && (
                <button
                  className="btn-secondary btn-small"
                  onClick={() => ocupar(mesa)}
                  disabled={!turno || cargandoTurno}
                  title={!turno ? MENSAJE_TURNO_REQUERIDO : "Ocupar la mesa"}
                >
                  <Icon nombre="check" size={14} />
                  Ocupar
                </button>
              )}
              {mesa.estado === "ocupada" && (
                <button
                  className="btn-secondary btn-small"
                  onClick={() => liberarMesa(mesa)}
                  title={
                    mesa.en_bolirana
                      ? `La mesa está en una partida de ${mesa.bolirana_nombre}. Pulsa para ver el aviso.`
                      : "Liberar la mesa"
                  }
                >
                  <Icon nombre="check" size={14} />
                  Liberar
                </button>
              )}
              <button
                className="btn-primary btn-small"
                onClick={() => abrirPedido(mesa)}
                title={
                  !turno
                    ? MENSAJE_TURNO_REQUERIDO
                    : `Abrir el pedido de ${etiquetaMesa(mesa)}`
                }
                disabled={!turno || cargandoTurno}
              >
                <Icon nombre="pedidos" size={14} />
                Pedido
              </button>
              <button
                className="btn-secondary btn-small"
                onClick={() =>
                  mesa.tipo === "barra"
                    ? setBarraCuenta(mesa.numero)
                    : setMesaCuenta(mesa.id)
                }
                title={
                  mesa.en_bolirana
                    ? `Consultar la cuenta (en partida de ${mesa.bolirana_nombre}). No se puede cobrar hasta liquidarla.`
                    : `Ver la cuenta de ${etiquetaMesa(mesa)}`
                }
              >
                <Icon nombre="recibo" size={14} />
                Cuenta
              </button>
              <button
                className="btn-icon danger"
                title={
                  mesa.en_bolirana
                    ? `No se puede eliminar: tiene una partida activa en ${mesa.bolirana_nombre}.`
                    : mesa.tipo === "barra"
                    ? "Eliminar barra completa"
                    : "Eliminar mesa"
                }
                onClick={() => {
                  setErrorEliminar(null);
                  setPorEliminar(mesa);
                }}
                disabled={Boolean(mesa.en_bolirana)}
              >
                <Icon nombre="eliminar" size={15} />
              </button>
            </div>
          </div>
        ))}

        {individuales.map((mesa) => (
          <div
            key={mesa.id}
            className={`mesa-card mesa-individual mesa-${mesa.estado}`}
          >
            <div className="mesa-individual-head">
              <div className="mesa-numero">{etiquetaMesa(mesa)}</div>
              <span className="badge badge-individual">Individual</span>
            </div>
            <div className="muted small">Cuenta personal sin mesa</div>
            <div className="mesa-estado-fila">
              <span className={claseEstado(mesa.estado)}>{mesa.estado}</span>
            </div>

            {mesa.en_bolirana && (
              <span
                className="badge badge-bolirana"
                title={`En partida en ${mesa.bolirana_nombre}. La cuenta se puede consultar, pero no cobrar ni cerrar hasta liquidarla.`}
              >
                <Icon nombre="bolirana" size={12} />
                <span className="badge-bolirana-nombre">
                  {mesa.bolirana_nombre || "Bolirana"}
                </span>
                <Icon nombre="candado" size={12} />
              </span>
            )}

            <div className="mesa-pendiente-valor">
              {formatearPrecio(mesa.total_cuenta || 0)}
            </div>

            <div className="mesa-acciones">
              <button
                className="btn-primary btn-small"
                onClick={() => abrirPedido(mesa)}
                title={
                  !turno
                    ? MENSAJE_TURNO_REQUERIDO
                    : `Abrir el pedido de ${etiquetaMesa(mesa)}`
                }
                disabled={!turno || cargandoTurno}
              >
                <Icon nombre="pedidos" size={14} />
                Pedido
              </button>
              <button
                className="btn-secondary btn-small"
                onClick={() => setMesaCuenta(mesa.id)}
                title={
                  mesa.en_bolirana
                    ? `Consultar la cuenta (en partida de ${mesa.bolirana_nombre}). No se puede cobrar hasta liquidarla.`
                    : `Ver la cuenta de ${etiquetaMesa(mesa)}`
                }
              >
                <Icon nombre="recibo" size={14} />
                Cuenta
              </button>
              {!mesa.tiene_cuenta_pendiente &&
                !mesa.en_bolirana &&
                Number(mesa.total_cuenta || 0) === 0 && (
                  <button
                    className="btn-icon danger"
                    title="Eliminar cliente individual"
                    onClick={() => {
                      setErrorEliminar(null);
                      setPorEliminar(mesa);
                    }}
                  >
                    <Icon nombre="eliminar" size={15} />
                  </button>
                )}
            </div>
          </div>
        ))}

        {mesasYBarras.length === 0 && individuales.length === 0 && (
          <p className="empty-state">No hay mesas registradas.</p>
        )}
      </div>

      {/* Confirmación de borrado */}
      {porEliminar && (
        <ConfirmModal
          titulo={
            porEliminar.tipo === "barra"
              ? "Eliminar barra"
              : porEliminar.tipo === "individual"
              ? "Eliminar cliente individual"
              : "Eliminar mesa"
          }
          mensaje={
            porEliminar.tipo === "barra"
              ? `¿Eliminar la barra ${porEliminar.numero}?`
              : porEliminar.tipo === "individual"
              ? `¿Eliminar el cliente individual "${
                  porEliminar.nombre || "Cliente"
                }"?`
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
                    navigate(`${basePedidos}/pedidos?mesa=${id}`);
                  }}
                >
                  Ver el pedido abierto
                </button>
              </>
            ) : null
          }
        />
      )}

      {/* Aviso al intentar liberar una mesa/barra en partida de Bolirana */}
      {avisoBolirana && (
        <ConfirmModal
          titulo="Partida de Bolirana activa"
          mensaje={`${
            avisoBolirana.tipo === "barra"
              ? "Esta barra"
              : avisoBolirana.tipo === "individual"
              ? "Este cliente individual"
              : "Esta mesa"
          } tiene una partida activa en ${
            avisoBolirana.bolirana_nombre || "Bolirana"
          }. Finaliza la partida y define el pago antes de liberarla.`}
          aceptar="Entendido"
          cancelar="Cerrar"
          onConfirmar={() => setAvisoBolirana(null)}
          onCancelar={() => setAvisoBolirana(null)}
          accionesExtra={
            <button
              className="btn-secondary btn-small"
              onClick={() => {
                const mesa = avisoBolirana;
                setAvisoBolirana(null);
                if (mesa.tipo === "barra") setBarraCuenta(mesa.numero);
                else setMesaCuenta(mesa.id);
              }}
            >
              <Icon nombre="recibo" size={14} />
              Ver la cuenta
            </button>
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
