"""Endpoints para gestión de pedidos y ventas por mesa."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import (
    Division,
    Mesa,
    Participante,
    ParticipanteItem,
    Pedido,
    PedidoItem,
    Producto,
    Usuario,
)
from app.schemas import (
    FORMAS_PAGO,
    PedidoCreate,
    PedidoItemAjuste,
    PedidoItemOut,
    PedidoOut,
)
from app.tiempo import ahora_local
from app.turnos import exigir_turno_abierto

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
        fecha_cierre=pedido.fecha_cierre,
        total=pedido.total,
        estado=pedido.estado,
        participante_id=pedido.participante_id,
        alias=pedido.participante.alias if pedido.participante else None,
        es_pago_division=bool(pedido.es_pago_division),
    )


def _cargar_pedido(db: Session, pedido_id: int) -> Pedido:
    return (
        db.query(Pedido)
        .options(
            joinedload(Pedido.mesa),
            joinedload(Pedido.usuario),
            joinedload(Pedido.participante),
            joinedload(Pedido.items).joinedload(PedidoItem.producto),
        )
        .filter(Pedido.id == pedido_id)
        .first()
    )


def _cargar_pedidos_mesa(db: Session, mesa_id: int) -> List[Pedido]:
    return (
        db.query(Pedido)
        .options(
            joinedload(Pedido.mesa),
            joinedload(Pedido.usuario),
            joinedload(Pedido.participante),
            joinedload(Pedido.items).joinedload(PedidoItem.producto),
        )
        .filter(Pedido.mesa_id == mesa_id)
        .order_by(Pedido.id.desc())
        .all()
    )


def _bloquear_cuenta(db: Session, mesa: Mesa) -> None:
    """Bloquea la fila (o filas) que representan la cuenta de una mesa/barra.

    En PostgreSQL ``FOR UPDATE`` serializa la creación de pedidos, los cobros
    y los cierres. En SQLite se ignora y la escritura ya queda serializada.
    """
    if (mesa.tipo or "mesa") == "barra" and mesa.grupo:
        (
            db.query(Mesa)
            .filter(Mesa.grupo == mesa.grupo)
            .order_by(Mesa.id)
            .with_for_update()
            .all()
        )
    else:
        db.query(Mesa).filter(Mesa.id == mesa.id).with_for_update().first()


def _misma_cuenta(division: Division, mesa: Mesa) -> bool:
    """True si la división pertenece a la misma mesa o a la misma barra."""
    if division.mesa_id == mesa.id:
        return True
    if (
        (mesa.tipo or "mesa") == "barra"
        and mesa.grupo
        and division.mesa
        and (division.mesa.tipo or "mesa") == "barra"
        and division.mesa.grupo == mesa.grupo
    ):
        return True
    return False


def _recalcular_participante(db: Session, participante: Participante) -> float:
    subtotal = (
        db.query(func.coalesce(func.sum(ParticipanteItem.subtotal), 0.0))
        .filter(ParticipanteItem.participante_id == participante.id)
        .scalar()
        or 0.0
    )
    participante.subtotal = round(float(subtotal), 2)
    return participante.subtotal


def _recalcular_division(db: Session, division: Division) -> float:
    total = (
        db.query(func.coalesce(func.sum(Participante.subtotal), 0.0))
        .filter(Participante.division_id == division.id)
        .scalar()
        or 0.0
    )
    division.total = round(float(total), 2)
    return division.total


@router.post("/", response_model=PedidoOut, status_code=201)
def crear_pedido(datos: PedidoCreate, db: Session = Depends(get_db)):
    """Crear un pedido y asignarlo a la cuenta general o a un alias.

    Un pedido completo tiene un solo destino. Si se envía
    ``participante_id``, el pedido nace como ``dividido`` y sus líneas se
    copian al alias; la cuenta general no se modifica. Sin ese campo el
    pedido queda ``abierto`` en la cuenta general.
    """
    exigir_turno_abierto(db)

    mesa = db.query(Mesa).filter(Mesa.id == datos.mesa_id).first()
    if not mesa:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")

    usuario = db.query(Usuario).filter(Usuario.id == datos.usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if not datos.items:
        raise HTTPException(status_code=400, detail="El pedido no tiene productos")

    participante = None
    division = None
    mesa_destino = mesa
    estado_pedido = "abierto"

    if datos.participante_id is not None:
        # Primera lectura para saber qué cuenta (mesa o barra) hay que bloquear.
        participante = (
            db.query(Participante)
            .options(joinedload(Participante.division).joinedload(Division.mesa))
            .filter(Participante.id == datos.participante_id)
            .first()
        )
        if not participante:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        division = participante.division
        if not division:
            raise HTTPException(
                status_code=409, detail="El cliente no pertenece a una división activa."
            )

        mesa_destino = division.mesa or db.query(Mesa).filter(
            Mesa.id == division.mesa_id
        ).first()
        if not mesa_destino:
            raise HTTPException(status_code=404, detail="Mesa de la división no encontrada")

        _bloquear_cuenta(db, mesa_destino)

        # Releer bajo el lock para que un pago simultáneo no pase inadvertido.
        participante = (
            db.query(Participante)
            .filter(Participante.id == datos.participante_id)
            .with_for_update()
            .first()
        )
        division = (
            db.query(Division)
            .filter(Division.id == division.id)
            .with_for_update()
            .first()
        )
        if not participante or not division:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

        if participante.pagado:
            raise HTTPException(
                status_code=409,
                detail="El cliente ya pagó su cuenta; elige otro destino.",
            )
        if division.estado != "pendiente":
            raise HTTPException(
                status_code=409, detail="La división ya está cerrada."
            )
        if not _misma_cuenta(division, mesa):
            raise HTTPException(
                status_code=400, detail="El cliente no pertenece a esta cuenta."
            )
        if mesa_destino.estado != "ocupada":
            raise HTTPException(
                status_code=409,
                detail="La cuenta ya no está activa; actualiza y vuelve a intentar.",
            )

        estado_pedido = "dividido"
    else:
        _bloquear_cuenta(db, mesa)

    # Validar y bloquear todos los productos en orden de id para evitar
    # interbloqueos entre pedidos concurrentes.
    ids_productos = sorted({item.producto_id for item in datos.items})
    productos = {
        p.id: p
        for p in (
            db.query(Producto)
            .filter(Producto.id.in_(ids_productos))
            .order_by(Producto.id)
            .with_for_update()
            .all()
        )
    }
    for item in datos.items:
        if item.producto_id not in productos:
            raise HTTPException(
                status_code=404,
                detail=f"Producto con ID {item.producto_id} no encontrado",
            )

    usado: dict = {}
    for item in datos.items:
        producto = productos[item.producto_id]
        solicitado = usado.get(producto.id, 0) + item.cantidad
        if producto.stock < solicitado:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Stock insuficiente para {producto.nombre}. "
                    f"Disponible: {producto.stock}, solicitado: {solicitado}"
                ),
            )
        usado[producto.id] = solicitado

    if not mesa_destino.fecha_ocupacion:
        mesa_destino.fecha_ocupacion = ahora_local()

    try:
        nuevo_pedido = Pedido(
            mesa_id=mesa_destino.id,
            usuario_id=usuario.id,
            estado=estado_pedido,
            total=0.0,
            fecha_ocupacion=mesa_destino.fecha_ocupacion,
            participante_id=participante.id if participante else None,
            es_pago_division=0,
        )
        nuevo_pedido.guardar_origen(mesa_destino)
        db.add(nuevo_pedido)
        db.flush()  # obtener ID sin confirmar todavía

        total = 0.0
        for item in datos.items:
            producto = productos[item.producto_id]
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

        if participante and division:
            for item in datos.items:
                producto = productos[item.producto_id]
                db.add(
                    ParticipanteItem(
                        participante_id=participante.id,
                        producto_id=producto.id,
                        cantidad=item.cantidad,
                        precio_unitario=producto.precio,
                        subtotal=round(producto.precio * item.cantidad, 2),
                        pedido_id=nuevo_pedido.id,
                    )
                )
            db.flush()
            _recalcular_participante(db, participante)
            # La división suma los subtotales ya guardados de sus alias.
            db.flush()
            _recalcular_division(db, division)

        mesa_destino.estado = "ocupada"
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

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
    exigir_turno_abierto(db)

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
        pedido.fecha_cierre = ahora_local()
        if not pedido.fecha_ocupacion:
            pedido.fecha_ocupacion = (
                pedido.mesa.fecha_ocupacion if pedido.mesa else None
            ) or pedido.fecha
        if pedido.mesa:
            pedido.guardar_origen(pedido.mesa)

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
            joinedload(Pedido.participante),
            joinedload(Pedido.items).joinedload(PedidoItem.producto),
        )
        .order_by(Pedido.id.desc())
        .all()
    )
    return [_pedido_to_out(p) for p in pedidos]


@router.get("/mesa/{mesa_id}", response_model=List[PedidoOut])
def pedidos_por_mesa(mesa_id: int, db: Session = Depends(get_db)):
    """Listar pedidos de una mesa específica."""
    return [_pedido_to_out(p) for p in _cargar_pedidos_mesa(db, mesa_id)]


@router.get("/barra/{numero_barra}", response_model=List[PedidoOut])
def pedidos_por_barra(numero_barra: int, db: Session = Depends(get_db)):
    """Listar los pedidos de todas las plazas de una barra.

    La pantalla de pedidos usa este endpoint para mostrar tanto la cuenta
    general de la barra como los pedidos asignados a alias que quedaron
    guardados en otra plaza.
    """
    grupo = f"Barra {numero_barra}"
    mesas = db.query(Mesa).filter(Mesa.grupo == grupo).order_by(Mesa.posicion).all()
    if not mesas:
        raise HTTPException(status_code=404, detail="Barra no encontrada")
    ids = [m.id for m in mesas]
    pedidos = (
        db.query(Pedido)
        .options(
            joinedload(Pedido.mesa),
            joinedload(Pedido.usuario),
            joinedload(Pedido.participante),
            joinedload(Pedido.items).joinedload(PedidoItem.producto),
        )
        .filter(Pedido.mesa_id.in_(ids))
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
    exigir_turno_abierto(db)

    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    if pedido.estado == "cerrado":
        raise HTTPException(status_code=400, detail="El pedido ya estaba cerrado")
    if pedido.estado == "dividido" or pedido.participante_id is not None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Este pedido pertenece a una división; cobra la parte del "
                "cliente desde la cuenta."
            ),
        )
    if pedido.es_pago_division:
        raise HTTPException(
            status_code=400,
            detail="Este pedido es un pago de división y ya está cerrado.",
        )

    if forma_pago not in FORMAS_PAGO:
        raise HTTPException(
            status_code=400,
            detail=f"Forma de pago invalida. Use: {', '.join(FORMAS_PAGO)}",
        )

    pedido.estado = "cerrado"
    pedido.forma_pago = forma_pago
    pedido.fecha_cierre = ahora_local()
    if not pedido.fecha_ocupacion:
        pedido.fecha_ocupacion = (
            pedido.mesa.fecha_ocupacion if pedido.mesa else None
        ) or pedido.fecha
    if pedido.mesa:
        pedido.guardar_origen(pedido.mesa)

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
                mesa.fecha_ocupacion = None

    db.commit()
    pedido_cargado = _cargar_pedido(db, pedido.id)
    return _pedido_to_out(pedido_cargado)
