"""Endpoints para gestión de pedidos y ventas por mesa."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Division, Mesa, Pedido, PedidoItem, Producto, Usuario
from app.schemas import (
    PedidoCreate,
    PedidoItemOut,
    PedidoOut,
)

router = APIRouter(tags=["pedidos"])


def _pedido_to_out(pedido: Pedido) -> PedidoOut:
    """Convertir un Pedido ORM al esquema de respuesta."""
    items = [
        PedidoItemOut(
            id=item.id,
            producto_id=item.producto_id,
            producto_nombre=item.producto.nombre if item.producto else "Desconocido",
            cantidad=item.cantidad,
            precio_unitario=item.precio_unitario,
            subtotal=item.subtotal,
        )
        for item in pedido.items
    ]
    return PedidoOut(
        id=pedido.id,
        mesa=pedido.mesa,
        usuario=pedido.usuario,
        items=items,
        fecha=pedido.fecha,
        total=pedido.total,
        estado=pedido.estado,
    )


def _cargar_pedido(db: Session, pedido_id: int) -> Pedido:
    return (
        db.query(Pedido)
        .options(
            joinedload(Pedido.mesa),
            joinedload(Pedido.usuario),
            joinedload(Pedido.items).joinedload(PedidoItem.producto),
        )
        .filter(Pedido.id == pedido_id)
        .first()
    )


@router.post("/", response_model=PedidoOut, status_code=201)
def crear_pedido(datos: PedidoCreate, db: Session = Depends(get_db)):
    """Crear un pedido, descontar stock y calcular el total."""
    mesa = db.query(Mesa).filter(Mesa.id == datos.mesa_id).first()
    if not mesa:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")

    usuario = db.query(Usuario).filter(Usuario.id == datos.usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if not datos.items:
        raise HTTPException(status_code=400, detail="El pedido no tiene productos")

    nuevo_pedido = Pedido(
        mesa_id=mesa.id,
        usuario_id=usuario.id,
        estado="abierto",
        total=0.0,
    )
    db.add(nuevo_pedido)
    db.flush()  # obtener ID sin confirmar todavía

    total = 0.0
    for item in datos.items:
        producto = db.query(Producto).filter(Producto.id == item.producto_id).first()
        if not producto:
            db.rollback()
            raise HTTPException(
                status_code=404,
                detail=f"Producto con ID {item.producto_id} no encontrado",
            )
        if producto.stock < item.cantidad:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Stock insuficiente para {producto.nombre}. "
                    f"Disponible: {producto.stock}, solicitado: {item.cantidad}"
                ),
            )

        subtotal = round(producto.precio * item.cantidad, 2)
        producto.stock -= item.cantidad
        db.add(
            PedidoItem(
                pedido_id=nuevo_pedido.id,
                producto_id=producto.id,
                cantidad=item.cantidad,
                precio_unitario=producto.precio,
                subtotal=subtotal,
            )
        )
        total += subtotal

    nuevo_pedido.total = round(total, 2)
    mesa.estado = "ocupada"
    db.commit()

    pedido_cargado = _cargar_pedido(db, nuevo_pedido.id)
    return _pedido_to_out(pedido_cargado)


@router.get("/", response_model=List[PedidoOut])
def listar_pedidos(db: Session = Depends(get_db)):
    """Listar todos los pedidos."""
    pedidos = (
        db.query(Pedido)
        .options(
            joinedload(Pedido.mesa),
            joinedload(Pedido.usuario),
            joinedload(Pedido.items).joinedload(PedidoItem.producto),
        )
        .order_by(Pedido.id.desc())
        .all()
    )
    return [_pedido_to_out(p) for p in pedidos]


@router.get("/mesa/{mesa_id}", response_model=List[PedidoOut])
def pedidos_por_mesa(mesa_id: int, db: Session = Depends(get_db)):
    """Listar pedidos de una mesa específica."""
    pedidos = (
        db.query(Pedido)
        .options(
            joinedload(Pedido.mesa),
            joinedload(Pedido.usuario),
            joinedload(Pedido.items).joinedload(PedidoItem.producto),
        )
        .filter(Pedido.mesa_id == mesa_id)
        .order_by(Pedido.id.desc())
        .all()
    )
    return [_pedido_to_out(p) for p in pedidos]


@router.put("/{pedido_id}/cerrar", response_model=PedidoOut)
def cerrar_pedido(pedido_id: int, db: Session = Depends(get_db)):
    """Cerrar un pedido (cobrar) y liberar la mesa si no quedan pedidos abiertos."""
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    if pedido.estado == "cerrado":
        raise HTTPException(status_code=400, detail="El pedido ya estaba cerrado")

    pedido.estado = "cerrado"

    # La mesa se libera solo si no quedan pedidos abiertos NI divisiones pendientes
    if pedido.mesa_id:
        db.flush()  # volcar cambios para que los COUNT sean exactos
        abiertos = (
            db.query(Pedido)
            .filter(
                Pedido.mesa_id == pedido.mesa_id,
                Pedido.estado == "abierto",
                Pedido.id != pedido.id,
            )
            .count()
        )
        divisiones_pendientes = (
            db.query(Division)
            .filter(Division.mesa_id == pedido.mesa_id, Division.estado == "pendiente")
            .count()
        )
        if abiertos == 0 and divisiones_pendientes == 0:
            mesa = db.query(Mesa).filter(Mesa.id == pedido.mesa_id).first()
            if mesa:
                mesa.estado = "disponible"

    db.commit()
    pedido_cargado = _cargar_pedido(db, pedido.id)
    return _pedido_to_out(pedido_cargado)
