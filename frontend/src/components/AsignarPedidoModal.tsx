/**
 * Ventana para decidir a quién pertenece un pedido nuevo.
 *
 * Solo aparece cuando la mesa o la barra tiene alias activos. Un pedido
 * completo tiene un único destino: un alias o la cuenta general.
 */

import { useEffect, useState } from "react";
import { formatearPrecio } from "../utils/format";

export interface DestinoPedido {
  participanteId: number | null;
  alias: string;
  divisionId?: number;
  subtotal: number;
  pagado: boolean;
  itemsCount: number;
  esGeneral?: boolean;
}

interface Props {
  etiquetaCuenta: string;
  totalPedido: number;
  cantidadItems: number;
  destinos: DestinoPedido[];
  procesando: boolean;
  error?: string | null;
  onConfirmar: (participanteId: number | null) => void;
  onClose: () => void;
}

export default function AsignarPedidoModal({
  etiquetaCuenta,
  totalPedido,
  cantidadItems,
  destinos,
  procesando,
  error,
  onConfirmar,
  onClose,
}: Props) {
  const [seleccion, setSeleccion] = useState<number | "general" | null>(null);

  // Al refrescar los destinos (por ejemplo tras un conflicto), se conserva
  // la selección solo si el alias sigue activo.
  useEffect(() => {
    if (seleccion === null || seleccion === "general") return;
    const sigueActivo = destinos.some(
      (d) => d.participanteId === seleccion && !d.pagado
    );
    if (!sigueActivo) setSeleccion(null);
  }, [destinos, seleccion]);

  const activos = destinos.filter((d) => !d.esGeneral && !d.pagado);
  const cerrados = destinos.filter((d) => !d.esGeneral && d.pagado);
  const general = destinos.find((d) => d.esGeneral);

  const confirmar = () => {
    if (seleccion === null) return;
    onConfirmar(seleccion === "general" ? null : seleccion);
  };

  const opcion = (destino: DestinoPedido, key: string) => {
    const valor =
      destino.esGeneral || destino.participanteId === null
        ? "general"
        : destino.participanteId;
    const activa = seleccion === valor;
    return (
      <label
        key={key}
        className={`asignacion-opcion ${activa ? "activa" : ""} ${
          destino.pagado ? "pagada" : ""
        }`}
      >
        <input
          type="radio"
          name="destino-pedido"
          checked={activa}
          disabled={destino.pagado || procesando}
          onChange={() => setSeleccion(valor)}
        />
        <span className="asignacion-info">
          <strong>
            {destino.alias}
            {destino.pagado && (
              <span className="badge badge-success asignacion-badge">Pagado</span>
            )}
            {destino.esGeneral && (
              <span className="badge badge-warning asignacion-badge">
                Cuenta general
              </span>
            )}
          </strong>
          <span className="muted small">
            {destino.esGeneral
              ? `${destino.itemsCount} pedido(s) general(es)`
              : `${destino.itemsCount} producto(s)`}
          </span>
        </span>
        <span className="asignacion-subtotal">
          {formatearPrecio(destino.subtotal)}
          <span className="muted small">
            {destino.pagado ? "ya pagado" : "pendiente"}
          </span>
        </span>
      </label>
    );
  };

  return (
    <div className="modal-overlay" onClick={procesando ? undefined : onClose}>
      <div
        className="modal-box modal-asignar"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-head">
          <div>
            <h3>¿A quién deseas asignar este pedido?</h3>
            <p className="muted small asignacion-contexto">
              {etiquetaCuenta} · {cantidadItems} producto(s) ·{" "}
              <strong>{formatearPrecio(totalPedido)}</strong>
            </p>
          </div>
          <button
            className="btn-icon"
            onClick={onClose}
            title="Volver al pedido"
            disabled={procesando}
          >
            ×
          </button>
        </div>

        {error && <p className="error-msg">{error}</p>}

        <div className="asignacion-lista">
          {activos.length === 0 && (
            <p className="muted small">
              No hay clientes activos. El pedido se agregará a la cuenta general.
            </p>
          )}
          {activos.map((d) => opcion(d, `activo-${d.participanteId}`))}
          {cerrados.map((d) => opcion(d, `pagado-${d.participanteId}`))}
          {general && opcion(general, "general")}
        </div>

        <div className="modal-actions">
          <button
            className="btn-secondary"
            onClick={onClose}
            disabled={procesando}
          >
            Volver al pedido
          </button>
          <button
            className="btn-primary"
            onClick={confirmar}
            disabled={procesando || seleccion === null}
          >
            {procesando ? "Agregando pedido..." : "Asignar pedido"}
          </button>
        </div>

        <p className="muted small asignacion-nota">
          Los alias marcados como <strong>Pagado</strong> no admiten pedidos
          nuevos. Si el cliente desea consumir más, usa la cuenta general o crea
          un alias nuevo desde "Pedido actual".
        </p>
      </div>
    </div>
  );
}
