"""Esquemas Pydantic para validación de datos de entrada/salida."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------- Usuarios ----------

class UsuarioBase(BaseModel):
    nombre: str = Field(..., max_length=100)
    rol: str = Field(default="mesero", max_length=20)
    email: str = Field(..., max_length=100)


class UsuarioCreate(UsuarioBase):
    password: str = Field(..., min_length=4, max_length=100)


class UsuarioLogin(BaseModel):
    email: str
    password: str


class UsuarioOut(UsuarioBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# ---------- Productos ----------

class ProductoBase(BaseModel):
    nombre: str = Field(..., max_length=150)
    descripcion: Optional[str] = Field(default=None, max_length=255)
    precio: float = Field(..., gt=0)
    stock: int = Field(default=0, ge=0)


class ProductoCreate(ProductoBase):
    pass


class ProductoOut(ProductoBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class StockUpdate(BaseModel):
    nuevo_stock: int = Field(..., ge=0)


# ---------- Mesas ----------

class MesaBase(BaseModel):
    numero: int = Field(..., gt=0)
    capacidad: int = Field(default=4, gt=0)
    estado: str = Field(default="disponible", max_length=20)


class MesaCreate(MesaBase):
    pass


class MesaOut(MesaBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class EstadoUpdate(BaseModel):
    nuevo_estado: str = Field(..., max_length=20)


# ---------- Pedidos ----------

class PedidoItemCreate(BaseModel):
    producto_id: int = Field(..., gt=0)
    cantidad: int = Field(default=1, ge=1)


class PedidoItemOut(BaseModel):
    id: int
    producto_id: int
    producto_nombre: str
    cantidad: int
    precio_unitario: float
    subtotal: float


class PedidoCreate(BaseModel):
    mesa_id: int = Field(..., gt=0)
    usuario_id: int = Field(..., gt=0)
    items: List[PedidoItemCreate]


class PedidoOut(BaseModel):
    id: int
    mesa: Optional[MesaOut] = None
    usuario: UsuarioOut
    items: List[PedidoItemOut]
    fecha: datetime
    total: float
    estado: str
    model_config = ConfigDict(from_attributes=True)
