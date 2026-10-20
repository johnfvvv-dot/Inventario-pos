"""Conexión a la base de datos SQLite (local) o PostgreSQL (nube)."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Configuración - SQLite local por defecto, PostgreSQL al cambiar la URL
SQLALCHEMY_DATABASE_URL = "sqlite:///./inventario.db"

# Para PostgreSQL en la nube:
# SQLALCHEMY_DATABASE_URL = "postgresql://usuario:password@localhost/inventario"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}  # Solo necesario para SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependencia para obtener sesión de BD en cada petición."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()