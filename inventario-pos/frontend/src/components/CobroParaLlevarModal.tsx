/**
 * Cobro inmediato de una venta "Para llevar".
 *
 * A diferencia de la cuenta de una mesa, este pedido no se guarda abierto:
 * se cobra en el momento con un método o con dos métodos combinados. El
 * desglose de pagos se envía al backend para registrarlo en caja, reportes,
 * tickets e historial sin duplicar la venta.
 */

import { useMemo, useState } from "react";
import { FORMAS_PAGO } from "../services/api";
import { formatearPrecio } from "../utils/format";
import Icon, { type NombreIcono } from "./Icon";

const ICONOS_PAGO: Record<string, NombreIcono> = {
  efectivo: "efectivo",
  tarjeta: "tarjeta",
  transferencia: "transferencia",
};

export interface ItemParaLlevar {
  nombre: string;
  cantidad: number;
  precio: number;
}

export interface PagoParaLlevar {
  forma_pago: string;
  monto: number;
}

interface Props {
  items: ItemParaLlevar[];
  total: number;
  /** Cliente asignado a la venta; "Mostrador" si no tiene alias. */
  cliente?: string | null;
  confirmar: (pagos: PagoParaLlevar[]) => void;
  onClose: () => void;
  procesando?: boolean;
  error?: string | null;
}

/** Permite solo números y hasta dos decimales. */
function limpiarMonto(valor: string): string {
  const limpio = valor.replace(/,/g, ".").replace(/[^\d.]/g, "");
  const [entero, ...resto] = limpio.split(".");
  const decimales = resto.join("").slice(0, 2);
  return resto.length > 0 ? `${entero}.${decimales}` : entero;
}

function redondear(valor: number): number {
  return Math.round(valor * 100) / 100;
}

export default function CobroParaLlevarModal({
  items,
  total,
  cliente,
  confirmar,
  onClose,
  procesando = false,
  error = null,
}: Props) {
  const [mixto, setMixto] = useState(false);
  const [formaSimple, setFormaSimple] = useState("efectivo");

  const [forma1, setForma1] = useState("efectivo");
  const [monto1, setMonto1] = useState("");
  const [forma2, setForma2] = useState("transferencia");
  const [monto2, setMonto2] = useState("");

  const cantidadProductos = useMemo(
    () => items.reduce((suma, item) => suma + item.cantidad, 0),
    [items]
  );

  const numero1 = Number(monto1 || 0) || 0;
  const numero2 = Number(monto2 || 0) || 0;
  const sumaMixto = redondear(numero1 + numero2);
  const diferencia = redondear(total - sumaMixto);

  const metodosDistintos = forma1 !== forma2;
  const mixtoValido =
    numero1 > 0 &&
    numero2 > 0 &&
    metodosDistintos &&
    Math.abs(sumaMixto - total) < 0.01;

  /** Al escribir el Monto 1 se completa el saldo restante en el Monto 2. */
  const cambiarMonto1 = (valor: string) => {
    const limpio = limpiarMonto(valor);
    setMonto1(limpio);
    const restante = redondear(total - Number(limpio || 0));
    setMonto2(restante > 0 ? restante.toFixed(2) : "0.00");
  };

  const cambiarForma1 = (valor: string) => {
    setForma1(valor);
    if (valor === forma2) {
      const alternativa = FORMAS_PAGO.find((f) => f.id !== valor);
      if (alternativa) setForma2(alternativa.id);
    }
  };

  const cambiarForma2 = (valor: string) => {
    setForma2(valor);
    if (valor === forma1) {
      const alternativa = FORMAS_PAGO.find((f) => f.id !== valor);
      if (alternativa) setForma1(alternativa.id);
    }
  };

  const activarMixto = () => {
    setMixto(true);
    // Sugerencia inicial: la mitad en cada método, siempre modificable.
    if (!monto1) {
      const mitad = redondear(total / 2);
      setMonto1(mitad.toFixed(2));
      setMonto2(redondear(total - mitad).toFixed(2));
    }
  };

  const cobrar = () => {
    if (procesando) return;
    if (!mixto) {
      confirmar([{ forma_pago: formaSimple, monto: redondear(total) }]);
      return;
    }
    if (!mixtoValido) return;
    confirmar([
      { forma_pago: forma1, monto: redondear(numero1) },
      { forma_pago: forma2, monto: redondear(numero2) },
    ]);
  };

  const mensajeValidacion = (): string | null => {
    if (!mixto) return null;
    if (!metodosDistintos) return "Elegí dos métodos de pago distintos.";
    if (numero1 <= 0) return "El Monto 1 debe ser mayor a cero.";
    if (numero2 <= 0) return "El Monto 2 debe ser mayor a cero.";
    if (Math.abs(diferencia) >= 0.01) {
      return diferencia > 0
        ? `Faltan ${formatearPrecio(diferencia)} para cubrir el total.`
        : `Sobran ${formatearPrecio(Math.abs(diferencia))} sobre el total.`;
    }
    return null;
  };

  const validacion = mensajeValidacion();

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-box modal-xl modal-para-llevar"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-head">
          <h3>Para Llevar</h3>
          <button
            className="btn-icon"
            onClick={onClose}
            title="Cerrar"
            disabled={procesando}
          >
            <Icon nombre="cerrar" size={15} />
          </button>
        </div>

        {error && <p className="error-msg">{error}</p>}

        <div className="cuenta-resumen para-llevar-resumen">
          <div className="cuenta-resumen-item">
            <span>
              <Icon nombre="pedidos" size={14} />
              Pedido actual
            </span>
            <strong>
              {cantidadProductos} producto{cantidadProductos === 1 ? "" : "s"}
            </strong>
            <span className="muted small">
              Cliente: {cliente || "Mostrador"}
            </span>
          </div>
          <div className="cuenta-resumen-item para-llevar-total">
            <span>Total a cobrar</span>
            <strong>{formatearPrecio(total)}</strong>
          </div>
        </div>

        <div className="cuenta-grupo cuenta-grupo--general para-llevar-detalle">
          <div className="cuenta-grupo-head">
            <div>
              <h4>Detalle del pedido</h4>
              <span className="muted small">
                {items.length} línea{items.length === 1 ? "" : "s"}
              </span>
            </div>
            <strong>{formatearPrecio(total)}</strong>
          </div>

          {items.length === 0 ? (
            <p className="empty-state">El pedido está vacío.</p>
          ) : (
            items.map((item, indice) => (
              <div className="cuenta-linea" key={`${item.nombre}-${indice}`}>
                <span>
                  {item.cantidad} × {item.nombre}
                </span>
                <strong>
                  {formatearPrecio(item.precio * item.cantidad)}
                </strong>
              </div>
            ))
          )}
        </div>

        {!mixto ? (
          <div className="para-llevar-pago">
            <h4>Forma de pago</h4>
            <div className="formas-pago">
              {FORMAS_PAGO.map((forma) => (
                <button
                  key={forma.id}
                  type="button"
                  className={`forma-pago${
                    formaSimple === forma.id ? " activa" : ""
                  }`}
                  onClick={() => setFormaSimple(forma.id)}
                  disabled={procesando}
                >
                  <Icon nombre={ICONOS_PAGO[forma.id]} size={18} />
                  {forma.label}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="pago-mixto">
            <div className="pago-mixto-bloque">
              <label htmlFor="pago-1-forma">Pago 1</label>
              <select
                id="pago-1-forma"
                value={forma1}
                onChange={(e) => cambiarForma1(e.target.value)}
                disabled={procesando}
              >
                {FORMAS_PAGO.map((forma) => (
                  <option key={forma.id} value={forma.id}>
                    {forma.label}
                  </option>
                ))}
              </select>
              <label htmlFor="pago-1-monto">Monto 1</label>
              <input
                id="pago-1-monto"
                type="text"
                inputMode="decimal"
                placeholder="0.00"
                value={monto1}
                onChange={(e) => cambiarMonto1(e.target.value)}
                disabled={procesando}
              />
            </div>

            <div className="pago-mixto-bloque">
              <label htmlFor="pago-2-forma">Pago 2</label>
              <select
                id="pago-2-forma"
                value={forma2}
                onChange={(e) => cambiarForma2(e.target.value)}
                disabled={procesando}
              >
                {FORMAS_PAGO.map((forma) => (
                  <option key={forma.id} value={forma.id}>
                    {forma.label}
                  </option>
                ))}
              </select>
              <label htmlFor="pago-2-monto">Monto 2</label>
              <input
                id="pago-2-monto"
                type="text"
                inputMode="decimal"
                placeholder="0.00"
                value={monto2}
                onChange={(e) => setMonto2(limpiarMonto(e.target.value))}
                disabled={procesando}
              />
            </div>

            <div className="pago-mixto-resumen">
              <span>
                Total: <strong>{formatearPrecio(total)}</strong>
              </span>
              <span>
                Suma: <strong>{formatearPrecio(sumaMixto)}</strong>
              </span>
              <span className={diferencia === 0 ? "ok" : "pendiente"}>
                {diferencia === 0
                  ? "Pago completo"
                  : diferencia > 0
                  ? `Falta ${formatearPrecio(diferencia)}`
                  : `Sobra ${formatearPrecio(Math.abs(diferencia))}`}
              </span>
            </div>

            {validacion && <p className="pago-mixto-error">{validacion}</p>}
          </div>
        )}

        <div className="modal-actions para-llevar-acciones">
          <button
            className="btn-secondary"
            onClick={() => setMixto((actual) => !actual)}
            disabled={procesando}
          >
            <Icon nombre={mixto ? "transferencia" : "filtrar"} size={16} />
            {mixto ? "Volver a un método" : "Pago mixto / 2 métodos"}
          </button>
          <button
            className="btn-primary"
            onClick={cobrar}
            disabled={procesando || (mixto && !mixtoValido)}
          >
            <Icon nombre="check" size={16} />
            {procesando
              ? "Procesando..."
              : mixto
              ? "Confirmar cobro"
              : "Cobrar cuenta"}
          </button>
        </div>
      </div>
    </div>
  );
}
