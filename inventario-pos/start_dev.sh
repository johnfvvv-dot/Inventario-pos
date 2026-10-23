#!/bin/bash
# Script de desarrollo para Inventario POS
# Este script intenta configurar y levantar la aplicación

echo "=== Inventario POS - Script de Desarrollo ==="
echo ""

# Verificar Python
echo "Verificando Python..."
PYTHON_CMD="python3"
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
echo "   Python $PYTHON_VERSION encontrado"

# Verificar si pip está disponible
echo "Verificando pip..."
if command -v pip3 &>/dev/null; then
    echo "   pip3 disponible"
    PIP="pip3"
elif $PYTHON_CMD -m pip --version &>/dev/null 2>&1; then
    echo "   Usando python3 -m pip"
    PIP="$PYTHON_CMD -m pip"
else
    echo "   ⚠ pip no disponible automáticamente"
    echo "   Para instalar: sudo apt-get install python3-pip"
    echo "   O descargar e instalar get-pip.py manualmente"
    echo ""
    echo "Opción alternativa: Usar venv manualmente"
    echo "   1. python3 -m venv venv"
    echo "   2. source venv/bin/activate"
    echo "   3. pip install -r requirements.txt"
    exit 1
fi

# Crear entorno virtual si no existe
echo ""
echo "Configurando entorno virtual..."
if [ ! -d "backend/venv" ]; then
    echo "   Creando venv..."
    $PYTHON_CMD -m venv venv
    if [ $? -ne 0 ]; then
        echo "   ❌ Error creando venv"
        exit 1
    fi
    echo "   ✓ Entorno virtual creado"
else
    echo "   ✓ Entorno virtual ya existe"
fi

# Activar entorno virtual
echo "   Activando entorno virtual..."
source venv/bin/activate

# Instalar dependencias Python
echo "   Instalando dependencias Python..."
$PIP install --upgrade pip 2>&1 | tail -1
$PIP install -r requirements.txt 2>&1 | tail -3

echo ""
echo "=== Dependencias Python instaladas ==="
echo ""

# Levantar backend
echo "=== Levantando Backend FastAPI ==="
cd backend
echo "   Ejecutando: uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo "   La API estará disponible en: http://localhost:8000"
echo "   Documentación API: http://localhost:8000/docs"
echo ""

uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Pequeña espera para que el backend inicie
sleep 2

# Levantar frontend
echo ""
echo "=== Levantando Frontend React ==="
cd ../frontend
echo "   Ejecutando: npm start"
echo "   La aplicación estará disponible en: http://localhost:3000"
echo ""

npm start &
FRONTEND_PID=$!

echo ""
echo "============================================"
echo "         SISTEMA EN EJECUCIÓN"
echo "============================================"
echo ""
echo "Backend (API):     http://localhost:8000"
echo "Docs API:          http://localhost:8000/docs"
echo "Frontend:          http://localhost:3000"
echo ""
echo "Para acceder desde otros dispositivos en la red WiFi:"
echo "  Usa la IP de esta PC (ej: http://192.168.1.XX:8000)"
echo ""
echo "Para detener: Presiona Ctrl+C"
echo ""

# Esperar a que los procesos terminen
wait