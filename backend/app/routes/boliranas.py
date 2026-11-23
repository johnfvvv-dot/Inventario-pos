"""Módulo de Bolirana: partidas, bebidas y transferencia a perdedores.

Flujo:
  1. El Administrador crea las boliranas (Bartender solo opera).
  2. Se inicia una partida con dos o más mesas, barras, clientes
     individuales o jugadores vinculados a una cuenta; varios jugadores
     pueden compartir la misma mesa, barra o cliente individual.
  3. Las bebidas se cargan a la ronda y descuentan stock, pero no son una
     venta todavía.
  4. Al finalizar, el total se reparte en partes iguales entre los perdedores.
     Todas las partes se cargan a la cuenta de origen (mesa, barra o cliente
     individual): no quedan jugadores libres ni cobros sueltos.
"""

import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.boliranas_servicio import (
    exigir_barra_sin_bolirana,
    exigir_mesa_sin_bolirana,
    partida_activa,
)
from app.database import get_db
from app.models import (
    Bolirana,
    Mesa,
    ParticipanteBolirana,
    PartidaBolirana,
    Pedido,
    PedidoItem,
    Producto,
    Usuario,
)
from app.schemas import (
    FORMAS_PAGO,
    BoliranaCreate,
    BoliranaOut,
    CargoBoliranaOut,
    ConsumoBoliranaOut,
    IniciarPartidaBoliranaIn,
    LiquidarPartidaBoliranaIn,
    PagarCargoBoliranaIn,
    ParticipanteBoliranaOut,
    PartidaBoliranaOut,
    PedidoBoliranaCreate,
)
from app.tiempo import ahora_local
from app.turnos import exigir_turno_abierto

router = APIRouter(tags=["boliranas"])


# ------------------------------------------------------------------
# Utilidades
# ------------------------------------------------------------------

def _usuario(db: Session, usuario_id: int) -> Usuario:
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario


def _etiqueta_bolirana(nombre: str) -> str:
    """Nombre visible sin repetir el prefijo "Bolirana".

    Si la máquina ya se llama "Bolirana 1" el concepto queda
    "Consumo Bolirana 1 (Partida)" en lugar de duplicar la palabra.
    """
    limpio = (nombre or "").strip()
    if limpio.lower().startswith("bolirana"):
        limpio = limpio[len("bolirana") :].lstrip(" -:")
    return limpio or "Bolirana"


def _numero_bolirana(partida: PartidaBolirana) -> int:
    """Número visible de la máquina; usa el primer número del nombre."""
    nombre = _etiqueta_bolirana(partida.bolirana.nombre)
    coincidencia = re.search(r"\d+", nombre)
    if coincidencia:
        return int(coincidencia.group(0))
    return int(partida.bolirana_id or 0)


def _concepto_partida(partida: PartidaBolirana) -> str:
    """Título corto del cargo: "Bolirana #1"."""
    return f"Bolirana #{_numero_bolirana(partida)}"


def _fraccion_corta(numerador: int, denominador: int) -> Optional[str]:
    """Fracción compacta: ½, 1/3, 2/3, 1/4, 3/4, 1/5..."""
    if denominador <= 0 or numerador >= denominador:
        return None
    if numerador == 1 and denominador == 2:
        return "½"
    return f"{numerador}/{denominador}"


def _bebidas_texto(consumo: List[ConsumoBoliranaOut]) -> Optional[str]:
    """Lista corta de bebidas: "2 Aguila 350ml · 2 Poker 350ml"."""
    if not consumo:
        return None
    return " · ".join(
        f"{item.cantidad} {item.producto_nombre}" for item in consumo
    )


def _detalle_cargo(
    consumo: List[ConsumoBoliranaOut], numerador: int, denominador: int
) -> Optional[str]:
    """Sub-línea del cargo: fracción y bebidas exactas de la ronda."""
    bebidas = _bebidas_texto(consumo)
    if not bebidas:
        return None
    fraccion = _fraccion_corta(numerador, denominador)
    if fraccion is None:
        return f"Ronda completa: {bebidas}"
    return f"{fraccion} de: {bebidas}"


def _exigir_admin(db: Session, usuario_id: int) -> Usuario:
    usuario = _usuario(db, usuario_id)
    if usuario.rol != "admin":
        raise HTTPException(
            status_code=403,
            detail="Solo el Administrador puede administrar las boliranas.",
        )
    return usuario


def _bolirana(db: Session, bolirana_id: int) -> Bolirana:
    bolirana = (
        db.query(Bolirana)
        .filter(Bolirana.id == bolirana_id, Bolirana.activa == 1)
        .first()
    )
    if not bolirana:
        raise HTTPException(status_code=404, detail="Bolirana no encontrada")
    return bolirana


def _partida_de_bolirana(
    db: Session, bolirana_id: int
) -> Optional[PartidaBolirana]:
    return (
        db.query(PartidaBolirana)
        .options(
            joinedload(PartidaBolirana.participantes).joinedload(
                ParticipanteBolirana.mesa
            ),
            joinedload(PartidaBolirana.participantes).joinedload(
                ParticipanteBolirana.origen_mesa
            ),
        )
        .filter(
            PartidaBolirana.bolirana_id == bolirana_id,
            PartidaBolirana.estado == "en_curso",
        )
        .order_by(PartidaBolirana.id.desc())
        .first()
    )


def _consumo_partida(db: Session, partida_id: int) -> List[ConsumoBoliranaOut]:
    """Agrupa las líneas de todas las comandas de la ronda por producto."""
    pedidos = (
        db.query(Pedido)
        .options(
            joinedload(Pedido.items).joinedload(PedidoItem.producto),
        )
        .filter(
            Pedido.bolirana_partida_id == partida_id,
            Pedido.estado == "bolirana",
        )
        .order_by(Pedido.id)
        .all()
    )
    agrupado: dict = {}
    for pedido in pedidos:
        for item in pedido.items:
            clave = (item.producto_id, round(float(item.precio_unitario), 2))
            fila = agrupado.setdefault(
                clave,
                {
                    "producto_id": item.producto_id,
                    "producto_nombre": (
                        item.producto.nombre if item.producto else "Producto eliminado"
                    ),
                    "cantidad": 0,
                    "precio_unitario": round(float(item.precio_unitario), 2),
                    "subtotal": 0.0,
                },
            )
            fila["cantidad"] += item.cantidad
            fila["subtotal"] = round(fila["subtotal"] + float(item.subtotal), 2)

    return [
        ConsumoBoliranaOut(**fila)
        for fila in sorted(
            agrupado.values(), key=lambda f: (f["producto_nombre"], f["precio_unitario"])
        )
    ]


def _participantes_out(
    participantes: List[ParticipanteBolirana],
) -> List[ParticipanteBoliranaOut]:
    return [
        ParticipanteBoliranaOut(
            id=p.id,
            tipo=p.tipo,
            mesa_id=p.mesa_id,
            barra_numero=p.barra_numero,
            alias=p.alias,
            origen_tipo=p.origen_tipo,
            origen_mesa_id=p.origen_mesa_id,
            origen_barra_numero=p.origen_barra_numero,
            origen_etiqueta=p.origen_etiqueta,
            equipo=p.equipo,
            etiqueta=p.etiqueta(),
            es_perdedor=bool(p.es_perdedor),
            monto_asignado=round(float(p.monto_asignado or 0.0), 2),
            estado_pago=p.estado_pago,
        )
        for p in sorted(participantes, key=lambda p: p.id)
    ]


def _partida_out(db: Session, partida: PartidaBolirana) -> PartidaBoliranaOut:
    return PartidaBoliranaOut(
        id=partida.id,
        bolirana_id=partida.bolirana_id,
        estado=partida.estado,
        modalidad=partida.modalidad or "directo",
        fecha_inicio=partida.fecha_inicio,
        fecha_fin=partida.fecha_fin,
        total_bebidas=round(float(partida.total_bebidas or 0.0), 2),
        participantes=_participantes_out(partida.participantes),
        consumo=_consumo_partida(db, partida.id),
    )


def _bolirana_out(db: Session, bolirana: Bolirana) -> BoliranaOut:
    partida = _partida_de_bolirana(db, bolirana.id)
    return BoliranaOut(
        id=bolirana.id,
        nombre=bolirana.nombre,
        activa=bool(bolirana.activa),
        creado_en=bolirana.creado_en,
        estado="en_partida" if partida else "disponible",
        partida=_partida_out(db, partida) if partida else None,
    )


def _mesa_por_id(db: Session, mesa_id: int) -> Mesa:
    mesa = db.query(Mesa).filter(Mesa.id == mesa_id).first()
    if not mesa:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")
    return mesa


def _mesas_de_barra(db: Session, numero_barra: int) -> List[Mesa]:
    mesas = (
        db.query(Mesa)
        .filter(Mesa.grupo == f"Barra {numero_barra}")
        .order_by(Mesa.posicion, Mesa.id)
        .all()
    )
    if not mesas:
        raise HTTPException(status_code=404, detail="Barra no encontrada")
    return mesas


def _validar_pagos(total: float, pagos) -> None:
    """Valida uno o dos métodos y que la suma cubra exactamente el cargo."""
    formas = [p.forma_pago for p in pagos]
    if any(forma not in FORMAS_PAGO for forma in formas):
        raise HTTPException(
            status_code=400,
            detail=f"Forma de pago invalida. Use: {', '.join(FORMAS_PAGO)}",
        )
    if len(set(formas)) != len(formas):
        raise HTTPException(
            status_code=400,
            detail="Los métodos de pago deben ser distintos.",
        )
    montos = [round(float(p.monto), 2) for p in pagos]
    if any(monto <= 0 for monto in montos):
        raise HTTPException(
            status_code=400,
            detail="Cada monto de pago debe ser mayor a cero.",
        )
    if abs(round(sum(montos), 2) - round(float(total), 2)) > 0.01:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Los pagos suman {sum(montos):.2f} y el cargo es "
                f"{float(total):.2f}."
            ),
        )


def _mesa_de_barra_para_cargo(db: Session, numero_barra: int) -> Mesa:
    """Elige la plaza de una barra que recibirá el cargo de la partida."""
    mesas = _mesas_de_barra(db, numero_barra)
    con_pedidos = {
        fila[0]
        for fila in db.query(Pedido.mesa_id)
        .filter(
            Pedido.mesa_id.in_([m.id for m in mesas]),
            Pedido.estado == "abierto",
        )
        .distinct()
        .all()
    }
    mesa = next((m for m in mesas if m.id in con_pedidos), None)
    if mesa is None:
        # Sin pedidos abiertos: se usa una plaza ocupada para no bloquear
        # un puesto libre de la barra.
        mesa = next((m for m in mesas if m.estado == "ocupada"), mesas[0])
    return mesa


def _mesa_destino_participante(
    db: Session, participante: ParticipanteBolirana
) -> Optional[Mesa]:
    """Cuenta que debe recibir la deuda de un participante.

    Solo los cargos legacy de jugadores libres devuelven None; las partidas
    nuevas siempre tienen una cuenta de origen.
    """
    if participante.tipo == "mesa":
        return _mesa_por_id(db, participante.mesa_id or 0)
    if participante.tipo == "barra":
        return _mesa_de_barra_para_cargo(db, participante.barra_numero or 0)
    if participante.origen_tipo in {"mesa", "individual"}:
        return _mesa_por_id(db, participante.origen_mesa_id or 0)
    if participante.origen_tipo == "barra":
        return _mesa_de_barra_para_cargo(
            db, participante.origen_barra_numero or 0
        )
    return None


def _concepto_cargo(
    partida: PartidaBolirana, participante: ParticipanteBolirana
) -> str:
    """Título del cargo: "Bolirana #1 · Fabio (Equipo B)"."""
    concepto = _concepto_partida(partida)
    jugador = participante.alias if participante.tipo == "alias" else None
    equipo = participante.equipo or None
    if jugador and equipo:
        return f"{concepto} · {jugador} ({equipo})"
    if jugador:
        return f"{concepto} · {jugador}"
    if equipo:
        return f"{concepto} · {equipo}"
    return concepto


def _crear_cargo_cuenta(
    db: Session,
    partida: PartidaBolirana,
    participante: ParticipanteBolirana,
    mesa: Mesa,
    monto: float,
    usuario_id: int,
    ahora,
    detalle: Optional[str] = None,
    bebidas: Optional[str] = None,
    fraccion_num: Optional[int] = None,
    fraccion_den: Optional[int] = None,
) -> Pedido:
    """Crea un cargo abierto en la cuenta de origen del perdedor."""
    alias_cliente = None
    if participante.tipo == "alias":
        alias_cliente = participante.alias
    elif (mesa.tipo or "mesa") == "individual":
        alias_cliente = mesa.nombre

    cargo = Pedido(
        mesa_id=mesa.id,
        usuario_id=usuario_id,
        fecha=ahora,
        total=round(float(monto), 2),
        estado="abierto",
        concepto=_concepto_cargo(partida, participante),
        concepto_detalle=detalle,
        bolirana_numero=_numero_bolirana(partida),
        bolirana_equipo=participante.equipo or None,
        bolirana_fraccion_num=fraccion_num,
        bolirana_fraccion_den=fraccion_den,
        bolirana_bebidas=bebidas,
        bolirana_partida_id=partida.id,
        fecha_ocupacion=mesa.fecha_ocupacion or ahora,
        alias_cliente=alias_cliente,
        es_pago_division=0,
    )
    cargo.guardar_origen(mesa)
    if not mesa.fecha_ocupacion:
        mesa.fecha_ocupacion = ahora
    mesa.estado = "ocupada"
    db.add(cargo)
    db.flush()
    return cargo


def _crear_cargo_alias(
    db: Session,
    partida: PartidaBolirana,
    participante: ParticipanteBolirana,
    monto: float,
    usuario_id: int,
    ahora,
    detalle: Optional[str] = None,
    bebidas: Optional[str] = None,
    fraccion_num: Optional[int] = None,
    fraccion_den: Optional[int] = None,
) -> Pedido:
    """Cargo legacy para jugadores libres de partidas antiguas.

    Las partidas nuevas exigen una cuenta de origen, así que este camino solo
    conserva la compatibilidad con cargos pendientes ya existentes.
    """
    cargo = Pedido(
        mesa_id=None,
        usuario_id=usuario_id,
        fecha=ahora,
        total=round(float(monto), 2),
        estado="pendiente",
        concepto=_concepto_cargo(partida, participante),
        concepto_detalle=detalle,
        bolirana_numero=_numero_bolirana(partida),
        bolirana_equipo=participante.equipo or None,
        bolirana_fraccion_num=fraccion_num,
        bolirana_fraccion_den=fraccion_den,
        bolirana_bebidas=bebidas,
        bolirana_partida_id=partida.id,
        fecha_ocupacion=ahora,
        alias_cliente=participante.alias,
        mesa_etiqueta_historica=(
            f"Bolirana {_etiqueta_bolirana(partida.bolirana.nombre)}"
        ),
        es_pago_division=0,
    )
    db.add(cargo)
    db.flush()
    return cargo


def _liquidar_participante(
    db: Session,
    partida: PartidaBolirana,
    participante: ParticipanteBolirana,
    monto: float,
    usuario_id: int,
    ahora,
    detalle: Optional[str] = None,
    bebidas: Optional[str] = None,
    fraccion_num: Optional[int] = None,
    fraccion_den: Optional[int] = None,
) -> None:
    """Marca al perdedor y crea su cargo en la cuenta que corresponda."""
    participante.es_perdedor = 1
    participante.monto_asignado = round(float(monto), 2)
    if monto <= 0:
        participante.estado_pago = "sin_consumo"
        return

    mesa = _mesa_destino_participante(db, participante)
    if mesa is not None:
        cargo = _crear_cargo_cuenta(
            db,
            partida,
            participante,
            mesa,
            monto,
            usuario_id,
            ahora,
            detalle,
            bebidas,
            fraccion_num,
            fraccion_den,
        )
        participante.estado_pago = "transferido"
    else:
        cargo = _crear_cargo_alias(
            db,
            partida,
            participante,
            monto,
            usuario_id,
            ahora,
            detalle,
            bebidas,
            fraccion_num,
            fraccion_den,
        )
        participante.estado_pago = "pendiente"
    participante.pedido_cobro_id = cargo.id


# ------------------------------------------------------------------
# Consultas
# ------------------------------------------------------------------

@router.get("/", response_model=List[BoliranaOut])
def listar_boliranas(db: Session = Depends(get_db)):
    """Lista las boliranas activas con su partida en curso, si existe."""
    boliranas = (
        db.query(Bolirana)
        .filter(Bolirana.activa == 1)
        .order_by(Bolirana.nombre, Bolirana.id)
        .all()
    )
    return [_bolirana_out(db, b) for b in boliranas]


@router.get("/cargos-pendientes", response_model=List[CargoBoliranaOut])
def cargos_pendientes(db: Session = Depends(get_db)):
    """Cargos legacy de jugadores libres que aún no se han pagado."""
    filas = (
        db.query(Pedido, PartidaBolirana, Bolirana)
        .join(PartidaBolirana, PartidaBolirana.id == Pedido.bolirana_partida_id)
        .join(Bolirana, Bolirana.id == PartidaBolirana.bolirana_id)
        .filter(
            Pedido.estado == "pendiente",
            Pedido.mesa_id.is_(None),
            Pedido.bolirana_partida_id.isnot(None),
        )
        .order_by(Pedido.fecha, Pedido.id)
        .all()
    )
    return [
        CargoBoliranaOut(
            pedido_id=pedido.id,
            partida_id=partida.id,
            bolirana_id=bolirana.id,
            bolirana_nombre=bolirana.nombre,
            alias=pedido.alias_cliente,
            concepto=pedido.concepto or "Consumo Bolirana (Partida)",
            total=round(float(pedido.total or 0.0), 2),
            fecha=pedido.fecha,
        )
        for pedido, partida, bolirana in filas
    ]


@router.get("/{bolirana_id}", response_model=BoliranaOut)
def obtener_bolirana(bolirana_id: int, db: Session = Depends(get_db)):
    """Detalle de una bolirana y de su ronda actual."""
    return _bolirana_out(db, _bolirana(db, bolirana_id))


# ------------------------------------------------------------------
# Administración (solo Administrador)
# ------------------------------------------------------------------

@router.post("/", response_model=BoliranaOut, status_code=201)
def crear_bolirana(datos: BoliranaCreate, db: Session = Depends(get_db)):
    """Da de alta una bolirana."""
    _exigir_admin(db, datos.usuario_id)
    nombre = datos.nombre.strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="Escribe el nombre de la bolirana")

    existente = (
        db.query(Bolirana)
        .filter(
            Bolirana.activa == 1,
            func.lower(Bolirana.nombre) == nombre.lower(),
        )
        .first()
    )
    if existente:
        raise HTTPException(
            status_code=400, detail=f"Ya existe una bolirana llamada {nombre}."
        )

    bolirana = Bolirana(nombre=nombre, activa=1)
    db.add(bolirana)
    db.commit()
    db.refresh(bolirana)
    return _bolirana_out(db, bolirana)


@router.delete("/{bolirana_id}")
def eliminar_bolirana(
    bolirana_id: int,
    usuario_id: int,
    db: Session = Depends(get_db),
):
    """Elimina una bolirana si no tiene una partida activa.

    Si ya tiene historial se marca inactiva para conservar los tickets y el
    historial de ventas. Las boliranas sin historial se borran físicamente.
    """
    _exigir_admin(db, usuario_id)
    bolirana = _bolirana(db, bolirana_id)
    if partida_activa(db, bolirana.id):
        raise HTTPException(
            status_code=409,
            detail=(
                f"La bolirana {bolirana.nombre} tiene una partida activa. "
                "Finaliza la partida antes de eliminarla."
            ),
        )

    tiene_historial = (
        db.query(PartidaBolirana.id)
        .filter(PartidaBolirana.bolirana_id == bolirana.id)
        .first()
        is not None
    )
    if tiene_historial:
        bolirana.activa = 0
        db.commit()
        return {"mensaje": f"Bolirana {bolirana.nombre} eliminada"}

    db.delete(bolirana)
    db.commit()
    return {"mensaje": f"Bolirana {bolirana.nombre} eliminada"}


# ------------------------------------------------------------------
# Operación de partidas
# ------------------------------------------------------------------

@router.post("/{bolirana_id}/iniciar", response_model=BoliranaOut)
def iniciar_partida(
    bolirana_id: int,
    datos: IniciarPartidaBoliranaIn,
    db: Session = Depends(get_db),
):
    """Inicia una partida con dos o más participantes.

    Varios alias pueden vincularse a la misma mesa o barra; cada uno recibe
    su propio cargo en esa cuenta al liquidar. Los clientes individuales
    representan a una sola persona y participan una única vez.
    """
    exigir_turno_abierto(db)
    _usuario(db, datos.usuario_id)
    bolirana = _bolirana(db, bolirana_id)
    if partida_activa(db, bolirana.id):
        raise HTTPException(
            status_code=409,
            detail=(
                f"La bolirana {bolirana.nombre} ya tiene una partida activa. "
                "Finalízala antes de iniciar otra."
            ),
        )

    # Validar referencias, cuentas individuales y candados antes de crear.
    # Varios alias pueden compartir la misma mesa o barra: cada jugador se
    # carga por separado a esa cuenta al liquidar. Los clientes individuales
    # representan a una sola persona, así que participan una única vez.
    mesas_vistas = set()
    barras_vistas = set()
    individuales_usados = set()
    alias_vistos = set()  # (nombre en minúsculas, cuenta de origen)
    for participante in datos.participantes:
        if participante.tipo == "mesa":
            mesa = _mesa_por_id(db, participante.mesa_id or 0)
            if mesa.id in mesas_vistas:
                raise HTTPException(
                    status_code=400, detail="No repitas la misma mesa."
                )
            es_individual = (mesa.tipo or "mesa") == "individual"
            if mesa.estado != "ocupada":
                etiqueta = (
                    f"Individual — {mesa.nombre or 'Cliente'}"
                    if es_individual
                    else f"Mesa {mesa.numero}"
                )
                raise HTTPException(
                    status_code=400,
                    detail=f"{etiqueta} debe estar ocupada para jugar.",
                )
            if es_individual and mesa.id in individuales_usados:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"El cliente individual {mesa.nombre or 'Cliente'} "
                        "ya participa en esta partida."
                    ),
                )
            exigir_mesa_sin_bolirana(db, mesa)
            mesas_vistas.add(mesa.id)
            if es_individual:
                individuales_usados.add(mesa.id)
        elif participante.tipo == "barra":
            numero_barra = participante.barra_numero or 0
            mesas = _mesas_de_barra(db, numero_barra)
            if numero_barra in barras_vistas:
                raise HTTPException(
                    status_code=400, detail="No repitas la misma barra."
                )
            if not any(m.estado == "ocupada" for m in mesas):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Barra {numero_barra} debe tener al menos "
                        "una plaza ocupada para jugar."
                    ),
                )
            exigir_barra_sin_bolirana(db, numero_barra)
            barras_vistas.add(numero_barra)
        else:
            alias = (participante.alias or "").strip()
            ya_juega = (
                db.query(ParticipanteBolirana.id)
                .join(
                    PartidaBolirana,
                    PartidaBolirana.id == ParticipanteBolirana.partida_id,
                )
                .filter(
                    PartidaBolirana.estado == "en_curso",
                    ParticipanteBolirana.tipo == "alias",
                    func.lower(ParticipanteBolirana.alias) == alias.lower(),
                )
                .first()
            )
            if ya_juega:
                raise HTTPException(
                    status_code=409,
                    detail=f"El jugador {alias} ya está en otra partida activa.",
                )

            # Clave de la cuenta de origen para validar duplicados.
            if participante.origen_tipo in {"mesa", "individual"}:
                origen = _mesa_por_id(db, participante.origen_mesa_id or 0)
                es_individual = (origen.tipo or "mesa") == "individual"
                if participante.origen_tipo == "individual" and not es_individual:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"El origen de {alias} no es un cliente individual."
                        ),
                    )
                if participante.origen_tipo == "mesa" and es_individual:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"El origen de {alias} es un cliente individual; "
                            "selecciónalo como Individual."
                        ),
                    )
                if origen.estado != "ocupada":
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"La cuenta de origen de {alias} debe estar ocupada "
                            "para vincularlo."
                        ),
                    )
                exigir_mesa_sin_bolirana(db, origen)
                if es_individual:
                    if origen.id in individuales_usados:
                        raise HTTPException(
                            status_code=400,
                            detail=(
                                f"El cliente individual "
                                f"{origen.nombre or 'Cliente'} ya participa "
                                "en esta partida."
                            ),
                        )
                    individuales_usados.add(origen.id)
                origen_clave = (
                    ("individual", origen.id)
                    if es_individual
                    else ("mesa", origen.id)
                )
            elif participante.origen_tipo == "barra":
                numero_barra = participante.origen_barra_numero or 0
                mesas = _mesas_de_barra(db, numero_barra)
                if not any(m.estado == "ocupada" for m in mesas):
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"La Barra {numero_barra} (origen de {alias}) debe "
                            "tener al menos una plaza ocupada."
                        ),
                    )
                exigir_barra_sin_bolirana(db, numero_barra)
                origen_clave = ("barra", numero_barra)
            else:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"El jugador {alias} debe estar vinculado a una mesa, "
                        "barra o cliente individual."
                    ),
                )

            # Solo se bloquea el mismo nombre en la misma cuenta de origen.
            combinacion = (alias.lower(), origen_clave)
            if combinacion in alias_vistos:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"El jugador {alias} ya está en esta partida con la "
                        "misma cuenta de origen."
                    ),
                )
            alias_vistos.add(combinacion)

    partida = PartidaBolirana(
        bolirana_id=bolirana.id,
        usuario_id=datos.usuario_id,
        estado="en_curso",
        modalidad=datos.modalidad,
        fecha_inicio=ahora_local(),
        total_bebidas=0.0,
    )
    db.add(partida)
    db.flush()

    for participante in datos.participantes:
        es_alias = participante.tipo == "alias"
        db.add(
            ParticipanteBolirana(
                partida_id=partida.id,
                tipo=participante.tipo,
                mesa_id=participante.mesa_id,
                barra_numero=participante.barra_numero,
                alias=(
                    (participante.alias or "").strip() if es_alias else None
                ),
                origen_tipo=(
                    participante.origen_tipo if es_alias else None
                ),
                origen_mesa_id=(
                    participante.origen_mesa_id if es_alias else None
                ),
                origen_barra_numero=(
                    participante.origen_barra_numero if es_alias else None
                ),
                equipo=(
                    (participante.equipo or "").strip()
                    if datos.modalidad == "equipos"
                    else None
                ),
                estado_pago="pendiente",
            )
        )

    db.commit()
    return _bolirana_out(db, bolirana)


@router.post("/{bolirana_id}/pedidos", response_model=BoliranaOut)
def cargar_bebidas(
    bolirana_id: int,
    datos: PedidoBoliranaCreate,
    db: Session = Depends(get_db),
):
    """Carga bebidas a la ronda actual y descuenta stock una sola vez."""
    exigir_turno_abierto(db)
    _usuario(db, datos.usuario_id)
    bolirana = _bolirana(db, bolirana_id)
    partida = partida_activa(db, bolirana.id)
    if not partida:
        raise HTTPException(
            status_code=409,
            detail=(
                f"La bolirana {bolirana.nombre} no tiene una partida activa. "
                "Inicia una partida para cargar bebidas."
            ),
        )
    if not datos.items:
        raise HTTPException(status_code=400, detail="El pedido no tiene productos")

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
    total = 0.0
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
        total += producto.precio * item.cantidad

    ahora = ahora_local()
    pedido = Pedido(
        mesa_id=None,
        usuario_id=datos.usuario_id,
        fecha=ahora,
        total=round(total, 2),
        estado="bolirana",
        bolirana_partida_id=partida.id,
        fecha_ocupacion=ahora,
        es_pago_division=0,
    )
    db.add(pedido)
    db.flush()

    for item in datos.items:
        producto = productos[item.producto_id]
        subtotal = round(producto.precio * item.cantidad, 2)
        producto.stock -= item.cantidad
        db.add(
            PedidoItem(
                pedido_id=pedido.id,
                producto_id=producto.id,
                cantidad=item.cantidad,
                precio_unitario=producto.precio,
                subtotal=subtotal,
            )
        )

    partida.total_bebidas = round(
        float(partida.total_bebidas or 0.0) + total, 2
    )
    db.commit()
    return _bolirana_out(db, bolirana)


@router.post("/{bolirana_id}/finalizar", response_model=BoliranaOut)
def finalizar_partida(
    bolirana_id: int,
    datos: LiquidarPartidaBoliranaIn,
    db: Session = Depends(get_db),
):
    """Liquida la ronda y reparte el total entre perdedores o equipos."""
    exigir_turno_abierto(db)
    _usuario(db, datos.usuario_id)
    bolirana = _bolirana(db, bolirana_id)
    partida = (
        db.query(PartidaBolirana)
        .options(
            joinedload(PartidaBolirana.participantes).joinedload(
                ParticipanteBolirana.mesa
            ),
            joinedload(PartidaBolirana.participantes).joinedload(
                ParticipanteBolirana.origen_mesa
            ),
            joinedload(PartidaBolirana.bolirana),
        )
        .filter(
            PartidaBolirana.id == (
                db.query(PartidaBolirana.id)
                .filter(
                    PartidaBolirana.bolirana_id == bolirana.id,
                    PartidaBolirana.estado == "en_curso",
                )
                .order_by(PartidaBolirana.id.desc())
                .limit(1)
                .scalar_subquery()
            )
        )
        .first()
    )
    if not partida:
        raise HTTPException(
            status_code=409,
            detail=f"La bolirana {bolirana.nombre} no tiene una partida activa.",
        )

    participantes = {p.id: p for p in partida.participantes}
    modalidad = partida.modalidad or "directo"

    if modalidad == "equipos":
        if datos.perdedores:
            raise HTTPException(
                status_code=400,
                detail=(
                    "La partida es por equipos: selecciona los equipos "
                    "perdedores, no participantes individuales."
                ),
            )
        if not datos.equipos_perdedores:
            raise HTTPException(
                status_code=400,
                detail="Selecciona al menos un equipo perdedor.",
            )
        equipos: dict = {}
        for participante in sorted(
            partida.participantes, key=lambda p: p.id
        ):
            nombre_equipo = (participante.equipo or "").strip()
            if nombre_equipo:
                equipos.setdefault(nombre_equipo, []).append(participante)
        for nombre_equipo in datos.equipos_perdedores:
            if nombre_equipo not in equipos:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"El equipo {nombre_equipo} no pertenece a esta partida."
                    ),
                )
    else:
        if datos.equipos_perdedores:
            raise HTTPException(
                status_code=400,
                detail=(
                    "La partida es directa: selecciona participantes "
                    "perdedores, no equipos."
                ),
            )
        if not datos.perdedores:
            raise HTTPException(
                status_code=400,
                detail="Selecciona al menos un perdedor.",
            )
        for participante_id in datos.perdedores:
            if participante_id not in participantes:
                raise HTTPException(
                    status_code=400,
                    detail="Uno de los perdedores no pertenece a esta partida.",
                )

    # El total se recalcula desde las comandas para no confiar en un valor
    # que pudo quedar desactualizado.
    total = round(
        float(
            db.query(func.coalesce(func.sum(Pedido.total), 0.0))
            .filter(
                Pedido.bolirana_partida_id == partida.id,
                Pedido.estado == "bolirana",
            )
            .scalar()
            or 0.0
        ),
        2,
    )
    partida.total_bebidas = total
    consumo = _consumo_partida(db, partida.id)
    bebidas = _bebidas_texto(consumo)

    ahora = ahora_local()

    def _repartir(monto_total: float, cantidad: int) -> List[float]:
        """Divide un monto en partes iguales ajustando los centavos."""
        if cantidad <= 0:
            return []
        base = round(monto_total / cantidad, 2)
        montos = [base] * cantidad
        # Ajuste de centavos para que la suma sea exactamente el total.
        montos[-1] = round(monto_total - base * (cantidad - 1), 2)
        return montos

    if modalidad == "equipos":
        # Primero se reparte entre los equipos perdedores y luego la parte
        # de cada equipo entre sus integrantes.
        equipos_perdedores = datos.equipos_perdedores
        montos_equipo = _repartir(total, len(equipos_perdedores))
        for nombre_equipo, monto_equipo in zip(
            equipos_perdedores, montos_equipo
        ):
            integrantes = equipos[nombre_equipo]
            montos = _repartir(monto_equipo, len(integrantes))
            denominador = len(equipos_perdedores) * len(integrantes)
            detalle = _detalle_cargo(consumo, 1, denominador)
            for integrante, monto in zip(integrantes, montos):
                _liquidar_participante(
                    db,
                    partida,
                    integrante,
                    monto,
                    datos.usuario_id,
                    ahora,
                    detalle,
                    bebidas,
                    1,
                    denominador,
                )
    else:
        montos = _repartir(total, len(datos.perdedores))
        denominador = len(datos.perdedores)
        detalle = _detalle_cargo(consumo, 1, denominador)
        for participante_id, monto in zip(datos.perdedores, montos):
            _liquidar_participante(
                db,
                partida,
                participantes[participante_id],
                monto,
                datos.usuario_id,
                ahora,
                detalle,
                bebidas,
                1,
                denominador,
            )

    partida.estado = "finalizada"
    partida.fecha_fin = ahora
    db.commit()
    return _bolirana_out(db, bolirana)


@router.post("/cargos/{pedido_id}/pagar")
def pagar_cargo(
    pedido_id: int,
    datos: PagarCargoBoliranaIn,
    db: Session = Depends(get_db),
):
    """Cobra un cargo legacy pendiente de un jugador libre (simple o mixto)."""
    exigir_turno_abierto(db)
    _usuario(db, datos.usuario_id)

    pedido = (
        db.query(Pedido)
        .filter(
            Pedido.id == pedido_id,
            Pedido.estado == "pendiente",
            Pedido.bolirana_partida_id.isnot(None),
            Pedido.mesa_id.is_(None),
        )
        .first()
    )
    if not pedido:
        raise HTTPException(
            status_code=404,
            detail="El cargo de bolirana no existe o ya fue cobrado.",
        )

    _validar_pagos(float(pedido.total or 0.0), datos.pagos)

    formas = [p.forma_pago for p in datos.pagos]
    montos = [round(float(p.monto), 2) for p in datos.pagos]
    ahora = ahora_local()
    pedido.estado = "cerrado"
    pedido.forma_pago = "mixto" if len(montos) > 1 else formas[0]
    pedido.pago_1_forma = formas[0]
    pedido.pago_1_monto = montos[0]
    pedido.pago_2_forma = formas[1] if len(montos) > 1 else None
    pedido.pago_2_monto = montos[1] if len(montos) > 1 else None
    pedido.fecha_cierre = ahora
    pedido.fecha_ocupacion = pedido.fecha_ocupacion or ahora
    pedido.usuario_cierre_id = datos.usuario_id

    participante = (
        db.query(ParticipanteBolirana)
        .filter(ParticipanteBolirana.pedido_cobro_id == pedido.id)
        .first()
    )
    if participante:
        participante.estado_pago = "pagado"

    db.commit()
    return {
        "mensaje": "Cargo de bolirana cobrado correctamente",
        "pedido_id": pedido.id,
        "total": round(float(pedido.total or 0.0), 2),
    }
