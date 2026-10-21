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

# 6. Crear base de datos y datos iniciales
echo "Creando base de datos y datos iniciales..."
cd ../backend
source venv/bin/activate
python3 -c "from app.main import crear_datos_iniciales; crear_datos_iniciales(); print('✓ Base de datos lista')"

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