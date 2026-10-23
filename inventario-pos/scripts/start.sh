#!/bin/bash
# Script para iniciar Inventario POS
# Levanta tanto el backend como el frontend en paralelo

echo "=== Iniciando Inventario POS ==="

# Verificar que el entorno virtual existe
if [ ! -d "backend/venv" ]; then
    echo "⚠ Entorno virtual no encontrado. Ejecuta primero scripts/install.sh"
    exit 1
fi

# Colores para output
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Función para iniciar backend
start_backend() {
    echo -e "${GREEN}Iniciando Backend FastAPI...${NC}"
    cd backend
    source venv/bin/activate
    uvicorn app.main:app --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    echo "✓ Backend corriendo en http://localhost:8000 (PID: $BACKEND_PID)"
}

# Función para iniciar frontend
start_frontend() {
    echo -e "${GREEN}Iniciando Frontend React...${NC}"
    cd frontend
    npm start &
    FRONTEND_PID=$!
    echo "✓ Frontend corriendo en http://localhost:3000 (PID: $FRONTEND_PID)"
}

# Iniciar ambos
start_backend
start_frontend

echo ""
echo "========================================="
echo "         SISTEMA EN EJECUCIÓN"
echo "========================================="
echo ""
echo "Backend (API):     http://localhost:8000"
echo "Docs API:          http://localhost:8000/docs"
echo "Frontend:          http://localhost:3000"
echo ""
echo "Para detener: Presiona Ctrl+C o cierra esta terminal"
echo ""

# Esperar a que ambos procesos terminen
wait