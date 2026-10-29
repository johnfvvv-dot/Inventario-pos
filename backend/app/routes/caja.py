"""Endpoints del corte de caja (turnos) y resumen de ventas por forma de pago."""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload, selectinload

from app.database import get_db
from app.models import (
    Mesa,
    Pedido,
    PedidoItem,
    Producto,
    TurnoCaja,
    Usuario,
    etiqueta_desde_numero_historico,
)
from app.schemas import (
    AbrirTurnoOut,
    CerrarTurnoIn,
    ResumenCajaOut,
    TotalesFormaPago,
    TurnoCajaOut,
)
from app.tiempo import ahora_local

router = APIRouter(tags=["caja"])

FORMAS_PAGO = ["efectivo", "tarjeta", "transferencia"]


def _totales_por_forma_pago(
    db: Session, desde: Optional[datetime] = None, hasta: Optional[datetime] = None
) -> TotalesFormaPago:
    """Suma los pedidos cerrados del periodo agrupados por forma de pago."""
    query = db.query(Pedido).filter(Pedido.estado == "cerrado")
    if desde:
        query = query.filter(Pedido.fecha_cierre >= desde)
    if hasta:
        query = query.filter(Pedido.fecha_cierre <= hasta)

    filas = (
        query.with_entities(
            Pedido.forma_pago, func.count(Pedido.id), func.coalesce(func.sum(Pedido.total), 0.0)
        )
        .group_by(Pedido.forma_pago)
        .all()
    )

    totales = {forma: 0.0 for forma in FORMAS_PAGO}
    operaciones = 0
    for forma, cantidad, total in filas:
        clave = forma if forma in totales else "efectivo"
        totales[clave] = round(totales[clave] + float(total or 0), 2)
        operaciones += cantidad or 0

    return TotalesFormaPago(
        efectivo=totales["efectivo"],
        tarjeta=totales["tarjeta"],
        transferencia=totales["transferencia"],
        total=round(sum(totales.values()), 2),
        operaciones=operaciones,
    )


def _ganancia_periodo(
    db: Session, desde: Optional[datetime] = None, hasta: Optional[datetime] = None
) -> float:
    """Ganancia de los pedidos cerrados del periodo.

    Ganancia = (precio de venta - precio de compra) x cantidad vendida.
    El precio de venta es el guardado en el ítem al momento de la venta y el
    de compra el registrado en el producto (0 si es anterior a esta versión).
    """
    consulta = (
        db.query(
            func.coalesce(
                func.sum(
                    (
                        PedidoItem.precio_unitario
                        - func.coalesce(Producto.precio_compra, 0.0)
                    )
                    * PedidoItem.cantidad
                ),
                0.0,
            )
        )
        .select_from(PedidoItem)
        .join(Pedido, Pedido.id == PedidoItem.pedido_id)
        .outerjoin(Producto, Producto.id == PedidoItem.producto_id)
        .filter(Pedido.estado == "cerrado")
    )
    if desde:
        consulta = consulta.filter(Pedido.fecha_cierre >= desde)
    if hasta:
        consulta = consulta.filter(Pedido.fecha_cierre <= hasta)

    return round(float(consulta.scalar() or 0.0), 2)


def _turno_out(db: Session, turno: TurnoCaja) -> TurnoCajaOut:
    hasta = turno.fecha_cierre or ahora_local()
    totales = _totales_por_forma_pago(db, turno.fecha_apertura, hasta)
    usuario = db.query(Usuario).filter(Usuario.id == turno.usuario_id).first()
    return TurnoCajaOut(
        id=turno.id,
        usuario_nombre=(
            (usuario.nombre or usuario.alias) if usuario else "Desconocido"
        ),
        fecha_apertura=turno.fecha_apertura,
        fecha_cierre=turno.fecha_cierre,
        observaciones=turno.observaciones,
        estado=turno.estado,
        totales=totales,
        ganancia=_ganancia_periodo(db, turno.fecha_apertura, hasta),
    )


def _turnos_out(db: Session, turnos: List[TurnoCaja]) -> List[TurnoCajaOut]:
    """Convierte varios turnos con consultas por lote.

    Sin esto, cada turno ejecuta tres consultas (totales, ganancia y usuario)
    y el historial de 20 turnos termina haciendo más de 60 consultas.
    """
    if not turnos:
        return []

    ahora = ahora_local()
    inicio = min(t.fecha_apertura for t in turnos)
    fin = max((t.fecha_cierre or ahora) for t in turnos)

    pedidos = (
        db.query(Pedido)
        .filter(
            Pedido.estado == "cerrado",
            Pedido.fecha_cierre.isnot(None),
            Pedido.fecha_cierre >= inicio,
            Pedido.fecha_cierre <= fin,
        )
        .all()
    )
    pedidos_por_id = {p.id: p for p in pedidos}
    items = (
        db.query(PedidoItem)
        .filter(PedidoItem.pedido_id.in_(list(pedidos_por_id)))
        .all()
        if pedidos_por_id
        else []
    )
    costos = {
        p.id: float(p.precio_compra or 0.0) for p in db.query(Producto).all()
    }
    usuarios = {
        u.id: (u.nombre or u.alias)
        for u in db.query(Usuario)
        .filter(Usuario.id.in_({t.usuario_id for t in turnos}))
        .all()
    }

    items_por_pedido: dict = {}
    for item in items:
        items_por_pedido.setdefault(item.pedido_id, []).append(item)

    resultado = []
    for turno in turnos:
        hasta = turno.fecha_cierre or ahora
        totales = {forma: 0.0 for forma in FORMAS_PAGO}
        operaciones = 0
        ganancia = 0.0

        for pedido in pedidos:
            if not pedido.fecha_cierre:
                continue
            if pedido.fecha_cierre < turno.fecha_apertura or pedido.fecha_cierre > hasta:
                continue
            forma = pedido.forma_pago if pedido.forma_pago in FORMAS_PAGO else "efectivo"
            totales[forma] = round(totales[forma] + (pedido.total or 0.0), 2)
            operaciones += 1
            for item in items_por_pedido.get(pedido.id, []):
                costo = costos.get(item.producto_id, 0.0)
                ganancia += (item.precio_unitario - costo) * item.cantidad

        resultado.append(
            TurnoCajaOut(
                id=turno.id,
                usuario_nombre=usuarios.get(turno.usuario_id, "Desconocido"),
                fecha_apertura=turno.fecha_apertura,
                fecha_cierre=turno.fecha_cierre,
                observaciones=turno.observaciones,
                estado=turno.estado,
                totales=TotalesFormaPago(
                    efectivo=totales["efectivo"],
                    tarjeta=totales["tarjeta"],
                    transferencia=totales["transferencia"],
                    total=round(sum(totales.values()), 2),
                    operaciones=operaciones,
                ),
                ganancia=round(ganancia, 2),
            )
        )
    return resultado


@router.get("/anios-ventas")
def anios_ventas(db: Session = Depends(get_db)):
    """Años con ventas registradas (pedidos cerrados).

    Se genera dinámicamente desde los datos, de modo que un año sin ventas
    no aparece como opción en el filtro de Reportes.
    """
    anios = (
        db.query(func.extract("year", Pedido.fecha_cierre))
        .filter(Pedido.estado == "cerrado", Pedido.fecha_cierre.isnot(None))
        .distinct()
        .all()
    )
    return sorted(
        {int(fila[0]) for fila in anios if fila[0] is not None}, reverse=True
    )


@router.get("/turno-ayer", response_model=Optional[TurnoCajaOut])
def turno_ayer(db: Session = Depends(get_db)):
    """Turno cuyo día de apertura fue ayer.

    Se identifica por ``fecha_apertura``, no por ``fecha_cierre``, de modo
    que un turno abierto ayer por la noche y cerrado de madrugada hoy sigue
    contando como el turno de ayer. Si hubiera varios, se devuelve el último
    abierto ese día.
    """
    ayer = (ahora_local() - timedelta(days=1)).date()
    inicio = datetime.combine(ayer, datetime.min.time())
    fin = inicio + timedelta(days=1)

    turno = (
        db.query(TurnoCaja)
        .filter(
            TurnoCaja.fecha_apertura >= inicio,
            TurnoCaja.fecha_apertura < fin,
        )
        .order_by(TurnoCaja.fecha_apertura.desc(), TurnoCaja.id.desc())
        .first()
    )
    return _turno_out(db, turno) if turno else None


@router.get("/turno-actual", response_model=Optional[TurnoCajaOut])
def turno_actual(db: Session = Depends(get_db)):
    """Devuelve el turno de caja abierto (o null si no hay ninguno)."""
    turno = (
        db.query(TurnoCaja)
        .filter(TurnoCaja.estado == "abierto")
        .order_by(TurnoCaja.id.desc())
        .first()
    )
    return _turno_out(db, turno) if turno else None


@router.post("/abrir", response_model=AbrirTurnoOut)
def abrir_turno(usuario_id: int = 1, db: Session = Depends(get_db)):
    """Abre un nuevo turno de caja."""
    abierto = (
        db.query(TurnoCaja).filter(TurnoCaja.estado == "abierto").first()
    )
    if abierto:
        raise HTTPException(
            status_code=400, detail="Ya hay un turno de caja abierto"
        )

    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    turno = TurnoCaja(usuario_id=usuario.id, estado="abierto")
    db.add(turno)
    db.commit()
    db.refresh(turno)
    return AbrirTurnoOut(
        mensaje="Turno de caja abierto", turno=_turno_out(db, turno)
    )


@router.post("/cerrar", response_model=TurnoCajaOut)
def cerrar_turno(datos: CerrarTurnoIn, db: Session = Depends(get_db)):
    """Cierra el turno de caja abierto."""
    turno = (
        db.query(TurnoCaja)
        .filter(TurnoCaja.estado == "abierto")
        .order_by(TurnoCaja.id.desc())
        .first()
    )
    if not turno:
        raise HTTPException(status_code=400, detail="No hay un turno de caja abierto")

    turno.estado = "cerrado"
    turno.fecha_cierre = ahora_local()
    turno.observaciones = datos.observaciones
    db.commit()
    db.refresh(turno)
    return _turno_out(db, turno)


@router.get("/turnos", response_model=List[TurnoCajaOut])
def listar_turnos(limite: int = 20, db: Session = Depends(get_db)):
    """Historial de turnos de caja."""
    turnos = (
        db.query(TurnoCaja).order_by(TurnoCaja.id.desc()).limit(limite).all()
    )
    return _turnos_out(db, turnos)


@router.get("/resumen", response_model=ResumenCajaOut)
def resumen_caja(
    dias: int = 1,
    offset_dias: int = 0,
    desde: Optional[datetime] = None,
    hasta: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    """Resumen de ventas y ganancias de un rango de días calendario.

    ``dias=1`` y ``offset_dias=0`` abarcan únicamente el día actual desde las
    00:00 hasta ahora. ``offset_dias=1`` permite consultar ayer completo
    (00:00 a 23:59:59.999999). Para N días se incluyen días completos desde la
    medianoche, de modo que no se mezclan ventas de fechas distintas.

    Si se envían ``desde`` y ``hasta`` (ISO), se usa ese rango exacto; es lo
    que permite consultar un mes concreto desde Reportes.
    """
    dias = max(1, min(dias, 365))
    offset_dias = max(0, min(offset_dias, 365))

    ahora = ahora_local()
    hoy_inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)

    if desde is not None and hasta is not None:
        rango_desde, rango_hasta = desde, hasta
    elif offset_dias:
        rango_desde = hoy_inicio - timedelta(days=offset_dias + dias - 1)
        rango_hasta = (
            hoy_inicio
            - timedelta(days=offset_dias - 1)
            - timedelta(microseconds=1)
        )
    else:
        rango_desde = hoy_inicio - timedelta(days=dias - 1)
        rango_hasta = ahora

    totales = _totales_por_forma_pago(db, rango_desde, rango_hasta)

    cerrados = (
        db.query(Pedido)
        .filter(
            Pedido.estado == "cerrado",
            Pedido.fecha_cierre.isnot(None),
            Pedido.fecha_cierre >= rango_desde,
            Pedido.fecha_cierre <= rango_hasta,
        )
        .all()
    )
    mesas = {p.mesa_id for p in cerrados if p.mesa_id}

    por_forma = {
        "efectivo": totales.efectivo,
        "tarjeta": totales.tarjeta,
        "transferencia": totales.transferencia,
    }

    return ResumenCajaOut(
        desde=rango_desde,
        hasta=rango_hasta,
        totales=totales,
        ganancia=_ganancia_periodo(db, rango_desde, rango_hasta),
        pedidos_cerrados=len(cerrados),
        mesas_atendidas=len(mesas),
        por_forma_pago=por_forma,
    )


@router.get("/ventas-por-dia")
def ventas_por_dia(
    dias: int = 14,
    offset_dias: int = 0,
    desde: Optional[datetime] = None,
    hasta: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    """Serie diaria de ventas y ganancias + top de productos.

    Acepta ``dias``/``offset_dias`` (misma semántica que el resumen) o un
    rango explícito ``desde``/``hasta`` en ISO, que es lo que usa Reportes
    para los filtros de día, semana y mes.
    """
    ahora = ahora_local()

    if desde is not None and hasta is not None:
        inicio, fin = desde, hasta
    else:
        dias = max(1, min(dias, 90))
        offset_dias = max(0, min(offset_dias, 365))
        hoy_inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
        if offset_dias:
            inicio = hoy_inicio - timedelta(days=offset_dias + dias - 1)
            fin = (
                hoy_inicio
                - timedelta(days=offset_dias - 1)
                - timedelta(microseconds=1)
            )
        else:
            inicio = hoy_inicio - timedelta(days=dias - 1)
            fin = ahora

    if fin < inicio:
        inicio, fin = fin, inicio
    if (fin.date() - inicio.date()).days > 366:
        inicio = fin - timedelta(days=366)

    dias_rango = (fin.date() - inicio.date()).days + 1

    cerrados = (
        db.query(Pedido)
        .filter(
            Pedido.estado == "cerrado",
            Pedido.fecha_cierre.isnot(None),
            Pedido.fecha_cierre >= inicio,
            Pedido.fecha_cierre <= fin,
        )
        .all()
    )

    serie: dict = {}
    for i in range(dias_rango):
        dia = (inicio + timedelta(days=i)).date()
        serie[dia] = {
            "efectivo": 0.0,
            "tarjeta": 0.0,
            "transferencia": 0.0,
            "total": 0.0,
            "ganancia": 0.0,
        }

    pedidos_ids = [p.id for p in cerrados]
    items = (
        db.query(PedidoItem).filter(PedidoItem.pedido_id.in_(pedidos_ids)).all()
        if pedidos_ids
        else []
    )

    # Costo actual por producto (0 si el producto ya no existe).
    costos = {
        p.id: float(p.precio_compra or 0.0) for p in db.query(Producto).all()
    }

    items_por_pedido: dict = {}
    for item in items:
        items_por_pedido.setdefault(item.pedido_id, []).append(item)

    for pedido in cerrados:
        if not pedido.fecha_cierre:
            continue
        clave = pedido.fecha_cierre.date()
        if clave not in serie:
            continue
        forma = pedido.forma_pago if pedido.forma_pago in FORMAS_PAGO else "efectivo"
        serie[clave][forma] = round(serie[clave][forma] + (pedido.total or 0), 2)
        serie[clave]["total"] = round(serie[clave]["total"] + (pedido.total or 0), 2)

        for item in items_por_pedido.get(pedido.id, []):
            costo = costos.get(item.producto_id, 0.0)
            serie[clave]["ganancia"] = round(
                serie[clave]["ganancia"]
                + (item.precio_unitario - costo) * item.cantidad,
                2,
            )

    etiquetas = [str(d) for d in sorted(serie.keys())]
    datos = [serie[d] for d in sorted(serie.keys())]

    # Top de productos vendidos en el periodo
    conteo: dict = {}
    for item in items:
        clave = item.producto_id
        if clave not in conteo:
            conteo[clave] = {"producto_id": clave, "cantidad": 0, "total": 0.0}
        conteo[clave]["cantidad"] += item.cantidad
        conteo[clave]["total"] = round(
            conteo[clave]["total"] + (item.subtotal or 0), 2
        )

    nombres = {}
    if conteo:
        nombres = {
            p.id: p.nombre
            for p in db.query(Producto)
            .filter(Producto.id.in_(list(conteo.keys())))
            .all()
        }

    for clave in conteo:
        conteo[clave]["nombre"] = nombres.get(clave, f"#{clave}")

    top = sorted(conteo.values(), key=lambda x: x["cantidad"], reverse=True)[:10]

    return {
        "etiquetas": etiquetas,
        "serie": datos,
        "top_productos": top,
        "dias": dias_rango,
        "desde": inicio.isoformat(),
        "hasta": fin.isoformat(),
        "total_ganancia": round(sum(d["ganancia"] for d in datos), 2),
    }


@router.get("/historial")
def historial_ventas(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    mesa: Optional[int] = None,
    producto: Optional[int] = None,
    forma_pago: Optional[str] = None,
    limite: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Historial de ventas con filtros por fecha, mesa, producto y forma de pago."""
    from datetime import datetime as _dt

    limite = max(1, min(limite, 500))
    offset = max(0, offset)

    query = db.query(Pedido).filter(Pedido.estado == "cerrado")

    if desde:
        try:
            query = query.filter(Pedido.fecha_cierre >= _dt.fromisoformat(desde))
        except ValueError:
            pass
    if hasta:
        try:
            hasta_dt = _dt.fromisoformat(hasta)
            # El formulario envía solo la fecha (YYYY-MM-DD): el filtro debe
            # incluir todo ese día, no únicamente la medianoche.
            if len(hasta.strip()) <= 10:
                hasta_dt = hasta_dt.replace(
                    hour=23, minute=59, second=59, microsecond=999999
                )
            query = query.filter(Pedido.fecha_cierre <= hasta_dt)
        except ValueError:
            pass
    if mesa:
        mesa_filtro = db.query(Mesa).filter(Mesa.id == mesa).first()
        if (
            mesa_filtro
            and (mesa_filtro.tipo or "mesa") == "barra"
            and mesa_filtro.grupo
        ):
            # La tarjeta de una barra representa todas sus plazas: el filtro
            # incluye tambien el historial de barras ya eliminadas.
            ids_barra = [
                m.id
                for m in db.query(Mesa)
                .filter(Mesa.grupo == mesa_filtro.grupo)
                .all()
            ]
            query = query.filter(
                or_(
                    Pedido.mesa_id.in_(ids_barra),
                    Pedido.mesa_etiqueta_historica == mesa_filtro.grupo,
                )
            )
        else:
            query = query.filter(Pedido.mesa_id == mesa)
    if forma_pago:
        query = query.filter(Pedido.forma_pago == forma_pago)

    if producto:
        subq = (
            db.query(PedidoItem.pedido_id)
            .filter(PedidoItem.producto_id == producto)
            .subquery()
        )
        query = query.filter(Pedido.id.in_(subq))

    total = query.count()
    pedidos = (
        query.options(
            selectinload(Pedido.items).joinedload(PedidoItem.producto),
            joinedload(Pedido.mesa),
            joinedload(Pedido.usuario),
        )
        .order_by(Pedido.fecha_cierre.desc())
        .offset(offset)
        .limit(limite)
        .all()
    )

    resultados = []
    for pedido in pedidos:
        productos_txt = [
            f"{item.cantidad}x "
            f"{item.producto.nombre if item.producto else 'Producto eliminado'}"
            for item in pedido.items
        ]
        mesa_obj = pedido.mesa
        usuario = pedido.usuario
        if pedido.mesa_etiqueta_historica:
            mesa_etiqueta = pedido.mesa_etiqueta_historica
        elif mesa_obj:
            mesa_etiqueta = mesa_obj.etiqueta_historial()
        elif pedido.mesa_numero_historico is not None:
            mesa_etiqueta = etiqueta_desde_numero_historico(
                pedido.mesa_numero_historico
            )
        else:
            mesa_etiqueta = None
        resultados.append(
            {
                "id": pedido.id,
                "fecha": pedido.fecha_cierre.isoformat() if pedido.fecha_cierre else None,
                "estado": pedido.estado,
                "forma_pago": pedido.forma_pago or "efectivo",
                "total": pedido.total,
                "mesa_numero": (
                    mesa_obj.numero
                    if mesa_obj
                    else pedido.mesa_numero_historico
                ),
                "mesa_etiqueta": mesa_etiqueta,
                "usuario_nombre": usuario.nombre if usuario else "",
                "productos": productos_txt,
            }
        )

    return {
        "items": resultados,
        "total": total,
        "limite": limite,
        "offset": offset,
        "paginas": max(1, (total + limite - 1) // limite),
    }
