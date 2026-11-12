/**
 * Ventana emergente con la cuenta actual de una mesa o barra.
 *
 * - La Cuenta General y cada Cuenta de Cliente tienen la misma estructura.
 * - "Cobrar Cuenta General" cobra solo los pedidos generales.
 * - "Cobrar cuenta [cliente]" cobra solo la parte de un cliente.
 * - "Cobrar cuenta total" cobra la Cuenta General y todas las partes
 *   pendientes, con opción de liberar el lugar.
 */

import { useEffect, useState } from "react";
import { api } from "../services/api";
import { formatearFechaHora, formatearPrecio } from "../utils/format";
import CobroModal from "./CobroModal";

interface LineaItem {
  producto_id: number;
  producto_nombre: string;
  cantidad: number;
  subtotal: number;
  participante_item_id?: number | null;
  pedido_id?: number | null;
}

interface Participante {
  id: number;
  alias: string;
  subtotal: number;
  pagado: boolean;
  forma_pago?: string | null;
  fecha_pago?: string | null;
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
  estado: string;
  participante_id?: number | null;
  alias?: string | null;
  items: LineaItem[];
}

interface Cuenta {
  mesa_id: number;
  mesa_numero: number;
  estado_mesa: string;
  total: number;
  total_general: number;
  total_divisiones: number;
  pedidos: Pedido[];
  divisiones: Division[];
}

type Cobro =
  | { tipo: "general"; total: number }
  | { tipo: "alias"; participanteId: number; alias: string; total: number }
  | { tipo: "cuenta"; total: number };

interface Props {
  mesaId: number;
  /** Si se indica, la cuenta es la agregada de la barra con ese numero */
  barraNumero?: number | null;
  onClose: () => void;
  onDividir?: () => void;
  onTransferir?: () => void;
  onActualizado?: () => void;
}

export default function CuentaModal({
  mesaId,
  barraNumero = null,
  onClose,
  onDividir,
  onTransferir,
  onActualizado,
}: Props) {
  const [cuenta, setCuenta] = useState<Cuenta | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [procesando, setProcesando] = useState(false);
  const [errorCobro, setErrorCobro] = useState<string | null>(null);
  const [cobro, setCobro] = useState<Cobro | null>(null);

  const esBarra = barraNumero != null;
  const etiqueta = esBarra ? "barra" : "mesa";
  const usuario = JSON.parse(localStorage.getItem("user") || "{}");
  const usuarioId: number = usuario?.id || 1;
  const nombreUsuario: string =
    usuario?.nombre || usuario?.alias || "el usuario actual";

  const cargar = async () => {
    try {
      const data: any =
        barraNumero != null
          ? await api.getCuentaBarra(barraNumero)
          : await api.getCuentaMesa(mesaId);
      setCuenta(data);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    }
  };

  useEffect(() => {
    const timer = setTimeout(cargar, 0);
    return () => clearTimeout(timer);
  }, [mesaId, barraNumero]);

  const confirmarCobro = async (formaPago: string, liberar = false) => {
    if (!cobro) return;
    setProcesando(true);
    setErrorCobro(null);
    setError(null);
    setMensaje(null);
    try {
      if (cobro.tipo === "general") {
        if (barraNumero != null) {
          await api.cerrarGeneralBarra(
            barraNumero,
            formaPago,
            usuarioId,
            true
          );
        } else {
          await api.cerrarGeneralMesa(mesaId, formaPago, usuarioId, true);
        }
        setMensaje(
          `Cuenta General cobrada con ${formaPago} por ${nombreUsuario}. Las cuentas de clientes pendientes, si existen, siguen abiertas.`
        );
      } else if (cobro.tipo === "alias") {
        await api.pagarParticipante(
          cobro.participanteId,
          formaPago,
          usuarioId
        );
        setMensaje(
          `Cuenta de cliente "${cobro.alias}" cobrada con ${formaPago} por ${nombreUsuario}.`
        );
      } else {
        if (barraNumero != null) {
          await api.cerrarCuentaBarra(
            barraNumero,
            liberar,
            formaPago,
            usuarioId
          );
        } else {
          await api.cerrarCuentaMesa(
            mesaId,
            liberar,
            formaPago,
            usuarioId
          );
        }
        setCobro(null);
        onActualizado?.();
        onClose();
        return;
      }
      setCobro(null);
      await cargar();
      onActualizado?.();
    } catch (err: any) {
      setErrorCobro(err.message);
    } finally {
      setProcesando(false);
    }
  };

  const cerrarCobro = () => {
    if (procesando) return;
    setCobro(null);
    setErrorCobro(null);
  };

  const lineasGenerales = cuenta
    ? cuenta.pedidos.flatMap((pedido) =>
        pedido.items.map((item, indice) => ({
          ...item,
          pedidoId: pedido.id,
          indice,
        }))
      )
    : [];

  const clientes = cuenta
    ? cuenta.divisiones.flatMap((division) =>
        division.participantes.map((participante) => ({
          ...participante,
          divisionId: division.id,
        }))
      )
    : [];

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box modal-xl" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3>
            {cuenta
              ? `Cuenta ${esBarra ? "Barra" : "Mesa"} ${cuenta.mesa_numero}`
              : "Cargando cuenta..."}
          </h3>
          <button className="btn-icon" onClick={onClose} title="Cerrar">
            ×
          </button>
        </div>

        {error && <p className="error-msg">{error}</p>}
        {mensaje && <p className="success-msg">{mensaje}</p>}

        {cuenta && (
          <>
            <div className="cuenta-resumen">
              <div className="cuenta-resumen-item">
                <span>Cuenta General</span>
                <strong>{formatearPrecio(cuenta.total_general || 0)}</strong>
              </div>
              <div className="cuenta-resumen-item">
                <span>Cuentas de clientes pendientes</span>
                <strong>{formatearPrecio(cuenta.total_divisiones || 0)}</strong>
              </div>
              <div className="cuenta-total">
                <span>Total pendiente</span>
                <strong>{formatearPrecio(cuenta.total)}</strong>
              </div>
            </div>

            <div className="cuenta-scroll">
              {cuenta.pedidos.length === 0 && clientes.length === 0 && (
                <p className="empty-state">La cuenta está vacía.</p>
              )}

              <div className="cuenta-grupo">
                <div className="cuenta-grupo-head">
                  <div>
                    <h4>Cuenta General de {esBarra ? "la barra" : "la mesa"}</h4>
                    <span className="muted small">
                      {cuenta.pedidos.length} pedido(s) ·{" "}
                      {formatearPrecio(cuenta.total_general || 0)}
                    </span>
                  </div>
                  {cuenta.total_general > 0 && (
                    <button
                      className="btn-primary btn-small cuenta-cobro-btn"
                      onClick={() =>
                        setCobro({
                          tipo: "general",
                          total: cuenta.total_general,
                        })
                      }
                      disabled={procesando}
                    >
                      Cobrar Cuenta General
                    </button>
                  )}
                </div>

                {lineasGenerales.length === 0 ? (
                  <p className="muted small">
                    Sin productos pendientes en la Cuenta General.
                  </p>
                ) : (
                  lineasGenerales.map((item, indice) => (
                    <div
                      className="cuenta-linea"
                      key={`general-${item.pedidoId}-${
                        item.producto_id ?? indice
                      }-${item.indice}`}
                    >
                      <span>
                        {item.cantidad} × {item.producto_nombre}
                      </span>
                      <strong>{formatearPrecio(item.subtotal)}</strong>
                    </div>
                  ))
                )}
              </div>

              {clientes.map((cliente) => (
                <div
                  key={`cliente-${cliente.id}`}
                  className="cuenta-grupo"
                >
                  <div className="cuenta-grupo-head">
                    <div>
                      <h4>
                        Cuenta de cliente {cliente.alias}{" "}
                        {cliente.pagado && (
                          <span className="badge badge-success">pagado</span>
                        )}
                      </h4>
                      <span className="muted small">
                        {cliente.items.length} producto(s) ·{" "}
                        {formatearPrecio(cliente.subtotal)}
                      </span>
                    </div>
                    {!cliente.pagado && (
                      <button
                        className="btn-primary btn-small cuenta-cobro-btn"
                        title={`Cobrar solo la cuenta de ${cliente.alias}`}
                        onClick={() =>
                          setCobro({
                            tipo: "alias",
                            participanteId: cliente.id,
                            alias: cliente.alias,
                            total: cliente.subtotal,
                          })
                        }
                        disabled={procesando}
                      >
                        Cobrar cuenta {cliente.alias}
                      </button>
                    )}
                  </div>

                  {cliente.pagado && (
                    <span className="cuenta-pago-info">
                      Pagado con {cliente.forma_pago || "—"}
                      {cliente.fecha_pago
                        ? ` · ${formatearFechaHora(cliente.fecha_pago)}`
                        : ""}
                    </span>
                  )}

                  {cliente.items.length === 0 ? (
                    <p className="muted small">
                      Sin productos en esta cuenta de cliente.
                    </p>
                  ) : (
                    cliente.items.map((item, indice) => (
                      <div
                        className="cuenta-linea"
                        key={`cliente-${cliente.id}-${
                          item.producto_id ?? indice
                        }-${indice}`}
                      >
                        <span>
                          {item.cantidad} × {item.producto_nombre}
                        </span>
                        <strong>{formatearPrecio(item.subtotal)}</strong>
                      </div>
                    ))
                  )}
                </div>
              ))}
            </div>

            <div className="modal-actions modal-actions-wrap">
              {onDividir && (
                <button
                  className="btn-secondary"
                  onClick={onDividir}
                  disabled={procesando}
                >
                  Dividir cuenta
                </button>
              )}
              {onTransferir && (
                <button
                  className="btn-secondary"
                  onClick={onTransferir}
                  disabled={procesando}
                >
                  Transferir cuenta
                </button>
              )}
              <button
                className="btn-primary"
                onClick={() =>
                  setCobro({
                    tipo: "cuenta",
                    total: cuenta.total,
                  })
                }
                disabled={procesando || cuenta.total === 0}
              >
                Cobrar cuenta total
              </button>
            </div>

            <p className="muted small">
              "Cobrar Cuenta General" cobra únicamente los pedidos generales.
              "Cobrar cuenta [Nombre del cliente]" cobra solo la parte de un
              cliente. "Cobrar cuenta total" cobra la Cuenta General y todas las
              cuentas de clientes pendientes.
            </p>
          </>
        )}

        {cobro && (
          <CobroModal
            titulo={
              cobro.tipo === "general"
                ? "Cobrar Cuenta General"
                : cobro.tipo === "alias"
                ? `Cobrar cuenta de "${cobro.alias}"`
                : `Cobrar cuenta total de la ${etiqueta}`
            }
            total={cobro.total}
            extra={
              cobro.tipo === "general"
                ? "Solo se cobra la Cuenta General. Las cuentas de clientes pendientes, si existen, permanecen abiertas."
                : cobro.tipo === "alias"
                ? `Se registra el pago de ${cobro.alias} con ${nombreUsuario}.`
                : "Se cobrarán la Cuenta General y todas las cuentas de clientes pendientes. \"Aceptar\" mantiene el lugar ocupado; \"Aceptar y liberar mesa\" lo deja disponible."
            }
            procesando={procesando}
            error={errorCobro}
            confirmar={(formaPago) => confirmarCobro(formaPago, false)}
            confirmarLiberar={
              cobro.tipo === "cuenta"
                ? (formaPago) => confirmarCobro(formaPago, true)
                : undefined
            }
            textoConfirmar="Aceptar"
            textoLiberar="Aceptar y liberar mesa"
            onClose={cerrarCobro}
          />
        )}
      </div>
    </div>
  );
}
