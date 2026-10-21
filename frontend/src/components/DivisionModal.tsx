/**
 * Ventana de división de cuenta por mesa.
 * - Carga los productos pendientes de la mesa (pedidos abiertos).
 * - El mesero crea clientes con alias (Cliente A, Cliente B, ...).
 * - Asigna productos a cada cliente y ve el subtotal de cada uno.
 * - Al confirmar, se generan los subtotales separados y la mesa sigue ocupada.
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

interface Pedido {
  id: number;
  items: Linea[];
}

interface Participante {
  alias: string;
  items: { producto_id: number; cantidad: number; precio_unitario: number; subtotal: number }[];
}

interface Props {
  mesaId: number;
  onClose: () => void;
  onConfirmado?: () => void;
}

export default function DivisionModal({ mesaId, onClose, onConfirmado }: Props) {
  const [lineas, setLineas] = useState<Linea[]>([]);
  const [participantes, setParticipantes] = useState<Participante[]>([]);
  const [aliasNuevo, setAliasNuevo] = useState("");
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
        (data.pedidos || []).forEach((p: Pedido) => {
          p.items.forEach((i) => {
            const existente = todas.find((t) => t.producto_id === i.producto_id);
            if (existente) {
              existente.cantidad += i.cantidad;
              existente.subtotal = round(existente.subtotal + i.subtotal);
            } else {
              todas.push({ ...i });
            }
          });
        });
        setLineas(todas);
        setError(null);
      } catch (err: any) {
        setError(err.message);
      }
    };
    cargar();
  }, [mesaId]);

  const round = (n: number) => Math.round(n * 100) / 100;

  /** Cantidad ya asignada de un producto en los participantes */
  const cantidadAsignada = (productoId: number) =>
    participantes.reduce(
      (sum, p) =>
        sum + p.items.filter((i) => i.producto_id === productoId).reduce((s, i) => s + i.cantidad, 0),
      0
    );

  const disponible = (linea: Linea) => linea.cantidad - cantidadAsignada(linea.producto_id);

  const agregarParticipante = () => {
    const alias = aliasNuevo.trim();
    if (!alias) return;
    if (participantes.some((p) => p.alias.toLowerCase() === alias.toLowerCase())) {
      setError(`Ya existe el alias "${alias}"`);
      return;
    }
    setParticipantes([...participantes, { alias, items: [] }]);
    setAliasNuevo("");
    setError(null);
  };

  const eliminarParticipante = (index: number) => {
    setParticipantes(participantes.filter((_, i) => i !== index));
  };

  const asignar = (participanteIndex: number, linea: Linea) => {
    if (disponible(linea) <= 0) {
      setError(`No quedan unidades de ${linea.producto_nombre}`);
      return;
    }
    setParticipantes(
      participantes.map((p, i) => {
        if (i !== participanteIndex) return p;
        const items = [...p.items];
        const existente = items.find((x) => x.producto_id === linea.producto_id);
        if (existente) {
          existente.cantidad += 1;
          existente.subtotal = round(
            existente.subtotal + existente.precio_unitario
          );
        } else {
          items.push({
            producto_id: linea.producto_id,
            cantidad: 1,
            precio_unitario: linea.precio_unitario,
            subtotal: linea.precio_unitario,
          });
        }
        return { ...p, items };
      })
    );
    setError(null);
  };

  const quitar = (participanteIndex: number, productoId: number) => {
    setParticipantes(
      participantes.map((p, i) => {
        if (i !== participanteIndex) return p;
        const existente = p.items.find((x) => x.producto_id === productoId);
        if (!existente) return p;
        if (existente.cantidad <= 1) {
          return { ...p, items: p.items.filter((x) => x.producto_id !== productoId) };
        }
        return {
          ...p,
          items: p.items.map((x) =>
            x.producto_id === productoId
              ? {
                  ...x,
                  cantidad: x.cantidad - 1,
                  subtotal: round(x.subtotal - x.precio_unitario),
                }
              : x
          ),
        };
      })
    );
  };

  const totalDivision = useMemo(
    () => round(participantes.reduce((s, p) => s + subtotal(p), 0)),
    [participantes]
  );

  const subtotal = (p: Participante) =>
    round(p.items.reduce((s, i) => s + i.subtotal, 0));

  const confirmar = async () => {
    if (participantes.length === 0) {
      setError("Agrega al menos un cliente");
      return;
    }
    if (participantes.some((p) => p.items.length === 0)) {
      setError("Cada cliente debe tener al menos un producto");
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
      setMensaje("Cuenta dividida. La mesa permanece ocupada.");
      setTimeout(() => {
        onConfirmado?.();
        onClose();
      }, 900);
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
            <div className="division-grid">
              {/* Columna 1: productos de la mesa */}
              <section className="panel">
                <h3>Productos de la mesa</h3>
                {lineas.map((linea) => (
                  <div key={linea.producto_id} className="cuenta-linea">
                    <span>
                      {linea.producto_nombre}{" "}
                      <span className="muted small">
                        (disp. {disponible(linea)} de {linea.cantidad})
                      </span>
                    </span>
                    <strong>${linea.subtotal.toFixed(2)}</strong>
                  </div>
                ))}
              </section>

              {/* Columna 2: clientes */}
              <section className="panel">
                <h3>Clientes</h3>

                <div className="inline-form">
                  <div className="form-group">
                    <label>Alias del cliente</label>
                    <input
                      value={aliasNuevo}
                      onChange={(e) => setAliasNuevo(e.target.value)}
                      placeholder="Cliente A"
                      onKeyDown={(e) => e.key === "Enter" && agregarParticipante()}
                    />
                  </div>
                  <button className="btn-primary" onClick={agregarParticipante}>
                    + Agregar
                  </button>
                </div>

                {participantes.length === 0 && (
                  <p className="empty-state">Crea los alias de los clientes.</p>
                )}

                {participantes.map((p, index) => (
                  <div key={index} className="participante-card">
                    <div className="participante-head">
                      <strong>{p.alias}</strong>
                      <span>
                        ${subtotal(p).toFixed(2)}
                        <button
                          className="btn-icon danger"
                          title="Quitar cliente"
                          onClick={() => eliminarParticipante(index)}
                        >
                          ×
                        </button>
                      </span>
                    </div>

                    {p.items.length === 0 && (
                      <p className="muted small">Sin productos asignados.</p>
                    )}

                    {p.items.map((item) => {
                      const linea = lineas.find((l) => l.producto_id === item.producto_id)!;
                      return (
                        <div key={item.producto_id} className="cuenta-linea small">
                          <span>
                            {item.cantidad} × {linea.producto_nombre}
                          </span>
                          <span>
                            ${item.subtotal.toFixed(2)}
                            <button
                              className="btn-icon danger"
                              title="Quitar"
                              onClick={() => quitar(index, item.producto_id)}
                            >
                              −
                            </button>
                          </span>
                        </div>
                      );
                    })}

                    <div className="participante-asignar">
                      {lineas
                        .filter((l) => disponible(l) > 0)
                        .map((l) => (
                          <button
                            key={l.producto_id}
                            className="btn-secondary btn-small"
                            onClick={() => asignar(index, l)}
                          >
                            + {l.producto_nombre}
                          </button>
                        ))}
                    </div>
                  </div>
                ))}
              </section>
            </div>

            <div className="total-row">
              <span>Total de la división</span>
              <strong>${totalDivision.toFixed(2)}</strong>
            </div>

            <div className="modal-actions">
              <button className="btn-secondary" onClick={onClose}>
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
