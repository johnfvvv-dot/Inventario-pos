/**
 * Ventana de confirmación reutilizable.
 * Muestra un mensaje y ofrece "Aceptar" / "Cancelar".
 */

interface Props {
  titulo?: string;
  mensaje: string;
  aceptar?: string;
  cancelar?: string;
  onConfirmar: () => void;
  onCancelar: () => void;
  procesando?: boolean;
  error?: string | null;
  accionesExtra?: React.ReactNode;
}

export default function ConfirmModal({
  titulo = "Confirmar",
  mensaje,
  aceptar = "Aceptar",
  cancelar = "Cancelar",
  onConfirmar,
  onCancelar,
  procesando = false,
  error = null,
  accionesExtra = null,
}: Props) {
  return (
    <div className="modal-overlay" onClick={onCancelar}>
      <div className="modal-box modal-confirm" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3>{titulo}</h3>
          <button className="btn-icon" onClick={onCancelar} title="Cerrar">
            ×
          </button>
        </div>

        <p className="confirm-mensaje">{mensaje}</p>

        {error && <p className="error-msg">{error}</p>}

        <div className="modal-actions">
          {accionesExtra}
          <button className="btn-secondary" onClick={onCancelar} disabled={procesando}>
            {cancelar}
          </button>
          <button className="btn-primary" onClick={onConfirmar} disabled={procesando}>
            {procesando ? "Procesando..." : aceptar}
          </button>
        </div>
      </div>
    </div>
  );
}
