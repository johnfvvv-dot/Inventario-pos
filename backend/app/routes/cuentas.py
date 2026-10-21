"""Endpoints de la cuenta de una mesa: consulta, cierre y división entre clientes."""

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
    TransferirCuentaOut,
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

    # La cuenta solo suma lo que falta por cobrar:
    # pedidos abiertos + partes de alias que aún no pagaron
    total = round(
        sum(p.total for p in pedidos)
        + sum(
            round(sum(p.subtotal for p in d.participantes if not p.pagado), 2)
            for d in divisiones
        ),
        2,
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
                total_pendiente=round(
                    sum(p.subtotal for p in d.participantes if not p.pagado), 2
                ),
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
def cerrar_cuenta(mesa_id: int, liberar_mesa: bool = False, db: Session = Depends(get_db)):
    """Cierra la cuenta completa de la mesa (pedidos + divisiones).

    Por defecto la mesa permanece OCUPADA (se puede abrir una nueva cuenta).
    Con liberar_mesa=True la mesa queda DISPONIBLE al terminar.
    """
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
    mesa.estado = "disponible" if liberar_mesa else "ocupada"

    db.commit()

    return consultar_cuenta(mesa_id, db)


@router.post("/mesa/{mesa_id}/transferir", response_model=TransferirCuentaOut)
def transferir_cuenta(
    mesa_id: int, destino_id: int, db: Session = Depends(get_db)
):
    """Transfiere la cuenta abierta de una mesa a otra mesa."""
    origen = db.query(Mesa).filter(Mesa.id == mesa_id).first()
    if not origen:
        raise HTTPException(status_code=404, detail="Mesa de origen no encontrada")

    destino = db.query(Mesa).filter(Mesa.id == destino_id).first()
    if not destino:
        raise HTTPException(status_code=404, detail="Mesa de destino no encontrada")

    if origen.id == destino.id:
        raise HTTPException(
            status_code=400, detail="El destino debe ser otra mesa"
        )

    db.flush()

    # La mesa destino no debe tener ya una cuenta abierta
    pedidos_destino = (
        db.query(func.count(Pedido.id))
        .filter(Pedido.mesa_id == destino.id, Pedido.estado == "abierto")
        .scalar()
        or 0
    )
    divisiones_destino = (
        db.query(func.count(Division.id))
        .filter(Division.mesa_id == destino.id, Division.estado == "pendiente")
        .scalar()
        or 0
    )
    if pedidos_destino or divisiones_destino:
        raise HTTPException(
            status_code=400,
            detail="La mesa destino ya tiene una cuenta abierta.",
        )

    # Mover pedidos abiertos
    pedidos = (
        db.query(Pedido)
        .options(joinedload(Pedido.items))
        .filter(Pedido.mesa_id == origen.id, Pedido.estado == "abierto")
        .all()
    )
    total = 0.0
    for pedido in pedidos:
        pedido.mesa_id = destino.id
        total += pedido.total or 0.0

    # Mover divisiones pendientes
    divisiones = _cargar_divisiones(db, origen.id)
    for division in divisiones:
        if division.estado == "pendiente":
            division.mesa_id = destino.id
            total += division.total or 0.0

    # Estados de las mesas
    origen.estado = "disponible"
    destino.estado = "ocupada"

    db.commit()

    return TransferirCuentaOut(
        mensaje=(
            f"Cuenta transferida de la mesa {origen.numero} "
            f"a la mesa {destino.numero}"
        ),
        mesa_origen=origen.id,
        mesa_destino=destino.id,
        total_transferido=round(total, 2),
    )


@router.post("/dividir", response_model=DivisionOut, status_code=201)
def dividir_cuenta(datos: DivisionCreate, db: Session = Depends(get_db)):
    """Divide la cuenta de una mesa entre varios clientes (alias).

    Solo se divide lo asignado a los alias. El resto de los productos queda
    en un pedido abierto (bloque único) para que la cuenta se complete.
    """
    mesa = db.query(Mesa).filter(Mesa.id == datos.mesa_id).first()
    if not mesa:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")

    usuario = db.query(Usuario).filter(Usuario.id == datos.usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if not datos.participantes:
        raise HTTPException(status_code=400, detail="Agrega al menos un cliente")

    # Pool de productos pendientes (pedidos abiertos de la mesa)
    pedidos = (
        db.query(Pedido)
        .options(joinedload(Pedido.items).joinedload(PedidoItem.producto))
        .filter(Pedido.mesa_id == mesa.id, Pedido.estado == "abierto")
        .order_by(Pedido.id)
        .all()
    )

    pool: dict = {}
    for pedido in pedidos:
        for item in pedido.items:
            entry = pool.setdefault(
                item.producto_id,
                {
                    "cantidad": 0,
                    "precio_unitario": item.precio_unitario,
                    "producto": item.producto,
                },
            )
            entry["cantidad"] += item.cantidad

    if not pool:
        raise HTTPException(
            status_code=400, detail="La mesa no tiene productos pendientes para dividir"
        )

    # Validar que lo asignado no exceda lo disponible
    solicitado: dict = {}
    for participante in datos.participantes:
        for item in participante.items:
            solicitado[item.producto_id] = (
                solicitado.get(item.producto_id, 0) + item.cantidad
            )

    for producto_id, cantidad in solicitado.items():
        disponible = pool.get(producto_id, {}).get("cantidad", 0)
        if cantidad > disponible:
            nombre = (
                pool[producto_id]["producto"].nombre
                if producto_id in pool and pool[producto_id]["producto"]
                else f"#{producto_id}"
            )
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Cantidad insuficiente de {nombre}: "
                    f"disponible {disponible}, asignado {cantidad}"
                ),
            )

    # Crear la división con los subtotales por alias
    division = Division(
        mesa_id=mesa.id,
        usuario_id=usuario.id,
        total=0.0,
        estado="pendiente",
    )
    db.add(division)
    db.flush()

    total = 0.0
    for participante in datos.participantes:
        subtotal = 0.0
        items_preparados = []
        for item in participante.items:
            entry = pool[item.producto_id]
            producto = entry["producto"]
            precio_unitario = entry["precio_unitario"]
            subtotal_item = round(precio_unitario * item.cantidad, 2)
            subtotal = round(subtotal + subtotal_item, 2)
            items_preparados.append((producto, item.cantidad, precio_unitario, subtotal_item))

        if not items_preparados:
            continue

        nuevo_participante = Participante(
            division_id=division.id,
            alias=participante.alias,
            subtotal=subtotal,
            pagado=0,
        )
        db.add(nuevo_participante)
        db.flush()

        for producto, cantidad, precio_unitario, subtotal_item in items_preparados:
            db.add(
                ParticipanteItem(
                    participante_id=nuevo_participante.id,
                    producto_id=producto.id,
                    cantidad=cantidad,
                    precio_unitario=precio_unitario,
                    subtotal=subtotal_item,
                )
            )
        total = round(total + subtotal, 2)

    if total <= 0:
        db.rollback()
        raise HTTPException(status_code=400, detail="La división no tiene productos")

    division.total = total

    # El RESTO no asignado queda como un pedido abierto (bloque único)
    resto_items = []
    resto_total = 0.0
    for producto_id, entry in pool.items():
        restante = entry["cantidad"] - solicitado.get(producto_id, 0)
        if restante > 0:
            subtotal = round(entry["precio_unitario"] * restante, 2)
            resto_total = round(resto_total + subtotal, 2)
            resto_items.append((producto_id, entry, restante, subtotal))

    if resto_items:
        pedido_resto = Pedido(
            mesa_id=mesa.id,
            usuario_id=usuario.id,
            estado="abierto",
            total=resto_total,
        )
        db.add(pedido_resto)
        db.flush()
        for producto_id, entry, restante, subtotal in resto_items:
            db.add(
                PedidoItem(
                    pedido_id=pedido_resto.id,
                    producto_id=producto_id,
                    cantidad=restante,
                    precio_unitario=entry["precio_unitario"],
                    subtotal=subtotal,
                )
            )

    # Los pedidos originales quedan cubiertos por la división
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


@router.post("/participante/{participante_id}/pagar", response_model=ParticipanteOut)
def pagar_participante(participante_id: int, db: Session = Depends(get_db)):
    """Cierra la división de UN alias (el cliente paga su parte).

    La cuenta general de la mesa sigue abierta para los demás clientes.
    La mesa se libera solo cuando todos pagaron y no quedan pedidos abiertos.
    """
    participante = (
        db.query(Participante)
        .options(
            joinedload(Participante.items).joinedload(ParticipanteItem.producto),
            joinedload(Participante.division),
        )
        .filter(Participante.id == participante_id)
        .first()
    )
    if not participante:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    if not participante.pagado:
        participante.pagado = 1

    division = participante.division
    todos = (
        db.query(Participante).filter(Participante.division_id == division.id).all()
    )
    if todos and all(p.pagado for p in todos):
        division.estado = "pagada"

    # La mesa se libera cuando ya no queda nada por cobrar
    mesa = db.query(Mesa).filter(Mesa.id == division.mesa_id).first()
    if mesa:
        # Importante: volcar los cambios en memoria para que los COUNT
        # reflejen el estado real (la sesion usa autoflush=False)
        db.flush()

        pedidos_abiertos = (
            db.query(Pedido)
            .filter(Pedido.mesa_id == mesa.id, Pedido.estado == "abierto")
            .count()
        )
        divisiones_pendientes = (
            db.query(Division)
            .filter(Division.mesa_id == mesa.id, Division.estado == "pendiente")
            .count()
        )
        if pedidos_abiertos == 0 and divisiones_pendientes == 0:
            mesa.estado = "disponible"

    db.commit()

    participante = (
        db.query(Participante)
        .options(joinedload(Participante.items).joinedload(ParticipanteItem.producto))
        .filter(Participante.id == participante_id)
        .first()
    )
    return _participante_out(participante)


@router.post("/division/{division_id}/pagar", response_model=DivisionOut)
def pagar_division(division_id: int, db: Session = Depends(get_db)):
    """Marca como pagados TODOS los clientes de una división."""
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
