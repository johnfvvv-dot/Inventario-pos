/** Pantalla de Corte de Caja - Administrador. */

import { useCallback, useEffect, useState } from "react";
import CierreTurnoModal from "../components/CierreTurnoModal";
import TicketsModal from "../components/TicketsModal";
import { useTurno } from "../context/TurnoContext";
import { api } from "../services/api";
import type { TotalesTurno, TurnoCaja } from "../types/turno";
import {
  formatearDiaSemana,
  formatearFechaHora,
  formatearPrecio,
} from "../utils/format";

interface Resumen {
  desde: string;
  hasta: string;
  totales: TotalesTurno;
  ganancia: number;
  pedidos_cerrados: number;
  mesas_atendidas: number;
  por_forma_pago: Record<string, number>;
}

export default function CorteCajaPage() {
  const {
    turno,
    cargando: cargandoTurno,
    error: errorTurno,
    recargar: recargarTurno,
    solicitarApertura,
  } = useTurno();
  const [turnos, setTurnos] = useState<TurnoCaja[]>([]);
  const [resumen, setResumen] = useState<Resumen | null>(null);
  const [periodo, setPeriodo] = useState(1);
  const [offsetDias, setOffsetDias] = useState(0);
  const [modalCierre, setModalCierre] = useState(false);
  const [ticketsTurnoId, setTicketsTurnoId] = useState<number | null>(null);
  const [errorCierre, setErrorCierre] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [procesando, setProcesando] = useState(false);
  const [cargandoDatos, setCargandoDatos] = useState(true);

  const cargarDatos = useCallback(async () => {
    setCargandoDatos(true);
    try {
      const [hist, res]: any = await Promise.all([
        api.getTurnos(10),
        api.getResumenCaja(periodo, offsetDias),
      ]);
      setTurnos(hist);
      setResumen(res);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setCargandoDatos(false);
    }
  }, [periodo, offsetDias]);

  // Espera a que el contexto resuelva el turno y recarga el historial cada
  // vez que se abre o cierra un turno.
  useEffect(() => {
    if (cargandoTurno) return;
    cargarDatos();
  }, [cargarDatos, cargandoTurno, turno?.id]);

  const actualizar = async () => {
    await Promise.all([recargarTurno(), cargarDatos()]);
  };

  const abrirModalCierre = () => {
    setErrorCierre(null);
    setMensaje(null);
    setModalCierre(true);
  };

  const confirmarCierre = async (observaciones: string) => {
    setProcesando(true);
    setErrorCierre(null);
    try {
      await api.cerrarTurno(observaciones);
      setModalCierre(false);
      setMensaje("Turno de caja cerrado");
      // El contexto actualiza el turno a null y el efecto recarga historial.
      await recargarTurno();
    } catch (err: any) {
      // El modal permanece abierto mostrando el rechazo del backend (409).
      setErrorCierre(err.message);
    } finally {
      setProcesando(false);
    }
  };

  const etiquetaResumen =
    offsetDias === 1
      ? "ayer"
      : periodo === 1
      ? "hoy"
      : `últimos ${periodo} días`;

  return (
    <div className="page">
      <div className="page-head">
        <h2>Corte de caja</h2>
        <div className="filters">
          <select
            value={offsetDias === 1 ? "ayer" : String(periodo)}
            onChange={(e) => {
              if (e.target.value === "ayer") {
                setOffsetDias(1);
                setPeriodo(1);
              } else {
                setOffsetDias(0);
                setPeriodo(Number(e.target.value));
              }
            }}
          >
            <option value="1">Hoy</option>
            <option value="ayer">Ayer</option>
            <option value="7">Últimos 7 días</option>
            <option value="30">Últimos 30 días</option>
          </select>
          <button className="btn-secondary" onClick={actualizar}>
            Actualizar
          </button>
        </div>
      </div>

      {(error || errorTurno) && (
        <p className="error-msg">{error || errorTurno}</p>
      )}
      {mensaje && <p className="success-msg">{mensaje}</p>}

      {/* Turno abierto */}
      <section className="panel">
        <div className="page-head">
          <h3>Turno actual</h3>
          {turno ? (
            <div className="acciones-turno">
              <button
                className="btn-secondary"
                onClick={() => setTicketsTurnoId(turno.id)}
                disabled={cargandoTurno}
              >
                Tickets
              </button>
              <button
                className="btn-warning"
                onClick={abrirModalCierre}
                disabled={procesando}
              >
                {procesando ? "Cerrando..." : "Cerrar turno"}
              </button>
            </div>
          ) : cargandoTurno ? (
            <button className="btn-secondary" disabled>
              Cargando...
            </button>
          ) : (
            <button
              className="btn-primary"
              onClick={solicitarApertura}
              disabled={procesando}
            >
              Abrir turno
            </button>
          )}
        </div>

        {turno ? (
          <>
            <p className="muted small">
              Abierto por <strong>{turno.usuario_nombre}</strong> el{" "}
              {formatearFechaHora(turno.fecha_apertura)} · Fondo inicial:{" "}
              <strong>{formatearPrecio(turno.fondo_inicial || 0)}</strong>
            </p>
            <div className="kpis">
              <div className="kpi-card">
                <h3>Efectivo</h3>
                <h2>{formatearPrecio(turno.totales.efectivo)}</h2>
              </div>
              <div className="kpi-card">
                <h3>Tarjeta</h3>
                <h2>{formatearPrecio(turno.totales.tarjeta)}</h2>
              </div>
              <div className="kpi-card">
                <h3>Transferencia</h3>
                <h2>{formatearPrecio(turno.totales.transferencia)}</h2>
              </div>
              <div className="kpi-card kpi-total">
                <h3>Total del turno</h3>
                <h2>{formatearPrecio(turno.totales.total)}</h2>
              </div>
              <div className="kpi-card kpi-ganancia">
                <h3>Ganancia del turno</h3>
                <h2>{formatearPrecio(turno.ganancia || 0)}</h2>
              </div>
            </div>
          </>
        ) : cargandoTurno ? (
          <p className="empty-state">Cargando turno...</p>
        ) : (
          <p className="empty-state">
            No hay un turno abierto. Abre un turno para empezar a registrar la caja del día.
          </p>
        )}
      </section>

      {/* Resumen del periodo */}
      {resumen && (
        <section className="panel">
          <h3>Resumen de ventas ({etiquetaResumen})</h3>
          <p className="muted small">
            Rango: {formatearFechaHora(resumen.desde)} —{" "}
            {formatearFechaHora(resumen.hasta)}
          </p>
          <div className="kpis">
            <div className="kpi-card">
              <h3>Efectivo</h3>
              <h2>{formatearPrecio(resumen.totales.efectivo)}</h2>
            </div>
            <div className="kpi-card">
              <h3>Tarjeta</h3>
              <h2>{formatearPrecio(resumen.totales.tarjeta)}</h2>
            </div>
            <div className="kpi-card">
              <h3>Transferencia</h3>
              <h2>{formatearPrecio(resumen.totales.transferencia)}</h2>
            </div>
            <div className="kpi-card kpi-total">
              <h3>Total</h3>
              <h2>{formatearPrecio(resumen.totales.total)}</h2>
            </div>
            <div className="kpi-card kpi-ganancia">
              <h3>Ganancia</h3>
              <h2>{formatearPrecio(resumen.ganancia || 0)}</h2>
            </div>
          </div>
          <p className="muted small">
            {resumen.pedidos_cerrados} pedidos cerrados · {resumen.mesas_atendidas} mesas atendidas ·{" "}
            {resumen.totales.operaciones} operaciones cobradas
          </p>
        </section>
      )}

      {/* Historial */}
      <section className="panel">
        <h3>Historial de turnos</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Día</th>
                <th>Abierto</th>
                <th>Cerrado</th>
                <th>Usuario</th>
                <th>Fondo inicial</th>
                <th>Efectivo</th>
                <th>Tarjeta</th>
                <th>Transfer.</th>
                <th>Total</th>
                <th>Ganancia</th>
                <th>Observaciones</th>
                <th>Tickets</th>
              </tr>
            </thead>
            <tbody>
              {turnos.map((t) => (
                <tr key={t.id}>
                  <td>{t.id}</td>
                  <td>{formatearDiaSemana(t.fecha_apertura)}</td>
                  <td>{formatearFechaHora(t.fecha_apertura)}</td>
                  <td>{formatearFechaHora(t.fecha_cierre)}</td>
                  <td>{t.usuario_nombre}</td>
                  <td>{formatearPrecio(t.fondo_inicial || 0)}</td>
                  <td>{formatearPrecio(t.totales.efectivo)}</td>
                  <td>{formatearPrecio(t.totales.tarjeta)}</td>
                  <td>{formatearPrecio(t.totales.transferencia)}</td>
                  <td>
                    <strong>{formatearPrecio(t.totales.total)}</strong>
                  </td>
                  <td>{formatearPrecio(t.ganancia || 0)}</td>
                  <td className="obs-cell">{t.observaciones || "—"}</td>
                  <td>
                    <button
                      className="btn-secondary btn-small"
                      onClick={() => setTicketsTurnoId(t.id)}
                    >
                      Ver tickets
                    </button>
                  </td>
                </tr>
              ))}
              {turnos.length === 0 && (
                <tr>
                  <td colSpan={13} className="empty-state">
                    {cargandoDatos
                      ? "Cargando turnos..."
                      : "Todavía no hay turnos registrados."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {ticketsTurnoId !== null && (
        <TicketsModal
          turnoId={ticketsTurnoId}
          onCerrar={() => setTicketsTurnoId(null)}
        />
      )}

      {modalCierre && turno && (
        <CierreTurnoModal
          total={turno.totales.total}
          onCancelar={() => {
            setModalCierre(false);
            setErrorCierre(null);
          }}
          onConfirmar={confirmarCierre}
          procesando={procesando}
          error={errorCierre}
        />
      )}
    </div>
  );
}
