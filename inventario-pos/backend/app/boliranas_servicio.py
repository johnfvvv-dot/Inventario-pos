"""Reglas compartidas del módulo de Bolirana.

La partida activa es la fuente de verdad del candado: mientras exista una
partida en curso, las mesas/barras participantes no pueden cobrarse ni
cerrarse, y el turno de caja tampoco puede cerrarse.
"""

from typing import Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import (
    Bolirana,
    ConfiguracionNegocio,
    Mesa,
    ParticipanteBolirana,
    PartidaBolirana,
)


def modulo_habilitado(db: Session) -> bool:
    """True si el Administrador habilitó el módulo de Bolirana.

    Cuando está desactivado no se aplican candados de cierre ni se muestran
    avisos en Mesas, aunque quede una partida antigua sin liquidar.
    """
    config = (
        db.query(ConfiguracionNegocio)
        .filter(ConfiguracionNegocio.id == 1)
        .first()
    )
    return bool(config and config.modulo_bolirana)


def partida_activa(
    db: Session, bolirana_id: int
) -> Optional[PartidaBolirana]:
    """Partida en curso de una bolirana (una máquina solo tiene una)."""
    return (
        db.query(PartidaBolirana)
        .filter(
            PartidaBolirana.bolirana_id == bolirana_id,
            PartidaBolirana.estado == "en_curso",
        )
        .order_by(PartidaBolirana.id.desc())
        .first()
    )


def _participacion_activa(
    db: Session, condiciones
) -> Optional[Tuple[PartidaBolirana, Bolirana]]:
    fila = (
        db.query(PartidaBolirana, Bolirana)
        .join(
            ParticipanteBolirana,
            ParticipanteBolirana.partida_id == PartidaBolirana.id,
        )
        .join(Bolirana, Bolirana.id == PartidaBolirana.bolirana_id)
        # ``condiciones`` es una sola expresión con OR/AND; pasarla como un
        # único argumento evita que SQLAlchemy la separe y convierta los OR
        # en AND al desempaquetarla.
        .filter(PartidaBolirana.estado == "en_curso", condiciones)
        .order_by(PartidaBolirana.id.desc())
        .first()
    )
    return (fila[0], fila[1]) if fila else None


def participacion_activa_mesa(
    db: Session, mesa: Mesa
) -> Optional[Tuple[PartidaBolirana, Bolirana]]:
    """Partida activa en la que participa una mesa o una barra completa.

    Incluye tanto la participación directa como los alias vinculados a la
    cuenta de la mesa, la barra o el cliente individual.
    """
    if (mesa.tipo or "mesa") == "barra" and mesa.grupo:
        numero_barra = mesa.numero // 100
        ids_grupo = [
            fila[0]
            for fila in db.query(Mesa.id).filter(Mesa.grupo == mesa.grupo).all()
        ]
        return _participacion_activa(
            db,
            (
                (ParticipanteBolirana.tipo == "barra")
                & (ParticipanteBolirana.barra_numero == numero_barra)
            )
            | (
                (ParticipanteBolirana.tipo == "mesa")
                & (ParticipanteBolirana.mesa_id.in_(ids_grupo))
            )
            | (
                (ParticipanteBolirana.tipo == "alias")
                & (ParticipanteBolirana.origen_barra_numero == numero_barra)
            )
            | (
                (ParticipanteBolirana.tipo == "alias")
                & (ParticipanteBolirana.origen_mesa_id.in_(ids_grupo))
            ),
        )
    return _participacion_activa(
        db,
        (
            (ParticipanteBolirana.tipo == "mesa")
            & (ParticipanteBolirana.mesa_id == mesa.id)
        )
        | (
            (ParticipanteBolirana.tipo == "alias")
            & (ParticipanteBolirana.origen_mesa_id == mesa.id)
        ),
    )


def participacion_activa_barra(
    db: Session, numero_barra: int
) -> Optional[Tuple[PartidaBolirana, Bolirana]]:
    """Partida activa en la que participa una barra por su número."""
    grupo = f"Barra {numero_barra}"
    ids_grupo = [
        fila[0] for fila in db.query(Mesa.id).filter(Mesa.grupo == grupo).all()
    ]
    return _participacion_activa(
        db,
        (
            (ParticipanteBolirana.tipo == "barra")
            & (ParticipanteBolirana.barra_numero == numero_barra)
        )
        | (
            (ParticipanteBolirana.tipo == "mesa")
            & (ParticipanteBolirana.mesa_id.in_(ids_grupo))
        )
        | (
            (ParticipanteBolirana.tipo == "alias")
            & (ParticipanteBolirana.origen_barra_numero == numero_barra)
        )
        | (
            (ParticipanteBolirana.tipo == "alias")
            & (ParticipanteBolirana.origen_mesa_id.in_(ids_grupo))
        ),
    )


def mensaje_candado(nombre_bolirana: str, tipo: str = "mesa") -> str:
    lugar = {
        "barra": "barra",
        "individual": "cuenta individual",
    }.get(tipo, "mesa")
    return (
        f"Esta {lugar} tiene una partida activa en Bolirana "
        f"{nombre_bolirana}. Finaliza la partida y define el pago antes de "
        "cerrar la cuenta."
    )


def exigir_mesa_sin_bolirana(db: Session, mesa: Mesa) -> None:
    """Corta el cobro/cierre si la mesa, barra o individual está en partida."""
    if not modulo_habilitado(db):
        return
    participacion = participacion_activa_mesa(db, mesa)
    if participacion:
        _, bolirana = participacion
        raise HTTPException(
            status_code=409,
            detail=mensaje_candado(bolirana.nombre, mesa.tipo or "mesa"),
        )


def exigir_barra_sin_bolirana(db: Session, numero_barra: int) -> None:
    """Corta el cobro/cierre de una barra completa."""
    if not modulo_habilitado(db):
        return
    participacion = participacion_activa_barra(db, numero_barra)
    if participacion:
        _, bolirana = participacion
        raise HTTPException(
            status_code=409,
            detail=mensaje_candado(bolirana.nombre, "barra"),
        )


def hay_partidas_activas(db: Session) -> bool:
    """True si el módulo está activo y hay una partida sin liquidar."""
    if not modulo_habilitado(db):
        return False
    return (
        db.query(PartidaBolirana.id)
        .filter(PartidaBolirana.estado == "en_curso")
        .first()
        is not None
    )


def mapa_boliranas_activas(db: Session) -> dict:
    """Nombres de bolirana por mesa y por barra con partida en curso.

    Se usa en el listado de mesas para pintar el candado sin consultar la
    partida una por una.
    """
    if not modulo_habilitado(db):
        return {"mesa": {}, "barra": {}}
    filas = (
        db.query(ParticipanteBolirana, Bolirana)
        .join(
            PartidaBolirana,
            PartidaBolirana.id == ParticipanteBolirana.partida_id,
        )
        .join(Bolirana, Bolirana.id == PartidaBolirana.bolirana_id)
        .filter(PartidaBolirana.estado == "en_curso")
        .all()
    )
    por_mesa: dict = {}
    por_barra: dict = {}
    for participante, bolirana in filas:
        if participante.tipo == "mesa" and participante.mesa_id:
            por_mesa[participante.mesa_id] = bolirana.nombre
        elif participante.tipo == "barra" and participante.barra_numero:
            por_barra[participante.barra_numero] = bolirana.nombre
        elif participante.tipo == "alias":
            # Un alias vinculado bloquea la cuenta de su mesa/barra/individual.
            if participante.origen_mesa_id:
                por_mesa[participante.origen_mesa_id] = bolirana.nombre
            elif participante.origen_barra_numero:
                por_barra[participante.origen_barra_numero] = bolirana.nombre
    return {"mesa": por_mesa, "barra": por_barra}
