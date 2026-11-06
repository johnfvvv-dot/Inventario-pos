/** Tipos compartidos del turno de caja. */

export interface TotalesTurno {
  efectivo: number;
  tarjeta: number;
  transferencia: number;
  total: number;
  operaciones: number;
}

export interface TurnoCaja {
  id: number;
  usuario_nombre: string;
  fecha_apertura: string;
  fecha_cierre: string | null;
  observaciones: string | null;
  estado: string;
  fondo_inicial: number;
  totales: TotalesTurno;
  ganancia: number;
}
