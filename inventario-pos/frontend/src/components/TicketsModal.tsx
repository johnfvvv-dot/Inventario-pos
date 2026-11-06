/**
 * Tickets internos de un turno de caja.
 *
 * Se solicitan al backend al abrir la ventana y viven solo en memoria del
 * navegador: al cerrarla desaparecen. Se muestran de uno en uno y se pueden
 * imprimir/guardar como PDF o descargar como imagen PNG.
 */

import { useCallback, useEffect, useState } from "react";
import { api } from "../services/api";
import {
  formatearDiaSemana,
  formatearFecha,
  formatearFechaHora,
  formatearPrecio,
} from "../utils/format";
import { descargarTicketPng } from "../utils/ticketImagen";

interface TicketItem {
  nombre: string;
  cantidad: number;
  precio_unitario: number;
  subtotal: number;
}

interface Ticket {
  id: string;
  tipo: string;
  folio: string;
  mesa: string;
  fecha_ocupacion: string;
  fecha_pago: string;
  alias?: string | null;
  forma_pago: string;
  total?: number | null;
  items: TicketItem[];
}

interface RespuestaTickets {
  turno_id: number;
  estado: string;
  fecha_apertura: string;
  fecha_cierre: string | null;
  nombre_negocio: string;
  tickets: Ticket[];
}

interface Props {
  turnoId?: number;
  onCerrar: () => void;
}

const ETIQUETAS_PAGO: Record<string, string> = {
  efectivo: "Efectivo",
  tarjeta: "Tarjeta",
  transferencia: "Transferencia",
};

function etiquetaPago(forma: string): string {
  return ETIQUETAS_PAGO[forma] || forma;
}

/** Usa el total del backend si existe; si no, suma cantidad × precio. */
function calcularTotalTicket(ticket: Ticket): number {
  if (typeof ticket.total === "number" && Number.isFinite(ticket.total)) {
    return ticket.total;
  }

  return ticket.items.reduce(
    (total, item) =>
      total +
      Number(item.cantidad || 0) * Number(item.precio_unitario || 0),
    0
  );
}

export default function TicketsModal({ turnoId, onCerrar }: Props) {
  const [datos, setDatos] = useState<RespuestaTickets | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [indiceActual, setIndiceActual] = useState(0);

  const cargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const respuesta: any = await api.getTicketsTurno(turnoId);
      setDatos(respuesta);
      setIndiceActual(0);
    } catch (err: any) {
      setError(err?.message || "No se pudieron generar los tickets.");
    } finally {
      setCargando(false);
    }
  }, [turnoId]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  useEffect(() => {
    const alPresionarTecla = (evento: KeyboardEvent) => {
      if (evento.key === "Escape") {
        onCerrar();
        return;
      }

      if (evento.key === "ArrowLeft") {
        setIndiceActual((indice) => Math.max(0, indice - 1));
      } else if (evento.key === "ArrowRight") {
        const total = datos?.tickets.length ?? 0;
        if (total > 0) {
          setIndiceActual((indice) => Math.min(total - 1, indice + 1));
        }
      }
    };

    window.addEventListener("keydown", alPresionarTecla);
    return () => window.removeEventListener("keydown", alPresionarTecla);
  }, [datos, onCerrar]);

  const totalTickets = datos?.tickets.length ?? 0;
  const ticketActual = datos?.tickets[indiceActual] ?? null;
  const esPrimero = indiceActual === 0;
  const esUltimo = indiceActual >= totalTickets - 1;
  const sinTickets = Boolean(datos && totalTickets === 0);

  const fechaTurno =
    datos?.fecha_apertura ||
    datos?.tickets[0]?.fecha_pago ||
    datos?.tickets[0]?.fecha_ocupacion;
  const tituloTickets = fechaTurno
    ? `Tickets del turno - ${formatearDiaSemana(fechaTurno)}, ${formatearFecha(
        fechaTurno
      )}`
    : "Tickets del turno";

  const irAnterior = () => {
    setIndiceActual((indice) => Math.max(0, indice - 1));
  };

  const irSiguiente = () => {
    setIndiceActual((indice) => Math.min(totalTickets - 1, indice + 1));
  };

  const imprimir = () => {
    if (ticketActual) window.print();
  };

  const descargar = (ticket: Ticket) => {
    if (!datos) return;
    try {
      descargarTicketPng(ticket, datos.nombre_negocio);
    } catch (err: any) {
      setError(err?.message || "No se pudo generar la imagen del ticket.");
    }
  };

  return (
    <div className="modal-overlay" onClick={onCerrar}>
      <div
        className="modal-box modal-xl tickets-modal"
        onClick={(evento) => evento.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="titulo-tickets"
      >
        <div className="modal-head tickets-modal-head">
          <div>
            <h3 id="titulo-tickets">{tituloTickets}</h3>
            {datos && (
              <p className="muted small">
                Turno #{datos.turno_id} · {totalTickets} ticket
                {totalTickets === 1 ? "" : "s"} ·{" "}
                {datos.estado === "abierto" ? "Turno abierto" : "Turno cerrado"}
              </p>
            )}
          </div>
          <div className="tickets-acciones">
            <button
              className="btn-secondary btn-small"
              onClick={cargar}
              disabled={cargando}
            >
              {cargando ? "Generando..." : "Actualizar"}
            </button>
            <button
              className="btn-secondary btn-small"
              onClick={imprimir}
              disabled={cargando || !ticketActual}
              title="Imprime el ticket seleccionado; permite guardar como PDF"
            >
              Imprimir / PDF
            </button>
            <button
              className="btn-icon"
              onClick={onCerrar}
              title="Cerrar"
              aria-label="Cerrar"
            >
              ×
            </button>
          </div>
        </div>

        <p className="muted small tickets-nota">
          Comprobantes internos de control administrativo.
        </p>

        {error && <p className="error-msg">{error}</p>}

        {cargando && !datos && (
          <p className="empty-state">Generando tickets desde las ventas...</p>
        )}

        {sinTickets && !cargando && (
          <p className="empty-state">
            Este turno todavía no tiene pagos registrados. Los tickets
            aparecerán a medida que se cierren pedidos o se paguen divisiones.
          </p>
        )}

        {datos && ticketActual && (
          <div className="tickets-visualizador">
            <div className="tickets-print-area">
              <article className="ticket-card">
                <header className="ticket-cabecera">
                  <strong className="ticket-negocio">
                    {datos.nombre_negocio}
                  </strong>
                  <span className="ticket-subtitulo">
                    Comprobante interno
                  </span>
                </header>

                <dl className="ticket-meta">
                  <div>
                    <dt>Folio</dt>
                    <dd>{ticketActual.folio}</dd>
                  </div>
                  <div>
                    <dt>Mesa</dt>
                    <dd>{ticketActual.mesa}</dd>
                  </div>
                  {ticketActual.alias && (
                    <div>
                      <dt>Cliente</dt>
                      <dd>{ticketActual.alias}</dd>
                    </div>
                  )}
                  <div>
                    <dt>Ocupación</dt>
                    <dd>{formatearFechaHora(ticketActual.fecha_ocupacion)}</dd>
                  </div>
                  <div>
                    <dt>Pago</dt>
                    <dd>{formatearFechaHora(ticketActual.fecha_pago)}</dd>
                  </div>
                </dl>

                <div className="ticket-separador" />

                <div className="ticket-items">
                  <div className="ticket-items-titulo">Productos</div>
                  {ticketActual.items.map((item, indice) => (
                    <div
                      className="ticket-item"
                      key={`${ticketActual.id}-${indice}`}
                    >
                      <span className="ticket-item-nombre">{item.nombre}</span>
                      <span className="ticket-item-precio">
                        {item.cantidad} × {formatearPrecio(item.precio_unitario)}
                      </span>
                    </div>
                  ))}
                </div>

                <div className="ticket-separador" />

                <div className="ticket-total">
                  <span>Total</span>
                  <strong>
                    {formatearPrecio(calcularTotalTicket(ticketActual))}
                  </strong>
                </div>

                <div className="ticket-separador" />

                <div className="ticket-pago">
                  <span>Forma de pago</span>
                  <strong>{etiquetaPago(ticketActual.forma_pago)}</strong>
                </div>

                <p className="ticket-pie">
                  Documento interno de control.
                  <br />
                  No válido como factura.
                </p>

                <button
                  type="button"
                  className="btn-secondary btn-small ticket-descarga"
                  onClick={() => descargar(ticketActual)}
                  aria-label={`Descargar imagen del ticket ${ticketActual.folio}`}
                >
                  Descargar imagen
                </button>
              </article>
            </div>

            <nav
              className="tickets-navegacion"
              aria-label="Navegación entre tickets"
            >
              <button
                type="button"
                className="btn-secondary btn-small ticket-nav-btn"
                onClick={irAnterior}
                disabled={esPrimero}
                aria-label="Ticket anterior"
              >
                <span className="ticket-nav-flecha" aria-hidden="true">
                  ‹
                </span>
                <span className="ticket-nav-texto">Anterior</span>
              </button>

              <span className="ticket-contador" aria-live="polite">
                Ticket {indiceActual + 1} de {totalTickets}
              </span>

              <button
                type="button"
                className="btn-secondary btn-small ticket-nav-btn"
                onClick={irSiguiente}
                disabled={esUltimo}
                aria-label="Ticket siguiente"
              >
                <span className="ticket-nav-texto">Siguiente</span>
                <span className="ticket-nav-flecha" aria-hidden="true">
                  ›
                </span>
              </button>
            </nav>
          </div>
        )}
      </div>
    </div>
  );
}
