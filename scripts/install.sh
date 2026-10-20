#!/bin/bash
# Script de instalación para Inventario POS
# Funciona en Linux y macOS (WSL en Windows también)

echo "=== Instalando Inventario POS ==="

# 1. Verificar Python
echo "Verificando Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 no encontrado. Instálalo primero."
    exit 1
fi
PYTHON_VER=$(python3 --version | cut -d' ' -f2)
echo "✓ Python $PYTHON_VER encontrado"

# 2. Verificar Node.js
echo "Verificando Node.js..."
if ! command -v node &> /dev/null; then
    echo "❌ Node.js no encontrado. Instálalo primero."
    exit 1
fi
NODE_VER=$(node --version)
echo "✓ Node.js $NODE_VER encontrado"

# 3. Crear entorno virtual Python
echo "Creando entorno virtual Python..."
cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Entorno virtual creado"
else
    echo "✓ Entorno virtual ya existe"
fi

# Activar entorno virtual
source venv/bin/activate

# 4. Instalar dependencias Python
echo "Instalando dependencias Python..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✓ Dependencias Python instaladas"

# 5. Instalar dependencias Node.js
echo "Instalando dependencias Node.js..."
cd ../frontend
npm install
echo "✓ Dependencias Node.js instaladas"

# 6. Configurar base de datos
echo "Configurando base de datos..."
cd ../backend
source venv/bin/activate
alembic upgrade head

# 7. Crear usuario admin por defecto
echo "Creando usuario administrador por defecto..."
python3 - << PYTHON_SCRIPT
from app.main import app
from app.database import get_db, engine, Base
from app.models import Usuario
from sqlalchemy.orm import Session

# Crear tablas
Base.metadata.create_all(bind=engine)

# Obtener sesión
db_gen = get_db()
db = next(db_gen)

# Verificar si ya existe un usuario admin
admin_existente = db.query(Usuario).filter(Usuario.rol == "admin").first()
if not admin_existente:
    admin = Usuario(
        nombre="Administrador",
        rol="admin",
        email="admin@localpos.com"
    )
    db.add(admin)
    db.commit()
    print("✓ Usuario admin creado: admin@localpos.com")
else:
    print("✓ Usuario admin ya existe")

db.close()
PYTHON_SCRIPT

echo ""
echo "=== Instalación completada ==="
echo ""
echo "Para iniciar la aplicación:"
echo "  1. Ejecutar: scripts/start.sh"
echo "  2. O iniciar manualmente:"
echo "     - Backend: cd backend && source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo "     - Frontend: cd frontend && npm start"
echo ""
echo "Accede a:"
echo "  - API:       http://localhost:8000"
echo "  - Docs API:  http://localhost:8000/docs"
echo "  - Frontend:  http://localhost:3000"