"""Modelos ORM SQLAlchemy para la base de datos."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Usuario(Base):
    """Usuario del sistema. Se identifica por alias (sin correo)."""

    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    alias = Column(String(60), unique=True, nullable=False, index=True)
    nombre = Column(String(100), nullable=True)  # nombre visible (opcional)
    rol = Column(String(20), nullable=False, default="bartender")  # admin | bartender
    password_hash = Column(String(128), nullable=False)
    activo = Column(Integer, default=1)
    creado_en = Column(DateTime, default=datetime.utcnow)

    pedidos = relationship("Pedido", back_populates="usuario")


class Categoria(Base):
    """Categoría de productos (bebidas, comidas, postres...)."""

    __tablename__ = "categorias"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(80), nullable=False, unique=True)
    activa = Column(Integer, default=1)

    productos = relationship("Producto", back_populates="categoria")


class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), nullable=False)
    descripcion = Column(String(255), nullable=True)
    precio = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False, default=0)
    categoria_id = Column(Integer, ForeignKey("categorias.id"), nullable=True)

    categoria = relationship("Categoria", back_populates="productos")


class Mesa(Base):
    __tablename__ = "mesas"

    id = Column(Integer, primary_key=True, index=True)
    numero = Column(Integer, unique=True, nullable=False)
    capacidad = Column(Integer, nullable=False, default=4)
    estado = Column(String(20), default="disponible")  # disponible | ocupada | cerrada

    pedidos = relationship("Pedido", back_populates="mesa")


class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, index=True)
    mesa_id = Column(Integer, ForeignKey("mesas.id"), nullable=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    fecha = Column(DateTime, default=datetime.utcnow)
    total = Column(Float, default=0.0)
    estado = Column(String(20), default="abierto")  # abierto | cerrado | dividido
    forma_pago = Column(String(20), nullable=True)  # efectivo | tarjeta | transferencia
    fecha_cierre = Column(DateTime, nullable=True)

    mesa = relationship("Mesa", back_populates="pedidos")
    usuario = relationship("Usuario", back_populates="pedidos")
    items = relationship(
        "PedidoItem", back_populates="pedido", cascade="all, delete-orphan"
    )


class PedidoItem(Base):
    __tablename__ = "pedido_items"

    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    cantidad = Column(Integer, nullable=False, default=1)
    precio_unitario = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)

    pedido = relationship("Pedido", back_populates="items")
    producto = relationship("Producto")


class Division(Base):
    """División de la cuenta de una mesa entre varios clientes."""

    __tablename__ = "divisiones"

    id = Column(Integer, primary_key=True, index=True)
    mesa_id = Column(Integer, ForeignKey("mesas.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    fecha = Column(DateTime, default=datetime.utcnow)
    total = Column(Float, default=0.0)
    estado = Column(String(20), default="pendiente")  # pendiente | pagada
    forma_pago = Column(String(20), nullable=True)  # efectivo | tarjeta | transferencia

    mesa = relationship("Mesa")
    usuario = relationship("Usuario")
    participantes = relationship(
        "Participante", back_populates="division", cascade="all, delete-orphan"
    )


class Participante(Base):
    """Cliente (alias) dentro de una división de cuenta."""

    __tablename__ = "participantes"

    id = Column(Integer, primary_key=True, index=True)
    division_id = Column(Integer, ForeignKey("divisiones.id"), nullable=False)
    alias = Column(String(60), nullable=False)
    subtotal = Column(Float, default=0.0)
    pagado = Column(Integer, default=0)  # 0 = pendiente, 1 = pagado
    forma_pago = Column(String(20), nullable=True)  # efectivo | tarjeta | transferencia

    division = relationship("Division", back_populates="participantes")
    items = relationship(
        "ParticipanteItem", back_populates="participante", cascade="all, delete-orphan"
    )


class ParticipanteItem(Base):
    """Producto asignado a un participante de la división."""

    __tablename__ = "participante_items"

    id = Column(Integer, primary_key=True, index=True)
    participante_id = Column(Integer, ForeignKey("participantes.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    cantidad = Column(Integer, nullable=False, default=1)
    precio_unitario = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)

    participante = relationship("Participante", back_populates="items")
    producto = relationship("Producto")


class TurnoCaja(Base):
    """Turno de caja: periodo de trabajo con totales por forma de pago."""

    __tablename__ = "turnos_caja"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    fecha_apertura = Column(DateTime, default=datetime.utcnow)
    fecha_cierre = Column(DateTime, nullable=True)
    observaciones = Column(String(255), nullable=True)
    estado = Column(String(20), default="abierto")  # abierto | cerrado

    usuario = relationship("Usuario")
