"""Endpoints de usuarios: login por usuario, gestión de usuarios y roles."""

import hashlib
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Division, Pedido, TurnoCaja, Usuario
from app.schemas import (
    CLAVE_INICIAL,
    ROLES,
    CambiarClaveIn,
    UsuarioCreate,
    UsuarioLogin,
    UsuarioOut,
    UsuarioUpdate,
)
from app.tiempo import ahora_local

router = APIRouter(tags=["usuarios"])


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _a_usuario_out(usuario: Usuario) -> UsuarioOut:
    return UsuarioOut(
        id=usuario.id,
        alias=usuario.alias,
        nombre=usuario.nombre,
        rol=usuario.rol,
        activo=bool(usuario.activo),
        ingreso_stock=bool(usuario.ingreso_stock),
        creado_en=usuario.creado_en or ahora_local(),
    )


@router.post("/login", response_model=UsuarioOut)
def login(datos: UsuarioLogin, db: Session = Depends(get_db)):
    """Autenticar por nombre de usuario y contraseña."""
    nombre_usuario = (datos.usuario or "").strip()
    usuario = db.query(Usuario).filter(Usuario.alias == nombre_usuario).first()

    if not usuario or usuario.password_hash != hash_password(datos.password):
        raise HTTPException(status_code=401, detail="Usuario o clave incorrectos")
    if not usuario.activo:
        raise HTTPException(status_code=403, detail="El usuario está desactivado")

    return _a_usuario_out(usuario)


@router.get("/", response_model=List[UsuarioOut])
def listar_usuarios(db: Session = Depends(get_db)):
    """Listar todos los usuarios."""
    usuarios = db.query(Usuario).order_by(Usuario.alias).all()
    return [_a_usuario_out(u) for u in usuarios]


@router.get("/{usuario_id}", response_model=UsuarioOut)
def obtener_usuario(usuario_id: int, db: Session = Depends(get_db)):
    """Devuelve un usuario; el Bartender lo consulta para refrescar permisos."""
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return _a_usuario_out(usuario)


@router.post("/", response_model=UsuarioOut, status_code=201)
def crear_usuario(datos: UsuarioCreate, db: Session = Depends(get_db)):
    """Crea un usuario. Si no se envía clave, se usa la clave inicial (1234)."""
    alias = datos.alias.strip()

    if datos.rol not in ROLES:
        raise HTTPException(
            status_code=400, detail=f"Rol inválido. Use: {', '.join(ROLES)}"
        )

    if not alias:
        raise HTTPException(status_code=400, detail="El alias no puede estar vacío")

    existente = db.query(Usuario).filter(Usuario.alias == alias).first()
    if existente:
        raise HTTPException(status_code=400, detail="El alias ya está en uso")

    clave = datos.password or CLAVE_INICIAL
    usuario = Usuario(
        alias=alias,
        nombre=(datos.nombre or alias).strip(),
        rol=datos.rol,
        password_hash=hash_password(clave),
        activo=1,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return _a_usuario_out(usuario)


@router.put("/{usuario_id}", response_model=UsuarioOut)
def actualizar_usuario(
    usuario_id: int, datos: UsuarioUpdate, db: Session = Depends(get_db)
):
    """Actualiza alias, nombre, rol, estado activo o permiso de stock."""
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if datos.alias is not None:
        alias = datos.alias.strip()
        if not alias:
            raise HTTPException(
                status_code=400, detail="El alias no puede estar vacío"
            )
        repetido = (
            db.query(Usuario)
            .filter(Usuario.alias == alias, Usuario.id != usuario_id)
            .first()
        )
        if repetido:
            raise HTTPException(status_code=400, detail="El alias ya está en uso")
        usuario.alias = alias

    if datos.nombre is not None:
        usuario.nombre = datos.nombre.strip()

    # Un administrador activo no puede degradarse ni desactivarse si es el
    # único que queda: la aplicación se quedaría sin acceso al panel.
    pierde_admin = (
        usuario.rol == "admin"
        and usuario.activo
        and (
            (datos.rol is not None and datos.rol != "admin")
            or datos.activo is False
        )
    )
    if pierde_admin:
        otros_admins = (
            db.query(Usuario)
            .filter(
                Usuario.rol == "admin",
                Usuario.id != usuario_id,
                Usuario.activo == 1,
            )
            .count()
        )
        if otros_admins == 0:
            raise HTTPException(
                status_code=400,
                detail=(
                    "No se puede quitar el último administrador activo. "
                    "Crea o activa otro administrador primero."
                ),
            )

    if datos.rol is not None:
        if datos.rol not in ROLES:
            raise HTTPException(
                status_code=400, detail=f"Rol inválido. Use: {', '.join(ROLES)}"
            )
        usuario.rol = datos.rol
    if datos.activo is not None:
        usuario.activo = 1 if datos.activo else 0
    if datos.ingreso_stock is not None:
        usuario.ingreso_stock = 1 if datos.ingreso_stock else 0

    db.commit()
    db.refresh(usuario)
    return _a_usuario_out(usuario)


@router.put("/{usuario_id}/clave", response_model=UsuarioOut)
def cambiar_clave(
    usuario_id: int, datos: CambiarClaveIn, db: Session = Depends(get_db)
):
    """Cambia la clave de un usuario."""
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    usuario.password_hash = hash_password(datos.password)
    db.commit()
    db.refresh(usuario)
    return _a_usuario_out(usuario)


@router.delete("/{usuario_id}")
def eliminar_usuario(usuario_id: int, db: Session = Depends(get_db)):
    """Elimina un usuario (no se permite borrar el último administrador)."""
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if usuario.rol == "admin":
        otros_admins = (
            db.query(Usuario)
            .filter(Usuario.rol == "admin", Usuario.id != usuario_id, Usuario.activo == 1)
            .count()
        )
        if otros_admins == 0:
            raise HTTPException(
                status_code=400,
                detail="No se puede eliminar el último administrador",
            )

    # El historial guarda el usuario de cada venta y turno. Borrar la cuenta
    # dejaría esos registros sin responsable, así que se conserva desactivada.
    tiene_historial = (
        db.query(Pedido).filter(Pedido.usuario_id == usuario_id).first()
        or db.query(TurnoCaja).filter(TurnoCaja.usuario_id == usuario_id).first()
        or db.query(Division).filter(Division.usuario_id == usuario_id).first()
    )
    if tiene_historial:
        raise HTTPException(
            status_code=400,
            detail=(
                "No se puede eliminar: el usuario tiene ventas, turnos o "
                "divisiones registradas. Desactívalo para conservar el historial."
            ),
        )

    alias = usuario.alias
    db.delete(usuario)
    db.commit()
    return {"message": f"Usuario '{alias}' eliminado"}
