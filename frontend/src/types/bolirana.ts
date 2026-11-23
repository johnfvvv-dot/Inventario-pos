/** Tipos compartidos del módulo de Bolirana. */

export interface ConsumoBolirana {
  producto_id: number;
  producto_nombre: string;
  cantidad: number;
  precio_unitario: number;
  subtotal: number;
}

export interface ParticipanteBolirana {
  id: number;
  tipo: "mesa" | "barra" | "alias";
  mesa_id?: number | null;
  barra_numero?: number | null;
  alias?: string | null;
  origen_tipo?: "mesa" | "barra" | "individual" | null;
  origen_mesa_id?: number | null;
  origen_barra_numero?: number | null;
  origen_etiqueta?: string | null;
  equipo?: string | null;
  etiqueta: string;
  es_perdedor: boolean;
  monto_asignado: number;
  estado_pago: string;
}

export interface PartidaBolirana {
  id: number;
  bolirana_id: number;
  estado: string;
  modalidad: "directo" | "equipos";
  fecha_inicio: string;
  fecha_fin?: string | null;
  total_bebidas: number;
  participantes: ParticipanteBolirana[];
  consumo: ConsumoBolirana[];
}

export interface Bolirana {
  id: number;
  nombre: string;
  activa: boolean;
  creado_en?: string | null;
  estado: "disponible" | "en_partida";
  partida?: PartidaBolirana | null;
}
