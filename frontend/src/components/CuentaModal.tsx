/**
 * Ventana emergente con la cuenta actual de una mesa.
 * - Muestra el total, el detalle por pedido y las divisiones pendientes.
 * - Permite cerrar la cuenta SIN liberar la mesa (genera una nueva cuenta).
 * - Permite abrir la ventana de división entre clientes.
 */

import { useEffect, useState } from "react";
import { api } from "../services/api";

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
}

export default function CuentaModal({ mesaId, onClose, onDividir }: Props) {
  const [cuenta, setCuenta] = useState<Cuenta | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [procesando, setProcesando] = useState(false);

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

  const cerrarCuenta = async () => {
    if (!window.confirm("¿Cerrar la cuenta de esta mesa? La mesa seguirá ocupada.")) {
      return;
    }
    setProcesando(true);
    try {
      await api.cerrarCuentaMesa(mesaId);
      setMensaje("Cuenta cerrada. La mesa permanece ocupada para una nueva cuenta.");
      await cargar();
    } catch (err: any) {
      setError(err.message);
    } finally {
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
                  <h4>División #{division.id}</h4>
                  {division.participantes.map((p) => (
                    <div key={p.id} className="cuenta-participante">
                      <div className="cuenta-linea">
                        <span>
                          {p.alias}{" "}
                          {p.pagado && <span className="badge badge-success">pagado</span>}
                        </span>
                        <strong>${p.subtotal.toFixed(2)}</strong>
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
                </div>
              ))}
            </div>

            <div className="modal-actions">
              {onDividir && (
                <button className="btn-secondary" onClick={onDividir} disabled={procesando}>
                  Dividir cuenta
                </button>
              )}
              <button
                className="btn-primary"
                onClick={cerrarCuenta}
                disabled={procesando || cuenta.total === 0}
              >
                {procesando ? "Procesando..." : "Cerrar cuenta"}
              </button>
            </div>
            <p className="muted small">
              Al cerrar la cuenta la mesa sigue ocupada: se puede abrir una nueva cuenta.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
