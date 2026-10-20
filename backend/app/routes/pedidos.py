"""Endpoints para gestión de pedidos y ventas por mesa."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Producto, Mesa, Pedido, producto_pedido
from schemas import (
    PedidoCreate, PedidoOut, PedidoItemCreate, PedidoItemOut,
    ProductoOut
)
from typing import List

router = APIRouter(prefix="/pedidos", tags=["pedidos"])


@router.post("/", response_model=PedidoOut)
def crear_pedido(datos: PedidoCreate, db: Session = Depends(get_db)):
    """Crear nuevo pedido para una mesa."""
    # Verificar que la mesa existe y obtener su estado
    mesa = db.query(Mesa).filter(Mesa.id == datos.mesa_id).first()
    if not mesa:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")
    
    # Verificar que el usuario existe
    usuario = db.query(Usuario).filter(Usuario.id == datos.usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Crear el pedido
    nuevo_pedido = Pedido(
        mesa_id=datos.mesa_id,
        usuario_id=datos.usuario_id,
        estado="abierto"
    )
    db.add(nuevo_pedido)
    db.commit()
    db.refresh(nuevo_pedido)
    
    # Agregar items al pedido y verificar stock
    total = 0.0
    for item in datos.items:
        producto = db.query(Producto).filter(Producto.id == item.producto_id).first()
        if not producto:
            # Eliminar el pedido creado y lanzar error
            db.delete(nuevo_pedido)
            db.commit()
            raise HTTPException(
                status_code=404, 
                detail=f"Producto con ID {item.producto_id} no encontrado"
            )
        
        if producto.stock < item.cantidad:
            # Eliminar el pedido creado y lanzar error
            db.delete(nuevo_pedido)
            db.commit()
            raise HTTPException(
                status_code=400, 
                detail=f"Stock insuficiente para {producto.nombre}. "
                f"Stock actual: {producto.stock}, Solicitado: {item.cantidad}"
            )
        
        # Descontar stock
        producto.stock -= item.cantidad
        
        # Agregar producto al pedido (tabla intermedia)
        db.execute(
            producto_pedido.insert().values(
                pedido_id=nuevo_pedido.id,
                producto_id=item.producto_id,
                cantidad=item.cantidad
            )
        )
        
        # Acumular total
        total += producto.precio * item.cantidad
    
    # Actualizar total del pedido
    nuevo_pedido.total = total
    db.commit()
    db.refresh(nuevo_pedido)
    
    # Cargar relaciones para la respuesta
    db.refresh(nuevo_pedido)
    
    return nuevo_pedido


@router.get("/", response_model=List[PedidoOut])
def listar_pedidos(db: Session = Depends(get_db)):
    """Listar todos los pedidos."""
    from sqlalchemy.orm import joinedload
    pedidos = db.query(Pedido).options(
        joinedload(Pedido.mesa),
        joinedload(Pedido.usuario),
        joinedload(Pedido.items).joinedload(producto_pedido.c.producto)
    ).all()
    return pedidos


@router.get("/mesa/{mesa_id}", response_model=List[PedidoOut])
def pedidos_por_mesa(mesa_id: int, db: Session = Depends(get_db)):
    """Listar pedidos de una mesa específica."""
    from sqlalchemy.orm import joinedload
    pedidos = db.query(Pedido).options(
        joinedload(Pedido.mesa),
        joinedload(Pedido.usuario),
        joinedload(Pedido.items).joinedload(producto_pedido.c.producto)
    ).filter(Pedido.mesa_id == mesa_id).all()
    return pedidos


@router.put("/{pedido_id}/cerrar", response_model=PedidoOut)
def cerrar_pedido(
    pedido_id: int, 
    db: Session = Depends(get_db)
):
    """Cerrar un pedido (cobrar)."""
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    
    if pedido.estado == "cerrado":
        raise HTTPException(status_code=400, detail="Pedido ya estaba cerrado")
    
    pedido.estado = "cerrado"
    db.commit()
    db.refresh(pedido)
    return pedido