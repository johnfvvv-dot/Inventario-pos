"""Endpoints de categorías de productos."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Categoria, Producto
from app.schemas import CategoriaCreate, CategoriaOut

router = APIRouter(tags=["categorias"])


@router.get("/", response_model=List[CategoriaOut])
def listar_categorias(db: Session = Depends(get_db)):
    """Lista las categorías con la cantidad de productos de cada una."""
    categorias = db.query(Categoria).order_by(Categoria.nombre).all()
    conteo = dict(
        db.query(Producto.categoria_id, func.count(Producto.id))
        .group_by(Producto.categoria_id)
        .all()
    )
    return [
        CategoriaOut(
            id=c.id,
            nombre=c.nombre,
            activa=bool(c.activa),
            total_productos=conteo.get(c.id, 0),
        )
        for c in categorias
    ]


@router.post("/", response_model=CategoriaOut, status_code=201)
def crear_categoria(datos: CategoriaCreate, db: Session = Depends(get_db)):
    """Crea una nueva categoría."""
    existente = (
        db.query(Categoria)
        .filter(func.lower(Categoria.nombre) == datos.nombre.strip().lower())
        .first()
    )
    if existente:
        raise HTTPException(status_code=400, detail="La categoría ya existe")

    categoria = Categoria(nombre=datos.nombre.strip(), activa=1)
    db.add(categoria)
    db.commit()
    db.refresh(categoria)
    return CategoriaOut(id=categoria.id, nombre=categoria.nombre, activa=True, total_productos=0)


@router.put("/{categoria_id}", response_model=CategoriaOut)
def actualizar_categoria(
    categoria_id: int, datos: CategoriaCreate, db: Session = Depends(get_db)
):
    """Renombra una categoría."""
    categoria = db.query(Categoria).filter(Categoria.id == categoria_id).first()
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")

    categoria.nombre = datos.nombre.strip()
    db.commit()
    db.refresh(categoria)

    total = (
        db.query(func.count(Producto.id))
        .filter(Producto.categoria_id == categoria.id)
        .scalar()
        or 0
    )
    return CategoriaOut(
        id=categoria.id,
        nombre=categoria.nombre,
        activa=bool(categoria.activa),
        total_productos=total,
    )


@router.delete("/{categoria_id}")
def eliminar_categoria(categoria_id: int, db: Session = Depends(get_db)):
    """Elimina una categoría (los productos quedan sin categoría)."""
    categoria = db.query(Categoria).filter(Categoria.id == categoria_id).first()
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")

    db.query(Producto).filter(Producto.categoria_id == categoria.id).update(
        {"categoria_id": None}
    )
    nombre = categoria.nombre
    db.delete(categoria)
    db.commit()
    return {"message": f"Categoría '{nombre}' eliminada"}
