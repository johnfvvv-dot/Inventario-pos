"""Endpoints para gestión de usuarios y login (admin/mesero)."""

import hashlib
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Usuario
from app.schemas import UsuarioCreate, UsuarioLogin, UsuarioOut

router = APIRouter(tags=["usuarios"])


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


@router.post("/login", response_model=UsuarioOut)
def login(datos: UsuarioLogin, db: Session = Depends(get_db)):
    """Autenticar usuario por email y contraseña."""
    usuario = db.query(Usuario).filter(Usuario.email == datos.email).first()
    if not usuario or usuario.password_hash != hash_password(datos.password):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    return usuario


@router.post("/", response_model=UsuarioOut, status_code=201)
def crear_usuario(datos: UsuarioCreate, db: Session = Depends(get_db)):
    """Crear nuevo usuario (admin o mesero)."""
    existente = db.query(Usuario).filter(Usuario.email == datos.email).first()
    if existente:
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    nuevo_usuario = Usuario(
        nombre=datos.nombre,
        rol=datos.rol,
        email=datos.email,
        password_hash=hash_password(datos.password),
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario


@router.get("/", response_model=List[UsuarioOut])
def listar_usuarios(db: Session = Depends(get_db)):
    """Listar todos los usuarios."""
    return db.query(Usuario).all()
