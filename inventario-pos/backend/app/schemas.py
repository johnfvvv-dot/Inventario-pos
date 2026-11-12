"""Esquemas Pydantic para validación de datos de entrada/salida."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    """Credenciales de acceso: el identificador se llama "usuario"."""

    usuario: str = Field(..., min_length=1, max_length=60)
    password: str

    @model_validator(mode="before")
    @classmethod
    def _aceptar_alias_antiguo(cls, datos):
        """Compatibilidad con clientes anteriores que enviaban 'alias'."""
        if isinstance(datos, dict) and not datos.get("usuario") and datos.get("alias"):
            return {**datos, "usuario": datos["alias"]}
        return datos


class UsuarioUpdate(BaseModel):
    alias: Optional[str] = Field(default=None, min_length=2, max_length=60)
    nombre: Optional[str] = Field(default=None, max_length=100)
    rol: Optional[str] = Field(default=None, max_length=20)
    activo: Optional[bool] = None
    ingreso_stock: Optional[bool] = None
    editar_cantidades: Optional[bool] = None


class CambiarClaveIn(BaseModel):
    password: str = Field(..., min_length=4, max_length=100)


class UsuarioOut(BaseModel):
    id: int
    alias: str
    nombre: Optional[str] = None
    rol: str
    activo: bool = True
    ingreso_stock: bool = False
    editar_cantidades: bool = False
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
    """Alta de producto: el precio de compra es obligatorio."""

    precio_compra: float = Field(..., ge=0)


class ProductoUpdate(ProductoBase):
    """Edición: incluye el precio de compra para poder corregirlo."""

    precio_compra: float = Field(..., ge=0)


class ProductoOut(ProductoBase):
    id: int
    precio_compra: Optional[float] = 0.0
    model_config = ConfigDict(from_attributes=True)


class StockUpdate(BaseModel):
    nuevo_stock: int = Field(..., ge=0)


class StockAjuste(BaseModel):
    """Variación de stock: positiva para ingresar, negativa para descontar."""

    delta: int = Field(..., ge=-1000000, le=1000000)


class ProductoFiltroOut(BaseModel):
    """Respuesta paginada del inventario."""
    items: List[ProductoOut]
    total: int
    stock_total: int = 0
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
    mesa_etiqueta: Optional[str] = None
    usuario_nombre: str = ""
    usuario_cierre_nombre: str = ""
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


class PosicionBarra(BaseModel):
    """Puesto (cliente) dentro de una barra."""
    id: int
    posicion: int = 1
    estado: str
    total_cuenta: float = 0.0


class MesaListadoOut(MesaBase):
    """Mesa (o barra agrupada) con el resumen de su cuenta pendiente."""
    id: int
    tipo: str = "mesa"
    grupo: Optional[str] = None
    posicion: int = 1
    total_cuenta: float = 0.0
    tiene_cuenta_pendiente: bool = False
    detalle_pendiente: str = ""
    posiciones: List[PosicionBarra] = []
    model_config = ConfigDict(from_attributes=True)


class OcuparMesaOut(BaseModel):
    """Resultado de asignar un cliente a una mesa o barra."""
    mesa_id: int
    mesa_numero: int
    tipo: str = "mesa"
    mensaje: str
    nueva: bool = False


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
    fondo_inicial: float = 0.0
    totales: TotalesFormaPago
    ganancia: float = 0.0


class AbrirTurnoIn(BaseModel):
    """Datos para abrir un turno: cajero y base en efectivo."""

    usuario_id: int = Field(default=1, gt=0)
    fondo_inicial: float = Field(..., ge=0)


class AbrirTurnoOut(BaseModel):
    mensaje: str
    turno: TurnoCajaOut


class CerrarTurnoIn(BaseModel):
    observaciones: Optional[str] = Field(default=None, max_length=255)


class ResumenCajaOut(BaseModel):
    desde: Optional[datetime] = None
    hasta: Optional[datetime] = None
    totales: TotalesFormaPago
    ganancia: float = 0.0
    pedidos_cerrados: int
    mesas_atendidas: int
    por_forma_pago: dict = {}


# ---------- Personalización ----------

class ConfiguracionNegocioIn(BaseModel):
    nombre_negocio: str = Field(..., min_length=1, max_length=80)
    logo: Optional[str] = Field(default=None, max_length=1_600_000)


class ConfiguracionNegocioOut(BaseModel):
    nombre_negocio: str = "Inventario POS"
    logo: Optional[str] = None
    actualizado_en: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# ---------- Tickets internos ----------

class TicketItemOut(BaseModel):
    nombre: str
    cantidad: int
    precio_unitario: float
    subtotal: float


class TicketOut(BaseModel):
    id: str
    tipo: str  # pedido | division
    folio: str
    mesa: str
    fecha_ocupacion: datetime
    fecha_pago: datetime
    alias: Optional[str] = None
    forma_pago: str = "efectivo"
    items: List[TicketItemOut]


class TicketsTurnoOut(BaseModel):
    turno_id: int
    estado: str
    fecha_apertura: datetime
    fecha_cierre: Optional[datetime] = None
    nombre_negocio: str = "Inventario POS"
    tickets: List[TicketOut]


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
    # NULL o ausente = cuenta general de la mesa/barra.
    participante_id: Optional[int] = Field(default=None, gt=0)
    # Si se envía, crea el alias y le asigna todo el pedido en una transacción.
    nuevo_alias: Optional[str] = Field(default=None, min_length=1, max_length=60)
    items: List[PedidoItemCreate]

    @model_validator(mode="after")
    def _destino_unico(self):
        if self.participante_id is not None and self.nuevo_alias:
            raise ValueError(
                "Elegí un alias existente o creá uno nuevo, pero no ambos."
            )
        return self


class PedidoItemAjuste(BaseModel):
    """Ajuste de cantidad de una línea de un pedido abierto."""
    cantidad: int = Field(..., ge=0)


class AjusteLineaOut(BaseModel):
    """Resultado de ajustar una línea de la cuenta de un alias."""

    participante_id: Optional[int] = None
    division_id: Optional[int] = None
    eliminado: bool = False
    subtotal: float = 0.0
    total_division: float = 0.0


class PedidoOut(BaseModel):
    id: int
    mesa: Optional[MesaOut] = None
    mesa_numero_historico: Optional[int] = None
    usuario: UsuarioOut
    items: List[PedidoItemOut]
    fecha: datetime
    fecha_cierre: Optional[datetime] = None
    total: float
    estado: str
    participante_id: Optional[int] = None
    alias: Optional[str] = None
    es_pago_division: bool = False
    usuario_cierre_id: Optional[int] = None
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
    # Identificadores para editar la línea desde el panel de pedidos.
    participante_item_id: Optional[int] = None
    pedido_id: Optional[int] = None


class ParticipanteResumen(BaseModel):
    id: int
    alias: str
    subtotal: float
    pagado: bool
    forma_pago: Optional[str] = None
    fecha_pago: Optional[datetime] = None
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
    total_general: float = 0.0
    total_divisiones: float = 0.0
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
    """División de una mesa o de una barra completa.

    Se debe indicar `mesa_id` (mesa o plaza concreta) o `barra_numero`
    (cuenta agregada de la barra, con todas sus plazas).
    """

    mesa_id: Optional[int] = Field(default=None, gt=0)
    barra_numero: Optional[int] = Field(default=None, gt=0)
    usuario_id: int = Field(..., gt=0)
    participantes: List[ParticipanteCreate]


class AliasCreate(BaseModel):
    """Crea un cliente/alias vacío para una mesa o barra."""

    mesa_id: Optional[int] = Field(default=None, gt=0)
    barra_numero: Optional[int] = Field(default=None, gt=0)
    usuario_id: int = Field(..., gt=0)
    alias: str = Field(..., min_length=1, max_length=60)

    @model_validator(mode="after")
    def _cuenta_unica(self):
        if (self.mesa_id is None) == (self.barra_numero is None):
            raise ValueError("Indicá la mesa o la barra, pero no ambas.")
        return self


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
    forma_pago: Optional[str] = None
    fecha_pago: Optional[datetime] = None
    items: List[ParticipanteItemOut]


class DivisionOut(BaseModel):
    id: int
    mesa_id: int
    total: float
    estado: str
    fecha: datetime
    participantes: List[ParticipanteOut]
