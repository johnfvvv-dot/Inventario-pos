"""Endpoints del corte de caja (turnos) y resumen de ventas por forma de pago."""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Mesa,
    Pedido,
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


def _turno_out(db: Session, turno: TurnoCaja) -> TurnoCajaOut:
    hasta = turno.fecha_cierre or ahora_local()
    totales = _totales_por_forma_pago(db, turno.fecha_apertura, hasta)
    usuario = db.query(Usuario).filter(Usuario.id == turno.usuario_id).first()
    return TurnoCajaOut(
        id=turno.id,
        usuario_nombre=usuario.nombre if usuario else "Desconocido",
        fecha_apertura=turno.fecha_apertura,
        fecha_cierre=turno.fecha_cierre,
        observaciones=turno.observaciones,
        estado=turno.estado,
        totales=totales,
    )


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
    return [_turno_out(db, t) for t in turnos]


@router.get("/resumen", response_model=ResumenCajaOut)
def resumen_caja(
    dias: int = 1, db: Session = Depends(get_db)
):
    """Resumen de ventas por forma de pago de los últimos N días."""
    desde = ahora_local() - timedelta(days=max(1, dias))
    hasta = ahora_local()

    totales = _totales_por_forma_pago(db, desde, hasta)

    cerrados = (
        db.query(Pedido)
        .filter(Pedido.estado == "cerrado", Pedido.fecha_cierre >= desde)
        .all()
    )
    mesas = {p.mesa_id for p in cerrados if p.mesa_id}

    por_forma = {
        "efectivo": totales.efectivo,
        "tarjeta": totales.tarjeta,
        "transferencia": totales.transferencia,
    }

    return ResumenCajaOut(
        desde=desde,
        hasta=hasta,
        totales=totales,
        pedidos_cerrados=len(cerrados),
        mesas_atendidas=len(mesas),
        por_forma_pago=por_forma,
    )


@router.get("/ventas-por-dia")
def ventas_por_dia(dias: int = 14, db: Session = Depends(get_db)):
    """Serie diaria de ventas (para el gráfico de líneas) y top de productos."""
    dias = max(1, min(dias, 90))
    desde = (ahora_local() - timedelta(days=dias - 1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    cerrados = (
        db.query(Pedido)
        .filter(Pedido.estado == "cerrado", Pedido.fecha_cierre >= desde)
        .all()
    )

    serie: dict = {}
    for i in range(dias):
        dia = (desde + timedelta(days=i)).date()
        serie[dia] = {"efectivo": 0.0, "tarjeta": 0.0, "transferencia": 0.0, "total": 0.0}

    for pedido in cerrados:
        if not pedido.fecha_cierre:
            continue
        clave = pedido.fecha_cierre.date()
        if clave not in serie:
            continue
        forma = pedido.forma_pago if pedido.forma_pago in FORMAS_PAGO else "efectivo"
        serie[clave][forma] = round(serie[clave][forma] + (pedido.total or 0), 2)
        serie[clave]["total"] = round(serie[clave]["total"] + (pedido.total or 0), 2)

    etiquetas = [str(d) for d in sorted(serie.keys())]
    datos = [serie[d] for d in sorted(serie.keys())]

    # Top de productos vendidos en el periodo
    from app.models import PedidoItem

    conteo: dict = {}
    pedidos_ids = [p.id for p in cerrados]
    if pedidos_ids:
        items = db.query(PedidoItem).filter(PedidoItem.pedido_id.in_(pedidos_ids)).all()
        for item in items:
            clave = item.producto_id
            if clave not in conteo:
                conteo[clave] = {"producto_id": clave, "cantidad": 0, "total": 0.0}
            conteo[clave]["cantidad"] += item.cantidad
            conteo[clave]["total"] = round(conteo[clave]["total"] + (item.subtotal or 0), 2)

        from app.models import Producto

        for clave in conteo:
            producto = db.query(Producto).filter(Producto.id == clave).first()
            conteo[clave]["nombre"] = producto.nombre if producto else f"#{clave}"

    top = sorted(conteo.values(), key=lambda x: x["cantidad"], reverse=True)[:10]

    return {
        "etiquetas": etiquetas,
        "serie": datos,
        "top_productos": top,
        "dias": dias,
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

    from app.models import PedidoItem, Producto

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
        query.order_by(Pedido.fecha_cierre.desc()).offset(offset).limit(limite).all()
    )

    resultados = []
    for pedido in pedidos:
        items = (
            db.query(PedidoItem).filter(PedidoItem.pedido_id == pedido.id).all()
        )
        productos_txt = []
        for item in items:
            prod = db.query(Producto).filter(Producto.id == item.producto_id).first()
            productos_txt.append(
                f"{item.cantidad}x {prod.nombre if prod else '?'}"
            )
        mesa_obj = db.query(Mesa).filter(Mesa.id == pedido.mesa_id).first() if pedido.mesa_id else None
        usuario = db.query(Usuario).filter(Usuario.id == pedido.usuario_id).first()
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
