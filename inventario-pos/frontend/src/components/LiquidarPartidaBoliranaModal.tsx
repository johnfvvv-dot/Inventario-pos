/**
 * Modal para liquidar una partida de Bolirana.
 *
 * En modalidad directa reparte el total entre los participantes perdedores.
 * En modalidad por equipos reparte primero entre los equipos perdedores y
 * luego entre los integrantes de cada equipo. Las mesas, barras, clientes
 * individuales y alias vinculados reciben el cargo en su cuenta; los alias
 * libres quedan como cargos pendientes de cobro.
 */

import { FormEvent, useMemo, useState } from "react";
import { api } from "../services/api";
import { formatearPrecio } from "../utils/format";
import Icon from "./Icon";
import type {
  Bolirana,
  ParticipanteBolirana,
  PartidaBolirana,
} from "../types/bolirana";

interface Props {
  bolirana: Bolirana;
  partida: PartidaBolirana;
  onClose: () => void;
  onLiquidado: (opciones: {
    cobrarAliasAhora: boolean;
    partidaId: number;
  }) => void;
}

interface EquipoPartida {
  nombre: string;
  integrantes: ParticipanteBolirana[];
}

const repartir = (monto: number, cantidad: number): number[] => {
  if (cantidad <= 0) return [];
  const base = Math.round((monto / cantidad) * 100) / 100;
  const montos = Array(cantidad).fill(base);
  montos[cantidad - 1] = Math.round(
    (monto - base * (cantidad - 1)) * 100
  ) / 100;
  return montos;
};

export default function LiquidarPartidaBoliranaModal({
  bolirana,
  partida,
  onClose,
  onLiquidado,
}: Props) {
  const usuario = JSON.parse(localStorage.getItem("user") || "{}");
  const usuarioId = Number(usuario?.id) || 1;
  const [perdedores, setPerdedores] = useState<number[]>([]);
  const [equiposPerdedores, setEquiposPerdedores] = useState<string[]>([]);
  const [cobrarAliasAhora, setCobrarAliasAhora] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [procesando, setProcesando] = useState(false);

  const esEquipos = partida.modalidad === "equipos";
  const total = Number(partida.total_bebidas) || 0;
  const cantidad = perdedores.length;

  const equipos = useMemo<EquipoPartida[]>(() => {
    const mapa = new Map<string, ParticipanteBolirana[]>();
    partida.participantes.forEach((participante) => {
      const nombre = (participante.equipo || "").trim();
      if (!nombre) return;
      const integrantes = mapa.get(nombre) || [];
      integrantes.push(participante);
      mapa.set(nombre, integrantes);
    });
    return Array.from(mapa.entries()).map(([nombre, integrantes]) => ({
      nombre,
      integrantes,
    }));
  }, [partida.participantes]);

  const montosEquipo = useMemo(() => {
    const resultado: Record<string, number> = {};
    if (!esEquipos) return resultado;
    const seleccionados = equipos.filter((equipo) =>
      equiposPerdedores.includes(equipo.nombre)
    );
    const partes = repartir(total, seleccionados.length);
    seleccionados.forEach((equipo, indice) => {
      resultado[equipo.nombre] = partes[indice];
    });
    return resultado;
  }, [esEquipos, equipos, equiposPerdedores, total]);

  const montos = useMemo(() => {
    const resultado: Record<number, number> = {};
    if (esEquipos) {
      equipos.forEach((equipo) => {
        if (!equiposPerdedores.includes(equipo.nombre)) return;
        const partes = repartir(
          montosEquipo[equipo.nombre] || 0,
          equipo.integrantes.length
        );
        equipo.integrantes.forEach((participante, indice) => {
          resultado[participante.id] = partes[indice] || 0;
        });
      });
    } else {
      const partes = repartir(total, perdedores.length);
      perdedores.forEach((id, indice) => {
        resultado[id] = partes[indice] || 0;
      });
    }
    return resultado;
  }, [
    esEquipos,
    equipos,
    equiposPerdedores,
    montosEquipo,
    perdedores,
    total,
  ]);

  const montoBase = cantidad
    ? Math.round((total / cantidad) * 100) / 100
    : 0;

  const hayAliasPerdedor = useMemo(() => {
    if (esEquipos) {
      return equipos
        .filter((equipo) => equiposPerdedores.includes(equipo.nombre))
        .some((equipo) =>
          equipo.integrantes.some(
            (participante) =>
              participante.tipo === "alias" && !participante.origen_tipo
          )
        );
    }
    return partida.participantes.some(
      (participante) =>
        perdedores.includes(participante.id) &&
        participante.tipo === "alias" &&
        !participante.origen_tipo
    );
  }, [esEquipos, equipos, equiposPerdedores, partida.participantes, perdedores]);

  const alternarPerdedor = (id: number) => {
    setPerdedores((actual) =>
      actual.includes(id) ? actual.filter((p) => p !== id) : [...actual, id]
    );
    setError(null);
  };

  const alternarEquipo = (nombre: string) => {
    setEquiposPerdedores((actual) =>
      actual.includes(nombre)
        ? actual.filter((equipo) => equipo !== nombre)
        : [...actual, nombre]
    );
    setError(null);
  };

  const enviar = async (evento?: FormEvent) => {
    evento?.preventDefault();
    if (procesando) return;

    if (esEquipos) {
      if (equiposPerdedores.length === 0) {
        setError("Marca al menos un equipo perdedor para repartir el consumo.");
        return;
      }
    } else if (perdedores.length === 0) {
      setError("Marca al menos un perdedor para repartir el consumo.");
      return;
    }

    setProcesando(true);
    setError(null);
    try {
      await api.finalizarPartidaBolirana(bolirana.id, {
        usuario_id: usuarioId,
        ...(esEquipos
          ? { equipos_perdedores: equiposPerdedores }
          : { perdedores }),
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
                      <tr key={`${item.producto_id}-${item.precio_unitario}`}>
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
            <p className="muted small">
              Modalidad:{" "}
              <strong>{esEquipos ? "Por equipos" : "Directo"}</strong>
            </p>
          </section>

          <section>
            <h4>
              {esEquipos
                ? "¿Qué equipos perdieron la partida?"
                : "¿Quién perdió la partida?"}
            </h4>
            <p className="muted small">
              {esEquipos
                ? "Marca uno o varios equipos. El total se divide entre los equipos perdedores y luego entre sus integrantes."
                : "Marca uno o varios perdedores. El total se divide en partes iguales."}
            </p>

            {esEquipos ? (
              <div className="bolirana-equipos-liquidacion">
                {equipos.map((equipo) => {
                  const seleccionado = equiposPerdedores.includes(
                    equipo.nombre
                  );
                  return (
                    <label
                      key={equipo.nombre}
                      className={`bolirana-equipo-card ${
                        seleccionado ? "seleccionado" : ""
                      }`}
                    >
                      <div className="bolirana-equipo-card-head">
                        <input
                          type="checkbox"
                          checked={seleccionado}
                          onChange={() => alternarEquipo(equipo.nombre)}
                          disabled={procesando}
                        />
                        <strong>{equipo.nombre}</strong>
                        <span className="muted small">
                          {equipo.integrantes.length} integrante
                          {equipo.integrantes.length === 1 ? "" : "s"}
                        </span>
                        {seleccionado && (
                          <strong className="bolirana-equipo-monto">
                            {formatearPrecio(
                              montosEquipo[equipo.nombre] || 0
                            )}
                          </strong>
                        )}
                      </div>
                      <ul className="bolirana-equipo-integrantes">
                        {equipo.integrantes.map((participante) => (
                          <li key={participante.id}>
                            <span>{participante.etiqueta}</span>
                            {seleccionado && (
                              <span>
                                {formatearPrecio(montos[participante.id] || 0)}
                              </span>
                            )}
                          </li>
                        ))}
                      </ul>
                    </label>
                  );
                })}
              </div>
            ) : (
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
            )}

            {esEquipos && equiposPerdedores.length > 0 && (
              <div className="bolirana-division-info">
                <span>
                  {formatearPrecio(total)} ÷ {equiposPerdedores.length} equipo
                  {equiposPerdedores.length > 1 ? "s" : ""} perdedor
                  {equiposPerdedores.length > 1 ? "es" : ""}
                </span>
                <strong>
                  {formatearPrecio(
                    total / equiposPerdedores.length
                  )}{" "}
                  c/u
                </strong>
              </div>
            )}

            {!esEquipos && cantidad > 0 && (
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
              Las mesas, barras y clientes individuales perdedores reciben el
              cargo en su cuenta general. Los alias vinculados se cargan a su
              cuenta de origen y los alias libres quedan como cargos pendientes
              de cobro.
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
