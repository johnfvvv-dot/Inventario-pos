"""Punto de entrada principal de la aplicación FastAPI."""

import hashlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, SessionLocal, engine
from app.models import Mesa, Producto, Usuario
from app.routes.inventario import router as inventario_router
from app.routes.mesas import router as mesas_router
from app.routes.pedidos import router as pedidos_router
from app.routes.usuarios import router as usuarios_router

app = FastAPI(
    title="Sistema Inventario y Punto de Venta",
    description="Aplicación multiplataforma para gestión de inventario, mesas y ventas",
    version="1.0.0",
)

# CORS: permite que el frontend React (localhost:3000 o IP de la red) consuma la API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(usuarios_router, prefix="/api/usuarios", tags=["usuarios"])
app.include_router(mesas_router, prefix="/api/mesas", tags=["mesas"])
app.include_router(inventario_router, prefix="/api/inventario", tags=["inventario"])
app.include_router(pedidos_router, prefix="/api/pedidos", tags=["pedidos"])


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def crear_datos_iniciales() -> None:
    """Crea tablas y siembra usuarios, productos y mesas de ejemplo."""
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if db.query(Usuario).count() == 0:
            db.add_all(
                [
                    Usuario(
                        nombre="Administrador",
                        rol="admin",
                        email="admin@localpos.com",
                        password_hash=hash_password("admin123"),
                    ),
                    Usuario(
                        nombre="Mesero Demo",
                        rol="mesero",
                        email="mesero@localpos.com",
                        password_hash=hash_password("mesero123"),
                    ),
                ]
            )

        if db.query(Producto).count() == 0:
            db.add_all(
                [
                    Producto(nombre="Hamburguesa", descripcion="Con papas", precio=9.00, stock=50),
                    Producto(nombre="Papas fritas", descripcion="Porción grande", precio=3.00, stock=50),
                    Producto(nombre="Refresco", descripcion="Botella 500 ml", precio=2.00, stock=100),
                    Producto(nombre="Café", descripcion="Taza caliente", precio=1.50, stock=100),
                ]
            )

        if db.query(Mesa).count() == 0:
            db.add_all([Mesa(numero=n, capacidad=4, estado="disponible") for n in range(1, 7)])

        db.commit()
    finally:
        db.close()


@app.on_event("startup")
def on_startup() -> None:
    crear_datos_iniciales()


@app.get("/")
def read_root():
    return {"message": "Sistema Inventario y Punto de Venta API", "docs": "/docs"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "1.0.0"}
