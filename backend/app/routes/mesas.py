"""Endpoints para gestión de mesas."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Division, Mesa, Pedido
from app.schemas import EstadoUpdate, MesaCreate, MesaListadoOut, MesaOut

router = APIRouter(tags=["mesas"])

ESTADOS_PERMITIDOS = ["disponible", "ocupada", "cerrada"]


def _resumen_cuenta(db: Session, mesas: List[Mesa]):
    """Calcula el total pendiente y el detalle por mesa."""
    if not mesas:
        return {}

    ids = [m.id for m in mesas]

    pedidos = (
        db.query(Pedido.mesa_id, func.count(Pedido.id), func.coalesce(func.sum(Pedido.total), 0.0))
        .filter(Pedido.mesa_id.in_(ids), Pedido.estado == "abierto")
        .group_by(Pedido.mesa_id)
        .all()
    )
    divisiones = (
        db.query(Division.mesa_id, func.count(Division.id), func.coalesce(func.sum(Division.total), 0.0))
        .filter(Division.mesa_id.in_(ids), Division.estado == "pendiente")
        .group_by(Division.mesa_id)
        .all()
    )

    resumen: dict = {}
    for mesa_id, cantidad, total in pedidos:
        resumen[mesa_id] = {
            "pedidos": cantidad,
            "divisiones": 0,
            "total": round(float(total or 0), 2),
        }
    for mesa_id, cantidad, total in divisiones:
        item = resumen.setdefault(
            mesa_id, {"pedidos": 0, "divisiones": 0, "total": 0.0}
        )
        item["divisiones"] = cantidad
        item["total"] = round(item["total"] + float(total or 0), 2)
    return resumen


@router.post("/", response_model=MesaOut, status_code=201)
def crear_mesa(datos: MesaCreate, db: Session = Depends(get_db)):
    """Crear nueva mesa."""
    existente = db.query(Mesa).filter(Mesa.numero == datos.numero).first()
    if existente:
        raise HTTPException(status_code=400, detail="El número de mesa ya existe")

    nueva_mesa = Mesa(
        numero=datos.numero,
        capacidad=datos.capacidad,
        estado="disponible",
    )
    db.add(nueva_mesa)
    db.commit()
    db.refresh(nueva_mesa)
    return nueva_mesa


@router.get("/", response_model=List[MesaListadoOut])
def listar_mesas(db: Session = Depends(get_db)):
    """Listar todas las mesas con el resumen de su cuenta pendiente."""
    mesas = db.query(Mesa).order_by(Mesa.numero).all()
    resumen = _resumen_cuenta(db, mesas)

    resultado = []
    for mesa in mesas:
        info = resumen.get(mesa.id, {"pedidos": 0, "divisiones": 0, "total": 0.0})
        pendientes = []
        if info["pedidos"]:
            pendientes.append(
                f"{info['pedidos']} pedido abierto" + ("s" if info["pedidos"] > 1 else "")
            )
        if info["divisiones"]:
            pendientes.append(
                f"{info['divisiones']} división pendiente"
                + ("s" if info["divisiones"] > 1 else "")
            )

        resultado.append(
            MesaListadoOut(
                id=mesa.id,
                numero=mesa.numero,
                capacidad=mesa.capacidad,
                estado=mesa.estado,
                total_cuenta=info["total"],
                tiene_cuenta_pendiente=bool(pendientes),
                detalle_pendiente=" · ".join(pendientes),
            )
        )
    return resultado


@router.put("/{mesa_id}/estado", response_model=MesaOut)
def actualizar_estado_mesa(
    mesa_id: int, datos: EstadoUpdate, db: Session = Depends(get_db)
):
    """Actualizar el estado de una mesa."""
    mesa = db.query(Mesa).filter(Mesa.id == mesa_id).first()
    if not mesa:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")

    if datos.nuevo_estado not in ESTADOS_PERMITIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Estado inválido. Use: {', '.join(ESTADOS_PERMITIDOS)}",
        )

    # No se puede marcar como disponible una mesa con cuentas pendientes
    if datos.nuevo_estado == "disponible":
        db.flush()
        pedidos_abiertos = (
            db.query(func.count(Pedido.id))
            .filter(Pedido.mesa_id == mesa.id, Pedido.estado == "abierto")
            .scalar()
            or 0
        )
        divisiones_pendientes = (
            db.query(func.count(Division.id))
            .filter(Division.mesa_id == mesa.id, Division.estado == "pendiente")
            .scalar()
            or 0
        )
        if pedidos_abiertos:
            raise HTTPException(
                status_code=400, detail="La mesa aún tiene un pedido abierto."
            )
        if divisiones_pendientes:
            raise HTTPException(
                status_code=400,
                detail="La mesa aún tiene una división de cuenta pendiente.",
            )

    mesa.estado = datos.nuevo_estado
    db.commit()
    db.refresh(mesa)
    return mesa


@router.post("/{mesa_id}/liberar", response_model=MesaOut)
def liberar_mesa(mesa_id: int, db: Session = Depends(get_db)):
    """Libera la mesa SOLO si no tiene cuentas pendientes."""
    mesa = db.query(Mesa).filter(Mesa.id == mesa_id).first()
    if not mesa:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")

    db.flush()
    pedidos_abiertos = (
        db.query(func.count(Pedido.id))
        .filter(Pedido.mesa_id == mesa.id, Pedido.estado == "abierto")
        .scalar()
        or 0
    )
    divisiones_pendientes = (
        db.query(func.count(Division.id))
        .filter(Division.mesa_id == mesa.id, Division.estado == "pendiente")
        .scalar()
        or 0
    )

    if pedidos_abiertos:
        raise HTTPException(
            status_code=400,
            detail="La mesa aún tiene un pedido abierto.",
        )
    if divisiones_pendientes:
        raise HTTPException(
            status_code=400,
            detail="La mesa aún tiene una división de cuenta pendiente.",
        )

    mesa.estado = "disponible"
    db.commit()
    db.refresh(mesa)
    return mesa
