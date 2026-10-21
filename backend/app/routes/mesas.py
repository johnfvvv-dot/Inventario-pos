"""Endpoints para gestión de mesas."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Mesa
from app.schemas import EstadoUpdate, MesaCreate, MesaOut

router = APIRouter(tags=["mesas"])

ESTADOS_PERMITIDOS = ["disponible", "ocupada", "cerrada"]


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


@router.get("/", response_model=List[MesaOut])
def listar_mesas(db: Session = Depends(get_db)):
    """Listar todas las mesas con su estado actual."""
    return db.query(Mesa).order_by(Mesa.numero).all()


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

    mesa.estado = datos.nuevo_estado
    db.commit()
    db.refresh(mesa)
    return mesa
