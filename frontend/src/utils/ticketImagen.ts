/**
 * Genera la imagen PNG de un ticket interno en el navegador.
 *
 * Los tickets no se guardan en el servidor: este dibujo se crea al pulsar
 * "Descargar imagen" y se entrega como descarga local.
 */

import { formatearFechaHora, formatearPrecio } from "./format";

export interface TicketImagenItem {
  nombre: string;
  cantidad: number;
  precio_unitario: number;
  subtotal: number;
}

export interface TicketImagen {
  folio: string;
  mesa: string;
  fecha_ocupacion: string;
  fecha_pago: string;
  alias?: string | null;
  forma_pago: string;
  items: TicketImagenItem[];
}

const ETIQUETAS_PAGO: Record<string, string> = {
  efectivo: "Efectivo",
  tarjeta: "Tarjeta",
  transferencia: "Transferencia",
};

interface Linea {
  izquierda?: string;
  derecha?: string;
  font?: string;
  color?: string;
  centrada?: boolean;
  margenArriba?: number;
  separador?: boolean;
  margenAbajo?: number;
}

const ANCHO = 440;
const PADDING = 24;

const FUENTE_TITULO = "700 19px 'Segoe UI', Arial, sans-serif";
const FUENTE_BASE = "13px 'Segoe UI', Arial, sans-serif";
const FUENTE_NEGRITA = "600 13px 'Segoe UI', Arial, sans-serif";
const FUENTE_MINI = "11px 'Segoe UI', Arial, sans-serif";
const FUENTE_MINI_NEGRITA = "600 10px 'Segoe UI', Arial, sans-serif";

function tamanoFuente(font: string): number {
  const coincidencia = /(\d+(?:\.\d+)?)px/.exec(font);
  return coincidencia ? Number(coincidencia[1]) : 13;
}

function envolverTexto(
  ctx: CanvasRenderingContext2D,
  texto: string,
  anchoMaximo: number
): string[] {
  const palabras = String(texto || "").split(/\s+/).filter(Boolean);
  if (!palabras.length) return [""];

  const partes: string[] = [];
  let actual = palabras[0];

  for (let i = 1; i < palabras.length; i++) {
    const prueba = `${actual} ${palabras[i]}`;
    if (ctx.measureText(prueba).width <= anchoMaximo) {
      actual = prueba;
    } else {
      partes.push(actual);
      actual = palabras[i];
    }
  }
  partes.push(actual);
  return partes;
}

function crearCanvasTicket(ticket: TicketImagen, nombreNegocio: string): HTMLCanvasElement {
  const canvas = document.createElement("canvas");
  canvas.width = ANCHO * 2;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("El navegador no pudo preparar la imagen");

  ctx.scale(2, 2);

  const lineas: Linea[] = [];
  const anchoUtil = ANCHO - PADDING * 2;

  const agregarPar = (etiqueta: string, valor: string) => {
    ctx.font = FUENTE_BASE;
    const partes = envolverTexto(ctx, valor, anchoUtil - 110);
    partes.forEach((parte, indice) => {
      lineas.push({
        izquierda: indice === 0 ? etiqueta : "",
        derecha: parte,
        font: FUENTE_BASE,
        margenArriba: indice === 0 ? 3 : 0,
      });
    });
  };

  lineas.push({
    izquierda: nombreNegocio,
    font: FUENTE_TITULO,
    centrada: true,
    margenArriba: 0,
  });
  lineas.push({
    izquierda: "COMPROBANTE INTERNO",
    font: FUENTE_MINI,
    color: "#6b7785",
    centrada: true,
    margenArriba: 3,
  });
  lineas.push({ separador: true, margenArriba: 12, margenAbajo: 5 });

  agregarPar("Folio", ticket.folio);
  agregarPar("Mesa", ticket.mesa);
  if (ticket.alias) agregarPar("Cliente", ticket.alias);
  agregarPar("Ocupación", formatearFechaHora(ticket.fecha_ocupacion));
  agregarPar("Pago", formatearFechaHora(ticket.fecha_pago));

  lineas.push({ separador: true, margenArriba: 10, margenAbajo: 4 });
  lineas.push({
    izquierda: "PRODUCTOS",
    font: FUENTE_MINI_NEGRITA,
    color: "#6b7785",
    margenArriba: 2,
  });

  for (const item of ticket.items) {
    const detalle = `${item.cantidad} × ${formatearPrecio(item.precio_unitario)}`;
    ctx.font = FUENTE_BASE;
    const anchoDetalle = ctx.measureText(detalle).width;
    const partes = envolverTexto(
      ctx,
      item.nombre,
      anchoUtil - anchoDetalle - 12
    );
    partes.forEach((parte, indice) => {
      lineas.push({
        izquierda: parte,
        derecha: indice === 0 ? detalle : undefined,
        font: FUENTE_BASE,
        margenArriba: indice === 0 ? 6 : 0,
      });
    });
  }

  lineas.push({ separador: true, margenArriba: 10, margenAbajo: 5 });
  lineas.push({
    izquierda: "Forma de pago",
    derecha: ETIQUETAS_PAGO[ticket.forma_pago] || ticket.forma_pago,
    font: FUENTE_NEGRITA,
    margenArriba: 2,
  });
  lineas.push({
    izquierda: "Documento interno de control.",
    font: FUENTE_MINI,
    color: "#6b7785",
    centrada: true,
    margenArriba: 14,
  });
  lineas.push({
    izquierda: "No válido como factura.",
    font: FUENTE_MINI,
    color: "#6b7785",
    centrada: true,
    margenArriba: 1,
  });

  let alto = PADDING;
  for (const linea of lineas) {
    if (linea.separador) {
      alto += (linea.margenArriba ?? 8) + 1 + (linea.margenAbajo ?? 8);
    } else {
      alto += (linea.margenArriba ?? 2) + tamanoFuente(linea.font || FUENTE_BASE) * 1.35;
    }
  }
  alto = Math.ceil(alto + PADDING - 2);

  // Si el ticket es muy largo (muchos productos), se reduce la escala para
  // no superar el límite de altura del canvas en los navegadores.
  const escala = alto * 2 > 30000 ? 1 : 2;
  canvas.width = ANCHO * escala;
  canvas.height = alto * escala;
  ctx.setTransform(escala, 0, 0, escala, 0, 0);

  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, ANCHO, alto);
  ctx.textBaseline = "alphabetic";

  let y = PADDING;
  for (const linea of lineas) {
    if (linea.separador) {
      y += linea.margenArriba ?? 8;
      ctx.strokeStyle = "#c9d2db";
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(PADDING, y + 0.5);
      ctx.lineTo(ANCHO - PADDING, y + 0.5);
      ctx.stroke();
      ctx.setLineDash([]);
      y += (linea.margenAbajo ?? 8) + 1;
      continue;
    }

    const font = linea.font || FUENTE_BASE;
    const tamano = tamanoFuente(font);
    y += linea.margenArriba ?? 2;

    ctx.font = font;
    ctx.fillStyle = linea.color || "#1c2833";
    const base = y + tamano;

    if (linea.centrada) {
      ctx.textAlign = "center";
      ctx.fillText(linea.izquierda || "", ANCHO / 2, base);
      ctx.textAlign = "left";
    } else {
      ctx.fillText(linea.izquierda || "", PADDING, base);
      if (linea.derecha) {
        ctx.textAlign = "right";
        ctx.fillText(linea.derecha, ANCHO - PADDING, base);
        ctx.textAlign = "left";
      }
    }

    y += tamano * 1.35;
  }

  return canvas;
}

export function descargarTicketPng(
  ticket: TicketImagen,
  nombreNegocio: string
): void {
  const canvas = crearCanvasTicket(ticket, nombreNegocio);
  canvas.toBlob((blob) => {
    if (!blob) return;
    const url = URL.createObjectURL(blob);
    const enlace = document.createElement("a");
    enlace.href = url;
    enlace.download = `ticket-${ticket.folio.replace(/[^a-zA-Z0-9_-]/g, "-")}.png`;
    document.body.appendChild(enlace);
    enlace.click();
    enlace.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1500);
  }, "image/png");
}
