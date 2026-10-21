"""Esquemas Pydantic para validación de datos de entrada/salida."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------- Usuarios ----------

ROLES = ["admin", "bartender"]
CLAVE_INICIAL = "1234"


class UsuarioBase(BaseModel):
    alias: str = Field(..., min_length=2, max_length=60)
    nombre: Optional[str] = Field(default=None, max_length=100)
    rol: str = Field(default="bartender", max_length=20)


class UsuarioCreate(UsuarioBase):
    """Si no se envia password se usa la clave inicial (1234)."""
    password: Optional[str] = Field(default=None, min_length=4, max_length=100)


class UsuarioLogin(BaseModel):
    alias: str
    password: str


class UsuarioUpdate(BaseModel):
    alias: Optional[str] = Field(default=None, min_length=2, max_length=60)
    nombre: Optional[str] = Field(default=None, max_length=100)
    rol: Optional[str] = Field(default=None, max_length=20)
    activo: Optional[bool] = None


class CambiarClaveIn(BaseModel):
    password: str = Field(..., min_length=4, max_length=100)


class UsuarioOut(BaseModel):
    id: int
    alias: str
    nombre: Optional[str] = None
    rol: str
    activo: bool = True
    creado_en: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# ---------- Categorias ----------

class CategoriaBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=80)


class CategoriaCreate(CategoriaBase):
    pass


class CategoriaOut(CategoriaBase):
    id: int
    activa: bool = True
    total_productos: int = 0
    model_config = ConfigDict(from_attributes=True)


# ---------- Productos ----------

class ProductoBase(BaseModel):
    nombre: str = Field(..., max_length=150)
    descripcion: Optional[str] = Field(default=None, max_length=255)
    precio: float = Field(..., gt=0)
    stock: int = Field(default=0, ge=0)
    categoria_id: Optional[int] = Field(default=None, gt=0)


class ProductoCreate(ProductoBase):
    pass


class ProductoOut(ProductoBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class StockUpdate(BaseModel):
    nuevo_stock: int = Field(..., ge=0)


class ProductoFiltroOut(BaseModel):
    """Respuesta paginada del inventario."""
    items: List[ProductoOut]
    total: int
    limite: int
    offset: int
    paginas: int


class PedidoHistorialOut(BaseModel):
    """Datos del historial de ventas."""
    id: int
    fecha: datetime
    estado: str
    forma_pago: Optional[str] = None
    total: float
    mesa_numero: Optional[int] = None
    usuario_nombre: str = ""
    productos: List[str] = []


# ---------- Mesas ----------

class MesaBase(BaseModel):
    numero: int = Field(..., gt=0)
    capacidad: int = Field(default=4, gt=0)
    estado: str = Field(default="disponible", max_length=20)


class MesaCreate(MesaBase):
    pass


class MesaOut(MesaBase):
    id: int
    tipo: str = "mesa"
    grupo: Optional[str] = None
    posicion: int = 1
    model_config = ConfigDict(from_attributes=True)


class MesaListadoOut(MesaBase):
    """Mesa con el resumen de su cuenta pendiente (para el panel de mesas)."""
    id: int
    tipo: str = "mesa"
    grupo: Optional[str] = None
    posicion: int = 1
    total_cuenta: float = 0.0
    tiene_cuenta_pendiente: bool = False
    detalle_pendiente: str = ""
    model_config = ConfigDict(from_attributes=True)


class BarraCreate(BaseModel):
    """Crea una barra.

    La capacidad define cuantos clientes (posiciones) puede tener la barra;
    cada posicion es una cuenta independiente, igual que una mesa.
    """
    numero: int = Field(..., gt=0)
    capacidad: int = Field(default=1, gt=0)
    # Opcional: si se indica, sobrescribe el numero de posiciones
    cuentas: Optional[int] = Field(default=None, ge=1, le=20)


class TransferirCuentaOut(BaseModel):
    mensaje: str
    mesa_origen: int
    mesa_destino: int
    total_transferido: float


# ---------- Formas de pago y corte de caja ----------

FORMAS_PAGO = ["efectivo", "tarjeta", "transferencia"]


class FormaPago(BaseModel):
    forma_pago: str = Field(default="efectivo", max_length=20)


class TotalesFormaPago(BaseModel):
    efectivo: float = 0.0
    tarjeta: float = 0.0
    transferencia: float = 0.0
    total: float = 0.0
    operaciones: int = 0


class TurnoCajaOut(BaseModel):
    id: int
    usuario_nombre: str
    fecha_apertura: datetime
    fecha_cierre: Optional[datetime] = None
    observaciones: Optional[str] = None
    estado: str
    totales: TotalesFormaPago


class AbrirTurnoOut(BaseModel):
    mensaje: str
    turno: TurnoCajaOut


class CerrarTurnoIn(BaseModel):
    observaciones: Optional[str] = Field(default=None, max_length=255)


class ResumenCajaOut(BaseModel):
    desde: Optional[datetime] = None
    hasta: Optional[datetime] = None
    totales: TotalesFormaPago
    pedidos_cerrados: int
    mesas_atendidas: int
    por_forma_pago: dict = {}


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


class PedidoItemAjuste(BaseModel):
    """Ajuste de cantidad de una línea de un pedido abierto."""
    cantidad: int = Field(..., ge=0)


class PedidoOut(BaseModel):
    id: int
    mesa: Optional[MesaOut] = None
    mesa_numero_historico: Optional[int] = None
    usuario: UsuarioOut
    items: List[PedidoItemOut]
    fecha: datetime
    total: float
    estado: str
    model_config = ConfigDict(from_attributes=True)


# ---------- Cuenta de la mesa ----------

class LineaCuenta(BaseModel):
    """Producto dentro de la cuenta, con el alias al que fue asignado."""
    producto_id: int
    producto_nombre: str
    cantidad: int
    precio_unitario: float
    subtotal: float
    alias: Optional[str] = None
    participante_id: Optional[int] = None


class ParticipanteResumen(BaseModel):
    id: int
    alias: str
    subtotal: float
    pagado: bool
    items: List[LineaCuenta]


class DivisionResumen(BaseModel):
    id: int
    total: float
    total_pendiente: float
    estado: str
    fecha: datetime
    participantes: List[ParticipanteResumen]


class CuentaMesaOut(BaseModel):
    mesa_id: int
    mesa_numero: int
    estado_mesa: str
    total: float
    pedidos: List[PedidoOut]
    divisiones: List[DivisionResumen]


# ---------- División de cuenta ----------

class ParticipanteItemCreate(BaseModel):
    producto_id: int = Field(..., gt=0)
    cantidad: int = Field(default=1, ge=1)


class ParticipanteCreate(BaseModel):
    alias: str = Field(..., min_length=1, max_length=60)
    items: List[ParticipanteItemCreate] = []


class DivisionCreate(BaseModel):
    mesa_id: int = Field(..., gt=0)
    usuario_id: int = Field(..., gt=0)
    participantes: List[ParticipanteCreate]


class ParticipanteItemOut(BaseModel):
    id: int
    producto_id: int
    producto_nombre: str
    cantidad: int
    precio_unitario: float
    subtotal: float


class ParticipanteOut(BaseModel):
    id: int
    alias: str
    subtotal: float
    pagado: bool
    items: List[ParticipanteItemOut]


class DivisionOut(BaseModel):
    id: int
    mesa_id: int
    total: float
    estado: str
    fecha: datetime
    participantes: List[ParticipanteOut]
