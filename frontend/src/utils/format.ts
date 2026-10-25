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

/**
 * Interpreta una fecha del backend como hora local.
 *
 * El servidor guarda horas locales "naive" (sin zona horaria). Si el texto
 * no trae zona, se construye con los componentes tal cual para evitar que
 * el navegador lo interprete como UTC (que era el origen del desfase).
 */
const parsearFecha = (valor: string): Date => {
  const soloFecha = /^(\d{4})-(\d{2})-(\d{2})$/.exec(valor);
  if (soloFecha) {
    return new Date(
      Number(soloFecha[1]),
      Number(soloFecha[2]) - 1,
      Number(soloFecha[3])
    );
  }

  const sinZona =
    /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2})(?:\.(\d{1,6}))?)?$/.exec(
      valor
    );
  if (sinZona) {
    const micros = (sinZona[7] || "").slice(0, 3).padEnd(3, "0");
    return new Date(
      Number(sinZona[1]),
      Number(sinZona[2]) - 1,
      Number(sinZona[3]),
      Number(sinZona[4]),
      Number(sinZona[5]),
      Number(sinZona[6] || 0),
      Number(micros || 0)
    );
  }

  return new Date(valor);
};

/**
 * Nombre completo del día de la semana en español (Lunes...Domingo).
 *
 * Se calcula con la fecha tal como la guarda el servidor (hora local), sin
 * convertirla a UTC, para que un turno abierto un sábado por la noche siga
 * mostrando "Sábado" aunque se cierre el domingo.
 */
const DIAS_SEMANA = [
  "Domingo",
  "Lunes",
  "Martes",
  "Miércoles",
  "Jueves",
  "Viernes",
  "Sábado",
];

export const formatearDiaSemana = (
  valor: string | Date | null | undefined
): string => {
  if (!valor) return "-";

  const fecha = typeof valor === "string" ? parsearFecha(valor) : valor;
  if (Number.isNaN(fecha.getTime())) return "-";

  return DIAS_SEMANA[fecha.getDay()];
};

/**
 * Fecha y hora local con formato DD/MM/YYYY, HH:mm:ss.
 * Ejemplo: "25/10/2026, 22:52:46".
 */
export const formatearFechaHora = (
  valor: string | Date | null | undefined
): string => {
  if (!valor) return "-";

  const fecha = typeof valor === "string" ? parsearFecha(valor) : valor;
  if (Number.isNaN(fecha.getTime())) return "-";

  const dia = String(fecha.getDate()).padStart(2, "0");
  const mes = String(fecha.getMonth() + 1).padStart(2, "0");
  const anio = fecha.getFullYear();
  const hora = String(fecha.getHours()).padStart(2, "0");
  const minuto = String(fecha.getMinutes()).padStart(2, "0");
  const segundo = String(fecha.getSeconds()).padStart(2, "0");

  return `${dia}/${mes}/${anio}, ${hora}:${minuto}:${segundo}`;
};

/** Fecha local en formato YYYY-MM-DD (para nombres de archivos). */
export const fechaParaArchivo = (valor: Date = new Date()): string => {
  const dia = String(valor.getDate()).padStart(2, "0");
  const mes = String(valor.getMonth() + 1).padStart(2, "0");
  return `${valor.getFullYear()}-${mes}-${dia}`;
};
