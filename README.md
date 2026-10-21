# Inventario POS

Sistema web multiplataforma de inventario y punto de venta para pequeños negocios.

- **Backend:** FastAPI (Python) + SQLAlchemy
- **Frontend:** React + TypeScript
- **Base de datos:** SQLite (local) / PostgreSQL (nube)
- **Hosting inicial:** local en la PC, sin costos de servidor

## Funcionalidades (v1)

### Módulos
- **Login** con roles `admin` y `mesero` (hash SHA-256), redirección según rol
- **Inventario:** alta de productos, ajuste de stock (+/−), eliminación, badges de stock (OK / bajo / agotado)
- **Mesas:** creación, estado (disponible/ocupada), apertura directa del pedido con mesa preseleccionada, importe pendiente en vivo y refresco automático cada 15 s
- **Pedidos:** selección de mesa, carrito con control de stock, total automático, cobro por pedido
- **Cuentas por mesa:** total en vivo, detalle por pedido y por división, cierre de cuenta con confirmación (Aceptar / Liberar mesa) sin liberar la mesa por defecto
- **División de cuenta:** reparto entre clientes con alias, cantidad exacta por producto, subtotales por cliente, resto de la cuenta conservado como bloque único y cobro individual de cada alias
- **Liberación controlada:** una mesa con cuentas pendientes no se puede liberar; se muestra el aviso *"La mesa aún tiene un pedido abierto."* con acceso directo al pedido abierto
- **Transferencia de cuenta:** mueve el pedido abierto y las divisiones pendientes a otra mesa (cambio de mesa de los clientes)
- **Reportes:** ventas totales, mesas atendidas, unidades vendidas, promedio por mesa, top de productos y estado del inventario

### Flujo de trabajo del mesero
```
Panel Mesas
 ├─ [Pedido]  → pedidos con la mesa ya seleccionada
 ├─ [Cuenta]  → ┌─ Dividir cuenta ────► alias con cantidades por producto
 │              ├─ Cerrar división ───► cobra 1 cliente, los demás siguen
 │              ├─ Transferir cuenta ─► mueve la cuenta a otra mesa
 │              └─ Cerrar cuenta ─────► [Aceptar | Liberar mesa]
 └─ [Liberar]  → si hay pendientes: aviso + "Ver el pedido abierto"
```

### API (17 endpoints)
| Módulo | Endpoints |
|---|---|
| Usuarios | `POST /login`, `POST /`, `GET /` |
| Mesas | `POST /`, `GET /`, `PUT /{id}/estado`, `POST /{id}/liberar` |
| Inventario | `POST /`, `GET /`, `PUT /{id}/stock`, `DELETE /{id}` |
| Pedidos | `POST /`, `GET /`, `GET /mesa/{id}`, `PUT /{id}/cerrar` |
| Cuentas | `GET /mesa/{id}`, `POST /mesa/{id}/cerrar`, `POST /mesa/{id}/transferir`, `POST /dividir`, `POST /division/{id}/pagar`, `POST /participante/{id}/pagar`, `GET /mesa/{id}/divisiones` |

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

**Repositorio:** https://github.com/johnfvvv-dot/Inventario-pos

### Historial de versiones
| Tag | Commit | Contenido |
|-----|--------|-----------|
| `v1.0.0` | `e8a5325` | Primera versión estable: inventario, mesas, pedidos, cuentas, división por alias, liberación controlada y transferencia de cuenta |

## Escalado a la nube

1. Crear una base PostgreSQL (Supabase, Neon, Railway…).
2. Definir la variable de entorno `DATABASE_URL=postgresql://...`.
3. Desplegar el backend en Render/Railway/Fly.io.
4. Desplegar el frontend en Vercel/Netlify apuntando `API_BASE` al backend público.
5. Migrar los datos de SQLite con un script de exportación/importación.
