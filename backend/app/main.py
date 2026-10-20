"""Punto de entrada principal de la aplicación FastAPI."""

from fastapi import FastAPI
from routes import pedidos, inventario, mesas, usuarios

app = FastAPI(
    title="Sistema Inventario y Punto de Venta",
    description="Aplicación multiplataforma para gestión de inventario y mesas",
    version="1.0.0"
)

# Routers
app.include_router(usuarios.router, prefix="/api/usuarios", tags=["usuarios"])
app.include_router(mesas.router, prefix="/api/mesas", tags=["mesas"])
app.include_router(inventario.router, prefix="/api/inventario", tags=["inventario"])
app.include_router(pedidos.router, prefix="/api/pedidos", tags=["pedidos"])

@app.get("/")
def read_root():
    return {"message": "Sistema Inventario y Punto de Venta API"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "1.0.0"}