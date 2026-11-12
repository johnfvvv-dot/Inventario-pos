"""Servicios compartidos para cuentas, divisiones y cobros.

Centraliza la lógica que antes estaba duplicada entre las rutas de pedidos y
de cuentas. Así la creación de alias, la edición de líneas y los cierres usan
las mismas reglas y los mismos recálculos.
"""

from typing import List, Optional, Sequence, Tuple

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

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
from app.tiempo import ahora_local

# Un ítem preparado para crear la parte de un alias:
# (producto, cantidad, precio_unitario).
ItemParticipante = Tuple[Producto, int, float]


def mesas_de_cuenta(db: Session, mesa: Mesa) -> List[Mesa]:
    """Todas las plazas que forman la cuenta de una mesa o barra."""
    if (mesa.tipo or "mesa") == "barra" and mesa.grupo:
        return (
            db.query(Mesa)
            .filter(Mesa.grupo == mesa.grupo)
            .order_by(Mesa.id)
            .all()
        )
    return [mesa]


def bloquear_cuenta(db: Session, mesa: Mesa) -> None:
    """Bloquea las filas de la mesa o de todas las plazas de una barra."""
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


def recalcular_participante(db: Session, participante: Participante) -> float:
    """Recalcula el subtotal de un alias desde sus líneas."""
    # La sesión usa autoflush=False: hay que volcar las líneas pendientes
    # (nuevas, editadas o eliminadas) antes de sumar.
    db.flush()
    subtotal = (
        db.query(func.coalesce(func.sum(ParticipanteItem.subtotal), 0.0))
        .filter(ParticipanteItem.participante_id == participante.id)
        .scalar()
        or 0.0
    )
    participante.subtotal = round(float(subtotal), 2)
    db.flush()
    return participante.subtotal


def recalcular_division(db: Session, division: Division) -> float:
    """Recalcula el total de una división desde los subtotales de sus alias."""
    # Volcar los subtotales recién calculados de los alias antes de sumarlos.
    db.flush()
    total = (
        db.query(func.coalesce(func.sum(Participante.subtotal), 0.0))
        .filter(Participante.division_id == division.id)
        .scalar()
        or 0.0
    )
    division.total = round(float(total), 2)
    db.flush()
    return division.total


def crear_division(
    db: Session,
    mesa: Mesa,
    usuario_id: int,
    fecha_ocupacion=None,
) -> Division:
    """Crea una división pendiente para una mesa/plaza."""
    if not mesa.fecha_ocupacion:
        mesa.fecha_ocupacion = ahora_local()
    division = Division(
        mesa_id=mesa.id,
        usuario_id=usuario_id,
        total=0.0,
        estado="pendiente",
        fecha_ocupacion=fecha_ocupacion or mesa.fecha_ocupacion,
    )
    db.add(division)
    db.flush()
    return division


def crear_participante(
    db: Session,
    division: Division,
    alias: str,
    items: Optional[Sequence[ItemParticipante]] = None,
) -> Participante:
    """Crea un alias con sus líneas y recalcula la división."""
    participante = Participante(
        division_id=division.id,
        alias=alias.strip(),
        subtotal=0.0,
        pagado=0,
    )
    db.add(participante)
    db.flush()

    for producto, cantidad, precio_unitario in items or []:
        subtotal = round(float(precio_unitario) * cantidad, 2)
        db.add(
            ParticipanteItem(
                participante_id=participante.id,
                producto_id=producto.id,
                cantidad=cantidad,
                precio_unitario=precio_unitario,
                subtotal=subtotal,
            )
        )

    db.flush()
    recalcular_participante(db, participante)
    recalcular_division(db, division)
    return participante


def obtener_o_crear_division_pendiente(
    db: Session,
    mesa: Mesa,
    usuario_id: int,
) -> Division:
    """Devuelve la división pendiente más reciente de la cuenta o crea una.

    En una barra se consideran todas las plazas del grupo para no abrir una
    división nueva si el cliente ya pertenece a una cuenta dividida.
    """
    mesas = mesas_de_cuenta(db, mesa)
    ids = [m.id for m in mesas]
    division = (
        db.query(Division)
        .filter(
            Division.mesa_id.in_(ids),
            Division.estado == "pendiente",
        )
        .order_by(Division.id.desc())
        .first()
    )
    if division:
        return division
    return crear_division(db, mesa, usuario_id)


def alias_existente_en_cuenta(
    db: Session,
    mesas: Sequence[Mesa],
    alias: str,
    excluir_participante_id: Optional[int] = None,
) -> Optional[Participante]:
    """Busca un alias activo dentro de las divisiones pendientes de la cuenta."""
    ids = [m.id for m in mesas]
    if not ids:
        return None
    query = (
        db.query(Participante)
        .join(Division, Division.id == Participante.division_id)
        .filter(
            Division.mesa_id.in_(ids),
            Division.estado == "pendiente",
            func.lower(Participante.alias) == alias.strip().lower(),
        )
    )
    if excluir_participante_id is not None:
        query = query.filter(Participante.id != excluir_participante_id)
    return query.first()


def registrar_pago_participante(
    db: Session,
    participante: Participante,
    forma_pago: str,
    ahora,
    usuario_cierre_id: Optional[int] = None,
) -> None:
    """Marca pagado un alias y crea el pedido financiero de su consumo.

    El pedido ``es_pago_division=1`` es la única fuente para caja, ganancia,
    historial y reportes. La generación de tickets lo excluye y mantiene el
    ticket del alias desde ``ParticipanteItem``.
    """
    if participante.pagado:
        return

    recalcular_participante(db, participante)

    # Si ya existe un pedido de pago (por un reintento), no se duplica.
    if participante.pedido_pago_id:
        participante.pagado = 1
        participante.forma_pago = forma_pago
        participante.fecha_pago = participante.fecha_pago or ahora
        return

    division = participante.division
    if division is None:
        division = (
            db.query(Division)
            .filter(Division.id == participante.division_id)
            .first()
        )
    mesa = division.mesa if division else None
    if division and mesa is None:
        mesa = db.query(Mesa).filter(Mesa.id == division.mesa_id).first()

    items = (
        db.query(ParticipanteItem)
        .filter(ParticipanteItem.participante_id == participante.id)
        .order_by(ParticipanteItem.id)
        .all()
    )
    if items and division:
        pedido_pago = Pedido(
            mesa_id=division.mesa_id,
            usuario_id=division.usuario_id,
            estado="cerrado",
            total=participante.subtotal,
            forma_pago=forma_pago,
            fecha_cierre=ahora,
            fecha_ocupacion=(
                division.fecha_ocupacion or division.fecha or ahora
            ),
            participante_id=participante.id,
            es_pago_division=1,
            usuario_cierre_id=usuario_cierre_id or division.usuario_id,
        )
        if mesa is not None:
            pedido_pago.guardar_origen(mesa)
        db.add(pedido_pago)
        db.flush()

        for item in items:
            db.add(
                PedidoItem(
                    pedido_id=pedido_pago.id,
                    producto_id=item.producto_id,
                    cantidad=item.cantidad,
                    precio_unitario=item.precio_unitario,
                    subtotal=item.subtotal,
                )
            )
        participante.pedido_pago_id = pedido_pago.id

    participante.pagado = 1
    participante.forma_pago = forma_pago
    participante.fecha_pago = ahora


def cerrar_division_si_corresponde(
    db: Session,
    division: Division,
    forma_pago: Optional[str] = None,
) -> bool:
    """Marca la división como pagada cuando todos sus alias pagaron."""
    db.flush()
    participantes = (
        db.query(Participante)
        .filter(Participante.division_id == division.id)
        .all()
    )
    if participantes and all(p.pagado for p in participantes):
        division.estado = "pagada"
        if forma_pago:
            division.forma_pago = division.forma_pago or forma_pago
        return True
    return False


def liberar_mesa_si_corresponde(db: Session, mesa_id: int) -> None:
    """Libera una mesa/plaza cuando ya no tiene nada pendiente de cobro."""
    mesa = db.query(Mesa).filter(Mesa.id == mesa_id).first()
    if not mesa:
        return
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
        mesa.fecha_ocupacion = None


def validar_permiso_cantidades(db: Session, usuario_id: Optional[int]) -> Usuario:
    """Valida quién puede ajustar cantidades.

    El Administrador siempre puede. El Bartender necesita el permiso
    ``editar_cantidades`` habilitado desde Usuarios.
    """
    if usuario_id is None:
        raise HTTPException(
            status_code=403,
            detail=(
                "Se requiere identificar al usuario para editar cantidades. "
                "Actualiza la aplicación e intenta de nuevo."
            ),
        )
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if usuario.rol != "admin" and not usuario.editar_cantidades:
        raise HTTPException(
            status_code=403,
            detail=(
                "No tenés permiso para editar pedidos. "
                "El Administrador debe habilitarlo desde Usuarios."
            ),
        )
    return usuario
