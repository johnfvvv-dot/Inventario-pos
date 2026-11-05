/**
 * Tickets internos de un turno de caja.
 *
 * Se solicitan al backend al abrir la ventana y viven solo en memoria del
 * navegador: al cerrarla desaparecen. Se pueden imprimir/guardar como PDF o
 * descargar como imagen PNG.
 */

import { useCallback, useEffect, useState } from "react";
import { api } from "../services/api";
import { formatearFechaHora, formatearPrecio } from "../utils/format";
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

export default function TicketsModal({ turnoId, onCerrar }: Props) {
  const [datos, setDatos] = useState<RespuestaTickets | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const respuesta: any = await api.getTicketsTurno(turnoId);
      setDatos(respuesta);
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
      if (evento.key === "Escape") onCerrar();
    };
    window.addEventListener("keydown", alPresionarTecla);
    return () => window.removeEventListener("keydown", alPresionarTecla);
  }, [onCerrar]);

  const imprimir = () => {
    if (datos?.tickets.length) window.print();
  };

  const descargar = (ticket: Ticket) => {
    if (!datos) return;
    try {
      descargarTicketPng(ticket, datos.nombre_negocio);
    } catch (err: any) {
      setError(err?.message || "No se pudo generar la imagen del ticket.");
    }
  };

  const sinTickets = Boolean(datos && datos.tickets.length === 0);

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
            <h3 id="titulo-tickets">Tickets del turno</h3>
            {datos && (
              <p className="muted small">
                Turno #{datos.turno_id} · {datos.tickets.length} ticket
                {datos.tickets.length === 1 ? "" : "s"} ·{" "}
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
              disabled={cargando || !datos?.tickets.length}
              title="Abre el diálogo de impresión; permite guardar como PDF"
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
          Comprobantes internos de control administrativo. No incluyen total ni
          impuestos y no se guardan en el servidor.
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

        {datos && datos.tickets.length > 0 && (
          <div className="tickets-print-area">
            {datos.tickets.map((ticket) => (
              <article className="ticket-card" key={ticket.id}>
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
                    <dd>{ticket.folio}</dd>
                  </div>
                  <div>
                    <dt>Mesa</dt>
                    <dd>{ticket.mesa}</dd>
                  </div>
                  {ticket.alias && (
                    <div>
                      <dt>Cliente</dt>
                      <dd>{ticket.alias}</dd>
                    </div>
                  )}
                  <div>
                    <dt>Ocupación</dt>
                    <dd>{formatearFechaHora(ticket.fecha_ocupacion)}</dd>
                  </div>
                  <div>
                    <dt>Pago</dt>
                    <dd>{formatearFechaHora(ticket.fecha_pago)}</dd>
                  </div>
                </dl>

                <div className="ticket-separador" />

                <div className="ticket-items">
                  <div className="ticket-items-titulo">Productos</div>
                  {ticket.items.map((item, indice) => (
                    <div
                      className="ticket-item"
                      key={`${ticket.id}-${indice}`}
                    >
                      <span className="ticket-item-nombre">{item.nombre}</span>
                      <span className="ticket-item-precio">
                        {item.cantidad} × {formatearPrecio(item.precio_unitario)}
                      </span>
                    </div>
                  ))}
                </div>

                <div className="ticket-separador" />

                <div className="ticket-pago">
                  <span>Forma de pago</span>
                  <strong>{etiquetaPago(ticket.forma_pago)}</strong>
                </div>

                <p className="ticket-pie">
                  Documento interno de control.
                  <br />
                  No válido como factura.
                </p>

                <button
                  type="button"
                  className="btn-secondary btn-small ticket-descarga"
                  onClick={() => descargar(ticket)}
                >
                  Descargar imagen
                </button>
              </article>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
