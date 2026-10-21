/**
 * Ventana de división de cuenta por mesa.
 *
 * - Productos de la mesa a la izquierda, clientes (alias) a la derecha.
 * - Al crear un alias se pueden marcar los productos que se le asignan.
 * - El subtotal de cada alias se calcula automáticamente.
 * - La parte NO asignada se mantiene como bloque único ("Resto de la cuenta"),
 *   sin obligar a crear alias adicionales.
 * - Al confirmar, la mesa permanece ocupada.
 */

import { useEffect, useMemo, useState } from "react";
import { api } from "../services/api";

interface Linea {
  producto_id: number;
  producto_nombre: string;
  cantidad: number;
  precio_unitario: number;
  subtotal: number;
}

interface ItemParticipante {
  producto_id: number;
  cantidad: number;
  precio_unitario: number;
  subtotal: number;
}

interface Participante {
  alias: string;
  items: ItemParticipante[];
}

const redondear = (n: number) => Math.round(n * 100) / 100;

const subtotalDe = (p: Participante) =>
  redondear(p.items.reduce((s, i) => s + i.subtotal, 0));

interface Props {
  mesaId: number;
  onClose: () => void;
  onConfirmado?: () => void;
}

export default function DivisionModal({ mesaId, onClose, onConfirmado }: Props) {
  const [lineas, setLineas] = useState<Linea[]>([]);
  const [participantes, setParticipantes] = useState<Participante[]>([]);
  const [aliasNuevo, setAliasNuevo] = useState("");
  const [destino, setDestino] = useState<string>("nuevo"); // "nuevo" o índice de participante
  const [seleccion, setSeleccion] = useState<Record<number, number>>({});
  const [totalCuenta, setTotalCuenta] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [procesando, setProcesando] = useState(false);

  const usuario = JSON.parse(localStorage.getItem("user") || "{}");
  const usuarioId: number = usuario?.id || 1;

  useEffect(() => {
    const cargar = async () => {
      try {
        const data: any = await api.getCuentaMesa(mesaId);
        const todas: Linea[] = [];
        (data.pedidos || []).forEach((pedido: any) => {
          pedido.items.forEach((i: Linea) => {
            const existente = todas.find((t) => t.producto_id === i.producto_id);
            if (existente) {
              existente.cantidad += i.cantidad;
              existente.subtotal = redondear(existente.subtotal + i.subtotal);
            } else {
              todas.push({ ...i });
            }
          });
        });
        setLineas(todas);
        setTotalCuenta(data.total || 0);
        setError(null);
      } catch (err: any) {
        setError(err.message);
      }
    };
    cargar();
  }, [mesaId]);

  /** Unidades ya asignadas de un producto, en todos los alias */
  const unidadesAsignadas = (productoId: number) =>
    participantes.reduce(
      (sum, p) =>
        sum +
        p.items
          .filter((i) => i.producto_id === productoId)
          .reduce((s, i) => s + i.cantidad, 0),
      0
    );

  const disponible = (linea: Linea) => linea.cantidad - unidadesAsignadas(linea.producto_id);

  /** Máximo de unidades que puede recibir el destino actual */
  const maximoAsignable = (linea: Linea) => {
    const propio = destino === "nuevo" ? 0 : marcadas(linea.producto_id);
    return Math.max(0, linea.cantidad - (unidadesAsignadas(linea.producto_id) - propio));
  };

  /** Unidades marcadas actualmente para el destino seleccionado */
  const marcadas = (productoId: number): number => {
    if (destino === "nuevo") return seleccion[productoId] || 0;
    const p = participantes[Number(destino)];
    if (!p) return 0;
    const item = p.items.find((i) => i.producto_id === productoId);
    return item ? item.cantidad : 0;
  };

  /** Ajusta la cantidad asignada de un producto (+1 / -1) para el destino actual */
  const ajustarCantidad = (linea: Linea, delta: number) => {
    const actual = marcadas(linea.producto_id);
    const maximo = maximoAsignable(linea);
    let nuevo = actual + delta;

    if (nuevo < 0) nuevo = 0;
    if (nuevo > maximo) {
      nuevo = maximo;
      setError(
        `Solo hay ${maximo} unidad(es) de ${linea.producto_nombre} para asignar`
      );
    }

    if (destino === "nuevo") {
      setSeleccion((prev) => {
        const copia = { ...prev };
        if (nuevo <= 0) delete copia[linea.producto_id];
        else copia[linea.producto_id] = nuevo;
        return copia;
      });
    } else {
      const index = Number(destino);
      setParticipantes(
        participantes.map((p, i) => {
          if (i !== index) return p;
          const items = p.items.filter((x) => x.producto_id !== linea.producto_id);
          if (nuevo > 0) {
            items.push({
              producto_id: linea.producto_id,
              cantidad: nuevo,
              precio_unitario: linea.precio_unitario,
              subtotal: redondear(linea.precio_unitario * nuevo),
            });
          }
          return { ...p, items };
        })
      );
    }
    setError(null);
  };

  const cambiarDestino = (valor: string) => {
    setDestino(valor);
    if (valor === "nuevo") {
      setSeleccion({});
    } else {
      const p = participantes[Number(valor)];
      const preseleccion: Record<number, number> = {};
      p?.items.forEach((i) => (preseleccion[i.producto_id] = i.cantidad));
      setSeleccion(preseleccion);
    }
  };

  const agregarAlias = () => {
    const alias = aliasNuevo.trim();
    if (!alias) {
      setError("Escribe el alias del cliente");
      return;
    }
    if (participantes.some((p) => p.alias.toLowerCase() === alias.toLowerCase())) {
      setError(`Ya existe el alias "${alias}"`);
      return;
    }

    // Los productos marcados se asignan al nuevo alias
    const items: ItemParticipante[] = Object.entries(seleccion)
      .map(([pid, cantidad]) => {
        const linea = lineas.find((l) => l.producto_id === Number(pid))!;
        return {
          producto_id: Number(pid),
          cantidad,
          precio_unitario: linea.precio_unitario,
          subtotal: redondear(linea.precio_unitario * cantidad),
        };
      })
      .filter((i) => i.cantidad > 0);

    setParticipantes([...participantes, { alias, items }]);
    setAliasNuevo("");
    setSeleccion({});
    setDestino("nuevo");
    setError(null);
  };

  const eliminarAlias = (index: number) => {
    setParticipantes(participantes.filter((_, i) => i !== index));
    if (destino === String(index)) {
      setDestino("nuevo");
      setSeleccion({});
    }
  };

  const quitarUnidad = (participanteIndex: number, productoId: number) => {
    setParticipantes(
      participantes.map((p, i) => {
        if (i !== participanteIndex) return p;
        const item = p.items.find((x) => x.producto_id === productoId);
        if (!item) return p;
        if (item.cantidad <= 1) {
          return { ...p, items: p.items.filter((x) => x.producto_id !== productoId) };
        }
        return {
          ...p,
          items: p.items.map((x) =>
            x.producto_id === productoId
              ? {
                  ...x,
                  cantidad: x.cantidad - 1,
                  subtotal: redondear(x.subtotal - x.precio_unitario),
                }
              : x
          ),
        };
      })
    );
  };

  const totalAsignado = useMemo(
    () => redondear(participantes.reduce((s, p) => s + subtotalDe(p), 0)),
    [participantes]
  );

  const resto = useMemo(
    () => redondear(Math.max(0, totalCuenta - totalAsignado)),
    [totalCuenta, totalAsignado]
  );

  const confirmar = async () => {
    if (participantes.length === 0) {
      setError("Agrega al menos un cliente");
      return;
    }
    if (participantes.some((p) => p.items.length === 0)) {
      setError("Cada alias debe tener al menos un producto asignado");
      return;
    }
    setProcesando(true);
    try {
      await api.dividirCuenta({
        mesa_id: mesaId,
        usuario_id: usuarioId,
        participantes: participantes.map((p) => ({
          alias: p.alias,
          items: p.items.map((i) => ({
            producto_id: i.producto_id,
            cantidad: i.cantidad,
          })),
        })),
      });
      setMensaje(
        resto > 0
          ? `División guardada. Quedan $${resto.toFixed(2)} sin asignar en la cuenta.`
          : "División guardada. La mesa permanece ocupada."
      );
      setTimeout(() => {
        onConfirmado?.();
        onClose();
      }, 1200);
    } catch (err: any) {
      setError(err.message);
      setProcesando(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box modal-xl" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3>Dividir cuenta por mesa</h3>
          <button className="btn-icon" onClick={onClose} title="Cerrar">
            ×
          </button>
        </div>

        {error && <p className="error-msg">{error}</p>}
        {mensaje && <p className="success-msg">{mensaje}</p>}

        {lineas.length === 0 ? (
          <p className="empty-state">
            No hay productos pendientes en esta mesa. Agrega productos al pedido primero.
          </p>
        ) : (
          <>
            <div className="division-toolbar">
              <div className="form-group">
                <label>Asignar productos a</label>
                <select value={destino} onChange={(e) => cambiarDestino(e.target.value)}>
                  <option value="nuevo">— Nuevo cliente —</option>
                  {participantes.map((p, i) => (
                    <option key={i} value={String(i)}>
                      {p.alias} (${subtotalDe(p).toFixed(2)})
                    </option>
                  ))}
                </select>
              </div>

              {destino === "nuevo" && (
                <div className="form-group">
                  <label>Alias del cliente</label>
                  <input
                    value={aliasNuevo}
                    onChange={(e) => setAliasNuevo(e.target.value)}
                    placeholder="Cliente A"
                    onKeyDown={(e) => e.key === "Enter" && agregarAlias()}
                  />
                </div>
              )}

              {destino === "nuevo" ? (
                <button className="btn-primary" onClick={agregarAlias}>
                  + Agregar cliente
                </button>
              ) : (
                <span className="muted small">
                  Marca los productos que pertenecen a{" "}
                  <strong>{participantes[Number(destino)]?.alias}</strong>
                </span>
              )}
            </div>

            <div className="division-grid">
              {/* Columna 1: productos de la mesa */}
              <section className="panel">
                <h3>Productos de la cuenta</h3>
                {lineas.map((linea) => {
                  const cantidad = marcadas(linea.producto_id);
                  const maximo = maximoAsignable(linea);
                  const libre = maximo - cantidad;
                  const totalProducto = linea.producto_nombre;
                  return (
                    <div
                      key={linea.producto_id}
                      className={`producto-fila ${cantidad > 0 ? "seleccionado" : ""}`}
                    >
                      <div className="producto-fila-info">
                        <span className="producto-check-nombre">
                          {totalProducto}
                          <span className="muted small">
                            {" "}
                            · {linea.precio_unitario.toFixed(2)} c/u · libre {libre} de{" "}
                            {maximo}
                          </span>
                        </span>
                        <strong>
                          ${redondear(linea.precio_unitario * cantidad).toFixed(2)}
                        </strong>
                      </div>

                      <div className="stepper">
                        <button
                          className="btn-icon"
                          title="Quitar una unidad"
                          onClick={() => ajustarCantidad(linea, -1)}
                          disabled={cantidad === 0}
                        >
                          −
                        </button>
                        <input
                          type="number"
                          className="stepper-input"
                          value={cantidad}
                          min={0}
                          max={maximo}
                          onChange={(e) => {
                            const valor = Math.max(
                              0,
                              Math.min(maximo, Number(e.target.value) || 0)
                            );
                            const diferencia = valor - cantidad;
                            if (diferencia !== 0) {
                              ajustarCantidad(linea, diferencia);
                            }
                          }}
                        />
                        <button
                          className="btn-icon"
                          title="Añadir una unidad"
                          onClick={() => ajustarCantidad(linea, +1)}
                          disabled={libre <= 0}
                        >
                          +
                        </button>
                      </div>
                    </div>
                  );
                })}

                {destino === "nuevo" && Object.keys(seleccion).length > 0 && (
                  <div className="resto-bloque">
                    <span>Marcado para el nuevo alias</span>
                    <strong>
                      $
                      {redondear(
                        Object.entries(seleccion).reduce((s, [pid, cant]) => {
                          const linea = lineas.find((l) => l.producto_id === Number(pid));
                          return s + (linea ? linea.precio_unitario * cant : 0);
                        }, 0)
                      ).toFixed(2)}
                    </strong>
                  </div>
                )}
              </section>

              {/* Columna 2: clientes */}
              <section className="panel">
                <h3>Clientes de la mesa</h3>

                {participantes.length === 0 && (
                  <p className="empty-state">
                    Escribe un alias y marca los productos que le asignas.
                  </p>
                )}

                {participantes.map((p, index) => (
                  <div key={index} className="participante-card">
                    <div className="participante-head">
                      <strong>{p.alias}</strong>
                      <span>
                        ${subtotalDe(p).toFixed(2)}
                        <button
                          className="btn-icon danger"
                          title="Quitar cliente"
                          onClick={() => eliminarAlias(index)}
                        >
                          ×
                        </button>
                      </span>
                    </div>

                    {p.items.length === 0 && (
                      <p className="muted small">
                        Sin productos. Selecciónalos en la columna izquierda.
                      </p>
                    )}

                    {p.items.map((item) => {
                      const linea = lineas.find((l) => l.producto_id === item.producto_id);
                      return (
                        <div key={item.producto_id} className="cuenta-linea small">
                          <span>
                            {item.cantidad} × {linea?.producto_nombre || "Producto"}
                          </span>
                          <span>
                            ${item.subtotal.toFixed(2)}
                            <button
                              className="btn-icon danger"
                              title="Quitar una unidad"
                              onClick={() => quitarUnidad(index, item.producto_id)}
                            >
                              −
                            </button>
                          </span>
                        </div>
                      );
                    })}
                  </div>
                ))}

                {participantes.length > 0 && (
                  <div className="resto-bloque">
                    <span>Resto sin asignar (queda como bloque único)</span>
                    <strong>${resto.toFixed(2)}</strong>
                  </div>
                )}
              </section>
            </div>

            <div className="total-row">
              <span>
                Total de la división: ${totalAsignado.toFixed(2)} · Resto: $
                {resto.toFixed(2)}
              </span>
              <strong>${totalCuenta.toFixed(2)}</strong>
            </div>

            <div className="modal-actions">
              <button className="btn-secondary" onClick={onClose} disabled={procesando}>
                Cancelar
              </button>
              <button
                className="btn-primary"
                onClick={confirmar}
                disabled={procesando || participantes.length === 0}
              >
                {procesando ? "Procesando..." : "Confirmar división"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
