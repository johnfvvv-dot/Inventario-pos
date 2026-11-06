"""Reglas compartidas de turnos de caja.

Centraliza la validación que exige un turno abierto antes de operar mesas o
pedidos, de modo que todos los endpoints respondan con el mismo código y
mensaje.
"""

from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import TurnoCaja

MENSAJE_TURNO_REQUERIDO = (
    "Operación no permitida: Debe abrir un turno de caja antes de "
    "atender mesas o tomar pedidos"
)

MENSAJE_CIERRE_BLOQUEADO = (
    "No se puede cerrar el turno: hay mesas ocupadas o pedidos pendientes "
    "de pago. Libere las mesas antes de continuar"
)


def turno_abierto(db: Session) -> Optional[TurnoCaja]:
    """Devuelve el turno de caja abierto más reciente, si existe."""
    return (
        db.query(TurnoCaja)
        .filter(TurnoCaja.estado == "abierto")
        .order_by(TurnoCaja.id.desc())
        .first()
    )


def exigir_turno_abierto(db: Session) -> TurnoCaja:
    """Corta la operación con HTTP 403 si no hay un turno abierto."""
    turno = turno_abierto(db)
    if turno is None:
        raise HTTPException(
            status_code=403,
            detail=MENSAJE_TURNO_REQUERIDO,
        )
    return turno
