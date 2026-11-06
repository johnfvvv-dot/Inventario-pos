/**
 * Modal de apertura de turno.
 *
 * Se muestra automáticamente cuando no existe un turno abierto. Exige el
 * Fondo Inicial de Caja (base en efectivo para cambio/vueltos) antes de
 * enviar la apertura al backend.
 */

import { FormEvent, useState } from "react";
import type { TurnoCaja } from "../types/turno";
import {
  formatearMontoEditable,
  parsearMontoEditable,
} from "../utils/format";

interface Props {
  abrirTurno: (fondoInicial: number) => Promise<TurnoCaja>;
  onAbierto: (turno: TurnoCaja) => void;
  onCancelar: () => void;
}

export default function AvisoTurnoModal({
  abrirTurno,
  onAbierto,
  onCancelar,
}: Props) {
  const [fondo, setFondo] = useState("");
  const [procesando, setProcesando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const cambiarFondo = (valor: string) => {
    // Se conservan solo dígitos: el "$" y los puntos son únicamente visuales.
    // El límite evita perder precisión con montos fuera del rango seguro.
    setFondo(valor.replace(/\D/g, "").slice(0, 12));
    setError(null);
  };

  const confirmar = async (evento: FormEvent) => {
    evento.preventDefault();
    setError(null);

    if (fondo.trim() === "") {
      setError("Ingresa el Fondo Inicial de Caja.");
      return;
    }

    const monto = parsearMontoEditable(fondo);
    if (!Number.isFinite(monto) || monto < 0) {
      setError(
        "El Fondo Inicial de Caja debe ser un número mayor o igual a cero."
      );
      return;
    }

    setProcesando(true);
    try {
      const turno = await abrirTurno(monto);
      onAbierto(turno);
    } catch (err: any) {
      setError(err?.message || "No se pudo abrir el turno.");
    } finally {
      setProcesando(false);
    }
  };

  return (
    <div
      className="modal-overlay"
      onClick={() => {
        if (!procesando) onCancelar();
      }}
    >
      <form
        className="modal-box modal-apertura-turno"
        onClick={(evento) => evento.stopPropagation()}
        onSubmit={confirmar}
        noValidate
        role="dialog"
        aria-modal="true"
        aria-labelledby="titulo-apertura-turno"
      >
        <div className="modal-head">
          <h3 id="titulo-apertura-turno">Apertura de turno</h3>
          <button
            type="button"
            className="btn-icon"
            onClick={onCancelar}
            title="Cerrar"
            disabled={procesando}
          >
            ×
          </button>
        </div>

        <p className="confirm-mensaje">
          No hay un turno de caja abierto. Registra la base en efectivo para
          empezar a atender mesas y tomar pedidos.
        </p>

        <div className="form-group">
          <label htmlFor="fondo-inicial">Fondo Inicial de Caja</label>
          <input
            id="fondo-inicial"
            type="text"
            inputMode="numeric"
            autoComplete="off"
            value={formatearMontoEditable(fondo)}
            onChange={(evento) => cambiarFondo(evento.target.value)}
            placeholder="Ej: $100.000"
            aria-describedby="ayuda-fondo-inicial"
            autoFocus
            required
            disabled={procesando}
          />
          <small id="ayuda-fondo-inicial" className="campo-ayuda">
            Base en efectivo para cambio/vueltos.
          </small>
        </div>

        {error && <p className="error-msg">{error}</p>}

        <div className="modal-actions">
          <button
            type="button"
            className="btn-secondary"
            onClick={onCancelar}
            disabled={procesando}
          >
            Ahora no
          </button>
          <button type="submit" className="btn-primary" disabled={procesando}>
            {procesando ? "Abriendo..." : "Abrir turno"}
          </button>
        </div>
      </form>
    </div>
  );
}
