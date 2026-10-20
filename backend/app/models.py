"""Modelos ORM SQLAlchemy para la base de datos."""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from datetime import datetime

# Tabla intermedia: producto <-> pedido
producto_pedido = Table(
    "producto_pedido",
    Base.metadata,
    Column("pedido_id", Integer, ForeignKey("pedidos.id"), primary_key=True),
    Column("producto_id", Integer, ForeignKey("productos.id"), primary_key=True),
    Column("cantidad", Integer, default=1)
)

class Usuario(Base):
    __tablename__ = "usuarios"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    rol = Column(String(20), nullable=False)  # "admin" o "mesero"
    email = Column(String(100), unique=True, nullable=False)

class Producto(Base):
    __tablename__ = "productos"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), nullable=False)
    descripcion = Column(String(255), nullable=True)
    precio = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False, default=0)

class Mesa(Base):
    __tablename__ = "mesas"
    
    id = Column(Integer, primary_key=True, index=True)
    numero = Column(Integer, unique=True, nullable=False)
    capacidad = Column(Integer, nullable=False, default=4)
    estado = Column(String(20), default="disponible")  # "disponible", "ocupada", "cerrada"

class Pedido(Base):
    __tablename__ = "pedidos"
    
    id = Column(Integer, primary_key=True, index=True)
    mesa_id = Column(Integer, ForeignKey("mesas.id"), nullable=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    fecha = Column(DateTime, default=datetime.utcnow)
    total = Column(Float, default=0.0)
    estado = Column(String(20), default="abierto")  # "abierto", "cerrado", "pagado"
    
    # Relaciones
    mesa = relationship("Mesa", backref="pedidos")
    usuario = relationship("Usuario", backref="pedidos")
    items = relationship("Producto", secondary=producto_pedido, backref="pedidos")