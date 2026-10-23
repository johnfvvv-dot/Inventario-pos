/** Ventana de cambio de clave de un usuario. */

import { useState } from "react";

interface Props {
  alias: string;
  onConfirmar: (clave: string) => void;
  onCancelar: () => void;
  procesando?: boolean;
  error?: string | null;
}

export default function CambiarClaveModal({
  alias,
  onConfirmar,
  onCancelar,
  procesando = false,
  error = null,
}: Props) {
  const [clave, setClave] = useState("");
  const [repetir, setRepetir] = useState("");
  const [errorLocal, setErrorLocal] = useState<string | null>(null);

  const confirmar = () => {
    if (clave.length < 4) {
      setErrorLocal("La clave debe tener al menos 4 caracteres");
      return;
    }
    if (clave !== repetir) {
      setErrorLocal("Las claves no coinciden");
      return;
    }
    setErrorLocal(null);
    onConfirmar(clave);
  };

  return (
    <div className="modal-overlay" onClick={onCancelar}>
      <div className="modal-box modal-confirm" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3>Cambiar clave de "{alias}"</h3>
          <button className="btn-icon" onClick={onCancelar} title="Cerrar">
            ×
          </button>
        </div>

        <div className="form-group">
          <label>Nueva clave</label>
          <input
            type="password"
            value={clave}
            onChange={(e) => setClave(e.target.value)}
            placeholder="Mínimo 4 caracteres"
            autoComplete="new-password"
          />
        </div>

        <div className="form-group">
          <label>Repetir nueva clave</label>
          <input
            type="password"
            value={repetir}
            onChange={(e) => setRepetir(e.target.value)}
            placeholder="Repite la clave"
            autoComplete="new-password"
            onKeyDown={(e) => e.key === "Enter" && confirmar()}
          />
        </div>

        {(errorLocal || error) && <p className="error-msg">{errorLocal || error}</p>}

        <div className="modal-actions">
          <button className="btn-secondary" onClick={onCancelar} disabled={procesando}>
            Cancelar
          </button>
          <button className="btn-primary" onClick={confirmar} disabled={procesando}>
            {procesando ? "Guardando..." : "Aceptar"}
          </button>
        </div>
      </div>
    </div>
  );
}
