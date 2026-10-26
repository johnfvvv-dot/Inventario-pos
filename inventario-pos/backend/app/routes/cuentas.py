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
    FORMAS_PAGO,
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
from app.tiempo import ahora_local

router = APIRouter(tags=["cuentas"])


def _etiqueta_puesto(mesa: Mesa) -> str:
    """Nombre visible de una mesa o de una plaza de barra."""
    if (mesa.tipo or "mesa") == "barra":
        return f"{mesa.grupo or 'Barra'} · Plaza {mesa.posicion or 1}"
    return f"Mesa {mesa.numero}"


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


@router.get("/barra/{numero_barra}", response_model=CuentaMesaOut)
def cuenta_barra(numero_barra: int, db: Session = Depends(get_db)):
    """Cuenta agregada de una barra: todos sus puestos juntos."""
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
            joinedload(Pedido.items).joinedload(PedidoItem.producto),
        )
        .filter(Pedido.mesa_id.in_(ids), Pedido.estado == "abierto")
        .order_by(Pedido.id)
        .all()
    )

    divisiones = [
        d for d in _cargar_divisiones(db, mesas[0].id) if d.estado == "pendiente"
    ]
    for mesa in mesas[1:]:
        divisiones += [
            d for d in _cargar_divisiones(db, mesa.id) if d.estado == "pendiente"
        ]

    total = round(
        sum(p.total for p in pedidos)
        + sum(round(sum(pp.subtotal for pp in d.participantes if not pp.pagado), 2) for d in divisiones),
        2,
    )

    return CuentaMesaOut(
        mesa_id=mesas[0].id,
        mesa_numero=numero_barra,
        estado_mesa=("ocupada" if any(m.estado == "ocupada" for m in mesas) else "disponible"),
        total=total,
        pedidos=[_pedido_out(p) for p in pedidos],
        divisiones=[
            DivisionResumen(
                id=d.id,
                total=d.total,
                total_pendiente=round(
                    sum(pp.subtotal for pp in d.participantes if not pp.pagado), 2
                ),
                estado=d.estado,
                fecha=d.fecha,
                participantes=[
                    ParticipanteResumen(
                        id=pp.id,
                        alias=pp.alias,
                        subtotal=pp.subtotal,
                        pagado=bool(pp.pagado),
                        items=[
                            LineaCuenta(
                                producto_id=item.producto_id,
                                producto_nombre=item.producto.nombre
                                if item.producto
                                else "Desconocido",
                                cantidad=item.cantidad,
                                precio_unitario=item.precio_unitario,
                                subtotal=item.subtotal,
                                alias=pp.alias,
                                participante_id=pp.id,
                            )
                            for item in pp.items
                        ],
                    )
                    for pp in d.participantes
                ],
            )
            for d in divisiones
        ],
    )


@router.post("/mesa/{mesa_id}/cerrar", response_model=CuentaMesaOut)
def cerrar_cuenta(
    mesa_id: int,
    liberar_mesa: bool = False,
    forma_pago: str = "efectivo",
    db: Session = Depends(get_db),
):
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
    if forma_pago not in FORMAS_PAGO:
        raise HTTPException(
            status_code=400,
            detail=f"Forma de pago invalida. Use: {', '.join(FORMAS_PAGO)}",
        )

    ahora = ahora_local()
    for pedido in pedidos:
        pedido.estado = "cerrado"
        pedido.forma_pago = forma_pago
        pedido.fecha_cierre = ahora
        pedido.guardar_origen(mesa)

    # Marcar como pagadas las divisiones pendientes
    divisiones = _cargar_divisiones(db, mesa_id)
    for division in divisiones:
        if division.estado == "pendiente":
            division.estado = "pagada"
            division.forma_pago = forma_pago
            for participante in division.participantes:
                participante.pagado = 1
                participante.forma_pago = forma_pago

    # La mesa permanece OCUPADA: se puede abrir una nueva cuenta
    mesa.estado = "disponible" if liberar_mesa else "ocupada"

    db.commit()

    return consultar_cuenta(mesa_id, db)


@router.post("/barra/{numero_barra}/cerrar", response_model=CuentaMesaOut)
def cerrar_cuenta_barra(
    numero_barra: int,
    liberar_barra: bool = False,
    forma_pago: str = "efectivo",
    db: Session = Depends(get_db),
):
    """Cierra la cuenta completa de una barra (todas sus plazas).

    Por defecto la barra permanece OCUPADA (se puede abrir una nueva cuenta).
    Con liberar_barra=True todas sus plazas quedan DISPONIBLES al terminar.
    """
    grupo = f"Barra {numero_barra}"
    mesas = (
        db.query(Mesa).filter(Mesa.grupo == grupo).order_by(Mesa.posicion).all()
    )
    if not mesas:
        raise HTTPException(status_code=404, detail="Barra no encontrada")

    if forma_pago not in FORMAS_PAGO:
        raise HTTPException(
            status_code=400,
            detail=f"Forma de pago invalida. Use: {', '.join(FORMAS_PAGO)}",
        )

    ids = [m.id for m in mesas]
    ahora = ahora_local()

    # Cerrar pedidos abiertos de todas las plazas
    pedidos = (
        db.query(Pedido)
        .filter(Pedido.mesa_id.in_(ids), Pedido.estado == "abierto")
        .all()
    )
    mesas_por_id = {m.id: m for m in mesas}
    for pedido in pedidos:
        pedido.estado = "cerrado"
        pedido.forma_pago = forma_pago
        pedido.fecha_cierre = ahora
        plaza = mesas_por_id.get(pedido.mesa_id)
        if plaza:
            pedido.guardar_origen(plaza)

    # Marcar como pagadas las divisiones pendientes de cada plaza
    for mesa in mesas:
        for division in _cargar_divisiones(db, mesa.id):
            if division.estado == "pendiente":
                division.estado = "pagada"
                division.forma_pago = forma_pago
                for participante in division.participantes:
                    participante.pagado = 1
                    participante.forma_pago = forma_pago

        mesa.estado = "disponible" if liberar_barra else "ocupada"

    db.commit()

    return cuenta_barra(numero_barra, db)


@router.post("/mesa/{mesa_id}/transferir", response_model=TransferirCuentaOut)
def transferir_cuenta(
    mesa_id: int, destino_id: int, db: Session = Depends(get_db)
):
    """Transfiere una cuenta abierta entre mesas y plazas de barra."""
    origen = db.query(Mesa).filter(Mesa.id == mesa_id).first()
    if not origen:
        raise HTTPException(status_code=404, detail="Mesa de origen no encontrada")

    destino = db.query(Mesa).filter(Mesa.id == destino_id).first()
    if not destino:
        raise HTTPException(status_code=404, detail="Mesa de destino no encontrada")

    if origen.id == destino.id:
        raise HTTPException(
            status_code=400,
            detail="El destino debe ser otra mesa o una plaza de barra distinta",
        )

    db.flush()

    # El destino no debe tener ya una cuenta abierta. En una barra se valida
    # el grupo completo: no se permite sumar la cuenta a una barra ocupada
    # aunque la plaza elegida esté libre.
    es_barra_destino = (destino.tipo or "mesa") == "barra" and bool(destino.grupo)
    if es_barra_destino:
        destinos_grupo = (
            db.query(Mesa).filter(Mesa.grupo == destino.grupo).all()
        )
        ids_destino = [m.id for m in destinos_grupo]
        barra_ocupada = any(m.estado == "ocupada" for m in destinos_grupo)
        detalle_ocupado = "La barra de destino ya tiene una cuenta abierta."
    else:
        ids_destino = [destino.id]
        barra_ocupada = False
        detalle_ocupado = "El destino ya tiene una cuenta abierta."

    pedidos_destino = (
        db.query(func.count(Pedido.id))
        .filter(Pedido.mesa_id.in_(ids_destino), Pedido.estado == "abierto")
        .scalar()
        or 0
    )
    divisiones_destino = (
        db.query(func.count(Division.id))
        .filter(Division.mesa_id.in_(ids_destino), Division.estado == "pendiente")
        .scalar()
        or 0
    )
    if barra_ocupada or pedidos_destino or divisiones_destino:
        raise HTTPException(
            status_code=400,
            detail=detalle_ocupado,
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
        pedido.guardar_origen(destino)
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
            f"Cuenta transferida de {_etiqueta_puesto(origen)} "
            f"a {_etiqueta_puesto(destino)}"
        ),
        mesa_origen=origen.id,
        mesa_destino=destino.id,
        total_transferido=round(total, 2),
    )


@router.post("/dividir", response_model=DivisionOut, status_code=201)
def dividir_cuenta(datos: DivisionCreate, db: Session = Depends(get_db)):
    """Divide la cuenta de una mesa o de una barra completa entre varios clientes.

    En una barra se toma la cuenta agregada de todas sus plazas. Solo se
    divide lo asignado a los alias; el resto queda en un pedido abierto
    (bloque único) para que la cuenta se complete.
    """
    es_barra = datos.barra_numero is not None
    if es_barra:
        grupo = f"Barra {datos.barra_numero}"
        mesas = (
            db.query(Mesa)
            .filter(Mesa.grupo == grupo)
            .order_by(Mesa.posicion)
            .all()
        )
        if not mesas:
            raise HTTPException(status_code=404, detail="Barra no encontrada")
        etiqueta = f"la barra {datos.barra_numero}"
    else:
        if datos.mesa_id is None:
            raise HTTPException(
                status_code=400,
                detail="Indicá la mesa o la barra que se va a dividir",
            )
        mesa = db.query(Mesa).filter(Mesa.id == datos.mesa_id).first()
        if not mesa:
            raise HTTPException(status_code=404, detail="Mesa no encontrada")
        mesas = [mesa]
        etiqueta = "la mesa"

    usuario = db.query(Usuario).filter(Usuario.id == datos.usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if not datos.participantes:
        raise HTTPException(status_code=400, detail="Agrega al menos un cliente")

    ids = [m.id for m in mesas]

    # Pool de productos pendientes (pedidos abiertos de la mesa o de la barra)
    pedidos = (
        db.query(Pedido)
        .options(joinedload(Pedido.items).joinedload(PedidoItem.producto))
        .filter(Pedido.mesa_id.in_(ids), Pedido.estado == "abierto")
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
            status_code=400,
            detail=f"{etiqueta.capitalize()} no tiene productos pendientes para dividir",
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

    # La división se guarda en una plaza concreta: en una barra, la primera
    # plaza que tenga pedidos abiertos (la cuenta se consulta de forma agregada).
    mesa_division = next(
        (m for m in mesas if any(p.mesa_id == m.id for p in pedidos)), mesas[0]
    )

    # Crear la división con los subtotales por alias
    division = Division(
        mesa_id=mesa_division.id,
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
            mesa_id=mesa_division.id,
            usuario_id=usuario.id,
            estado="abierto",
            total=resto_total,
        )
        pedido_resto.guardar_origen(mesa_division)
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

    # La mesa/plaza sigue ocupada
    mesa_division.estado = "ocupada"

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
def pagar_participante(
    participante_id: int,
    forma_pago: str = "efectivo",
    db: Session = Depends(get_db),
):
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

    if forma_pago not in FORMAS_PAGO:
        raise HTTPException(
            status_code=400,
            detail=f"Forma de pago invalida. Use: {', '.join(FORMAS_PAGO)}",
        )

    if not participante.pagado:
        participante.pagado = 1
        participante.forma_pago = forma_pago
        participante.division.forma_pago = forma_pago

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
