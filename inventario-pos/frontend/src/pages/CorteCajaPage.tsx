/** Pantalla de Corte de Caja - Administrador. */

import { useEffect, useState } from "react";
import { api } from "../services/api";

interface Totales {
  efectivo: number;
  tarjeta: number;
  transferencia: number;
  total: number;
  operaciones: number;
}

interface Turno {
  id: number;
  usuario_nombre: string;
  fecha_apertura: string;
  fecha_cierre: string | null;
  observaciones: string | null;
  estado: string;
  totales: Totales;
}

interface Resumen {
  desde: string;
  hasta: string;
  totales: Totales;
  pedidos_cerrados: number;
  mesas_atendidas: number;
  por_forma_pago: Record<string, number>;
}

export default function CorteCajaPage() {
  const [turno, setTurno] = useState<Turno | null>(null);
  const [turnos, setTurnos] = useState<Turno[]>([]);
  const [resumen, setResumen] = useState<Resumen | null>(null);
  const [periodo, setPeriodo] = useState(1);
  const [observaciones, setObservaciones] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [procesando, setProcesando] = useState(false);

  const usuario = JSON.parse(localStorage.getItem("user") || "{}");
  const usuarioId: number = usuario?.id || 1;

  const cargar = async () => {
    try {
      const [t, hist, res]: any = await Promise.all([
        api.getTurnoActual(),
        api.getTurnos(10),
        api.getResumenCaja(periodo),
      ]);
      setTurno(t);
      setTurnos(hist);
      setResumen(res);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    }
  };

  useEffect(() => {
    cargar();
  }, [periodo]);

  const abrirTurno = async () => {
    setProcesando(true);
    try {
      const res: any = await api.abrirTurno(usuarioId);
      setMensaje(res.mensaje || "Turno abierto");
      await cargar();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setProcesando(false);
    }
  };

  const cerrarTurno = async () => {
    if (!window.confirm("¿Cerrar el turno de caja? El resumen quedará guardado.")) {
      return;
    }
    setProcesando(true);
    try {
      await api.cerrarTurno(observaciones);
      setObservaciones("");
      setMensaje("Turno de caja cerrado");
      await cargar();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setProcesando(false);
    }
  };

  const fmtFecha = (f: string | null) =>
    f ? new Date(f).toLocaleString("es", { dateStyle: "short", timeStyle: "short" }) : "-";

  return (
    <div className="page">
      <div className="page-head">
        <h2>Corte de caja</h2>
        <div className="filters">
          <select value={periodo} onChange={(e) => setPeriodo(Number(e.target.value))}>
            <option value={1}>Hoy</option>
            <option value={7}>Últimos 7 días</option>
            <option value={30}>Últimos 30 días</option>
          </select>
          <button className="btn-secondary" onClick={cargar}>
            Actualizar
          </button>
        </div>
      </div>

      {error && <p className="error-msg">{error}</p>}
      {mensaje && <p className="success-msg">{mensaje}</p>}

      {/* Turno abierto */}
      <section className="panel">
        <div className="page-head">
          <h3>Turno actual</h3>
          {turno ? (
            <button className="btn-warning" onClick={cerrarTurno} disabled={procesando}>
              {procesando ? "Cerrando..." : "Cerrar turno"}
            </button>
          ) : (
            <button className="btn-primary" onClick={abrirTurno} disabled={procesando}>
              {procesando ? "Abriendo..." : "Abrir turno"}
            </button>
          )}
        </div>

        {turno ? (
          <>
            <p className="muted small">
              Abierto por <strong>{turno.usuario_nombre}</strong> el {fmtFecha(turno.fecha_apertura)}
            </p>
            <div className="kpis">
              <div className="kpi-card">
                <h3>Efectivo</h3>
                <h2>${turno.totales.efectivo.toFixed(2)}</h2>
              </div>
              <div className="kpi-card">
                <h3>Tarjeta</h3>
                <h2>${turno.totales.tarjeta.toFixed(2)}</h2>
              </div>
              <div className="kpi-card">
                <h3>Transferencia</h3>
                <h2>${turno.totales.transferencia.toFixed(2)}</h2>
              </div>
              <div className="kpi-card kpi-total">
                <h3>Total del turno</h3>
                <h2>${turno.totales.total.toFixed(2)}</h2>
              </div>
            </div>
            <div className="form-group">
              <label>Observaciones del cierre</label>
              <input
                value={observaciones}
                onChange={(e) => setObservaciones(e.target.value)}
                placeholder="Ej: caja contada, sobrante $2.50"
              />
            </div>
          </>
        ) : (
          <p className="empty-state">
            No hay un turno abierto. Abre un turno para empezar a registrar la caja del día.
          </p>
        )}
      </section>

      {/* Resumen del periodo */}
      {resumen && (
        <section className="panel">
          <h3>Resumen de ventas ({periodo === 1 ? "hoy" : `últimos ${periodo} días`})</h3>
          <div className="kpis">
            <div className="kpi-card">
              <h3>Efectivo</h3>
              <h2>${resumen.totales.efectivo.toFixed(2)}</h2>
            </div>
            <div className="kpi-card">
              <h3>Tarjeta</h3>
              <h2>${resumen.totales.tarjeta.toFixed(2)}</h2>
            </div>
            <div className="kpi-card">
              <h3>Transferencia</h3>
              <h2>${resumen.totales.transferencia.toFixed(2)}</h2>
            </div>
            <div className="kpi-card kpi-total">
              <h3>Total</h3>
              <h2>${resumen.totales.total.toFixed(2)}</h2>
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
                <th>Abierto</th>
                <th>Cerrado</th>
                <th>Usuario</th>
                <th>Efectivo</th>
                <th>Tarjeta</th>
                <th>Transfer.</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody>
              {turnos.map((t) => (
                <tr key={t.id}>
                  <td>{t.id}</td>
                  <td>{fmtFecha(t.fecha_apertura)}</td>
                  <td>{fmtFecha(t.fecha_cierre)}</td>
                  <td>{t.usuario_nombre}</td>
                  <td>${t.totales.efectivo.toFixed(2)}</td>
                  <td>${t.totales.tarjeta.toFixed(2)}</td>
                  <td>${t.totales.transferencia.toFixed(2)}</td>
                  <td>
                    <strong>${t.totales.total.toFixed(2)}</strong>
                  </td>
                </tr>
              ))}
              {turnos.length === 0 && (
                <tr>
                  <td colSpan={8} className="empty-state">
                    Todavía no hay turnos registrados.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
