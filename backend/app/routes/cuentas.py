"""Endpoints de la cuenta de una mesa: consulta, cierre y división entre clientes."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.cuentas_servicio import (
    alias_existente_en_cuenta,
    bloquear_cuenta,
    cerrar_division_si_corresponde,
    crear_division,
    crear_participante,
    liberar_mesa_si_corresponde,
    obtener_o_crear_division_pendiente,
    recalcular_division,
    recalcular_participante,
    registrar_pago_participante,
    validar_permiso_cantidades,
)
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
    AjusteLineaOut,
    AliasCreate,
    CuentaMesaOut,
    DivisionCreate,
    DivisionOut,
    DivisionResumen,
    LineaCuenta,
    ParticipanteResumen,
    ParticipanteItemOut,
    ParticipanteOut,
    PedidoItemAjuste,
    PedidoOut,
    PedidoItemOut,
    TransferirCuentaOut,
)
from app.tiempo import ahora_local
from app.turnos import exigir_turno_abierto

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
        participante_id=pedido.participante_id,
        alias=pedido.participante.alias if pedido.participante else None,
        es_pago_division=bool(pedido.es_pago_division),
        usuario_cierre_id=pedido.usuario_cierre_id,
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
        forma_pago=participante.forma_pago,
        fecha_pago=participante.fecha_pago,
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
            joinedload(Division.mesa),
            joinedload(Division.participantes).joinedload(Participante.items).joinedload(
                ParticipanteItem.producto
            ),
        )
        .filter(Division.mesa_id == mesa_id)
        .order_by(Division.id.desc())
        .all()
    )


def _cargar_division(db: Session, division_id: int) -> Optional[Division]:
    return (
        db.query(Division)
        .options(
            joinedload(Division.participantes).joinedload(Participante.items).joinedload(
                ParticipanteItem.producto
            )
        )
        .filter(Division.id == division_id)
        .first()
    )


def _resolver_mesas_cuenta(
    db: Session,
    mesa_id: Optional[int],
    barra_numero: Optional[int],
    bloquear: bool = False,
) -> tuple[List[Mesa], Mesa]:
    """Devuelve las plazas de la cuenta y la plaza base para crear divisiones.

    En una barra la cuenta es agregada: se consideran todas sus plazas y la
    base es la primera con pedidos abiertos (o la primera plaza).
    """
    if barra_numero is not None:
        grupo = f"Barra {barra_numero}"
        query = db.query(Mesa).filter(Mesa.grupo == grupo).order_by(Mesa.id)
        if bloquear:
            query = query.with_for_update()
        mesas = query.all()
        if not mesas:
            raise HTTPException(status_code=404, detail="Barra no encontrada")
        ids = [m.id for m in mesas]
        con_pedidos = {
            row[0]
            for row in db.query(Pedido.mesa_id)
            .filter(Pedido.mesa_id.in_(ids), Pedido.estado == "abierto")
            .distinct()
            .all()
        }
        base = next((m for m in mesas if m.id in con_pedidos), mesas[0])
        return mesas, base

    if mesa_id is None:
        raise HTTPException(
            status_code=400, detail="Indicá la mesa o la barra de la cuenta"
        )
    query = db.query(Mesa).filter(Mesa.id == mesa_id)
    if bloquear:
        query = query.with_for_update()
    mesa = query.first()
    if not mesa:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")

    if (mesa.tipo or "mesa") == "barra" and mesa.grupo:
        group_query = db.query(Mesa).filter(Mesa.grupo == mesa.grupo).order_by(Mesa.id)
        if bloquear:
            group_query = group_query.with_for_update()
        return group_query.all(), mesa
    return [mesa], mesa


def _cerrar_pedidos_generales(
    db: Session,
    mesas: List[Mesa],
    forma_pago: str,
    usuario_id: Optional[int],
    ahora,
) -> int:
    """Cierra solo la cuenta general (pedidos sin alias) de las plazas."""
    ids = [m.id for m in mesas]
    pedidos = (
        db.query(Pedido)
        .filter(
            Pedido.mesa_id.in_(ids),
            Pedido.estado == "abierto",
            Pedido.participante_id.is_(None),
        )
        .all()
    )
    if not pedidos:
        raise HTTPException(
            status_code=400,
            detail="No hay una Cuenta General pendiente de cobro.",
        )

    mesas_por_id = {m.id: m for m in mesas}
    for pedido in pedidos:
        pedido.estado = "cerrado"
        pedido.forma_pago = forma_pago
        pedido.fecha_cierre = ahora
        pedido.usuario_cierre_id = usuario_id
        mesa = mesas_por_id.get(pedido.mesa_id)
        if mesa:
            if not pedido.fecha_ocupacion:
                pedido.fecha_ocupacion = (
                    mesa.fecha_ocupacion or pedido.fecha or ahora
                )
            pedido.guardar_origen(mesa)
    return len(pedidos)


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
            joinedload(Pedido.participante),
            joinedload(Pedido.items).joinedload(PedidoItem.producto),
        )
        .filter(Pedido.mesa_id == mesa_id, Pedido.estado == "abierto")
        .order_by(Pedido.id)
        .all()
    )

    divisiones = [d for d in _cargar_divisiones(db, mesa_id) if d.estado == "pendiente"]

    # La cuenta solo suma lo que falta por cobrar:
    # pedidos abiertos + partes de alias que aún no pagaron
    total_general = round(sum(p.total for p in pedidos), 2)
    total_divisiones = round(
        sum(
            round(sum(p.subtotal for p in d.participantes if not p.pagado), 2)
            for d in divisiones
        ),
        2,
    )
    total = round(total_general + total_divisiones, 2)

    return CuentaMesaOut(
        mesa_id=mesa.id,
        mesa_numero=mesa.numero,
        estado_mesa=mesa.estado,
        total=total,
        total_general=total_general,
        total_divisiones=total_divisiones,
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
                        forma_pago=p.forma_pago,
                        fecha_pago=p.fecha_pago,
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
                                participante_item_id=item.id,
                                pedido_id=item.pedido_id,
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
            joinedload(Pedido.participante),
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

    total_general = round(sum(p.total for p in pedidos), 2)
    total_divisiones = round(
        sum(
            round(sum(pp.subtotal for pp in d.participantes if not pp.pagado), 2)
            for d in divisiones
        ),
        2,
    )
    total = round(total_general + total_divisiones, 2)

    return CuentaMesaOut(
        mesa_id=mesas[0].id,
        mesa_numero=numero_barra,
        estado_mesa=("ocupada" if any(m.estado == "ocupada" for m in mesas) else "disponible"),
        total=total,
        total_general=total_general,
        total_divisiones=total_divisiones,
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
                        forma_pago=pp.forma_pago,
                        fecha_pago=pp.fecha_pago,
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
                                participante_item_id=item.id,
                                pedido_id=item.pedido_id,
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
    usuario_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Cierra la cuenta completa de la mesa (pedidos + divisiones).

    Por defecto la mesa permanece OCUPADA (se puede abrir una nueva cuenta).
    Con liberar_mesa=True la mesa queda DISPONIBLE al terminar.
    """
    exigir_turno_abierto(db)

    mesa = db.query(Mesa).filter(Mesa.id == mesa_id).first()
    if not mesa:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")

    bloquear_cuenta(db, mesa)

    if forma_pago not in FORMAS_PAGO:
        raise HTTPException(
            status_code=400,
            detail=f"Forma de pago invalida. Use: {', '.join(FORMAS_PAGO)}",
        )

    ahora = ahora_local()

    # Cerrar pedidos abiertos (la cuenta general)
    pedidos = (
        db.query(Pedido)
        .options(
            joinedload(Pedido.mesa),
            joinedload(Pedido.usuario),
            joinedload(Pedido.items).joinedload(PedidoItem.producto),
        )
        .filter(
            Pedido.mesa_id == mesa_id,
            Pedido.estado == "abierto",
            Pedido.participante_id.is_(None),
        )
        .all()
    )
    for pedido in pedidos:
        pedido.estado = "cerrado"
        pedido.forma_pago = forma_pago
        pedido.fecha_cierre = ahora
        pedido.usuario_cierre_id = usuario_id
        if not pedido.fecha_ocupacion:
            pedido.fecha_ocupacion = mesa.fecha_ocupacion or pedido.fecha or ahora
        pedido.guardar_origen(mesa)

    # Cobrar solo las partes impagas. Los alias que ya pagaron conservan su
    # forma de pago y su fecha original.
    divisiones = _cargar_divisiones(db, mesa_id)
    for division in divisiones:
        if division.estado != "pendiente":
            continue
        if not division.fecha_ocupacion:
            division.fecha_ocupacion = mesa.fecha_ocupacion or division.fecha or ahora
        for participante in division.participantes:
            registrar_pago_participante(
                db,
                participante,
                forma_pago,
                ahora,
                usuario_cierre_id=usuario_id or division.usuario_id,
            )
        db.flush()
        recalcular_division(db, division)
        cerrar_division_si_corresponde(db, division, forma_pago)

    # La mesa permanece OCUPADA: se puede abrir una nueva cuenta
    mesa.estado = "disponible" if liberar_mesa else "ocupada"
    if liberar_mesa:
        mesa.fecha_ocupacion = None

    db.commit()

    return consultar_cuenta(mesa_id, db)


@router.post("/barra/{numero_barra}/cerrar", response_model=CuentaMesaOut)
def cerrar_cuenta_barra(
    numero_barra: int,
    liberar_barra: bool = False,
    forma_pago: str = "efectivo",
    usuario_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Cierra la cuenta completa de una barra (todas sus plazas).

    Por defecto la barra permanece OCUPADA (se puede abrir una nueva cuenta).
    Con liberar_barra=True todas sus plazas quedan DISPONIBLES al terminar.
    """
    exigir_turno_abierto(db)

    grupo = f"Barra {numero_barra}"
    mesas = (
        db.query(Mesa)
        .filter(Mesa.grupo == grupo)
        .order_by(Mesa.id)
        .with_for_update()
        .all()
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

    # Cerrar pedidos abiertos de todas las plazas (solo cuenta general)
    pedidos = (
        db.query(Pedido)
        .filter(
            Pedido.mesa_id.in_(ids),
            Pedido.estado == "abierto",
            Pedido.participante_id.is_(None),
        )
        .all()
    )
    mesas_por_id = {m.id: m for m in mesas}
    for pedido in pedidos:
        pedido.estado = "cerrado"
        pedido.forma_pago = forma_pago
        pedido.fecha_cierre = ahora
        pedido.usuario_cierre_id = usuario_id
        plaza = mesas_por_id.get(pedido.mesa_id)
        if plaza:
            if not pedido.fecha_ocupacion:
                pedido.fecha_ocupacion = plaza.fecha_ocupacion or pedido.fecha or ahora
            pedido.guardar_origen(plaza)

    # Cobrar solo las partes impagas de cada plaza. Los alias que ya pagaron
    # conservan su forma de pago y su fecha original.
    for mesa in mesas:
        for division in _cargar_divisiones(db, mesa.id):
            if division.estado != "pendiente":
                continue
            if not division.fecha_ocupacion:
                division.fecha_ocupacion = (
                    mesa.fecha_ocupacion or division.fecha or ahora
                )
            for participante in division.participantes:
                registrar_pago_participante(
                    db,
                    participante,
                    forma_pago,
                    ahora,
                    usuario_cierre_id=usuario_id or division.usuario_id,
                )
            db.flush()
            recalcular_division(db, division)
            cerrar_division_si_corresponde(db, division, forma_pago)

        mesa.estado = "disponible" if liberar_barra else "ocupada"
        if liberar_barra:
            mesa.fecha_ocupacion = None

    db.commit()

    return cuenta_barra(numero_barra, db)


@router.post("/mesa/{mesa_id}/transferir", response_model=TransferirCuentaOut)
def transferir_cuenta(
    mesa_id: int, destino_id: int, db: Session = Depends(get_db)
):
    """Transfiere una cuenta abierta entre mesas y plazas de barra."""
    exigir_turno_abierto(db)

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

    bloquear_cuenta(db, origen)
    bloquear_cuenta(db, destino)
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
        db.query(Pedido)
        .filter(Pedido.mesa_id.in_(ids_destino), Pedido.estado == "abierto")
        .count()
    )
    divisiones_destino = (
        db.query(Division)
        .filter(Division.mesa_id.in_(ids_destino), Division.estado == "pendiente")
        .count()
    )
    if barra_ocupada or pedidos_destino or divisiones_destino:
        raise HTTPException(
            status_code=400,
            detail=detalle_ocupado,
        )

    # Mover pedidos abiertos (cuenta general)
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

    # Mover divisiones pendientes y los pedidos asignados a sus alias.
    # Los pedidos financieros (es_pago_division=1) son históricos y no se mueven.
    divisiones = _cargar_divisiones(db, origen.id)
    ids_participantes = []
    for division in divisiones:
        if division.estado != "pendiente":
            continue
        division.mesa_id = destino.id
        ids_participantes.extend(p.id for p in division.participantes)
        total += round(
            sum(p.subtotal for p in division.participantes if not p.pagado), 2
        )

    if ids_participantes:
        asignados = (
            db.query(Pedido)
            .filter(
                Pedido.participante_id.in_(ids_participantes),
                Pedido.estado == "dividido",
                Pedido.es_pago_division == 0,
            )
            .all()
        )
        for pedido in asignados:
            pedido.mesa_id = destino.id
            pedido.guardar_origen(destino)

    # Estados de las mesas
    origen.estado = "disponible"
    origen.fecha_ocupacion = None
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
    exigir_turno_abierto(db)

    es_barra = datos.barra_numero is not None
    if es_barra:
        grupo = f"Barra {datos.barra_numero}"
        mesas = (
            db.query(Mesa)
            .filter(Mesa.grupo == grupo)
            .order_by(Mesa.id)
            .with_for_update()
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
        mesa = (
            db.query(Mesa)
            .filter(Mesa.id == datos.mesa_id)
            .with_for_update()
            .first()
        )
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
    fecha_ocupacion = mesa_division.fecha_ocupacion or ahora_local()
    division = crear_division(db, mesa_division, usuario.id, fecha_ocupacion)

    for participante in datos.participantes:
        items_preparados = [
            (
                pool[item.producto_id]["producto"],
                item.cantidad,
                pool[item.producto_id]["precio_unitario"],
            )
            for item in participante.items
        ]
        if not items_preparados:
            continue
        crear_participante(db, division, participante.alias, items_preparados)

    recalcular_division(db, division)
    if division.total <= 0:
        db.rollback()
        raise HTTPException(status_code=400, detail="La división no tiene productos")

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
            fecha_ocupacion=fecha_ocupacion,
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
    usuario_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Cierra la división de UN alias (el cliente paga su parte).

    La cuenta general de la mesa sigue abierta para los demás clientes.
    La mesa se libera solo cuando todos pagaron y no quedan pedidos abiertos.
    """
    exigir_turno_abierto(db)

    participante = (
        db.query(Participante)
        .options(
            joinedload(Participante.items).joinedload(ParticipanteItem.producto),
            joinedload(Participante.division).joinedload(Division.mesa),
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

    division = participante.division
    if not division:
        raise HTTPException(
            status_code=409, detail="El cliente no pertenece a una división activa."
        )
    mesa = division.mesa
    if not mesa:
        raise HTTPException(status_code=404, detail="Mesa de la división no encontrada")

    bloquear_cuenta(db, mesa)
    db.refresh(participante)
    division = db.query(Division).filter(Division.id == division.id).first()

    ahora = ahora_local()
    registrar_pago_participante(
        db,
        participante,
        forma_pago,
        ahora,
        usuario_cierre_id=usuario_id or division.usuario_id,
    )
    db.flush()
    recalcular_division(db, division)
    cerrar_division_si_corresponde(db, division, forma_pago)

    liberar_mesa_si_corresponde(db, mesa.id)
    db.commit()

    participante = (
        db.query(Participante)
        .options(joinedload(Participante.items).joinedload(ParticipanteItem.producto))
        .filter(Participante.id == participante_id)
        .first()
    )
    return _participante_out(participante)


@router.post("/division/{division_id}/pagar", response_model=DivisionOut)
def pagar_division(
    division_id: int,
    forma_pago: str = "efectivo",
    usuario_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Marca como pagados TODOS los clientes de una división."""
    exigir_turno_abierto(db)

    division = (
        db.query(Division)
        .options(
            joinedload(Division.participantes).joinedload(Participante.items).joinedload(
                ParticipanteItem.producto
            ),
            joinedload(Division.mesa),
        )
        .filter(Division.id == division_id)
        .first()
    )
    if not division:
        raise HTTPException(status_code=404, detail="División no encontrada")

    if forma_pago not in FORMAS_PAGO:
        raise HTTPException(
            status_code=400,
            detail=f"Forma de pago invalida. Use: {', '.join(FORMAS_PAGO)}",
        )

    mesa = division.mesa
    if mesa:
        bloquear_cuenta(db, mesa)
        db.refresh(division)

    ahora = ahora_local()
    for participante in division.participantes:
        registrar_pago_participante(
            db,
            participante,
            forma_pago,
            ahora,
            usuario_cierre_id=usuario_id or division.usuario_id,
        )

    db.flush()
    recalcular_division(db, division)
    cerrar_division_si_corresponde(db, division, forma_pago)

    if mesa:
        liberar_mesa_si_corresponde(db, mesa.id)

    db.commit()
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
    return _division_out(division)


@router.post("/alias", response_model=DivisionOut, status_code=201)
def crear_alias(datos: AliasCreate, db: Session = Depends(get_db)):
    """Crea un alias vacío en la cuenta abierta de una mesa o barra.

    Reutiliza la misma estructura de divisiones que ``Dividir Cuenta``. El
    alias se suma a la división pendiente más reciente de la cuenta o se crea
    una nueva si todavía no hay ninguna.
    """
    exigir_turno_abierto(db)

    mesas, mesa_base = _resolver_mesas_cuenta(
        db, datos.mesa_id, datos.barra_numero, bloquear=True
    )

    usuario = db.query(Usuario).filter(Usuario.id == datos.usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    alias = datos.alias.strip()
    if not alias:
        raise HTTPException(status_code=400, detail="El alias no puede estar vacío")

    ids = [m.id for m in mesas]
    pedidos_abiertos = (
        db.query(Pedido)
        .filter(Pedido.mesa_id.in_(ids), Pedido.estado == "abierto")
        .count()
    )
    divisiones_pendientes = (
        db.query(Division)
        .filter(Division.mesa_id.in_(ids), Division.estado == "pendiente")
        .count()
    )
    if not pedidos_abiertos and not divisiones_pendientes:
        raise HTTPException(
            status_code=400,
            detail="La cuenta no tiene productos pendientes para asignar.",
        )

    existente = alias_existente_en_cuenta(db, mesas, alias)
    if existente:
        raise HTTPException(
            status_code=409,
            detail=f"Ya existe un alias activo llamado {existente.alias}.",
        )

    division = obtener_o_crear_division_pendiente(db, mesa_base, usuario.id)
    crear_participante(db, division, alias)

    mesa_base.estado = "ocupada"
    if not mesa_base.fecha_ocupacion:
        mesa_base.fecha_ocupacion = ahora_local()

    db.commit()

    division = _cargar_division(db, division.id)
    return _division_out(division)


@router.put("/participante-item/{item_id}", response_model=AjusteLineaOut)
def ajustar_linea_alias(
    item_id: int,
    datos: PedidoItemAjuste,
    usuario_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Ajusta la cantidad de una línea de la cuenta de un alias.

    ``cantidad=0`` elimina la línea. Si el alias queda vacío se elimina; si la
    división queda sin clientes también se elimina y la mesa se libera cuando
    no queda nada pendiente. Requiere el permiso ``editar_cantidades``.
    """
    exigir_turno_abierto(db)
    validar_permiso_cantidades(db, usuario_id)

    item = (
        db.query(ParticipanteItem)
        .options(
            joinedload(ParticipanteItem.participante)
            .joinedload(Participante.division)
            .joinedload(Division.mesa)
        )
        .filter(ParticipanteItem.id == item_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Línea de la cuenta no encontrada")

    participante = item.participante
    division = participante.division if participante else None
    mesa = division.mesa if division else None
    if not participante or not division or not mesa:
        raise HTTPException(
            status_code=409, detail="La línea no pertenece a una cuenta activa."
        )
    if participante.pagado or division.estado != "pendiente":
        raise HTTPException(
            status_code=409,
            detail="La parte de este cliente ya fue cobrada y no se puede editar.",
        )

    bloquear_cuenta(db, mesa)

    # Volver a leer después del bloqueo para evitar carreras con otro cobro.
    item = (
        db.query(ParticipanteItem)
        .options(
            joinedload(ParticipanteItem.participante)
            .joinedload(Participante.division)
            .joinedload(Division.mesa)
        )
        .filter(ParticipanteItem.id == item_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Línea de la cuenta no encontrada")
    participante = item.participante
    division = participante.division
    mesa = division.mesa
    if participante.pagado or division.estado != "pendiente":
        raise HTTPException(
            status_code=409,
            detail="La parte de este cliente ya fue cobrada y no se puede editar.",
        )

    cantidad = datos.cantidad

    # Misma lógica de inventario que el ajuste de un pedido general: la
    # diferencia se descuenta del stock y, al eliminar la línea, se devuelve.
    producto = (
        db.query(Producto)
        .filter(Producto.id == item.producto_id)
        .with_for_update()
        .first()
    )
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    diferencia = cantidad - item.cantidad
    if diferencia > 0 and producto.stock < diferencia:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Stock insuficiente de {producto.nombre}: "
                f"disponible {producto.stock}"
            ),
        )
    producto.stock -= diferencia

    pedido_item = None
    if item.pedido_item_id:
        pedido_item = (
            db.query(PedidoItem)
            .filter(PedidoItem.id == item.pedido_item_id)
            .first()
        )

    if cantidad == 0:
        if pedido_item:
            pedido = pedido_item.pedido
            db.delete(pedido_item)
            db.flush()
            restantes_pedido = (
                db.query(PedidoItem)
                .filter(PedidoItem.pedido_id == pedido.id)
                .all()
            )
            if restantes_pedido:
                pedido.total = round(
                    sum(linea.subtotal for linea in restantes_pedido), 2
                )
            else:
                db.delete(pedido)
        db.delete(item)
        db.flush()
    else:
        item.cantidad = cantidad
        item.subtotal = round(float(item.precio_unitario) * cantidad, 2)
        if pedido_item:
            pedido_item.cantidad = cantidad
            pedido_item.subtotal = item.subtotal
            db.flush()
            pedido = db.query(Pedido).filter(Pedido.id == pedido_item.pedido_id).first()
            if pedido:
                pedido.total = round(
                    sum(
                        linea.subtotal
                        for linea in db.query(PedidoItem)
                        .filter(PedidoItem.pedido_id == pedido.id)
                        .all()
                    ),
                    2,
                )

    recalcular_participante(db, participante)
    restantes_alias = (
        db.query(ParticipanteItem)
        .filter(ParticipanteItem.participante_id == participante.id)
        .count()
    )

    eliminado = restantes_alias == 0
    division_id_out: Optional[int] = division.id
    total_division = 0.0
    if eliminado:
        division_id = division.id
        db.delete(participante)
        db.flush()
        otros_clientes = (
            db.query(Participante)
            .filter(Participante.division_id == division_id)
            .count()
        )
        if otros_clientes == 0:
            db.delete(division)
            db.flush()
            division_id_out = None
            liberar_mesa_si_corresponde(db, mesa.id)
        else:
            recalcular_division(db, division)
            total_division = division.total
            liberar_mesa_si_corresponde(db, mesa.id)
        participante_id_out = None
        subtotal_out = 0.0
    else:
        recalcular_division(db, division)
        total_division = division.total
        participante_id_out = participante.id
        subtotal_out = participante.subtotal

    db.commit()

    return AjusteLineaOut(
        participante_id=participante_id_out,
        division_id=division_id_out,
        eliminado=eliminado,
        subtotal=subtotal_out,
        total_division=total_division,
    )


@router.post("/mesa/{mesa_id}/cerrar-general", response_model=CuentaMesaOut)
def cerrar_general_mesa(
    mesa_id: int,
    forma_pago: str = "efectivo",
    usuario_id: Optional[int] = None,
    liberar_mesa: bool = True,
    db: Session = Depends(get_db),
):
    """Cobra solo la Cuenta General de una mesa, sin tocar las divisiones."""
    exigir_turno_abierto(db)

    mesas, _ = _resolver_mesas_cuenta(db, mesa_id, None, bloquear=True)
    if forma_pago not in FORMAS_PAGO:
        raise HTTPException(
            status_code=400,
            detail=f"Forma de pago invalida. Use: {', '.join(FORMAS_PAGO)}",
        )

    ahora = ahora_local()
    _cerrar_pedidos_generales(db, mesas, forma_pago, usuario_id, ahora)

    if liberar_mesa:
        for mesa in mesas:
            liberar_mesa_si_corresponde(db, mesa.id)

    db.commit()
    return consultar_cuenta(mesa_id, db)


@router.post("/barra/{numero_barra}/cerrar-general", response_model=CuentaMesaOut)
def cerrar_general_barra(
    numero_barra: int,
    forma_pago: str = "efectivo",
    usuario_id: Optional[int] = None,
    liberar_barra: bool = True,
    db: Session = Depends(get_db),
):
    """Cobra solo la Cuenta General agregada de una barra."""
    exigir_turno_abierto(db)

    mesas, _ = _resolver_mesas_cuenta(db, None, numero_barra, bloquear=True)
    if forma_pago not in FORMAS_PAGO:
        raise HTTPException(
            status_code=400,
            detail=f"Forma de pago invalida. Use: {', '.join(FORMAS_PAGO)}",
        )

    ahora = ahora_local()
    _cerrar_pedidos_generales(db, mesas, forma_pago, usuario_id, ahora)

    if liberar_barra:
        for mesa in mesas:
            liberar_mesa_si_corresponde(db, mesa.id)

    db.commit()
    return cuenta_barra(numero_barra, db)


@router.get("/mesa/{mesa_id}/divisiones", response_model=List[DivisionOut])
def listar_divisiones(mesa_id: int, db: Session = Depends(get_db)):
    """Historial de divisiones de la mesa."""
    return [_division_out(d) for d in _cargar_divisiones(db, mesa_id)]
