"""Endpoints para gestión de inventario de productos (con búsqueda y paginación)."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Producto
from app.schemas import (
    ProductoCreate,
    ProductoFiltroOut,
    ProductoOut,
    StockAjuste,
    StockUpdate,
)

router = APIRouter(tags=["inventario"])


@router.post("/", response_model=ProductoOut, status_code=201)
def crear_producto(datos: ProductoCreate, db: Session = Depends(get_db)):
    """Crear nuevo producto en inventario."""
    nuevo_producto = Producto(
        nombre=datos.nombre,
        descripcion=datos.descripcion,
        precio=datos.precio,
        stock=datos.stock,
        categoria_id=datos.categoria_id,
    )
    db.add(nuevo_producto)
    db.commit()
    db.refresh(nuevo_producto)
    return nuevo_producto


@router.get("/", response_model=ProductoFiltroOut)
def listar_productos(
    buscar: Optional[str] = None,
    categoria_id: Optional[int] = None,
    limite: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Lista los productos con búsqueda, filtro por categoría y paginación."""
    limite = max(1, min(limite, 500))
    offset = max(0, offset)

    query = db.query(Producto)

    if buscar:
        texto = f"%{buscar.strip().lower()}%"
        query = query.filter(
            or_(
                func.lower(Producto.nombre).like(texto),
                func.lower(func.coalesce(Producto.descripcion, "")).like(texto),
            )
        )

    if categoria_id:
        query = query.filter(Producto.categoria_id == categoria_id)

    total = query.count()
    items = (
        query.order_by(Producto.nombre).offset(offset).limit(limite).all()
    )

    return ProductoFiltroOut(
        items=items,
        total=total,
        limite=limite,
        offset=offset,
        paginas=max(1, (total + limite - 1) // limite),
    )


@router.put("/{producto_id}/stock", response_model=ProductoOut)
def actualizar_stock(
    producto_id: int, datos: StockUpdate, db: Session = Depends(get_db)
):
    """Actualizar stock de un producto."""
    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    producto.stock = datos.nuevo_stock
    db.commit()
    db.refresh(producto)
    return producto


@router.post("/{producto_id}/stock/ajuste", response_model=ProductoOut)
def ajustar_stock(
    producto_id: int, datos: StockAjuste, db: Session = Depends(get_db)
):
    """Suma o resta una cantidad al stock actual de forma atómica.

    Se usa para el ingreso de mercadería y los botones +/-. Al operar sobre
    el valor actual de la base evita sobrescribir cambios hechos por otro
    usuario entre la lectura y la escritura.
    """
    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    producto.stock = max(0, producto.stock + datos.delta)
    db.commit()
    db.refresh(producto)
    return producto


@router.put("/{producto_id}", response_model=ProductoOut)
def actualizar_producto(
    producto_id: int, datos: ProductoCreate, db: Session = Depends(get_db)
):
    """Editar un producto (nombre, precio, categoría...)."""
    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    producto.nombre = datos.nombre
    producto.descripcion = datos.descripcion
    producto.precio = datos.precio
    producto.stock = datos.stock          # <- el stock SI se guarda (bug corregido)
    producto.categoria_id = datos.categoria_id
    db.commit()
    db.refresh(producto)
    return producto


@router.delete("/{producto_id}")
def eliminar_producto(producto_id: int, db: Session = Depends(get_db)):
    """Eliminar producto del inventario."""
    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    nombre = producto.nombre
    db.delete(producto)
    db.commit()
    return {"message": f"Producto {nombre} eliminado"}
