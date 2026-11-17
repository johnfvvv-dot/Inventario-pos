/**
 * Modal para liquidar una partida de Bolirana.
 *
 * Muestra el consumo de la ronda y reparte el total en partes iguales entre
 * los perdedores seleccionados. Las mesas/barras reciben el cargo en su
 * cuenta; los jugadores libres quedan como cargos pendientes de cobro.
 */

import { FormEvent, useMemo, useState } from "react";
import { api } from "../services/api";
import { formatearPrecio } from "../utils/format";
import Icon from "./Icon";
import type { Bolirana, PartidaBolirana } from "../types/bolirana";

interface Props {
  bolirana: Bolirana;
  partida: PartidaBolirana;
  onClose: () => void;
  onLiquidado: (opciones: {
    cobrarAliasAhora: boolean;
    partidaId: number;
  }) => void;
}

export default function LiquidarPartidaBoliranaModal({
  bolirana,
  partida,
  onClose,
  onLiquidado,
}: Props) {
  const usuario = JSON.parse(localStorage.getItem("user") || "{}");
  const usuarioId = Number(usuario?.id) || 1;
  const [perdedores, setPerdedores] = useState<number[]>([]);
  const [cobrarAliasAhora, setCobrarAliasAhora] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [procesando, setProcesando] = useState(false);

  const total = Number(partida.total_bebidas) || 0;
  const cantidad = perdedores.length;

  const montos = useMemo(() => {
    if (!cantidad) return {} as Record<number, number>;
    const base = Math.round((total / cantidad) * 100) / 100;
    const resultado: Record<number, number> = {};
    perdedores.forEach((id, indice) => {
      resultado[id] =
        indice === cantidad - 1
          ? Math.round((total - base * (cantidad - 1)) * 100) / 100
          : base;
    });
    return resultado;
  }, [perdedores, cantidad, total]);

  const montoBase = cantidad ? Math.round((total / cantidad) * 100) / 100 : 0;
  const hayAliasPerdedor = perdedores.some((id) => {
    const participante = partida.participantes.find((p) => p.id === id);
    return participante?.tipo === "alias";
  });

  const alternarPerdedor = (id: number) => {
    setPerdedores((actual) =>
      actual.includes(id) ? actual.filter((p) => p !== id) : [...actual, id]
    );
  };

  const enviar = async (evento?: FormEvent) => {
    evento?.preventDefault();
    if (procesando) return;

    if (perdedores.length === 0) {
      setError("Marca al menos un perdedor para repartir el consumo.");
      return;
    }

    setProcesando(true);
    setError(null);
    try {
      await api.finalizarPartidaBolirana(bolirana.id, {
        usuario_id: usuarioId,
        perdedores,
      });
      onLiquidado({
        cobrarAliasAhora: cobrarAliasAhora && hayAliasPerdedor,
        partidaId: partida.id,
      });
      onClose();
    } catch (err: any) {
      setError(err?.message || "No se pudo liquidar la partida.");
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
            <Icon nombre="recibo" size={17} />
            Liquidar Partida — {bolirana.nombre}
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

        <div className="bolirana-liquidacion-grid">
          <section>
            <h4>Consumo de la ronda</h4>
            {partida.consumo.length === 0 ? (
              <p className="muted small">La ronda no tiene bebidas cargadas.</p>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Producto</th>
                      <th>Cant.</th>
                      <th>Subtotal</th>
                    </tr>
                  </thead>
                  <tbody>
                    {partida.consumo.map((item) => (
                      <tr
                        key={`${item.producto_id}-${item.precio_unitario}`}
                      >
                        <td>{item.producto_nombre}</td>
                        <td>{item.cantidad}</td>
                        <td>{formatearPrecio(item.subtotal)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <div className="total-row pos-total">
              <span>Total de la ronda</span>
              <strong>{formatearPrecio(total)}</strong>
            </div>
          </section>

          <section>
            <h4>¿Quién perdió la partida?</h4>
            <p className="muted small">
              Marca uno o varios perdedores. El total se divide en partes
              iguales.
            </p>
            <div className="bolirana-opciones">
              {partida.participantes.map((participante) => (
                <label
                  key={participante.id}
                  className="bolirana-opcion bolirana-opcion--perdedor"
                >
                  <input
                    type="checkbox"
                    checked={perdedores.includes(participante.id)}
                    onChange={() => alternarPerdedor(participante.id)}
                    disabled={procesando}
                  />
                  <span>{participante.etiqueta}</span>
                  {perdedores.includes(participante.id) && (
                    <strong>
                      {formatearPrecio(montos[participante.id] || 0)}
                    </strong>
                  )}
                </label>
              ))}
            </div>

            {cantidad > 0 && (
              <div className="bolirana-division-info">
                <span>
                  {formatearPrecio(total)} ÷ {cantidad} perdedor
                  {cantidad > 1 ? "es" : ""}
                </span>
                <strong>{formatearPrecio(montoBase)} c/u</strong>
              </div>
            )}

            {hayAliasPerdedor && (
              <label className="bolirana-check-cobro">
                <input
                  type="checkbox"
                  checked={cobrarAliasAhora}
                  onChange={(e) => setCobrarAliasAhora(e.target.checked)}
                  disabled={procesando}
                />
                <span>
                  Cobrar ahora el cargo pendiente del jugador libre al confirmar
                </span>
              </label>
            )}

            <p className="muted small">
              Las mesas y barras perdedoras reciben el cargo en su cuenta
              general. Los jugadores libres quedan como cargos pendientes de
              cobro.
            </p>
          </section>
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
            {procesando ? "Liquidando..." : "Confirmar liquidación"}
          </button>
        </div>
      </form>
    </div>
  );
}
