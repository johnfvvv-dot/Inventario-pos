"""Endpoints de la cuenta de una mesa: consulta, cierre y división entre clientes."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
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
    CuentaMesaOut,
    DivisionCreate,
    DivisionOut,
    DivisionResumen,
    LineaCuenta,
    ParticipanteResumen,
    ParticipanteItemOut,
    ParticipanteOut,
    PedidoOut,
    PedidoItemOut,
)

router = APIRouter(tags=["cuentas"])


def _pedido_out(pedido: Pedido) -> PedidoOut:
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


def _participante_out(participante: Participante) -> ParticipanteOut:
    items = [
        ParticipanteItemOut(
            id=item.id,
            producto_id=item.producto_id,
            producto_nombre=item.producto.nombre if item.producto else "Desconocido",
            cantidad=item.cantidad,
            precio_unitario=item.precio_unitario,
            subtotal=item.subtotal,
        )
        for item in participante.items
    ]
    return ParticipanteOut(
        id=participante.id,
        alias=participante.alias,
        subtotal=participante.subtotal,
        pagado=bool(participante.pagado),
        items=items,
    )


def _division_out(division: Division) -> DivisionOut:
    return DivisionOut(
        id=division.id,
        mesa_id=division.mesa_id,
        total=division.total,
        estado=division.estado,
        fecha=division.fecha,
        participantes=[_participante_out(p) for p in division.participantes],
    )


def _cargar_divisiones(db: Session, mesa_id: int) -> List[Division]:
    return (
        db.query(Division)
        .options(
            joinedload(Division.participantes).joinedload(Participante.items).joinedload(
                ParticipanteItem.producto
            )
        )
        .filter(Division.mesa_id == mesa_id)
        .order_by(Division.id.desc())
        .all()
    )


@router.get("/mesa/{mesa_id}", response_model=CuentaMesaOut)
def consultar_cuenta(mesa_id: int, db: Session = Depends(get_db)):
    """Devuelve el detalle de la cuenta actual de una mesa."""
    mesa = db.query(Mesa).filter(Mesa.id == mesa_id).first()
    if not mesa:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")

    pedidos = (
        db.query(Pedido)
        .options(
            joinedload(Pedido.mesa),
            joinedload(Pedido.usuario),
            joinedload(Pedido.items).joinedload(PedidoItem.producto),
        )
        .filter(Pedido.mesa_id == mesa_id, Pedido.estado == "abierto")
        .order_by(Pedido.id)
        .all()
    )

    divisiones = [d for d in _cargar_divisiones(db, mesa_id) if d.estado == "pendiente"]

    total = round(
        sum(p.total for p in pedidos) + sum(d.total for d in divisiones), 2
    )

    return CuentaMesaOut(
        mesa_id=mesa.id,
        mesa_numero=mesa.numero,
        estado_mesa=mesa.estado,
        total=total,
        pedidos=[_pedido_out(p) for p in pedidos],
        divisiones=[
            DivisionResumen(
                id=d.id,
                total=d.total,
                estado=d.estado,
                fecha=d.fecha,
                participantes=[
                    ParticipanteResumen(
                        id=p.id,
                        alias=p.alias,
                        subtotal=p.subtotal,
                        pagado=bool(p.pagado),
                        items=[
                            LineaCuenta(
                                producto_id=item.producto_id,
                                producto_nombre=item.producto.nombre
                                if item.producto
                                else "Desconocido",
                                cantidad=item.cantidad,
                                precio_unitario=item.precio_unitario,
                                subtotal=item.subtotal,
                                alias=p.alias,
                                participante_id=p.id,
                            )
                            for item in p.items
                        ],
                    )
                    for p in d.participantes
                ],
            )
            for d in divisiones
        ],
    )


@router.post("/mesa/{mesa_id}/cerrar", response_model=CuentaMesaOut)
def cerrar_cuenta(mesa_id: int, db: Session = Depends(get_db)):
    """Cierra la cuenta completa de la mesa (pedidos + divisiones) SIN liberar la mesa."""
    mesa = db.query(Mesa).filter(Mesa.id == mesa_id).first()
    if not mesa:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")

    # Cerrar pedidos abiertos
    pedidos = (
        db.query(Pedido)
        .options(
            joinedload(Pedido.mesa),
            joinedload(Pedido.usuario),
            joinedload(Pedido.items).joinedload(PedidoItem.producto),
        )
        .filter(Pedido.mesa_id == mesa_id, Pedido.estado == "abierto")
        .all()
    )
    for pedido in pedidos:
        pedido.estado = "cerrado"

    # Marcar como pagadas las divisiones pendientes
    divisiones = _cargar_divisiones(db, mesa_id)
    for division in divisiones:
        if division.estado == "pendiente":
            division.estado = "pagada"
            for participante in division.participantes:
                participante.pagado = 1

    # La mesa permanece OCUPADA: se puede abrir una nueva cuenta
    if mesa.estado != "ocupada":
        mesa.estado = "ocupada"

    db.commit()

    return consultar_cuenta(mesa_id, db)


@router.post("/dividir", response_model=DivisionOut, status_code=201)
def dividir_cuenta(datos: DivisionCreate, db: Session = Depends(get_db)):
    """Divide la cuenta de una mesa entre varios clientes (alias)."""
    mesa = db.query(Mesa).filter(Mesa.id == datos.mesa_id).first()
    if not mesa:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")

    usuario = db.query(Usuario).filter(Usuario.id == datos.usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if not datos.participantes:
        raise HTTPException(status_code=400, detail="Agrega al menos un cliente")

    # Verificar que los productos existen y calcular subtotales
    productos_cache: dict = {}
    total = 0.0
    participantes_preparados = []

    for participante in datos.participantes:
        subtotal = 0.0
        items_preparados = []
        for item in participante.items:
            producto = productos_cache.get(item.producto_id)
            if producto is None:
                producto = (
                    db.query(Producto).filter(Producto.id == item.producto_id).first()
                )
                if not producto:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Producto con ID {item.producto_id} no encontrado",
                    )
                productos_cache[item.producto_id] = producto

            subtotal_item = round(producto.precio * item.cantidad, 2)
            subtotal = round(subtotal + subtotal_item, 2)
            items_preparados.append(
                {
                    "producto": producto,
                    "cantidad": item.cantidad,
                    "precio_unitario": producto.precio,
                    "subtotal": subtotal_item,
                }
            )
        total = round(total + subtotal, 2)
        participantes_preparados.append(
            {"alias": participante.alias, "subtotal": subtotal, "items": items_preparados}
        )

    if total <= 0:
        raise HTTPException(status_code=400, detail="La división no tiene productos")

    # Crear la división
    division = Division(
        mesa_id=mesa.id,
        usuario_id=usuario.id,
        total=total,
        estado="pendiente",
    )
    db.add(division)
    db.flush()

    for data in participantes_preparados:
        participante = Participante(
            division_id=division.id,
            alias=data["alias"],
            subtotal=data["subtotal"],
            pagado=0,
        )
        db.add(participante)
        db.flush()
        for item in data["items"]:
            db.add(
                ParticipanteItem(
                    participante_id=participante.id,
                    producto_id=item["producto"].id,
                    cantidad=item["cantidad"],
                    precio_unitario=item["precio_unitario"],
                    subtotal=item["subtotal"],
                )
            )

    # Los pedidos abiertos de la mesa quedan cubiertos por la división
    pedidos = (
        db.query(Pedido)
        .options(joinedload(Pedido.items))
        .filter(Pedido.mesa_id == mesa.id, Pedido.estado == "abierto")
        .all()
    )
    for pedido in pedidos:
        pedido.estado = "dividido"

    # La mesa sigue ocupada
    mesa.estado = "ocupada"

    db.commit()

    division = (
        db.query(Division)
        .options(
            joinedload(Division.participantes).joinedload(Participante.items).joinedload(
                ParticipanteItem.producto
            )
        )
        .filter(Division.id == division.id)
        .first()
    )
    return _division_out(division)


@router.post("/division/{division_id}/pagar", response_model=DivisionOut)
def pagar_participante(division_id: int, db: Session = Depends(get_db)):
    """Marca como pagado un cliente (participante) de una división."""
    division = (
        db.query(Division)
        .options(
            joinedload(Division.participantes).joinedload(Participante.items).joinedload(
                ParticipanteItem.producto
            )
        )
        .filter(Division.id == division_id)
        .first()
    )
    if not division:
        raise HTTPException(status_code=404, detail="División no encontrada")

    for participante in division.participantes:
        if not participante.pagado:
            participante.pagado = 1

    if all(p.pagado for p in division.participantes):
        division.estado = "pagada"

    db.commit()
    return _division_out(division)


@router.get("/mesa/{mesa_id}/divisiones", response_model=List[DivisionOut])
def listar_divisiones(mesa_id: int, db: Session = Depends(get_db)):
    """Historial de divisiones de la mesa."""
    return [_division_out(d) for d in _cargar_divisiones(db, mesa_id)]
