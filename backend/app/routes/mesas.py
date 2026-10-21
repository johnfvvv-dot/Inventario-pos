"""Endpoints para gestión de mesas y barras."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Division, Mesa, Pedido
from app.schemas import (
    BarraCreate,
    EstadoUpdate,
    MesaCreate,
    MesaListadoOut,
    MesaOut,
    OcuparMesaOut,
    PosicionBarra,
)

router = APIRouter(tags=["mesas"])

ESTADOS_PERMITIDOS = ["disponible", "ocupada", "cerrada"]


def _resumen_cuenta(db: Session, mesas: List[Mesa]):
    """Calcula el total pendiente y el detalle por mesa."""
    if not mesas:
        return {}

    ids = [m.id for m in mesas]

    pedidos = (
        db.query(Pedido.mesa_id, func.count(Pedido.id), func.coalesce(func.sum(Pedido.total), 0.0))
        .filter(Pedido.mesa_id.in_(ids), Pedido.estado == "abierto")
        .group_by(Pedido.mesa_id)
        .all()
    )
    divisiones = (
        db.query(Division.mesa_id, func.count(Division.id), func.coalesce(func.sum(Division.total), 0.0))
        .filter(Division.mesa_id.in_(ids), Division.estado == "pendiente")
        .group_by(Division.mesa_id)
        .all()
    )

    resumen: dict = {}
    for mesa_id, cantidad, total in pedidos:
        resumen[mesa_id] = {
            "pedidos": cantidad,
            "divisiones": 0,
            "total": round(float(total or 0), 2),
        }
    for mesa_id, cantidad, total in divisiones:
        item = resumen.setdefault(
            mesa_id, {"pedidos": 0, "divisiones": 0, "total": 0.0}
        )
        item["divisiones"] = cantidad
        item["total"] = round(item["total"] + float(total or 0), 2)
    return resumen


@router.post("/", response_model=MesaOut, status_code=201)
def crear_mesa(datos: MesaCreate, db: Session = Depends(get_db)):
    """Crear nueva mesa."""
    existente = db.query(Mesa).filter(Mesa.numero == datos.numero).first()
    if existente:
        raise HTTPException(status_code=400, detail="El número de mesa ya existe")

    nueva_mesa = Mesa(
        numero=datos.numero,
        capacidad=datos.capacidad,
        estado="disponible",
        tipo="mesa",
    )
    db.add(nueva_mesa)
    db.commit()
    db.refresh(nueva_mesa)
    return nueva_mesa


@router.post("/barra", response_model=List[MesaOut], status_code=201)
def crear_barra(datos: BarraCreate, db: Session = Depends(get_db)):
    """Crea una barra con una cuenta por cada posicion (cliente).

    Ej: Barra 2 con capacidad 3 genera 3 cuentas del grupo "Barra 2",
    cada una con su propia cuenta, igual que las mesas.
    """
    # Por defecto, una posicion (cuenta) por cada plaza de la barra
    cuentas = datos.cuentas if datos.cuentas else datos.capacidad
    cuentas = max(1, min(cuentas, 20))
    numero_base = datos.numero * 100  # evita chocar con mesas numeradas

    existentes = (
        db.query(Mesa)
        .filter(Mesa.grupo == f"Barra {datos.numero}")
        .all()
    )
    if existentes:
        raise HTTPException(
            status_code=400, detail=f"La Barra {datos.numero} ya existe"
        )

    grupo = f"Barra {datos.numero}"
    creadas = []
    for posicion in range(1, cuentas + 1):
        mesa = Mesa(
            numero=numero_base + posicion,
            capacidad=1,  # cada posicion es para un cliente
            estado="disponible",
            tipo="barra",
            grupo=grupo,
            posicion=posicion,
        )
        db.add(mesa)
        creadas.append(mesa)

    db.commit()
    for mesa in creadas:
        db.refresh(mesa)
    return creadas


@router.get("/", response_model=List[MesaListadoOut])
def listar_mesas(db: Session = Depends(get_db)):
    """Lista mesas y barras.

    Las mesas se listan una por una. Las barras se agrupan en UNA tarjeta
    por barra (titulo "Barra N", N plazas, estado y total agregados),
    conservando internamente una posicion por cliente.
    """
    mesas = db.query(Mesa).order_by(Mesa.tipo, Mesa.grupo, Mesa.numero).all()
    resumen = _resumen_cuenta(db, mesas)

    # --- Barras agrupadas (una tarjeta por barra) ---
    grupos: dict = {}
    for mesa in mesas:
        if (mesa.tipo or "mesa") != "barra" or not mesa.grupo:
            continue
        g = grupos.setdefault(mesa.grupo, [])
        g.append(mesa)

    resultado_barras = []
    for grupo, posiciones in grupos.items():
        posiciones.sort(key=lambda m: m.posicion or 0)
        info_pos = [resumen.get(m.id, {"pedidos": 0, "divisiones": 0, "total": 0.0}) for m in posiciones]
        total = round(sum(i["total"] for i in info_pos), 2)
        ocupada = any(m.estado == "ocupada" for m in posiciones)
        tiene = any(i["pedidos"] or i["divisiones"] for i in info_pos)

        # posicion activa: la primera ocupada, si no la primera libre
        activa = next((m for m in posiciones if m.estado == "ocupada"), posiciones[0])
        numero_barra = posiciones[0].numero // 100

        resultado_barras.append(
            MesaListadoOut(
                id=activa.id,
                numero=numero_barra,
                capacidad=len(posiciones),
                estado="ocupada" if ocupada else "disponible",
                tipo="barra",
                grupo=grupo,
                posicion=activa.posicion or 1,
                total_cuenta=total,
                tiene_cuenta_pendiente=tiene,
                detalle_pendiente=(
                    f"{sum(1 for m in posiciones if m.estado == 'ocupada')} cliente(s) en uso"
                    if ocupada
                    else ""
                ),
                posiciones=[
                    PosicionBarra(
                        id=m.id,
                        estado=m.estado,
                        total_cuenta=resumen.get(m.id, {}).get("total", 0.0),
                    )
                    for m in posiciones
                ],
            )
        )

    # --- Mesas normales ---
    resultado = []
    for mesa in mesas:
        if (mesa.tipo or "mesa") == "barra":
            continue
        info = resumen.get(mesa.id, {"pedidos": 0, "divisiones": 0, "total": 0.0})
        pendientes = []
        if info["pedidos"]:
            pendientes.append(
                f"{info['pedidos']} pedido abierto" + ("s" if info["pedidos"] > 1 else "")
            )
        if info["divisiones"]:
            pendientes.append(
                f"{info['divisiones']} división pendiente"
                + ("s" if info["divisiones"] > 1 else "")
            )

        resultado.append(
            MesaListadoOut(
                id=mesa.id,
                numero=mesa.numero,
                capacidad=mesa.capacidad,
                estado=mesa.estado,
                tipo=mesa.tipo or "mesa",
                grupo=mesa.grupo,
                posicion=mesa.posicion or 1,
                total_cuenta=info["total"],
                tiene_cuenta_pendiente=bool(pendientes),
                detalle_pendiente=" · ".join(pendientes),
            )
        )
    return resultado + resultado_barras


@router.post("/{mesa_id}/ocupar", response_model=OcuparMesaOut)
def ocupar_mesa(mesa_id: int, db: Session = Depends(get_db)):
    """Asigna un cliente a una mesa o a un puesto libre de una barra."""
    mesa = db.query(Mesa).filter(Mesa.id == mesa_id).first()
    if not mesa:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")

    if (mesa.tipo or "mesa") == "barra" and mesa.grupo:
        # primera posicion libre de la barra
        posiciones = (
            db.query(Mesa)
            .filter(Mesa.grupo == mesa.grupo)
            .order_by(Mesa.posicion)
            .all()
        )
        libre = next((m for m in posiciones if m.estado != "ocupada"), None)
        if not libre:
            raise HTTPException(
                status_code=400, detail="No hay puestos libres en esta barra"
            )
        libre.estado = "ocupada"
        db.commit()
        db.refresh(libre)
        return OcuparMesaOut(
            mesa_id=libre.id,
            mesa_numero=libre.numero // 100,
            tipo="barra",
            mensaje=f"Cliente asignado en {libre.grupo}",
            nueva=True,
        )

    mesa.estado = "ocupada"
    db.commit()
    db.refresh(mesa)
    return OcuparMesaOut(
        mesa_id=mesa.id,
        mesa_numero=mesa.numero,
        tipo="mesa",
        mensaje=f"Mesa {mesa.numero} ocupada",
    )


@router.put("/{mesa_id}/estado", response_model=MesaOut)
def actualizar_estado_mesa(
    mesa_id: int, datos: EstadoUpdate, db: Session = Depends(get_db)
):
    """Actualizar el estado de una mesa."""
    mesa = db.query(Mesa).filter(Mesa.id == mesa_id).first()
    if not mesa:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")

    if datos.nuevo_estado not in ESTADOS_PERMITIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Estado inválido. Use: {', '.join(ESTADOS_PERMITIDOS)}",
        )

    # No se puede marcar como disponible una mesa con cuentas pendientes
    if datos.nuevo_estado == "disponible":
        db.flush()
        pedidos_abiertos = (
            db.query(func.count(Pedido.id))
            .filter(Pedido.mesa_id == mesa.id, Pedido.estado == "abierto")
            .scalar()
            or 0
        )
        divisiones_pendientes = (
            db.query(func.count(Division.id))
            .filter(Division.mesa_id == mesa.id, Division.estado == "pendiente")
            .scalar()
            or 0
        )
        if pedidos_abiertos:
            raise HTTPException(
                status_code=400, detail="La mesa aún tiene un pedido abierto."
            )
        if divisiones_pendientes:
            raise HTTPException(
                status_code=400,
                detail="La mesa aún tiene una división de cuenta pendiente.",
            )

    mesa.estado = datos.nuevo_estado
    db.commit()
    db.refresh(mesa)
    return mesa


@router.post("/{mesa_id}/liberar", response_model=MesaOut)
def liberar_mesa(mesa_id: int, db: Session = Depends(get_db)):
    """Libera la mesa SOLO si no tiene cuentas pendientes."""
    mesa = db.query(Mesa).filter(Mesa.id == mesa_id).first()
    if not mesa:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")

    db.flush()
    pedidos_abiertos = (
        db.query(func.count(Pedido.id))
        .filter(Pedido.mesa_id == mesa.id, Pedido.estado == "abierto")
        .scalar()
        or 0
    )
    divisiones_pendientes = (
        db.query(func.count(Division.id))
        .filter(Division.mesa_id == mesa.id, Division.estado == "pendiente")
        .scalar()
        or 0
    )

    if pedidos_abiertos:
        raise HTTPException(
            status_code=400,
            detail="La mesa aún tiene un pedido abierto.",
        )
    if divisiones_pendientes:
        raise HTTPException(
            status_code=400,
            detail="La mesa aún tiene una división de cuenta pendiente.",
        )

    mesa.estado = "disponible"
    db.commit()
    db.refresh(mesa)
    return mesa


@router.delete("/{mesa_id}")
def eliminar_mesa(mesa_id: int, db: Session = Depends(get_db)):
    """Elimina una mesa o puesto de barra (solo si no tiene cuentas pendientes)."""
    mesa = db.query(Mesa).filter(Mesa.id == mesa_id).first()
    if not mesa:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")

    db.flush()
    pedidos_abiertos = (
        db.query(func.count(Pedido.id))
        .filter(Pedido.mesa_id == mesa.id, Pedido.estado == "abierto")
        .scalar()
        or 0
    )
    divisiones_pendientes = (
        db.query(func.count(Division.id))
        .filter(Division.mesa_id == mesa.id, Division.estado == "pendiente")
        .scalar()
        or 0
    )
    if pedidos_abiertos or divisiones_pendientes:
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar: la mesa tiene una cuenta pendiente.",
        )

    # Historial: se conservan los pedidos (cerrados) con el numero de mesa
    db.query(Pedido).filter(Pedido.mesa_id == mesa.id).update(
        {"mesa_id": None, "mesa_numero_historico": mesa.numero}
    )

    numero = mesa.numero
    grupo = mesa.grupo
    db.delete(mesa)
    db.commit()

    if grupo:
        # Si era la última cuenta de la barra, se elimina el grupo completo
        restantes = db.query(Mesa).filter(Mesa.grupo == grupo).count()
        if restantes == 0:
            return {"message": f"Barra '{grupo}' eliminada", "mesa": numero}
        return {"message": f"Cuenta eliminada de '{grupo}'", "mesa": numero}

    return {"message": f"Mesa {numero} eliminada", "mesa": numero}
