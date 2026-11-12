/**
 * Ventana reutilizable para crear un alias/cliente dentro de una cuenta
 * abierta de mesa o barra.
 *
 * No crea divisiones por su cuenta: delega en `onCrear`, que reutiliza la
 * lógica interna de "Dividir Cuenta" del backend para sumar el alias a la
 * división pendiente más reciente (o crear una si todavía no existe).
 */

import { FormEvent, useState } from "react";

interface Props {
  titulo?: string;
  descripcion?: string;
  onCrear: (alias: string) => Promise<unknown> | unknown;
  onClose: () => void;
}

export default function CrearAliasModal({
  titulo = "Crear alias / cliente",
  descripcion = "El alias se agrega a la cuenta abierta y podrá recibir pedidos.",
  onCrear,
  onClose,
}: Props) {
  const [alias, setAlias] = useState("");
  const [procesando, setProcesando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const enviar = async (evento?: FormEvent) => {
    evento?.preventDefault();
    if (procesando) return;

    const limpio = alias.trim();
    if (!limpio) {
      setError("Escribe el alias o nombre del cliente.");
      return;
    }

    setProcesando(true);
    setError(null);
    try {
      await onCrear(limpio);
      onClose();
    } catch (err: any) {
      setError(err?.message || "No se pudo crear el alias.");
    } finally {
      setProcesando(false);
    }
  };

  return (
    <div
      className="modal-overlay"
      onClick={procesando ? undefined : onClose}
    >
      <form
        className="modal-box modal-confirm modal-alias"
        onClick={(e) => e.stopPropagation()}
        onSubmit={enviar}
      >
        <div className="modal-head">
          <h3>{titulo}</h3>
          <button
            type="button"
            className="btn-icon"
            onClick={onClose}
            title="Cerrar"
            disabled={procesando}
          >
            ×
          </button>
        </div>

        <p className="muted small">{descripcion}</p>

        <div className="form-group">
          <label>Alias / nombre del cliente *</label>
          <input
            autoFocus
            value={alias}
            onChange={(e) => setAlias(e.target.value)}
            placeholder="Ej: Cliente A"
            maxLength={60}
            disabled={procesando}
          />
        </div>

        {error && <p className="error-msg">{error}</p>}

        <div className="modal-actions">
          <button
            type="button"
            className="btn-secondary"
            onClick={onClose}
            disabled={procesando}
          >
            Cancelar
          </button>
          <button
            type="submit"
            className="btn-primary"
            disabled={procesando}
          >
            {procesando ? "Creando..." : "Crear alias"}
          </button>
        </div>

        <p className="muted small">
          El alias aparece en la cuenta y en el modal de asignación de pedidos.
          No se cobra nada hasta cerrar su división.
        </p>
      </form>
    </div>
  );
}
