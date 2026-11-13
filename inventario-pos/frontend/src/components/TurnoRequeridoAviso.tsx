/** Aviso reutilizable cuando no hay un turno de caja abierto. */

import Icon from "./Icon";

interface Props {
  onAbrir: () => void;
}

export default function TurnoRequeridoAviso({ onAbrir }: Props) {
  return (
    <div className="aviso-panel aviso-turno">
      <span className="aviso-icono aviso-icono--azul">
        <Icon nombre="reloj" size={18} />
      </span>
      <div className="aviso-texto">
        <strong>No hay un turno de caja abierto.</strong> Abre un turno para
        ocupar mesas y tomar pedidos.
      </div>
      <div className="aviso-acciones">
        <button className="btn-primary btn-small" onClick={onAbrir}>
          <Icon nombre="caja" size={14} />
          Abrir turno
        </button>
      </div>
    </div>
  );
}
