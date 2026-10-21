/**
 * Ventana de cobro: muestra el total y permite elegir la forma de pago
 * (efectivo / tarjeta / transferencia) antes de confirmar.
 */

import { useState } from "react";
import { FORMAS_PAGO } from "../services/api";

interface Props {
  titulo: string;
  total: number;
  confirmar: (formaPago: string) => void;
  onClose: () => void;
  procesando?: boolean;
  error?: string | null;
  extra?: string;
}

export default function CobroModal({
  titulo,
  total,
  confirmar,
  onClose,
  procesando = false,
  error = null,
  extra,
}: Props) {
  const [formaPago, setFormaPago] = useState("efectivo");

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box modal-cobro" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3>{titulo}</h3>
          <button className="btn-icon" onClick={onClose} title="Cerrar">
            ×
          </button>
        </div>

        <div className="cobro-total">
          <span>Total a cobrar</span>
          <strong>${total.toFixed(2)}</strong>
        </div>

        {extra && <p className="muted small">{extra}</p>}

        <div className="form-group">
          <label>Forma de pago</label>
          <div className="formas-pago">
            {FORMAS_PAGO.map((f) => (
              <button
                key={f.id}
                type="button"
                className={`forma-pago ${formaPago === f.id ? "activa" : ""}`}
                onClick={() => setFormaPago(f.id)}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {error && <p className="error-msg">{error}</p>}

        <div className="modal-actions">
          <button className="btn-secondary" onClick={onClose} disabled={procesando}>
            Cancelar
          </button>
          <button
            className="btn-primary"
            onClick={() => confirmar(formaPago)}
            disabled={procesando}
          >
            {procesando ? "Cobrando..." : `Confirmar cobro (${formaPago})`}
          </button>
        </div>
      </div>
    </div>
  );
}
