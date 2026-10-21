"""Endpoints del corte de caja (turnos) y resumen de ventas por forma de pago."""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Pedido, TurnoCaja, Usuario
from app.schemas import (
    AbrirTurnoOut,
    CerrarTurnoIn,
    ResumenCajaOut,
    TotalesFormaPago,
    TurnoCajaOut,
)

router = APIRouter(tags=["caja"])

FORMAS_PAGO = ["efectivo", "tarjeta", "transferencia"]


def _totales_por_forma_pago(
    db: Session, desde: Optional[datetime] = None, hasta: Optional[datetime] = None
) -> TotalesFormaPago:
    """Suma los pedidos cerrados del periodo agrupados por forma de pago."""
    query = db.query(Pedido).filter(Pedido.estado == "cerrado")
    if desde:
        query = query.filter(Pedido.fecha_cierre >= desde)
    if hasta:
        query = query.filter(Pedido.fecha_cierre <= hasta)

    filas = (
        query.with_entities(
            Pedido.forma_pago, func.count(Pedido.id), func.coalesce(func.sum(Pedido.total), 0.0)
        )
        .group_by(Pedido.forma_pago)
        .all()
    )

    totales = {forma: 0.0 for forma in FORMAS_PAGO}
    operaciones = 0
    for forma, cantidad, total in filas:
        clave = forma if forma in totales else "efectivo"
        totales[clave] = round(totales[clave] + float(total or 0), 2)
        operaciones += cantidad or 0

    return TotalesFormaPago(
        efectivo=totales["efectivo"],
        tarjeta=totales["tarjeta"],
        transferencia=totales["transferencia"],
        total=round(sum(totales.values()), 2),
        operaciones=operaciones,
    )


def _turno_out(db: Session, turno: TurnoCaja) -> TurnoCajaOut:
    hasta = turno.fecha_cierre or datetime.utcnow()
    totales = _totales_por_forma_pago(db, turno.fecha_apertura, hasta)
    usuario = db.query(Usuario).filter(Usuario.id == turno.usuario_id).first()
    return TurnoCajaOut(
        id=turno.id,
        usuario_nombre=usuario.nombre if usuario else "Desconocido",
        fecha_apertura=turno.fecha_apertura,
        fecha_cierre=turno.fecha_cierre,
        observaciones=turno.observaciones,
        estado=turno.estado,
        totales=totales,
    )


@router.get("/turno-actual", response_model=Optional[TurnoCajaOut])
def turno_actual(db: Session = Depends(get_db)):
    """Devuelve el turno de caja abierto (o null si no hay ninguno)."""
    turno = (
        db.query(TurnoCaja)
        .filter(TurnoCaja.estado == "abierto")
        .order_by(TurnoCaja.id.desc())
        .first()
    )
    return _turno_out(db, turno) if turno else None


@router.post("/abrir", response_model=AbrirTurnoOut)
def abrir_turno(usuario_id: int = 1, db: Session = Depends(get_db)):
    """Abre un nuevo turno de caja."""
    abierto = (
        db.query(TurnoCaja).filter(TurnoCaja.estado == "abierto").first()
    )
    if abierto:
        raise HTTPException(
            status_code=400, detail="Ya hay un turno de caja abierto"
        )

    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    turno = TurnoCaja(usuario_id=usuario.id, estado="abierto")
    db.add(turno)
    db.commit()
    db.refresh(turno)
    return AbrirTurnoOut(
        mensaje="Turno de caja abierto", turno=_turno_out(db, turno)
    )


@router.post("/cerrar", response_model=TurnoCajaOut)
def cerrar_turno(datos: CerrarTurnoIn, db: Session = Depends(get_db)):
    """Cierra el turno de caja abierto."""
    turno = (
        db.query(TurnoCaja)
        .filter(TurnoCaja.estado == "abierto")
        .order_by(TurnoCaja.id.desc())
        .first()
    )
    if not turno:
        raise HTTPException(status_code=400, detail="No hay un turno de caja abierto")

    turno.estado = "cerrado"
    turno.fecha_cierre = datetime.utcnow()
    turno.observaciones = datos.observaciones
    db.commit()
    db.refresh(turno)
    return _turno_out(db, turno)


@router.get("/turnos", response_model=List[TurnoCajaOut])
def listar_turnos(limite: int = 20, db: Session = Depends(get_db)):
    """Historial de turnos de caja."""
    turnos = (
        db.query(TurnoCaja).order_by(TurnoCaja.id.desc()).limit(limite).all()
    )
    return [_turno_out(db, t) for t in turnos]


@router.get("/resumen", response_model=ResumenCajaOut)
def resumen_caja(
    dias: int = 1, db: Session = Depends(get_db)
):
    """Resumen de ventas por forma de pago de los últimos N días."""
    desde = datetime.utcnow() - timedelta(days=max(1, dias))
    hasta = datetime.utcnow()

    totales = _totales_por_forma_pago(db, desde, hasta)

    cerrados = (
        db.query(Pedido)
        .filter(Pedido.estado == "cerrado", Pedido.fecha_cierre >= desde)
        .all()
    )
    mesas = {p.mesa_id for p in cerrados if p.mesa_id}

    por_forma = {
        "efectivo": totales.efectivo,
        "tarjeta": totales.tarjeta,
        "transferencia": totales.transferencia,
    }

    return ResumenCajaOut(
        desde=desde,
        hasta=hasta,
        totales=totales,
        pedidos_cerrados=len(cerrados),
        mesas_atendidas=len(mesas),
        por_forma_pago=por_forma,
    )
