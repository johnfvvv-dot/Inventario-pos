/**
 * Modal para iniciar una partida de Bolirana.
 *
 * Permite elegir dos o más participantes entre mesas ocupadas, barras con
 * plazas ocupadas, clientes individuales activos y jugadores escritos a mano.
 * Un alias puede vincularse a una cuenta de origen para que su parte se cobre
 * allí al liquidar. También permite jugar en modalidad directa o por equipos.
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
  nombre?: string | null;
  en_bolirana?: boolean;
  posiciones?: { id: number; estado: string }[];
}

type Modalidad = "directo" | "equipos";

interface AliasSeleccion {
  nombre: string;
  /** Cuenta de origen codificada: mesa:ID | individual:ID | barra:N. */
  origen: string;
}

interface Seleccionado {
  clave: string;
  etiqueta: string;
  tipo: "mesa" | "individual" | "barra" | "alias";
  mesaId?: number;
  barraNumero?: number;
  alias?: AliasSeleccion;
}

interface Props {
  bolirana: Bolirana;
  mesas: MesaDisponible[];
  onClose: () => void;
  onIniciado: () => void;
}

const EQUIPOS_INICIALES = ["Equipo A", "Equipo B"];

const claveMesa = (id: number) => `mesa:${id}`;
const claveIndividual = (id: number) => `individual:${id}`;
const claveBarra = (numero: number) => `barra:${numero}`;
const claveAlias = (nombre: string) => `alias:${nombre.trim().toLowerCase()}`;

export default function IniciarPartidaBoliranaModal({
  bolirana,
  mesas,
  onClose,
  onIniciado,
}: Props) {
  const usuario = JSON.parse(localStorage.getItem("user") || "{}");
  const usuarioId = Number(usuario?.id) || 1;

  const [modalidad, setModalidad] = useState<Modalidad>("directo");
  const [mesasSeleccionadas, setMesasSeleccionadas] = useState<number[]>([]);
  const [individualesSeleccionados, setIndividualesSeleccionados] = useState<
    number[]
  >([]);
  const [barrasSeleccionadas, setBarrasSeleccionadas] = useState<number[]>([]);
  const [alias, setAlias] = useState<AliasSeleccion[]>([]);
  const [nuevoAlias, setNuevoAlias] = useState("");
  const [origenNuevoAlias, setOrigenNuevoAlias] = useState("");
  const [equipos, setEquipos] = useState<string[]>(EQUIPOS_INICIALES);
  const [nuevoEquipo, setNuevoEquipo] = useState("");
  const [equipoAsignado, setEquipoAsignado] = useState<
    Record<string, string>
  >({});
  const [error, setError] = useState<string | null>(null);
  const [procesando, setProcesando] = useState(false);

  const mesasLibres = useMemo(
    () =>
      mesas.filter(
        (m) =>
          m.tipo !== "barra" &&
          m.tipo !== "individual" &&
          m.estado === "ocupada" &&
          !m.en_bolirana
      ),
    [mesas]
  );

  const individualesActivos = useMemo(
    () =>
      mesas.filter(
        (m) =>
          m.tipo === "individual" && m.estado === "ocupada" && !m.en_bolirana
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

  const etiquetaOrigen = (origen: string) => {
    if (!origen) return "";
    const [tipo, valor] = origen.split(":");
    if (tipo === "mesa") {
      const mesa = mesas.find((m) => m.id === Number(valor));
      return mesa ? `Mesa ${mesa.numero}` : "Mesa";
    }
    if (tipo === "individual") return "Individual";
    if (tipo === "barra") return `Barra ${valor}`;
    return "";
  };

  const seleccionados = useMemo<Seleccionado[]>(() => {
    const lista: Seleccionado[] = [];
    mesasSeleccionadas.forEach((id) => {
      const mesa = mesas.find((m) => m.id === id);
      if (mesa) {
        lista.push({
          clave: claveMesa(id),
          etiqueta: `Mesa ${mesa.numero}`,
          tipo: "mesa",
          mesaId: id,
        });
      }
    });
    barrasSeleccionadas.forEach((numero) => {
      lista.push({
        clave: claveBarra(numero),
        etiqueta: `Barra ${numero}`,
        tipo: "barra",
        barraNumero: numero,
      });
    });
    individualesSeleccionados.forEach((id) => {
      const mesa = mesas.find((m) => m.id === id);
      lista.push({
        clave: claveIndividual(id),
        etiqueta: `Individual — ${mesa?.nombre || "Cliente"}`,
        tipo: "individual",
        mesaId: id,
      });
    });
    alias.forEach((jugador) => {
      const origen = etiquetaOrigen(jugador.origen);
      lista.push({
        clave: claveAlias(jugador.nombre),
        etiqueta: origen
          ? `${jugador.nombre} · ${origen}`
          : jugador.nombre,
        tipo: "alias",
        alias: jugador,
      });
    });
    return lista;
  }, [
    mesasSeleccionadas,
    barrasSeleccionadas,
    individualesSeleccionados,
    alias,
    mesas,
  ]);

  const cuentasSeleccionadas = useMemo(
    () =>
      new Set(
        seleccionados
          .filter((seleccionado) => seleccionado.tipo !== "alias")
          .map((seleccionado) => seleccionado.clave)
      ),
    [seleccionados]
  );

  const origenesUsados = useMemo(
    () => new Set(alias.map((jugador) => jugador.origen).filter(Boolean)),
    [alias]
  );

  const opcionesOrigen = useMemo(() => {
    const usados = new Set([...cuentasSeleccionadas, ...origenesUsados]);
    const opciones: { valor: string; etiqueta: string; grupo: string }[] = [];
    mesasLibres.forEach((mesa) => {
      const valor = claveMesa(mesa.id);
      if (!usados.has(valor)) {
        opciones.push({
          valor,
          etiqueta: `Mesa ${mesa.numero}`,
          grupo: "Mesas",
        });
      }
    });
    barrasLibres.forEach((barra) => {
      const valor = claveBarra(barra.numero);
      if (!usados.has(valor)) {
        opciones.push({
          valor,
          etiqueta: `Barra ${barra.numero}`,
          grupo: "Barras",
        });
      }
    });
    individualesActivos.forEach((cliente) => {
      const valor = claveIndividual(cliente.id);
      if (!usados.has(valor)) {
        opciones.push({
          valor,
          etiqueta: `Individual — ${cliente.nombre || "Cliente"}`,
          grupo: "Clientes individuales",
        });
      }
    });
    return opciones;
  }, [
    mesasLibres,
    barrasLibres,
    individualesActivos,
    cuentasSeleccionadas,
    origenesUsados,
  ]);

  const gruposOrigen = useMemo(() => {
    const grupos = new Map<string, typeof opcionesOrigen>();
    opcionesOrigen.forEach((opcion) => {
      const actual = grupos.get(opcion.grupo) || [];
      actual.push(opcion);
      grupos.set(opcion.grupo, actual);
    });
    return Array.from(grupos.entries());
  }, [opcionesOrigen]);

  const totalParticipantes = seleccionados.length;

  const registrarEquipo = (clave: string) => {
    if (modalidad !== "equipos") return;
    const inicial = equipos[0] || "Equipo A";
    setEquipoAsignado((actual) =>
      actual[clave] ? actual : { ...actual, [clave]: inicial }
    );
  };

  const quitarEquipo = (clave: string) => {
    setEquipoAsignado((actual) => {
      if (!(clave in actual)) return actual;
      const copia = { ...actual };
      delete copia[clave];
      return copia;
    });
  };

  const cambiarModalidad = (nueva: Modalidad) => {
    setModalidad(nueva);
    setError(null);
    if (nueva === "equipos") {
      const inicial = equipos[0] || "Equipo A";
      setEquipoAsignado((actual) => {
        const copia = { ...actual };
        seleccionados.forEach((seleccionado) => {
          if (!copia[seleccionado.clave]) {
            copia[seleccionado.clave] = inicial;
          }
        });
        return copia;
      });
    }
  };

  const aliasConOrigen = (clave: string) =>
    alias.find((jugador) => jugador.origen === clave);

  const alternarMesa = (id: number) => {
    const clave = claveMesa(id);
    if (!mesasSeleccionadas.includes(id)) {
      const vinculado = aliasConOrigen(clave);
      if (vinculado) {
        setError(
          `La cuenta ya está vinculada al jugador ${vinculado.nombre}.`
        );
        return;
      }
      if (origenNuevoAlias === clave) setOrigenNuevoAlias("");
      setMesasSeleccionadas((actual) => [...actual, id]);
      registrarEquipo(clave);
    } else {
      setMesasSeleccionadas((actual) => actual.filter((m) => m !== id));
      quitarEquipo(clave);
    }
    setError(null);
  };

  const alternarIndividual = (id: number) => {
    const clave = claveIndividual(id);
    if (!individualesSeleccionados.includes(id)) {
      const vinculado = aliasConOrigen(clave);
      if (vinculado) {
        setError(
          `La cuenta ya está vinculada al jugador ${vinculado.nombre}.`
        );
        return;
      }
      if (origenNuevoAlias === clave) setOrigenNuevoAlias("");
      setIndividualesSeleccionados((actual) => [...actual, id]);
      registrarEquipo(clave);
    } else {
      setIndividualesSeleccionados((actual) =>
        actual.filter((m) => m !== id)
      );
      quitarEquipo(clave);
    }
    setError(null);
  };

  const alternarBarra = (numero: number) => {
    const clave = claveBarra(numero);
    if (!barrasSeleccionadas.includes(numero)) {
      const vinculado = aliasConOrigen(clave);
      if (vinculado) {
        setError(
          `La cuenta ya está vinculada al jugador ${vinculado.nombre}.`
        );
        return;
      }
      if (origenNuevoAlias === clave) setOrigenNuevoAlias("");
      setBarrasSeleccionadas((actual) => [...actual, numero]);
      registrarEquipo(clave);
    } else {
      setBarrasSeleccionadas((actual) =>
        actual.filter((b) => b !== numero)
      );
      quitarEquipo(clave);
    }
    setError(null);
  };

  const agregarAlias = () => {
    const limpio = nuevoAlias.trim();
    if (!limpio) return;
    if (alias.some((a) => a.nombre.toLowerCase() === limpio.toLowerCase())) {
      setError(`El jugador ${limpio} ya está en la lista.`);
      return;
    }
    if (
      origenNuevoAlias &&
      (cuentasSeleccionadas.has(origenNuevoAlias) ||
        origenesUsados.has(origenNuevoAlias))
    ) {
      setError("La cuenta de origen ya está participando en esta partida.");
      return;
    }
    setAlias((actual) => [
      ...actual,
      { nombre: limpio, origen: origenNuevoAlias },
    ]);
    registrarEquipo(claveAlias(limpio));
    setNuevoAlias("");
    setOrigenNuevoAlias("");
    setError(null);
  };

  const quitarAlias = (nombre: string) => {
    setAlias((actual) => actual.filter((a) => a.nombre !== nombre));
    quitarEquipo(claveAlias(nombre));
    setError(null);
  };

  const agregarEquipo = () => {
    const limpio = nuevoEquipo.trim();
    if (!limpio) return;
    if (equipos.some((e) => e.toLowerCase() === limpio.toLowerCase())) {
      setError("Ese equipo ya existe.");
      return;
    }
    setEquipos((actual) => [...actual, limpio]);
    setNuevoEquipo("");
    setError(null);
  };

  const quitarNombreEquipo = (nombre: string) => {
    if (seleccionados.some((s) => equipoAsignado[s.clave] === nombre)) {
      setError("No puedes quitar un equipo que tiene integrantes.");
      return;
    }
    if (equipos.length <= 2) {
      setError("La partida por equipos necesita al menos dos equipos.");
      return;
    }
    setEquipos((actual) => actual.filter((e) => e !== nombre));
    setError(null);
  };

  const enviar = async (evento?: FormEvent) => {
    evento?.preventDefault();
    if (procesando) return;

    if (totalParticipantes < 2) {
      setError("Selecciona al menos dos participantes para iniciar la partida.");
      return;
    }

    if (modalidad === "equipos") {
      const equiposConIntegrantes = new Set<string>();
      for (const seleccionado of seleccionados) {
        const equipo = (equipoAsignado[seleccionado.clave] || "").trim();
        if (!equipo) {
          setError(`Asigna un equipo a ${seleccionado.etiqueta}.`);
          return;
        }
        equiposConIntegrantes.add(equipo);
      }
      if (equiposConIntegrantes.size < 2) {
        setError(
          "Crea al menos dos equipos y asigna un integrante a cada uno."
        );
        return;
      }
    }

    setProcesando(true);
    setError(null);
    try {
      const participantes = seleccionados.map((seleccionado) => {
        const equipo =
          modalidad === "equipos"
            ? (equipoAsignado[seleccionado.clave] || "").trim()
            : undefined;

        if (seleccionado.tipo === "mesa") {
          return {
            tipo: "mesa",
            mesa_id: seleccionado.mesaId,
            equipo,
          };
        }
        if (seleccionado.tipo === "individual") {
          return {
            tipo: "mesa",
            mesa_id: seleccionado.mesaId,
            equipo,
          };
        }
        if (seleccionado.tipo === "barra") {
          return {
            tipo: "barra",
            barra_numero: seleccionado.barraNumero,
            equipo,
          };
        }

        const jugador = seleccionado.alias!;
        const base = {
          tipo: "alias",
          alias: jugador.nombre,
          equipo,
        };
        if (!jugador.origen) return base;

        const [tipoOrigen, valor] = jugador.origen.split(":");
        if (tipoOrigen === "barra") {
          return {
            ...base,
            origen_tipo: "barra" as const,
            origen_barra_numero: Number(valor),
          };
        }
        return {
          ...base,
          origen_tipo: tipoOrigen as "mesa" | "individual",
          origen_mesa_id: Number(valor),
        };
      });

      await api.iniciarPartidaBolirana(bolirana.id, {
        usuario_id: usuarioId,
        modalidad,
        participantes,
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
          Elige mesas, barras, clientes individuales o jugadores libres.
          Necesitas al menos dos participantes.
        </p>

        <div className="bolirana-modalidad" role="group" aria-label="Modalidad">
          <button
            type="button"
            className={`bolirana-modalidad-opcion ${
              modalidad === "directo" ? "activa" : ""
            }`}
            onClick={() => cambiarModalidad("directo")}
            disabled={procesando}
          >
            <Icon nombre="usuario" size={15} />
            Directo
          </button>
          <button
            type="button"
            className={`bolirana-modalidad-opcion ${
              modalidad === "equipos" ? "activa" : ""
            }`}
            onClick={() => cambiarModalidad("equipos")}
            disabled={procesando}
          >
            <Icon nombre="usuarios" size={15} />
            Por equipos
          </button>
        </div>

        <div className="bolirana-modal-grid">
          <section>
            <h4>Mesas ocupadas</h4>
            {mesasLibres.length === 0 ? (
              <p className="muted small">No hay mesas disponibles.</p>
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
                  <label
                    key={`barra-${barra.numero}`}
                    className="bolirana-opcion"
                  >
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

          <section>
            <h4>Clientes individuales activos</h4>
            {individualesActivos.length === 0 ? (
              <p className="muted small">
                No hay clientes individuales activos.
              </p>
            ) : (
              <div className="bolirana-opciones">
                {individualesActivos.map((cliente) => (
                  <label key={cliente.id} className="bolirana-opcion">
                    <input
                      type="checkbox"
                      checked={individualesSeleccionados.includes(cliente.id)}
                      onChange={() => alternarIndividual(cliente.id)}
                      disabled={procesando}
                    />
                    <span>
                      Individual — {cliente.nombre || "Cliente"}
                    </span>
                  </label>
                ))}
              </div>
            )}
          </section>
        </div>

        <section className="bolirana-alias-seccion">
          <h4>Jugadores / alias</h4>
          <p className="muted small">
            Puedes vincular un alias a una mesa, barra o cliente individual
            para cargarle su parte en esa cuenta.
          </p>
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
              placeholder="Ej.: Carlos, Juan"
              maxLength={60}
              disabled={procesando}
            />
            <select
              value={origenNuevoAlias}
              onChange={(e) => setOrigenNuevoAlias(e.target.value)}
              disabled={procesando}
              title="Cuenta de origen del alias"
            >
              <option value="">Sin cuenta (jugador libre)</option>
              {gruposOrigen.map(([grupo, opciones]) => (
                <optgroup key={grupo} label={grupo}>
                  {opciones.map((opcion) => (
                    <option key={opcion.valor} value={opcion.valor}>
                      {opcion.etiqueta}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
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
              {alias.map((jugador) => {
                const origen = etiquetaOrigen(jugador.origen);
                return (
                  <span key={jugador.nombre} className="bolirana-chip">
                    {jugador.nombre}
                    {origen ? ` · ${origen}` : ""}
                    <button
                      type="button"
                      className="btn-icon"
                      title={`Quitar ${jugador.nombre}`}
                      onClick={() => quitarAlias(jugador.nombre)}
                      disabled={procesando}
                    >
                      <Icon nombre="cerrar" size={12} />
                    </button>
                  </span>
                );
              })}
            </div>
          )}
        </section>

        {modalidad === "equipos" && (
          <section className="bolirana-equipos-seccion">
            <h4>Equipos</h4>
            <p className="muted small">
              Crea dos o más equipos y asigna cada participante a uno. Los
              equipos pueden mezclar mesas, barras, individuales y alias.
            </p>
            <div className="bolirana-equipos-chips">
              {equipos.map((equipo) => {
                const integrantes = seleccionados.filter(
                  (seleccionado) =>
                    equipoAsignado[seleccionado.clave] === equipo
                ).length;
                return (
                  <span
                    key={equipo}
                    className="bolirana-chip bolirana-chip--equipo"
                  >
                    {equipo}
                    <span className="bolirana-equipo-conteo">
                      {integrantes}
                    </span>
                    <button
                      type="button"
                      className="btn-icon"
                      title={`Quitar ${equipo}`}
                      onClick={() => quitarNombreEquipo(equipo)}
                      disabled={procesando}
                    >
                      <Icon nombre="cerrar" size={12} />
                    </button>
                  </span>
                );
              })}
            </div>
            <div className="bolirana-alias-fila bolirana-equipo-fila">
              <input
                value={nuevoEquipo}
                onChange={(e) => setNuevoEquipo(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    agregarEquipo();
                  }
                }}
                placeholder="Ej.: Equipo C"
                maxLength={60}
                disabled={procesando}
              />
              <button
                type="button"
                className="btn-secondary"
                onClick={agregarEquipo}
                disabled={procesando || !nuevoEquipo.trim()}
              >
                <Icon nombre="mas" size={14} />
                Agregar equipo
              </button>
            </div>

            {seleccionados.length === 0 ? (
              <p className="muted small">
                Selecciona participantes para asignarles un equipo.
              </p>
            ) : (
              <div className="bolirana-equipo-asignacion">
                {seleccionados.map((seleccionado) => (
                  <label
                    key={seleccionado.clave}
                    className="bolirana-equipo-asignado"
                  >
                    <span>{seleccionado.etiqueta}</span>
                    <select
                      value={equipoAsignado[seleccionado.clave] || ""}
                      onChange={(e) =>
                        setEquipoAsignado((actual) => ({
                          ...actual,
                          [seleccionado.clave]: e.target.value,
                        }))
                      }
                      disabled={procesando}
                    >
                      {equipos.map((equipo) => (
                        <option key={equipo} value={equipo}>
                          {equipo}
                        </option>
                      ))}
                    </select>
                  </label>
                ))}
              </div>
            )}
          </section>
        )}

        <div className="bolirana-resumen-seleccion">
          Participantes seleccionados: <strong>{totalParticipantes}</strong>
          {modalidad === "equipos" && (
            <>
              {" · "}
              Equipos con integrantes:{" "}
              <strong>
                {
                  new Set(
                    seleccionados
                      .map((s) => equipoAsignado[s.clave])
                      .filter(Boolean)
                  ).size
                }
              </strong>
            </>
          )}
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
