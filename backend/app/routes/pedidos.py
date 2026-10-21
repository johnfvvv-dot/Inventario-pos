"""Endpoints para gestión de pedidos y ventas por mesa."""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Division, Mesa, Pedido, PedidoItem, Producto, Usuario
from app.schemas import (
    FORMAS_PAGO,
    PedidoCreate,
    PedidoItemAjuste,
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
        mesa_numero_historico=(
            pedido.mesa_numero_historico
            if pedido.mesa is None
            else (pedido.mesa.numero if pedido.mesa else None)
        ),
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


@router.put("/{pedido_id}/items/{item_id}", response_model=PedidoOut)
def ajustar_item_pedido(
    pedido_id: int,
    item_id: int,
    datos: PedidoItemAjuste,
    db: Session = Depends(get_db),
):
    """Ajusta la cantidad de una línea de un pedido abierto.

    cantidad=0 elimina la línea; devuelve el stock al inventario.
    """
    pedido = (
        db.query(Pedido)
        .options(joinedload(Pedido.items).joinedload(PedidoItem.producto))
        .filter(Pedido.id == pedido_id)
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    if pedido.estado != "abierto":
        raise HTTPException(
            status_code=400, detail="Solo se pueden editar pedidos abiertos"
        )

    item = next((i for i in pedido.items if i.id == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Línea no encontrada")

    producto = db.query(Producto).filter(Producto.id == item.producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    diferencia = datos.cantidad - item.cantidad
    if diferencia > 0 and producto.stock < diferencia:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Stock insuficiente de {producto.nombre}: "
                f"disponible {producto.stock}"
            ),
        )

    producto.stock -= diferencia
    item.cantidad = datos.cantidad
    item.subtotal = round(producto.precio * datos.cantidad, 2)

    # Si la cantidad llega a 0, se elimina la línea
    if datos.cantidad == 0:
        db.delete(item)

    # Recalcular el total
    db.flush()
    total = round(
        sum(
            i.subtotal
            for i in db.query(PedidoItem).filter(PedidoItem.pedido_id == pedido.id).all()
        ),
        2,
    )
    pedido.total = total

    # Si el pedido se queda sin líneas, se cierra
    if total == 0:
        pedido.estado = "cerrado"
        pedido.forma_pago = "efectivo"
        pedido.fecha_cierre = datetime.utcnow()

    db.commit()
    pedido_cargado = _cargar_pedido(db, pedido.id)
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
def cerrar_pedido(
    pedido_id: int,
    forma_pago: str = "efectivo",
    db: Session = Depends(get_db),
):
    """Cerrar un pedido (cobrar) y liberar la mesa si no quedan cuentas pendientes."""
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    if pedido.estado == "cerrado":
        raise HTTPException(status_code=400, detail="El pedido ya estaba cerrado")

    if forma_pago not in FORMAS_PAGO:
        raise HTTPException(
            status_code=400,
            detail=f"Forma de pago invalida. Use: {', '.join(FORMAS_PAGO)}",
        )

    pedido.estado = "cerrado"
    pedido.forma_pago = forma_pago
    pedido.fecha_cierre = datetime.utcnow()

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
