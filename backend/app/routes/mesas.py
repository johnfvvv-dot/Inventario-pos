"""Endpoints para gestión de mesas."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Mesa

router = APIRouter(prefix="/mesas", tags=["mesas"])

@router.post("/", response_model=dict)
def crear_mesa(numero: int, capacidad: int = 4, db: Session = Depends(get_db)):
    """Crear nueva mesa."""
    # Verificar si el número de mesa ya existe
    existente = db.query(Mesa).filter(Mesa.numero == numero).first()
    if existente:
        raise HTTPException(status_code=400, detail="El número de mesa ya existe")
    
    nueva_mesa = Mesa(numero=numero, capacidad=capacidad, estado="disponible")
    db.add(nueva_mesa)
    db.commit()
    db.refresh(nueva_mesa)
    return {"message": f"Mesa {numero} creada exitosamente", "mesa_id": nueva_mesa.id}

@router.get("/", response_model=List[dict])
listar_mesas(db: Session = Depends(get_db)):
    """Listar todas las mesas con estado actual."""
    mesas = db.query(Mesa).all()
    return [
        {
            "id": m.id,
            "numero": m.numero,
            "capacidad": m.capacidad,
            "estado": m.estado
        }
        for m in mesas
    ]

@router.put("/{mesa_id}/estado", response_model=dict)
actualizar_estado_mesa(
    mesa_id: int, 
    nuevo_estado: str, 
    db: Session = Depends(get_db)
):
    """Actualizar estado de mesa."""
    mesa = db.query(Mesa).filter(Mesa.id == mesa_id).first()
    if not mesa:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")
    
    estados_permitidos = ["disponible", "ocupada", "cerrada"]
    if nuevo_estado not in estados_permitidos:
        raise HTTPException(
            status_code=400, 
            detail=f"Estado inválido. Use: {', '.join(estados_permitidos)}"
        )
    
    mesa.estado = nuevo_estado
    db.commit()
    db.refresh(mesa)
    return {"message": f"Mesa {mesa.numero} actualizada a {nuevo_estado}", "mesa_id": mesa.id}