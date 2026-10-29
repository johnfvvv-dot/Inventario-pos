"""Modelos ORM SQLAlchemy para la base de datos."""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base
from app.tiempo import ahora_local


def etiqueta_desde_numero_historico(numero: int) -> str:
    """Etiqueta para pedidos antiguos que solo conservan el numero.

    Las plazas de barra usan la numeracion N*100 + posicion (101 -> Barra 1),
    por lo que se puede reconstruir la barra cuando ya no existe la mesa.
    """
    if numero >= 100 and 1 <= numero % 100 <= 20:
        return f"Barra {numero // 100}"
    return f"Mesa {numero}"


class Usuario(Base):
    """Usuario del sistema. Se identifica por alias (sin correo)."""

    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    alias = Column(String(60), unique=True, nullable=False, index=True)
    nombre = Column(String(100), nullable=True)  # nombre visible (opcional)
    rol = Column(String(20), nullable=False, default="bartender")  # admin | bartender
    password_hash = Column(String(128), nullable=False)
    activo = Column(Integer, default=1)
    # Permiso para ingresar stock (solo aplica a bartenders; el admin siempre
    # tiene la columna activa). Lo habilita el administrador desde Usuarios.
    ingreso_stock = Column(Integer, default=0)
    creado_en = Column(DateTime, default=ahora_local)

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
    # Precio de compra (costo). Se registra al crear el producto, no se
    # muestra en el listado y alimenta el cálculo de ganancias.
    precio_compra = Column(Float, nullable=False, default=0.0)
    stock = Column(Integer, nullable=False, default=0)
    categoria_id = Column(Integer, ForeignKey("categorias.id"), nullable=True)

    categoria = relationship("Categoria", back_populates="productos")


class Mesa(Base):
    """Mesa o puesto de barra.

    tipo:  "mesa"  -> mesa normal
           "barra" -> puesto de barra (varias cuentas para la misma barra)
    grupo: nombre compartido de la barra (ej: "Barra 1")
    """

    __tablename__ = "mesas"

    id = Column(Integer, primary_key=True, index=True)
    numero = Column(Integer, unique=True, nullable=False)
    capacidad = Column(Integer, nullable=False, default=4)
    estado = Column(String(20), default="disponible")  # disponible | ocupada | cerrada
    tipo = Column(String(20), default="mesa")  # mesa | barra
    grupo = Column(String(60), nullable=True)  # ej: "Barra 1"
    posicion = Column(Integer, default=1)

    pedidos = relationship("Pedido", back_populates="mesa")

    def etiqueta_historial(self) -> str:
        """Nombre visible para el historial: "Mesa N" o "Barra N"."""
        if (self.tipo or "mesa") == "barra":
            return self.grupo or f"Barra {self.numero // 100}"
        return f"Mesa {self.numero}"


class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, index=True)
    mesa_id = Column(Integer, ForeignKey("mesas.id"), nullable=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    fecha = Column(DateTime, default=ahora_local)
    total = Column(Float, default=0.0)
    estado = Column(String(20), default="abierto")  # abierto | cerrado | dividido
    forma_pago = Column(String(20), nullable=True)  # efectivo | tarjeta | transferencia
    fecha_cierre = Column(DateTime, nullable=True)
    # Numero de mesa conservado cuando la mesa se elimina (historial)
    mesa_numero_historico = Column(Integer, nullable=True)
    # Etiqueta conservada para el historial ("Mesa N" o "Barra N")
    mesa_etiqueta_historica = Column(String(60), nullable=True)

    mesa = relationship("Mesa", back_populates="pedidos")
    usuario = relationship("Usuario", back_populates="pedidos")
    items = relationship(
        "PedidoItem", back_populates="pedido", cascade="all, delete-orphan"
    )

    def guardar_origen(self, mesa: "Mesa") -> None:
        """Conserva el origen del pedido para el historial.

        Guarda el número de la mesa/plaza y su etiqueta visible
        ("Mesa 3" o "Barra 2"), de modo que el historial siga mostrando
        el origen aunque la mesa se elimine o se reutilice.
        """
        self.mesa_numero_historico = mesa.numero
        self.mesa_etiqueta_historica = mesa.etiqueta_historial()


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
    fecha = Column(DateTime, default=ahora_local)
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
    fecha_apertura = Column(DateTime, default=ahora_local)
    fecha_cierre = Column(DateTime, nullable=True)
    observaciones = Column(String(255), nullable=True)
    estado = Column(String(20), default="abierto")  # abierto | cerrado

    usuario = relationship("Usuario")


class MigracionSistema(Base):
    """Marcador de migraciones ya aplicadas a la base de datos."""

    __tablename__ = "migraciones_sistema"

    clave = Column(String(80), primary_key=True)
    aplicado_en = Column(DateTime, default=ahora_local)
