/**
 * Modal para iniciar una partida de Bolirana.
 *
 * Permite elegir dos o más participantes entre mesas ocupadas, barras con
 * plazas ocupadas y jugadores libres escritos a mano.
 */

import { FormEvent, useMemo, useState } from "react";
import { api } from "../services/api";
import Icon from "./Icon";
import type { Bolirana } from "../types/bolirana";

interface MesaDisponible {
  id: number;
  numero: number;
  tipo: string;
  estado: string;
  grupo?: string | null;
  en_bolirana?: boolean;
  posiciones?: { id: number; estado: string }[];
}

interface Props {
  bolirana: Bolirana;
  mesas: MesaDisponible[];
  onClose: () => void;
  onIniciado: () => void;
}

export default function IniciarPartidaBoliranaModal({
  bolirana,
  mesas,
  onClose,
  onIniciado,
}: Props) {
  const usuario = JSON.parse(localStorage.getItem("user") || "{}");
  const usuarioId = Number(usuario?.id) || 1;
  const [mesasSeleccionadas, setMesasSeleccionadas] = useState<number[]>([]);
  const [barrasSeleccionadas, setBarrasSeleccionadas] = useState<number[]>([]);
  const [alias, setAlias] = useState<string[]>([]);
  const [nuevoAlias, setNuevoAlias] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [procesando, setProcesando] = useState(false);

  const mesasLibres = useMemo(
    () =>
      mesas.filter(
        (m) => m.tipo !== "barra" && m.estado === "ocupada" && !m.en_bolirana
      ),
    [mesas]
  );

  const barrasLibres = useMemo(
    () =>
      mesas.filter(
        (m) =>
          m.tipo === "barra" &&
          !m.en_bolirana &&
          (m.estado === "ocupada" ||
            (m.posiciones || []).some((p) => p.estado === "ocupada"))
      ),
    [mesas]
  );

  const totalParticipantes =
    mesasSeleccionadas.length + barrasSeleccionadas.length + alias.length;

  const alternarMesa = (id: number) => {
    setMesasSeleccionadas((actual) =>
      actual.includes(id) ? actual.filter((m) => m !== id) : [...actual, id]
    );
  };

  const alternarBarra = (numero: number) => {
    setBarrasSeleccionadas((actual) =>
      actual.includes(numero)
        ? actual.filter((b) => b !== numero)
        : [...actual, numero]
    );
  };

  const agregarAlias = () => {
    const limpio = nuevoAlias.trim();
    if (!limpio) return;
    if (alias.some((a) => a.toLowerCase() === limpio.toLowerCase())) {
      setError(`El jugador ${limpio} ya está en la lista.`);
      return;
    }
    setAlias((actual) => [...actual, limpio]);
    setNuevoAlias("");
    setError(null);
  };

  const enviar = async (evento?: FormEvent) => {
    evento?.preventDefault();
    if (procesando) return;

    if (totalParticipantes < 2) {
      setError("Selecciona al menos dos participantes para iniciar la partida.");
      return;
    }

    setProcesando(true);
    setError(null);
    try {
      await api.iniciarPartidaBolirana(bolirana.id, {
        usuario_id: usuarioId,
        participantes: [
          ...mesasSeleccionadas.map((id) => ({
            tipo: "mesa",
            mesa_id: id,
          })),
          ...barrasSeleccionadas.map((numero) => ({
            tipo: "barra",
            barra_numero: numero,
          })),
          ...alias.map((nombre) => ({ tipo: "alias", alias: nombre })),
        ],
      });
      onIniciado();
      onClose();
    } catch (err: any) {
      setError(err?.message || "No se pudo iniciar la partida.");
    } finally {
      setProcesando(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={procesando ? undefined : onClose}>
      <form
        className="modal-box modal-bolirana modal-xl"
        onClick={(e) => e.stopPropagation()}
        onSubmit={enviar}
      >
        <div className="modal-head">
          <h3>
            <Icon nombre="bolirana" size={17} />
            Iniciar partida — {bolirana.nombre}
          </h3>
          <button
            type="button"
            className="btn-icon"
            onClick={onClose}
            title="Cerrar"
            disabled={procesando}
          >
            <Icon nombre="cerrar" size={15} />
          </button>
        </div>

        <p className="muted small modal-nota">
          <Icon nombre="info" size={14} />
          Elige mesas, barras ocupadas o jugadores libres. Necesitas al menos
          dos participantes.
        </p>

        <div className="bolirana-modal-grid">
          <section>
            <h4>Mesas ocupadas</h4>
            {mesasLibres.length === 0 ? (
              <p className="muted small">No hay mesas ocupadas disponibles.</p>
            ) : (
              <div className="bolirana-opciones">
                {mesasLibres.map((mesa) => (
                  <label key={mesa.id} className="bolirana-opcion">
                    <input
                      type="checkbox"
                      checked={mesasSeleccionadas.includes(mesa.id)}
                      onChange={() => alternarMesa(mesa.id)}
                      disabled={procesando}
                    />
                    <span>Mesa {mesa.numero}</span>
                  </label>
                ))}
              </div>
            )}
          </section>

          <section>
            <h4>Barras ocupadas</h4>
            {barrasLibres.length === 0 ? (
              <p className="muted small">No hay barras ocupadas disponibles.</p>
            ) : (
              <div className="bolirana-opciones">
                {barrasLibres.map((barra) => (
                  <label key={`barra-${barra.numero}`} className="bolirana-opcion">
                    <input
                      type="checkbox"
                      checked={barrasSeleccionadas.includes(barra.numero)}
                      onChange={() => alternarBarra(barra.numero)}
                      disabled={procesando}
                    />
                    <span>Barra {barra.numero}</span>
                  </label>
                ))}
              </div>
            )}
          </section>
        </div>

        <section className="bolirana-alias-seccion">
          <h4>Jugadores libres / alias</h4>
          <div className="bolirana-alias-fila">
            <input
              value={nuevoAlias}
              onChange={(e) => setNuevoAlias(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  agregarAlias();
                }
              }}
              placeholder="Ej.: Carlos, Equipo A"
              maxLength={60}
              disabled={procesando}
            />
            <button
              type="button"
              className="btn-secondary"
              onClick={agregarAlias}
              disabled={procesando || !nuevoAlias.trim()}
            >
              <Icon nombre="mas" size={14} />
              Agregar
            </button>
          </div>
          {alias.length > 0 && (
            <div className="bolirana-alias-chips">
              {alias.map((nombre) => (
                <span key={nombre} className="bolirana-chip">
                  {nombre}
                  <button
                    type="button"
                    className="btn-icon"
                    title={`Quitar ${nombre}`}
                    onClick={() =>
                      setAlias((actual) => actual.filter((a) => a !== nombre))
                    }
                    disabled={procesando}
                  >
                    <Icon nombre="cerrar" size={12} />
                  </button>
                </span>
              ))}
            </div>
          )}
        </section>

        <div className="bolirana-resumen-seleccion">
          Participantes seleccionados: <strong>{totalParticipantes}</strong>
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
          <button type="submit" className="btn-primary" disabled={procesando}>
            <Icon nombre="check" size={15} />
            {procesando ? "Iniciando..." : "Iniciar partida"}
          </button>
        </div>
      </form>
    </div>
  );
}
