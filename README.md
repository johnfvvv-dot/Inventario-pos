# Inventario POS - Sistema de Inventario y Punto de Venta

Aplicación web multiplataforma para gestión de inventario y punto de venta para pequeños negocios.

## Arquitectura
- **Backend:** FastAPI (Python) - API REST
- **Frontend:** React + TypeScript
- **Base de datos:** SQLite (local) / PostgreSQL (nube)
- **Hosting:** Local en PC (sin costos de servidor), escalable a la nube

## Estructura del Proyecto
```
inventario-pos/
├── backend/       # Servidor FastAPI
├── frontend/      # Aplicación React
├── scripts/       # Scripts de instalación y ejecución
└── docs/          # Documentación y wireframes
```

## Instalación y Ejecución

### Prerrequisitos
- Python 3.11+ instalado
- Node.js 20+ instalado
- Git instalado

### Pasos para clonar y ejecutar

```bash
# 1. Clonar repositorio
git clone https://github.com/TU_USUARIO/inventario-pos.git
cd inventario-pos

# 2. Ejecutar script de instalación (opcional, o seguir pasos manuales)
# Windows: scripts\install.bat
# Linux/macOS: scripts/install.sh

# 3. Iniciar la aplicación
# Windows: scripts\start.bat
# Linux/macOS: scripts/start.sh
# O manualmente:
#   - Backend: cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000
#   - Frontend: cd frontend && npm start
```

### Acceso desde la red local
Una vez en ejecución, la aplicación estará disponible en:
- **Backend API:** http://localhost:8000
- **Documentación API:** http://localhost:8000/docs
- **Frontend:** http://localhost:3000
- **Desde otros dispositivos en la misma red WiFi:** Usa la IP de tu PC (ej. http://192.168.1.XX:8000)

## Versión y Ramas
- `main`: Rama estable con releases
- `dev`: Rama de desarrollo con funcionalidades en integración
- `feature/*`: Ramas para nuevas funcionalidades
- `bugfix/*`: Ramas para correcciones de errores

## Escalado a la Nube
Para escalar del hosting local a la nube:
1. Cambiar `SQLALCHEMY_DATABASE_URL` en `.env` a una URL de PostgreSQL
2. Desplegar backend en Render.com, Railway o Fly.io
3. Desplegar frontend en Vercel, Netlify o GitHub Pages
4. Migrar datos de SQLite a PostgreSQL usando `pg_dump`/`pg_restore`