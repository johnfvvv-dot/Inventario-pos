# Inventario POS

Sistema web multiplataforma de inventario y punto de venta para pequeños negocios.

- **Backend:** FastAPI (Python) + SQLAlchemy
- **Frontend:** React + TypeScript
- **Base de datos:** SQLite (local) / PostgreSQL (nube)
- **Hosting inicial:** local en la PC, sin costos de servidor

## Funcionalidades (v1)

- Login con roles **admin** y **mesero**
- Inventario: alta, ajuste de stock y eliminación de productos
- Mesas: creación, estado (disponible/ocupada) y acceso a pedidos
- Pedidos: selección de mesa, carrito, descuento automático de stock y cierre/cobro
- Reportes: ventas totales, mesas atendidas, unidades vendidas, top de productos y estado del inventario

## Requisitos

- Python 3.10+
- Node.js 18+ (incluye npm)
- Git (opcional)

## Instalación y ejecución (Windows PowerShell)

### 1. Backend

```powershell
cd C:\Users\XR-18\Desktop\Python\inventario-pos\backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. Frontend (en otra ventana)

```powershell
cd C:\Users\XR-18\Desktop\Python\inventario-pos\frontend
npm install
npm start
```

> Si ya existía una instalación previa, conviene limpiar:
> `Remove-Item -Recurse -Force node_modules, package-lock.json` y volver a ejecutar `npm install`.

### 3. Acceso

- Frontend: http://localhost:3000
- API: http://localhost:8000
- Documentación interactiva: http://localhost:8000/docs

## Usuarios de prueba

| Rol | Email | Contraseña |
|-----|-------|------------|
| Administrador | `admin@localpos.com` | `admin123` |
| Mesero | `mesero@localpos.com` | `mesero123` |

La base de datos SQLite (`backend/inventario.db`) se crea automáticamente con productos y mesas de ejemplo la primera vez que arranca el backend.

## Acceso desde celular o tablet (misma WiFi)

1. Obtén la IP de la PC con `ipconfig` (Windows).
2. Inicia el backend con `--host 0.0.0.0`.
3. Abre en el dispositivo: `http://IP_DE_LA_PC:3000`.
4. Si el frontend no conecta, cambia `API_BASE` en `frontend/src/services/api.ts` por `http://IP_DE_LA_PC:8000/api`.
5. Permite los puertos 3000 y 8000 en el firewall de Windows.

## Estructura

```
inventario-pos/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI, CORS, datos iniciales
│   │   ├── database.py      # SQLite/PostgreSQL
│   │   ├── models.py        # Usuario, Producto, Mesa, Pedido, PedidoItem
│   │   ├── schemas.py       # Validaciones Pydantic
│   │   └── routes/          # usuarios, mesas, inventario, pedidos
│   └── requirements.txt
├── frontend/
│   ├── public/index.html
│   └── src/
│       ├── pages/           # Login, Inventario, Mesas, Pedidos, Reportes
│       ├── layouts/         # Admin y Mesero
│       └── services/api.ts
├── scripts/                 # install/start para Linux y Windows
└── docs/
```

## Git

- `main`: versiones estables
- `dev`: integración
- `feature/*`: nuevas funcionalidades
- `bugfix/*`: correcciones

```bash
git checkout -b feature/nueva-funcionalidad dev
# trabajar...
git add .
git commit -m "Descripción del cambio"
git push -u origin feature/nueva-funcionalidad
```

## Escalado a la nube

1. Crear una base PostgreSQL (Supabase, Neon, Railway…).
2. Definir la variable de entorno `DATABASE_URL=postgresql://...`.
3. Desplegar el backend en Render/Railway/Fly.io.
4. Desplegar el frontend en Vercel/Netlify apuntando `API_BASE` al backend público.
5. Migrar los datos de SQLite con un script de exportación/importación.
