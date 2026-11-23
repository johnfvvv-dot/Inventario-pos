"""Endpoints del corte de caja (turnos) y resumen de ventas por forma de pago."""

import re
from datetime import datetime, timedelta
from math import gcd
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload, selectinload

from app.boliranas_servicio import hay_partidas_activas, modulo_habilitado
from app.database import get_db
from app.models import (
    ConfiguracionNegocio,
    Division,
    Mesa,
    Participante,
    ParticipanteItem,
    Pedido,
    PedidoItem,
    Producto,
    TurnoCaja,
    Usuario,
    etiqueta_desde_numero_historico,
)
from app.schemas import (
    AbrirTurnoIn,
    AbrirTurnoOut,
    CerrarTurnoIn,
    ResumenCajaOut,
    TicketItemOut,
    TicketOut,
    TicketsTurnoOut,
    TotalesFormaPago,
    TurnoCajaOut,
)
from app.tiempo import ahora_local
from app.turnos import MENSAJE_CIERRE_BLOQUEADO, turno_abierto

router = APIRouter(tags=["caja"])

FORMAS_PAGO = ["efectivo", "tarjeta", "transferencia"]

NOMBRES_FORMA_PAGO = {
    "efectivo": "Efectivo",
    "tarjeta": "Tarjeta",
    "transferencia": "Transferencia",
}


def _pagos_de_pedido(pedido: Pedido) -> List[tuple[str, float]]:
    """Desglose de pagos de un pedido (uno o dos métodos).

    Los pedidos nuevos guardan el desglose en pago_1/pago_2. Los pedidos
    anteriores solo tienen forma_pago y total, por lo que se usa ese único
    método como respaldo.
    """
    pagos: List[tuple[str, float]] = []
    if (
        pedido.pago_1_forma in FORMAS_PAGO
        and pedido.pago_1_monto is not None
        and float(pedido.pago_1_monto) > 0
    ):
        pagos.append((pedido.pago_1_forma, float(pedido.pago_1_monto)))
    if (
        pedido.pago_2_forma in FORMAS_PAGO
        and pedido.pago_2_monto is not None
        and float(pedido.pago_2_monto) > 0
    ):
        pagos.append((pedido.pago_2_forma, float(pedido.pago_2_monto)))
    if pagos:
        return pagos

    forma = pedido.forma_pago if pedido.forma_pago in FORMAS_PAGO else "efectivo"
    return [(forma, float(pedido.total or 0.0))]


def _etiqueta_forma_pago(pedido: Pedido) -> str:
    """Texto visible para el historial y los tickets."""
    pagos = _pagos_de_pedido(pedido)
    if len(pagos) > 1:
        detalle = " + ".join(
            f"{NOMBRES_FORMA_PAGO.get(forma, forma)} (${monto:.2f})"
            for forma, monto in pagos
        )
        return f"Mixto: {detalle}"
    return pedido.forma_pago or "efectivo"


def _totales_por_forma_pago(
    db: Session, desde: Optional[datetime] = None, hasta: Optional[datetime] = None
) -> TotalesFormaPago:
    """Suma los pedidos cerrados del periodo agrupados por forma de pago."""
    query = db.query(Pedido).filter(Pedido.estado == "cerrado")
    if desde:
        query = query.filter(Pedido.fecha_cierre >= desde)
    if hasta:
        query = query.filter(Pedido.fecha_cierre <= hasta)

    pedidos = query.all()

    totales = {forma: 0.0 for forma in FORMAS_PAGO}
    operaciones = 0
    for pedido in pedidos:
        for forma, monto in _pagos_de_pedido(pedido):
            totales[forma] = round(totales[forma] + monto, 2)
        operaciones += 1

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
        fondo_inicial=float(turno.fondo_inicial or 0.0),
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
            for forma, monto in _pagos_de_pedido(pedido):
                totales[forma] = round(totales[forma] + monto, 2)
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
                fondo_inicial=float(turno.fondo_inicial or 0.0),
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
    turno = turno_abierto(db)
    return _turno_out(db, turno) if turno else None


def _crear_turno(
    db: Session, usuario_id: int, fondo_inicial: float
) -> AbrirTurnoOut:
    """Abre un turno nuevo si no existe otro abierto."""
    if turno_abierto(db):
        raise HTTPException(
            status_code=400, detail="Ya hay un turno de caja abierto"
        )

    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    turno = TurnoCaja(
        usuario_id=usuario.id,
        estado="abierto",
        fondo_inicial=round(float(fondo_inicial), 2),
    )
    db.add(turno)
    db.commit()
    db.refresh(turno)
    return AbrirTurnoOut(
        mensaje="Turno de caja abierto", turno=_turno_out(db, turno)
    )


@router.post("/abrir-turno", response_model=AbrirTurnoOut)
def abrir_turno(datos: AbrirTurnoIn, db: Session = Depends(get_db)):
    """Abre un turno de caja con el fondo inicial en efectivo."""
    return _crear_turno(db, datos.usuario_id, datos.fondo_inicial)


@router.post("/abrir", response_model=AbrirTurnoOut)
def abrir_turno_compatibilidad(
    usuario_id: int = 1, fondo_inicial: float = 0.0, db: Session = Depends(get_db)
):
    """Alias compatible para clientes anteriores que abren sin cuerpo JSON."""
    return _crear_turno(db, usuario_id, fondo_inicial)


@router.post("/cerrar", response_model=TurnoCajaOut)
def cerrar_turno(datos: CerrarTurnoIn, db: Session = Depends(get_db)):
    """Cierra el turno de caja abierto.

    Se rechaza el cierre mientras existan mesas ocupadas, pedidos sin
    liquidar o divisiones de cuenta pendientes de pago.
    """
    turno = turno_abierto(db)
    if not turno:
        raise HTTPException(status_code=400, detail="No hay un turno de caja abierto")

    db.flush()
    mesas_ocupadas = (
        db.query(func.count(Mesa.id))
        .filter(Mesa.estado == "ocupada")
        .scalar()
        or 0
    )
    pedidos_pendientes = (
        db.query(func.count(Pedido.id))
        .filter(Pedido.estado.in_(["abierto", "pendiente"]))
        .scalar()
        or 0
    )
    divisiones_pendientes = (
        db.query(func.count(Division.id))
        .filter(Division.estado == "pendiente")
        .scalar()
        or 0
    )
    if hay_partidas_activas(db):
        raise HTTPException(
            status_code=409,
            detail=(
                "No se puede cerrar el turno: hay partidas de Bolirana "
                "activas o bebidas pendientes de transferir. Finaliza las "
                "partidas antes de continuar."
            ),
        )
    cargos_bolirana_pendientes = (
        db.query(func.count(Pedido.id))
        .filter(
            Pedido.estado == "pendiente",
            Pedido.bolirana_partida_id.isnot(None),
        )
        .scalar()
        or 0
    )
    if cargos_bolirana_pendientes and modulo_habilitado(db):
        raise HTTPException(
            status_code=409,
            detail=(
                "No se puede cerrar el turno: hay cargos de Bolirana "
                "pendientes de cobro. Cóbralos antes de continuar."
            ),
        )
    if mesas_ocupadas or pedidos_pendientes or divisiones_pendientes:
        raise HTTPException(
            status_code=409,
            detail=MENSAJE_CIERRE_BLOQUEADO,
        )

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
        for forma, monto in _pagos_de_pedido(pedido):
            serie[clave][forma] = round(serie[clave][forma] + monto, 2)
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


def _etiqueta_mesa_ticket(
    mesa: Optional[Mesa],
    etiqueta_historica: Optional[str],
    numero_historico: Optional[int],
) -> str:
    """Nombre visible de la mesa en un ticket, incluso si ya fue eliminada."""
    if etiqueta_historica:
        return etiqueta_historica
    if mesa:
        return mesa.etiqueta_historial()
    if numero_historico is not None:
        return etiqueta_desde_numero_historico(numero_historico)
    return "Sin mesa"


def _fraccion_corta(numerador: int, denominador: int) -> Optional[str]:
    """Fracción compacta y reducida: ½, 1/3, 2/3, 1/4, 3/4..."""
    if denominador <= 0 or numerador >= denominador:
        return None
    divisor = gcd(numerador, denominador)
    num = numerador // divisor
    den = denominador // divisor
    if num == 1 and den == 2:
        return "½"
    return f"{num}/{den}"


def _unir_nombres(nombres: List[str]) -> str:
    """Une nombres con lenguaje natural: "Fabio y Camilo"."""
    if not nombres:
        return ""
    if len(nombres) == 1:
        return nombres[0]
    if len(nombres) == 2:
        return f"{nombres[0]} y {nombres[1]}"
    return f"{', '.join(nombres[:-1])} y {nombres[-1]}"


def _titulo_cargo(cargos: List[Pedido]) -> str:
    """Título agrupado: "Bolirana #1 · Fabio y Camilo (Equipo B)"."""
    numero = next(
        (p.bolirana_numero for p in cargos if p.bolirana_numero is not None),
        None,
    )
    if numero is None:
        for pedido in cargos:
            coincidencia = re.search(r"#\s*(\d+)", pedido.concepto or "")
            if coincidencia:
                numero = int(coincidencia.group(1))
                break

    nombres: List[str] = []
    for pedido in cargos:
        alias = (pedido.alias_cliente or "").strip()
        if alias and alias not in nombres:
            nombres.append(alias)
    equipo = next(
        (p.bolirana_equipo for p in cargos if p.bolirana_equipo), None
    )

    if numero is None:
        return cargos[0].concepto or "Bolirana"
    titulo = f"Bolirana #{numero}"
    if nombres:
        titulo += f" · {_unir_nombres(nombres)}"
    if equipo:
        titulo += f" ({equipo})"
    return titulo


def _detalle_cargo_grupo(cargos: List[Pedido]) -> Optional[str]:
    """Combina las fracciones de una misma cuenta: "2/3 de: ..."."""
    bebidas = next(
        (p.bolirana_bebidas for p in cargos if p.bolirana_bebidas), None
    )
    fracciones = [
        (p.bolirana_fraccion_num, p.bolirana_fraccion_den) for p in cargos
    ]
    if bebidas and all(num is not None and den for num, den in fracciones):
        denominador = fracciones[0][1]
        if all(den == denominador for _, den in fracciones):
            numerador = sum(num for num, _ in fracciones)
            fraccion = _fraccion_corta(numerador, denominador)
            if fraccion is None:
                return f"Ronda completa: {bebidas}"
            return f"{fraccion} de: {bebidas}"
    return next(
        (p.concepto_detalle for p in cargos if p.concepto_detalle), None
    )


def _forma_pago_consolidada(pedidos: List[Pedido]) -> str:
    """Forma de pago de un ticket que agrupa varios pedidos."""
    totales: dict = {}
    for pedido in pedidos:
        for forma, monto in _pagos_de_pedido(pedido):
            totales[forma] = round(totales.get(forma, 0.0) + monto, 2)
    if len(totales) > 1:
        detalle = " + ".join(
            f"{NOMBRES_FORMA_PAGO.get(forma, forma)} (${totales[forma]:.2f})"
            for forma in FORMAS_PAGO
            if forma in totales
        )
        return f"Mixto: {detalle}"
    return next(iter(totales), "efectivo")


def _ticket_grupo(grupo: List[Pedido], desde: datetime) -> Optional[TicketOut]:
    """Un comprobante por cuenta y cobro, con productos y cargos agrupados."""
    grupo = sorted(grupo, key=lambda p: (p.fecha or desde, p.id))
    items: List[TicketItemOut] = []
    indices: dict = {}
    cargos: dict = {}
    orden_cargos: List = []

    for pedido in grupo:
        if pedido.items:
            for item in sorted(pedido.items, key=lambda i: i.id):
                nombre = (
                    item.producto.nombre
                    if item.producto
                    else "Producto eliminado"
                )
                clave = (nombre, round(float(item.precio_unitario), 2))
                if clave in indices:
                    existente = items[indices[clave]]
                    existente.cantidad += item.cantidad
                    existente.subtotal = round(
                        existente.subtotal + item.subtotal, 2
                    )
                else:
                    indices[clave] = len(items)
                    items.append(
                        TicketItemOut(
                            nombre=nombre,
                            cantidad=item.cantidad,
                            precio_unitario=item.precio_unitario,
                            subtotal=item.subtotal,
                        )
                    )
        elif pedido.concepto:
            clave_cargo = pedido.bolirana_partida_id or f"pedido-{pedido.id}"
            if clave_cargo not in cargos:
                cargos[clave_cargo] = []
                orden_cargos.append(clave_cargo)
            cargos[clave_cargo].append(pedido)

    for clave_cargo in orden_cargos:
        pedidos_cargo = cargos[clave_cargo]
        estructurados = all(
            p.bolirana_fraccion_den and p.bolirana_bebidas
            for p in pedidos_cargo
        )
        if estructurados:
            total_cargo = round(
                sum(float(p.total or 0.0) for p in pedidos_cargo), 2
            )
            items.append(
                TicketItemOut(
                    nombre=_titulo_cargo(pedidos_cargo),
                    cantidad=1,
                    precio_unitario=total_cargo,
                    subtotal=total_cargo,
                    detalle=_detalle_cargo_grupo(pedidos_cargo),
                    es_cargo=True,
                )
            )
            continue
        # Cargos legacy sin metadatos: se conservan uno por pedido.
        for pedido in pedidos_cargo:
            total_cargo = round(float(pedido.total or 0.0), 2)
            items.append(
                TicketItemOut(
                    nombre=pedido.concepto or "Cargo Bolirana",
                    cantidad=1,
                    precio_unitario=total_cargo,
                    subtotal=total_cargo,
                    detalle=pedido.concepto_detalle,
                    es_cargo=True,
                )
            )

    if not items:
        return None

    primero = grupo[0]
    ultimo = grupo[-1]
    fecha_ocupacion = next(
        (p.fecha_ocupacion for p in grupo if p.fecha_ocupacion),
        primero.fecha or desde,
    )
    fecha_pago = ultimo.fecha_cierre or primero.fecha_cierre or desde
    total = round(sum(float(item.subtotal) for item in items), 2)
    es_individual = bool(
        primero.mesa and (primero.mesa.tipo or "mesa") == "individual"
    ) or primero.mesa_etiqueta_historica == "Individual"

    if es_individual:
        nombre_cliente = (
            (primero.mesa.nombre if primero.mesa else None)
            or primero.alias_cliente
            or "Cliente"
        )
        return TicketOut(
            id=f"individual-{primero.mesa_id or 0}-{primero.id}",
            tipo="individual",
            folio=f"I-{primero.id:05d}",
            mesa="Individual",
            fecha_ocupacion=fecha_ocupacion,
            fecha_pago=fecha_pago,
            alias=nombre_cliente,
            forma_pago=_forma_pago_consolidada(grupo),
            total=total,
            items=items,
        )

    return TicketOut(
        id=f"pedido-{primero.id}",
        tipo="pedido",
        folio=f"P-{primero.id:05d}",
        mesa=_etiqueta_mesa_ticket(
            primero.mesa,
            primero.mesa_etiqueta_historica,
            primero.mesa_numero_historico,
        ),
        fecha_ocupacion=fecha_ocupacion,
        fecha_pago=fecha_pago,
        alias=primero.alias_cliente if len(grupo) == 1 else None,
        forma_pago=_forma_pago_consolidada(grupo),
        total=total,
        items=items,
    )


@router.get("/tickets", response_model=TicketsTurnoOut)
def tickets_turno(
    turno_id: Optional[int] = None, db: Session = Depends(get_db)
):
    """Genera los tickets internos de un turno bajo demanda.

    No se almacenan en la base de datos: se construyen desde los pedidos
    cerrados y los participantes pagados dentro del rango del turno. Al
    cerrar la ventana emergente del navegador desaparecen.
    """
    if turno_id is not None:
        turno = db.query(TurnoCaja).filter(TurnoCaja.id == turno_id).first()
        if not turno:
            raise HTTPException(status_code=404, detail="Turno no encontrado")
    else:
        turno = (
            db.query(TurnoCaja)
            .filter(TurnoCaja.estado == "abierto")
            .order_by(TurnoCaja.id.desc())
            .first()
        )
        if not turno:
            raise HTTPException(
                status_code=404, detail="No hay un turno de caja abierto"
            )

    desde = turno.fecha_apertura
    hasta = turno.fecha_cierre or ahora_local()
    tickets: List[TicketOut] = []

    # Un ticket por cada pedido cerrado (pago completo de una cuenta).
    pedidos = (
        db.query(Pedido)
        .options(
            joinedload(Pedido.mesa),
            selectinload(Pedido.items).joinedload(PedidoItem.producto),
        )
        .filter(
            Pedido.estado == "cerrado",
            or_(
                Pedido.es_pago_division == 0,
                Pedido.es_pago_division.is_(None),
            ),
            Pedido.fecha_cierre.isnot(None),
            Pedido.fecha_cierre >= desde,
            Pedido.fecha_cierre <= hasta,
        )
        .order_by(Pedido.fecha_cierre, Pedido.id)
        .all()
    )

    # Todos los pedidos cobrados en un mismo cierre de cuenta se consolidan
    # en un solo comprobante: productos agrupados, cargos de Bolirana
    # agrupados por partida y un único total/formas de pago. Esto cubre mesas,
    # barras y clientes individuales. Los pedidos históricos sin mesa
    # conservan su propio ticket.
    grupos: dict = {}
    sueltos: List[Pedido] = []
    for pedido in pedidos:
        if pedido.mesa_id is None:
            sueltos.append(pedido)
        else:
            clave = (pedido.mesa_id, pedido.fecha_cierre)
            grupos.setdefault(clave, []).append(pedido)

    for grupo in grupos.values():
        ticket = _ticket_grupo(grupo, desde)
        if ticket:
            tickets.append(ticket)

    for pedido in sueltos:
        ticket = _ticket_grupo([pedido], desde)
        if ticket:
            tickets.append(ticket)

    # Un ticket por cada cliente que pagó su parte de una división.
    participantes = (
        db.query(Participante)
        .join(Division, Division.id == Participante.division_id)
        .options(
            joinedload(Participante.division).joinedload(Division.mesa),
            selectinload(Participante.items).joinedload(ParticipanteItem.producto),
        )
        .filter(
            Participante.pagado == 1,
            or_(
                and_(
                    Participante.fecha_pago.isnot(None),
                    Participante.fecha_pago >= desde,
                    Participante.fecha_pago <= hasta,
                ),
                # Divisiones pagadas antes de existir fecha_pago: se usa la
                # fecha de creación de la división como respaldo.
                and_(
                    Participante.fecha_pago.is_(None),
                    Division.fecha >= desde,
                    Division.fecha <= hasta,
                ),
            ),
        )
        .order_by(Participante.division_id, Participante.id)
        .all()
    )

    # Correlativo estable de cada alias dentro de su división (D-0001-01).
    indices: dict = {}
    ids_divisiones = {p.division_id for p in participantes}
    if ids_divisiones:
        contador: dict = {}
        for pid, did in (
            db.query(Participante.id, Participante.division_id)
            .filter(Participante.division_id.in_(ids_divisiones))
            .order_by(Participante.division_id, Participante.id)
            .all()
        ):
            contador[did] = contador.get(did, 0) + 1
            indices[pid] = contador[did]

    for participante in participantes:
        division = participante.division
        items = [
            TicketItemOut(
                nombre=item.producto.nombre if item.producto else "Producto eliminado",
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario,
                subtotal=item.subtotal,
            )
            for item in sorted(participante.items, key=lambda i: i.id)
        ]
        if not items:
            continue
        tickets.append(
            TicketOut(
                id=f"participante-{participante.id}",
                tipo="division",
                folio=(
                    f"D-{division.id:04d}-"
                    f"{indices.get(participante.id, 1):02d}"
                ),
                mesa=_etiqueta_mesa_ticket(
                    division.mesa if division else None,
                    None,
                    None,
                ),
                fecha_ocupacion=(
                    (division.fecha_ocupacion if division else None)
                    or (division.fecha if division else None)
                    or desde
                ),
                fecha_pago=participante.fecha_pago
                or (division.fecha if division else None)
                or desde,
                alias=participante.alias,
                forma_pago=participante.forma_pago
                or (division.forma_pago if division else None)
                or "efectivo",
                total=round(
                    sum(float(item.subtotal) for item in items), 2
                ),
                items=items,
            )
        )

    tickets.sort(key=lambda t: (t.fecha_pago, t.id))

    config = (
        db.query(ConfiguracionNegocio)
        .filter(ConfiguracionNegocio.id == 1)
        .first()
    )
    nombre_negocio = (
        config.nombre_negocio
        if config and config.nombre_negocio
        else "Inventario POS"
    )

    return TicketsTurnoOut(
        turno_id=turno.id,
        estado=turno.estado,
        fecha_apertura=turno.fecha_apertura,
        fecha_cierre=turno.fecha_cierre,
        nombre_negocio=nombre_negocio,
        tickets=tickets,
    )


@router.get("/historial")
def historial_ventas(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    mesa: Optional[int] = None,
    producto: Optional[int] = None,
    forma_pago: Optional[str] = None,
    origen: Optional[str] = None,
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
        query = query.filter(
            or_(
                Pedido.forma_pago == forma_pago,
                Pedido.pago_1_forma == forma_pago,
                Pedido.pago_2_forma == forma_pago,
            )
        )
    if origen == "para_llevar":
        query = query.filter(
            Pedido.mesa_id.is_(None),
            Pedido.mesa_etiqueta_historica == "Para llevar",
        )

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
            joinedload(Pedido.participante),
        )
        .order_by(Pedido.fecha_cierre.desc())
        .offset(offset)
        .limit(limite)
        .all()
    )

    ids_cierre = {
        pedido.usuario_cierre_id
        for pedido in pedidos
        if pedido.usuario_cierre_id
    }
    usuarios_cierre = (
        {
            u.id: u
            for u in db.query(Usuario).filter(Usuario.id.in_(ids_cierre)).all()
        }
        if ids_cierre
        else {}
    )

    resultados = []
    for pedido in pedidos:
        productos_txt = [
            f"{item.cantidad}x "
            f"{item.producto.nombre if item.producto else 'Producto eliminado'}"
            for item in pedido.items
        ]
        if not productos_txt and pedido.concepto:
            productos_txt = [pedido.concepto]
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
                "forma_pago": _etiqueta_forma_pago(pedido),
                "pagos": [
                    {"forma_pago": forma, "monto": round(monto, 2)}
                    for forma, monto in _pagos_de_pedido(pedido)
                ],
                "total": pedido.total,
                "mesa_numero": (
                    mesa_obj.numero
                    if mesa_obj
                    else pedido.mesa_numero_historico
                ),
                "mesa_etiqueta": mesa_etiqueta,
                "usuario_nombre": usuario.nombre if usuario else "",
                "usuario_cierre_nombre": (
                    usuarios_cierre[pedido.usuario_cierre_id].nombre
                    if pedido.usuario_cierre_id in usuarios_cierre
                    else ""
                ),
                "alias": (
                    pedido.participante.alias
                    if pedido.participante
                    else pedido.alias_cliente
                ),
                "concepto": pedido.concepto,
                "concepto_detalle": pedido.concepto_detalle,
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
