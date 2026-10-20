"""Endpoints para gestión de usuarios (admin/mesero)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Usuario
from schemas import UsuarioCreate, UsuarioOut

router = APIRouter(prefix="/usuarios", tags=["usuarios"])

@router.post("/", response_model=UsuarioOut)
def crear_usuario(datos: UsuarioCreate, db: Session = Depends(get_db)):
    """Crear nuevo usuario (solo admin)."""
    # Verificar si el email ya existe
    existente = db.query(Usuario).filter(Usuario.email == datos.email).first()
    if existente:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    nuevo_usuario = Usuario(
        nombre=datos.nombre,
        rol=datos.rol,
        email=datos.email
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario

@router.get("/", response_model=List[UsuarioOut])
def listar_usuarios(db: Session = Depends(get_db)):
    """Listar todos los usuarios."""
    return db.query(Usuario).all()