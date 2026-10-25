/**
 * Formato único de moneda para toda la aplicación.
 *
 * Reglas:
 *  - Separador de miles con punto (formato español: 3.800).
 *  - Sin decimales (se redondea al entero más cercano).
 *  - Prefijo "$" sin espacio: "$3.800".
 */

export const formatearPrecio = (valor: number | null | undefined): string => {
  const numero = Number(valor);
  const seguro = Number.isFinite(numero) ? Math.round(numero) : 0;
  return `$${seguro.toLocaleString("es-CO", { maximumFractionDigits: 0 })}`;
};

/** Número con separador de miles y sin decimales, sin el prefijo "$". */
export const formatearNumero = (valor: number | null | undefined): string => {
  const numero = Number(valor);
  const seguro = Number.isFinite(numero) ? Math.round(numero) : 0;
  return seguro.toLocaleString("es-CO", { maximumFractionDigits: 0 });
};
