"""Ciclo de vida de los clientes individuales.

Un cliente individual es una fila de ``mesas`` con ``tipo="individual"``:
no ocupa una mesa ni una barra física, pero mantiene el mismo flujo de
pedidos, división, cobro y cierre.

Cuando su cuenta queda saldada la tarjeta debe desaparecer de la vista
activa. Para no romper las claves foráneas del historial (pedidos y
divisiones conservan ``mesa_id``), la fila no se borra: se archiva con
``estado="cerrada"`` y se excluye del listado. Así Historial, Corte y
Reportes siguen mostrando ``Individual`` y el nombre del cliente.
"""

from typing import Optional

from sqlalchemy.orm import Session

from app.models import Mesa

ESTADO_ARCHIVADO = "cerrada"


def es_cliente_individual(mesa: Optional[Mesa]) -> bool:
    """True si la fila representa a un cliente individual."""
    return bool(mesa) and (mesa.tipo or "mesa") == "individual"


def esta_activo(mesa: Optional[Mesa]) -> bool:
    """True si el cliente individual debe mostrarse como cuenta activa."""
    return es_cliente_individual(mesa) and mesa.estado != ESTADO_ARCHIVADO


def archivar_cliente_individual(db: Session, mesa: Optional[Mesa]) -> bool:
    """Oculta la tarjeta de un cliente individual conservando su historial.

    Devuelve True si la fila era un cliente individual y quedó archivada.
    """
    if not es_cliente_individual(mesa):
        return False
    mesa.estado = ESTADO_ARCHIVADO
    mesa.fecha_ocupacion = None
    db.flush()
    return True
