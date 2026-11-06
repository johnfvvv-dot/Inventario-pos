/** Aviso reutilizable cuando no hay un turno de caja abierto. */

interface Props {
  onAbrir: () => void;
}

export default function TurnoRequeridoAviso({ onAbrir }: Props) {
  return (
    <div className="aviso-panel aviso-turno">
      <div className="aviso-texto">
        <strong>No hay un turno de caja abierto.</strong> Abre un turno para
        ocupar mesas y tomar pedidos.
      </div>
      <div className="aviso-acciones">
        <button className="btn-primary btn-small" onClick={onAbrir}>
          Abrir turno
        </button>
      </div>
    </div>
  );
}
