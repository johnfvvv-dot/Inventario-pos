/**
 * Utilidades para interpretar el texto combinado de un pago mixto.
 *
 * El backend lo guarda como:
 *   "Mixto: Efectivo ($15000.00) + Transferencia ($13400.00)"
 *
 * El Historial muestra solo el badge "mixto" y usa esta utilidad para el
 * tooltip; los tickets y su descarga muestran el desglose completo.
 */

import { formatearPrecio } from "./format";

export interface PagoDetalle {
  /** Identificador interno: efectivo | tarjeta | transferencia. */
  forma: string;
  /** Nombre visible: Efectivo | Tarjeta | Transferencia. */
  etiqueta: string;
  monto: number;
}

const ETIQUETAS: Record<string, string> = {
  efectivo: "Efectivo",
  tarjeta: "Tarjeta",
  transferencia: "Transferencia",
};

export const etiquetaFormaPago = (forma?: string | null): string => {
  const clave = (forma || "").trim().toLowerCase();
  if (!clave) return "";
  return ETIQUETAS[clave] || clave.charAt(0).toUpperCase() + clave.slice(1);
};

/** true cuando el texto guardado corresponde a un pago combinado. */
export const esPagoMixto = (formaPago?: string | null): boolean =>
  (formaPago || "").trim().toLowerCase().startsWith("mixto");

/** Extrae los métodos y montos del texto "Mixto: ..." del backend. */
export const parsearPagoMixto = (formaPago?: string | null): PagoDetalle[] => {
  const texto = (formaPago || "").trim();
  if (!esPagoMixto(texto)) return [];

  const detalle = texto.replace(/^mixto:\s*/i, "");
  const pagos: PagoDetalle[] = [];
  const regex = /([A-Za-zÁÉÍÓÚáéíóúÑñ]+)\s*\(\$([\d.,]+)\)/g;
  let match = regex.exec(detalle);
  while (match) {
    const forma = match[1].toLowerCase();
    // El backend usa punto decimal y dos dígitos (15000.00); las comas se
    // descartan por compatibilidad con formatos que separan miles.
    const monto = Number(match[2].replace(/,/g, ""));
    if (Number.isFinite(monto)) {
      pagos.push({ forma, etiqueta: etiquetaFormaPago(forma), monto });
    }
    match = regex.exec(detalle);
  }
  return pagos;
};

/** Texto legible: "Efectivo ($15.000) + Transferencia ($13.400)". */
export const formatearDetallePago = (pagos: PagoDetalle[]): string =>
  pagos
    .map((pago) => `${pago.etiqueta} (${formatearPrecio(pago.monto)})`)
    .join(" + ");
