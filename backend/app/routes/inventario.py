"""Endpoints para gestión de inventario de productos."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Producto
from schemas import ProductoCreate, ProductoOut

router = APIRouter(prefix="/inventario", tags=["inventario"])

@router.post("/", response_model=ProductoOut)
def crear_producto(datos: ProductoCreate, db: Session = Depends(get_db)):
    """Crear nuevo producto en inventario."""
    nuevo_producto = Producto(
        nombre=datos.nombre,
        descripcion=datos.descripcion,
        precio=datos.precio,
        stock=datos.stock
    )
    db.add(nuevo_producto)
    db.commit()
    db.refresh(nuevo_producto)
    return nuevo_producto

@router.get("/", response_model=List[ProductoOut])
def listar_productos(db: Session = Depends(get_db)):
    """Listar todos los productos con stock actual."""
    return db.query(Producto).all()

@router.put("/{producto_id}/stock", response_model=ProductoOut)
def actualizar_stock(
    producto_id: int, 
    nuevo_stock: int, 
    db: Session = Depends(get_db)
):
    """Actualizar stock de un producto."""
    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    producto.stock = nuevo_stock
    db.commit()
    db.refresh(producto)
    return producto

@router.delete("/{producto_id}")
def eliminar_producto(producto_id: int, db: Session = Depends(get_db)):
    """Eliminar producto del inventario."""
    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    db.delete(producto)
    db.commit()
    return {"message": f"Producto {producto.nombre} eliminado"}