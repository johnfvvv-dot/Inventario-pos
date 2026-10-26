/**
 * Modal de cierre de turno de caja.
 * Muestra el monto final, permite registrar observaciones y confirmar el cierre.
 */

import { useEffect, useState } from "react";
import { formatearPrecio } from "../utils/format";

interface Props {
  total: number;
  onCancelar: () => void;
  onConfirmar: (observaciones: string) => void;
  procesando?: boolean;
  error?: string | null;
}

export default function CierreTurnoModal({
  total,
  onCancelar,
  onConfirmar,
  procesando = false,
  error = null,
}: Props) {
  const [observaciones, setObservaciones] = useState("");

  useEffect(() => {
    const alPresionarTecla = (evento: KeyboardEvent) => {
      if (evento.key === "Escape" && !procesando) {
        onCancelar();
      }
    };
    window.addEventListener("keydown", alPresionarTecla);
    return () => window.removeEventListener("keydown", alPresionarTecla);
  }, [onCancelar, procesando]);

  return (
    <div
      className="modal-overlay"
      onClick={() => {
        if (!procesando) onCancelar();
      }}
    >
      <div
        className="modal-box modal-cierre-turno"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="titulo-cierre-turno"
      >
        <div className="modal-head">
          <h3 id="titulo-cierre-turno">Cerrar turno de caja</h3>
          <button
            className="btn-icon"
            onClick={onCancelar}
            title="Cerrar"
            disabled={procesando}
          >
            ×
          </button>
        </div>

        <p className="confirm-mensaje">
          ¿Cerrar el turno de caja? El resumen quedará guardado.
        </p>

        <div className="cierre-monto">
          <span>Monto final del turno</span>
          <strong>{formatearPrecio(total)}</strong>
        </div>

        <div className="form-group">
          <label htmlFor="observaciones-cierre">Observaciones del cierre</label>
          <textarea
            id="observaciones-cierre"
            value={observaciones}
            onChange={(e) => setObservaciones(e.target.value)}
            rows={4}
            maxLength={255}
            placeholder="Sobrantes, faltantes, deudores..."
            autoFocus
            disabled={procesando}
          />
          <small className="muted">
            Opcional. Se guardará en el historial del turno.
          </small>
        </div>

        {error && <p className="error-msg">{error}</p>}

        <div className="modal-actions">
          <button
            className="btn-secondary"
            onClick={onCancelar}
            disabled={procesando}
          >
            Cancelar
          </button>
          <button
            className="btn-primary"
            onClick={() => onConfirmar(observaciones.trim())}
            disabled={procesando}
          >
            {procesando ? "Cerrando..." : "Confirmar cierre"}
          </button>
        </div>
      </div>
    </div>
  );
}
