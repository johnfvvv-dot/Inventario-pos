"""Esquemas Pydantic para validación de datos de entrada/salida."""

from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

# --- Usuarios ---

class UsuarioBase(BaseModel):
    nombre: str = Field(..., max_length=100)
    rol: str = Field(..., max_length=20)
    email: str = Field(..., max_length=100)

class UsuarioCreate(UsuarioBase):
    pass

class UsuarioOut(UsuarioBase):
    id: int
    class Config:
        from_attributes = True

# --- Productos ---

class ProductoBase(BaseModel):
    nombre: str = Field(..., max_length=150)
    descripcion: Optional[str] = Field(None, max_length=255)
    precio: float = Field(..., gt=0)
    stock: int = Field(default=0, ge=0)

class ProductoCreate(ProductoBase):
    pass

class ProductoOut(ProductoBase):
    id: int
    class Config:
        from_attributes = True

# --- Mesas ---

class MesaBase(BaseModel):
    numero: int = Field(..., gt=0)
    capacidad: int = Field(..., gt=0)
    estado: str = Field(default="disponible", max_length=20)

class MesaCreate(MesaBase):
    pass

class MesaOut(MesaBase):
    id: int
    class Config:
        from_attributes = True

# --- Pedidos ---

class PedidoItemBase(BaseModel):
    producto_id: int = Field(..., gt=0)
    cantidad: int = Field(default=1, ge=1)

class PedidoItemCreate(PedidoItemBase):
    pass

class PedidoItemOut(PedidoItemBase):
    producto_nombre: str
    producto_precio: float
    subtotal: float

class PedidoBase(BaseModel):
    mesa_id: Optional[int] = Field(None, ge=0)
    usuario_id: int = Field(..., gt=0)

class PedidoCreate(PedidoBase):
    items: List[PedidoItemBase]

class PedidoOut(PedioBase):
    id: int
    mesa: Optional[MesaOut]
    usuario: UsuarioOut
    items: List[PedidoItemOut]
    fecha: datetime
    total: float
    estado: str
    class Config:
        from_attributes = True