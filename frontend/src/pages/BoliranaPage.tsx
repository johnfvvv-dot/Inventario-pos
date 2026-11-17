/**
 * Módulo de Bolirana.
 *
 * Administra las boliranas, inicia partidas con mesas/barras/alias, muestra
 * el consumo de la ronda y liquida el total entre los perdedores elegidos.
 */

import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../services/api";
import { formatearPrecio } from "../utils/format";
import { useConfiguracionNegocio } from "../hooks/useConfiguracionNegocio";
import {
  MENSAJE_TURNO_REQUERIDO,
  useTurno,
} from "../context/TurnoContext";
import ConfirmModal from "../components/ConfirmModal";
import CobroParaLlevarModal, {
  type PagoParaLlevar,
} from "../components/CobroParaLlevarModal";
import IniciarPartidaBoliranaModal from "../components/IniciarPartidaBoliranaModal";
import LiquidarPartidaBoliranaModal from "../components/LiquidarPartidaBoliranaModal";
import TurnoRequeridoAviso from "../components/TurnoRequeridoAviso";
import Icon from "../components/Icon";
import type { Bolirana, CargoBolirana } from "../types/bolirana";

interface MesaDisponible {
  id: number;
  numero: number;
  tipo: string;
  estado: string;
  grupo?: string | null;
  en_bolirana?: boolean;
  posiciones?: { id: number; estado: string }[];
}

export default function BoliranaPage() {
  const navigate = useNavigate();
  const negocio = useConfiguracionNegocio();
  const usuario = JSON.parse(localStorage.getItem("user") || "{}");
  const usuarioId = Number(usuario?.id) || 1;
  const esAdmin = usuario?.rol === "admin";
  const basePedidos = esAdmin ? "/admin" : "/bartender";
  const { turno, cargando: cargandoTurno, solicitarApertura } = useTurno();
  const sinTurno = !cargandoTurno && !turno;

  const [boliranas, setBoliranas] = useState<Bolirana[]>([]);
  const [cargos, setCargos] = useState<CargoBolirana[]>([]);
  const [mesas, setMesas] = useState<MesaDisponible[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [nuevaBolirana, setNuevaBolirana] = useState("");
  const [creando, setCreando] = useState(false);

  const [iniciarEn, setIniciarEn] = useState<Bolirana | null>(null);
  const [liquidarEn, setLiquidarEn] = useState<Bolirana | null>(null);
  const [porEliminar, setPorEliminar] = useState<Bolirana | null>(null);
  const [errorEliminar, setErrorEliminar] = useState<string | null>(null);
  const [eliminando, setEliminando] = useState(false);

  const [cargoCobrar, setCargoCobrar] = useState<CargoBolirana | null>(null);
  const [procesandoCargo, setProcesandoCargo] = useState(false);
  const [errorCargo, setErrorCargo] = useState<string | null>(null);

  const cargar = async () => {
    try {
      const [bols, pendientes, mesasData]: any = await Promise.all([
        api.getBoliranas(),
        api.getCargosBolirana(),
        api.getMesas(),
      ]);
      setBoliranas(bols);
      setCargos(pendientes);
      setMesas(mesasData);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setCargando(false);
    }
  };

  useEffect(() => {
    cargar();
    const intervalo = window.setInterval(cargar, 15000);
    return () => window.clearInterval(intervalo);
  }, []);

  const crearBolirana = async (evento: FormEvent) => {
    evento.preventDefault();
    const nombre = nuevaBolirana.trim();
    if (!nombre) {
      setError("Escribe el nombre de la bolirana.");
      return;
    }
    setCreando(true);
    setError(null);
    setMensaje(null);
    try {
      await api.createBolirana(nombre, usuarioId);
      setNuevaBolirana("");
      setMensaje(`Bolirana ${nombre} creada.`);
      await cargar();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setCreando(false);
    }
  };

  const eliminarBolirana = async () => {
    if (!porEliminar) return;
    setEliminando(true);
    setErrorEliminar(null);
    try {
      const res: any = await api.deleteBolirana(porEliminar.id, usuarioId);
      setMensaje(res?.mensaje || "Bolirana eliminada.");
      setPorEliminar(null);
      await cargar();
    } catch (err: any) {
      setErrorEliminar(err.message);
    } finally {
      setEliminando(false);
    }
  };

  const abrirCargaBebidas = (bolirana: Bolirana) => {
    navigate(`${basePedidos}/pedidos?bolirana=${bolirana.id}`);
  };

  const alLiquidar = async (opciones: {
    cobrarAliasAhora: boolean;
    partidaId: number;
  }) => {
    setMensaje("Partida liquidada correctamente.");
    await cargar();
    if (opciones.cobrarAliasAhora) {
      try {
        const pendientes: any = await api.getCargosBolirana();
        setCargos(pendientes);
        // Abre el cargo generado por esta liquidación, no uno anterior.
        const propio = pendientes.find(
          (cargo: CargoBolirana) => cargo.partida_id === opciones.partidaId
        );
        if (propio) setCargoCobrar(propio);
      } catch {
        /* el cargo queda visible en la lista de pendientes */
      }
    }
  };

  const cobrarCargo = async (pagos: PagoParaLlevar[]) => {
    if (!cargoCobrar) return;
    setProcesandoCargo(true);
    setErrorCargo(null);
    try {
      await api.pagarCargoBolirana(cargoCobrar.pedido_id, {
        usuario_id: usuarioId,
        pagos,
      });
      setMensaje(
        `Cargo de ${cargoCobrar.alias || "jugador libre"} cobrado correctamente.`
      );
      setCargoCobrar(null);
      await cargar();
    } catch (err: any) {
      setErrorCargo(err.message);
    } finally {
      setProcesandoCargo(false);
    }
  };

  if (!negocio.modulo_bolirana) {
    return (
      <div className="page">
        <div className="page-head">
          <div>
            <h2>Bolirana</h2>
            <p className="page-subtitulo">
              Competencias por ronda y transferencia del consumo.
            </p>
          </div>
        </div>
        <section className="panel panel-acento panel-acento--naranja">
          <h3>
            <Icon nombre="info" size={15} />
            Módulo desactivado
          </h3>
          <p className="muted">
            El módulo de Bolirana está desactivado. Un Administrador puede
            habilitarlo desde <strong>Personalización → Módulos adicionales</strong>.
          </p>
          {esAdmin && (
            <button
              className="btn-primary"
              onClick={() => navigate("/admin/personalizacion")}
            >
              <Icon nombre="personalizacion" size={16} />
              Ir a Personalización
            </button>
          )}
        </section>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h2>Bolirana</h2>
          <p className="page-subtitulo">
            Competencias por ronda: carga bebidas y transfiere el consumo a los
            perdedores.
          </p>
        </div>
        <button className="btn-secondary" onClick={cargar}>
          <Icon nombre="actualizar" size={16} />
          Actualizar
        </button>
      </div>

      {error && <p className="error-msg">{error}</p>}
      {mensaje && <p className="success-msg">{mensaje}</p>}
      {sinTurno && <TurnoRequeridoAviso onAbrir={solicitarApertura} />}

      {esAdmin && (
        <form className="panel mesas-form bolirana-form" onSubmit={crearBolirana}>
          <div className="mesas-form-head">
            <span className="mesas-form-icono mesas-form-icono--bolirana">
              <Icon nombre="bolirana" size={18} />
            </span>
            <div>
              <h3>Crear bolirana</h3>
              <p>Máquinas disponibles para las competencias</p>
            </div>
          </div>
          <div className="bolirana-form-campos">
            <div className="form-group">
              <label>Nombre de la bolirana</label>
              <input
                value={nuevaBolirana}
                onChange={(e) => setNuevaBolirana(e.target.value)}
                placeholder="Ej: Bolirana 1"
                maxLength={60}
                disabled={creando}
              />
            </div>
            <button
              type="submit"
              className="btn-primary"
              disabled={creando || !nuevaBolirana.trim()}
            >
              <Icon nombre="mas" size={15} />
              {creando ? "Creando..." : "Crear bolirana"}
            </button>
          </div>
        </form>
      )}

      {cargando ? (
        <p className="empty-state">Cargando boliranas...</p>
      ) : boliranas.length === 0 ? (
        <p className="empty-state">
          No hay boliranas registradas.
          {esAdmin ? " Crea la primera con el formulario de arriba." : ""}
        </p>
      ) : (
        <div className="bolirana-grid">
          {boliranas.map((bolirana) => {
            const partida = bolirana.partida;
            return (
              <article
                key={bolirana.id}
                className={`panel bolirana-card ${
                  partida
                    ? "bolirana-card--ocupada"
                    : "bolirana-card--disponible"
                }`}
              >
                <div className="bolirana-card-head">
                  <div>
                    <h3>{bolirana.nombre}</h3>
                    <span
                      className={
                        partida
                          ? "badge badge-warning"
                          : "badge badge-success"
                      }
                    >
                      {partida ? "En partida" : "Disponible"}
                    </span>
                  </div>
                  {esAdmin && (
                    <button
                      className="btn-icon danger"
                      title={`Eliminar ${bolirana.nombre}`}
                      onClick={() => {
                        setErrorEliminar(null);
                        setPorEliminar(bolirana);
                      }}
                    >
                      <Icon nombre="eliminar" size={15} />
                    </button>
                  )}
                </div>

                {partida ? (
                  <>
                    <div className="bolirana-participantes-chips">
                      {partida.participantes.map((participante) => (
                        <span key={participante.id} className="bolirana-chip">
                          {participante.etiqueta}
                        </span>
                      ))}
                    </div>

                    <div className="bolirana-consumo-lista">
                      {partida.consumo.length === 0 ? (
                        <p className="muted small">
                          Sin bebidas cargadas en esta ronda.
                        </p>
                      ) : (
                        partida.consumo.map((item) => (
                          <div
                            key={`${item.producto_id}-${item.precio_unitario}`}
                            className="bolirana-consumo-linea"
                          >
                            <span>
                              {item.cantidad} × {item.producto_nombre}
                            </span>
                            <strong>{formatearPrecio(item.subtotal)}</strong>
                          </div>
                        ))
                      )}
                    </div>

                    <div className="total-row pos-total">
                      <span>Total de la ronda</span>
                      <strong>{formatearPrecio(partida.total_bebidas)}</strong>
                    </div>

                    <div className="bolirana-card-acciones">
                      <button
                        className="btn-secondary"
                        onClick={() => abrirCargaBebidas(bolirana)}
                        disabled={!turno || cargandoTurno}
                        title={!turno ? MENSAJE_TURNO_REQUERIDO : undefined}
                      >
                        <Icon nombre="mas" size={15} />
                        Cargar bebidas
                      </button>
                      <button
                        className="btn-primary"
                        onClick={() => setLiquidarEn(bolirana)}
                        disabled={!turno || cargandoTurno}
                        title={!turno ? MENSAJE_TURNO_REQUERIDO : undefined}
                      >
                        <Icon nombre="recibo" size={15} />
                        Finalizar partida y asignar pago
                      </button>
                    </div>
                  </>
                ) : (
                  <>
                    <p className="muted small">
                      Sin partida activa. Inicia una competencia con dos o más
                      participantes.
                    </p>
                    <div className="bolirana-card-acciones">
                      <button
                        className="btn-primary"
                        onClick={() => setIniciarEn(bolirana)}
                        disabled={!turno || cargandoTurno}
                        title={!turno ? MENSAJE_TURNO_REQUERIDO : undefined}
                      >
                        <Icon nombre="bolirana" size={15} />
                        Iniciar partida
                      </button>
                    </div>
                  </>
                )}
              </article>
            );
          })}
        </div>
      )}

      <section className="panel bolirana-cargos-panel">
        <h3>
          <Icon nombre="recibo" size={15} />
          Cargos pendientes de jugadores libres
        </h3>
        {cargos.length === 0 ? (
          <p className="muted small">
            No hay cargos pendientes. Los jugadores libres perdedores aparecen
            aquí para cobrarlos en caja.
          </p>
        ) : (
          <div className="bolirana-cargos-lista">
            {cargos.map((cargo) => (
              <div key={cargo.pedido_id} className="bolirana-cargo-fila">
                <div>
                  <strong>{cargo.alias || "Jugador libre"}</strong>
                  <span className="muted small"> · {cargo.concepto}</span>
                </div>
                <div className="bolirana-cargo-acciones">
                  <strong>{formatearPrecio(cargo.total)}</strong>
                  <button
                    className="btn-primary btn-small"
                    onClick={() => {
                      setErrorCargo(null);
                      setCargoCobrar(cargo);
                    }}
                    disabled={!turno || cargandoTurno}
                    title={!turno ? MENSAJE_TURNO_REQUERIDO : undefined}
                  >
                    <Icon nombre="efectivo" size={14} />
                    Cobrar
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {iniciarEn && (
        <IniciarPartidaBoliranaModal
          bolirana={iniciarEn}
          mesas={mesas}
          onClose={() => setIniciarEn(null)}
          onIniciado={() => {
            setMensaje(`Partida iniciada en ${iniciarEn.nombre}.`);
            cargar();
          }}
        />
      )}

      {liquidarEn && liquidarEn.partida && (
        <LiquidarPartidaBoliranaModal
          bolirana={liquidarEn}
          partida={liquidarEn.partida}
          onClose={() => setLiquidarEn(null)}
          onLiquidado={alLiquidar}
        />
      )}

      {cargoCobrar && (
        <CobroParaLlevarModal
          items={[
            {
              nombre: cargoCobrar.concepto,
              cantidad: 1,
              precio: cargoCobrar.total,
            },
          ]}
          total={cargoCobrar.total}
          cliente={cargoCobrar.alias}
          titulo="Cobrar cargo de Bolirana"
          etiquetaResumen="Cargo pendiente"
          confirmar={cobrarCargo}
          onClose={() => {
            setCargoCobrar(null);
            setErrorCargo(null);
          }}
          procesando={procesandoCargo}
          error={errorCargo}
        />
      )}

      {porEliminar && (
        <ConfirmModal
          titulo="Eliminar bolirana"
          mensaje={`¿Eliminar ${porEliminar.nombre}? Si ya tiene historial se ocultará sin borrar sus partidas.`}
          aceptar="Eliminar"
          cancelar="Cancelar"
          onConfirmar={eliminarBolirana}
          onCancelar={() => {
            setPorEliminar(null);
            setErrorEliminar(null);
          }}
          procesando={eliminando}
          error={errorEliminar}
        />
      )}
    </div>
  );
}
