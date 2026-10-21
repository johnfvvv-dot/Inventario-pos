/**
 * Ventana emergente con la cuenta actual de una mesa.
 * - Muestra el total, el detalle por pedido y las divisiones pendientes.
 * - Permite cerrar la cuenta SIN liberar la mesa (genera una nueva cuenta).
 * - Permite abrir la ventana de división entre clientes.
 */

import { useEffect, useState } from "react";
import { api, FORMAS_PAGO } from "../services/api";

interface LineaItem {
  producto_id: number;
  producto_nombre: string;
  cantidad: number;
  subtotal: number;
}

interface Participante {
  id: number;
  alias: string;
  subtotal: number;
  pagado: boolean;
  items: LineaItem[];
}

interface Division {
  id: number;
  total: number;
  total_pendiente: number;
  estado: string;
  participantes: Participante[];
}

interface Pedido {
  id: number;
  total: number;
  items: LineaItem[];
}

interface Cuenta {
  mesa_id: number;
  mesa_numero: number;
  estado_mesa: string;
  total: number;
  pedidos: Pedido[];
  divisiones: Division[];
}

interface Props {
  mesaId: number;
  onClose: () => void;
  onDividir?: () => void;
  onTransferir?: () => void;
  onActualizado?: () => void;
}

export default function CuentaModal({
  mesaId,
  onClose,
  onDividir,
  onTransferir,
  onActualizado,
}: Props) {
  const [cuenta, setCuenta] = useState<Cuenta | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [procesando, setProcesando] = useState(false);
  const [confirmacion, setConfirmacion] = useState(false);
  const [formaPago, setFormaPago] = useState("efectivo");

  const cargar = async () => {
    try {
      const data: any = await api.getCuentaMesa(mesaId);
      setCuenta(data);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    }
  };

  useEffect(() => {
    cargar();
  }, [mesaId]);

  const cerrarCuenta = async (liberarMesa = false) => {
    setProcesando(true);
    try {
      // 1) Cobrar toda la cuenta (pedidos + divisiones)
      await api.cerrarCuentaMesa(mesaId, false, formaPago);
      // 2) Si se pidió liberar, el backend valida que no queden cuentas pendientes
      if (liberarMesa) {
        await api.liberarMesa(mesaId);
      }
      setConfirmacion(false);
      setMensaje(
        liberarMesa
          ? "Cuenta cerrada y mesa liberada."
          : "Cuenta cerrada. La mesa permanece ocupada para una nueva cuenta."
      );
      await cargar();
      onActualizado?.();
      onClose();
    } catch (err: any) {
      setError(err.message);
      setProcesando(false);
    }
  };

  const pagarDivision = async (divisionId: number) => {
    setProcesando(true);
    try {
      await api.pagarDivision(divisionId);
      setMensaje("División cobrada.");
      await cargar();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setProcesando(false);
    }
  };

  /** Cierra solo la cuenta de un alias: ese cliente paga su parte */
  const cerrarAlias = async (participanteId: number, alias: string) => {
    setProcesando(true);
    try {
      await api.pagarParticipante(participanteId, formaPago);
      setMensaje(`"${alias}" pagó su parte. La cuenta sigue abierta para los demás.`);
      await cargar();
      onActualizado?.();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setProcesando(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box modal-xl" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3>
            {cuenta ? `Cuenta Mesa ${cuenta.mesa_numero}` : "Cargando cuenta..."}
          </h3>
          <button className="btn-icon" onClick={onClose} title="Cerrar">
            ×
          </button>
        </div>

        {error && <p className="error-msg">{error}</p>}
        {mensaje && <p className="success-msg">{mensaje}</p>}

        {cuenta && (
          <>
            <div className="cuenta-total">
              <span>Total de la cuenta</span>
              <strong>${cuenta.total.toFixed(2)}</strong>
            </div>

            <div className="cuenta-scroll">
              {cuenta.pedidos.length === 0 && cuenta.divisiones.length === 0 && (
                <p className="empty-state">La cuenta está vacía.</p>
              )}

              {cuenta.pedidos.map((pedido) => (
                <div key={`p-${pedido.id}`} className="cuenta-bloque">
                  <h4>Pedido #{pedido.id}</h4>
                  {pedido.items.map((item, i) => (
                    <div key={i} className="cuenta-linea">
                      <span>
                        {item.cantidad} × {item.producto_nombre}
                      </span>
                      <strong>${item.subtotal.toFixed(2)}</strong>
                    </div>
                  ))}
                  <div className="cuenta-linea cuenta-subtotal">
                    <span>Subtotal pedido</span>
                    <strong>${pedido.total.toFixed(2)}</strong>
                  </div>
                </div>
              ))}

              {cuenta.divisiones.map((division) => (
                <div key={`d-${division.id}`} className="cuenta-bloque">
                  <div className="cuenta-bloque-head">
                    <h4>División #{division.id}</h4>
                    <span className="muted small">
                      Total ${division.total.toFixed(2)} · Pendiente $
                      {division.total_pendiente.toFixed(2)}
                    </span>
                  </div>

                  {division.participantes.map((p) => (
                    <div key={p.id} className="cuenta-participante">
                      <div className="cuenta-linea">
                        <span>
                          <strong>{p.alias}</strong>{" "}
                          {p.pagado ? (
                            <span className="badge badge-success">pagado</span>
                          ) : (
                            <span className="badge badge-warning">pendiente</span>
                          )}
                        </span>
                        <span>
                          ${p.subtotal.toFixed(2)}
                          {!p.pagado && (
                            <button
                              className="btn-secondary btn-small"
                              title={`Cerrar la división de ${p.alias}`}
                              onClick={() => cerrarAlias(p.id, p.alias)}
                              disabled={procesando}
                            >
                              Cerrar división
                            </button>
                          )}
                        </span>
                      </div>
                      {p.items.map((item, i) => (
                        <div key={i} className="cuenta-linea small">
                          <span>
                            {item.cantidad} × {item.producto_nombre}
                          </span>
                          <span>${item.subtotal.toFixed(2)}</span>
                        </div>
                      ))}
                    </div>
                  ))}

                  {division.participantes.some((p) => !p.pagado) && (
                    <div className="cuenta-linea cuenta-subtotal">
                      <span>Pendiente de cobro</span>
                      <strong>${division.total_pendiente.toFixed(2)}</strong>
                    </div>
                  )}
                </div>
              ))}
            </div>

            <div className="form-group">
              <label>Forma de pago</label>
              <div className="formas-pago">
                {FORMAS_PAGO.map((f) => (
                  <button
                    key={f.id}
                    type="button"
                    className={`forma-pago ${formaPago === f.id ? "activa" : ""}`}
                    onClick={() => setFormaPago(f.id)}
                    disabled={procesando}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
            </div>

            {confirmacion ? (
              <div className="confirm-panel">
                <p className="confirm-pregunta">
                  ¿Cerrar la cuenta de esta mesa? La mesa seguirá ocupada.
                </p>
                <div className="modal-actions">
                  <button
                    className="btn-secondary"
                    onClick={() => setConfirmacion(false)}
                    disabled={procesando}
                  >
                    Cancelar
                  </button>
                  <button
                    className="btn-primary"
                    onClick={() => cerrarCuenta(false)}
                    disabled={procesando}
                  >
                    {procesando ? "Procesando..." : "Aceptar"}
                  </button>
                  <button
                    className="btn-warning"
                    onClick={() => cerrarCuenta(true)}
                    disabled={procesando}
                  >
                    Liberar mesa
                  </button>
                </div>
                <p className="muted small">
                  Cobro con <strong>{formaPago}</strong>. "Aceptar" cobra la cuenta y
                  mantiene la mesa ocupada. "Liberar mesa" cobra y deja la mesa disponible.
                </p>
              </div>
            ) : (
              <div className="modal-actions">
                {onDividir && (
                  <button className="btn-secondary" onClick={onDividir} disabled={procesando}>
                    Dividir cuenta
                  </button>
                )}
                {onTransferir && (
                  <button className="btn-secondary" onClick={onTransferir} disabled={procesando}>
                    Transferir cuenta
                  </button>
                )}
                <button
                  className="btn-primary"
                  onClick={() => setConfirmacion(true)}
                  disabled={procesando || cuenta.total === 0}
                >
                  {procesando ? "Procesando..." : "Cerrar cuenta"}
                </button>
              </div>
            )}
            <p className="muted small">
              "Cerrar división" cobra la parte de un solo cliente y mantiene abierta la
              cuenta de los demás. "Cerrar cuenta" cobra todo y la mesa sigue ocupada.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
