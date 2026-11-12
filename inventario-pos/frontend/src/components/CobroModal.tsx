/**
 * Ventana de cobro: muestra el total y permite elegir la forma de pago
 * (efectivo / tarjeta / transferencia) antes de confirmar.
 */

import { useState } from "react";
import { FORMAS_PAGO } from "../services/api";
import { formatearPrecio } from "../utils/format";

interface Props {
  titulo: string;
  total: number;
  confirmar: (formaPago: string) => void;
  /** Si se indica, muestra el botón "Aceptar y liberar mesa". */
  confirmarLiberar?: (formaPago: string) => void;
  onClose: () => void;
  procesando?: boolean;
  error?: string | null;
  extra?: string;
  textoConfirmar?: string;
  textoLiberar?: string;
}

export default function CobroModal({
  titulo,
  total,
  confirmar,
  confirmarLiberar,
  onClose,
  procesando = false,
  error = null,
  extra,
  textoConfirmar = "Aceptar",
  textoLiberar = "Aceptar y liberar mesa",
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
          <strong>{formatearPrecio(total)}</strong>
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
                disabled={procesando}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {error && <p className="error-msg">{error}</p>}

        <div className="modal-actions modal-actions-wrap">
          <button className="btn-secondary" onClick={onClose} disabled={procesando}>
            Cancelar
          </button>
          <button
            className="btn-primary"
            onClick={() => confirmar(formaPago)}
            disabled={procesando}
          >
            {procesando ? "Procesando..." : textoConfirmar}
          </button>
          {confirmarLiberar && (
            <button
              className="btn-warning"
              onClick={() => confirmarLiberar(formaPago)}
              disabled={procesando}
            >
              {procesando ? "Procesando..." : textoLiberar}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
