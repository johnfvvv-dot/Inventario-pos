# Inventario POS

Sistema web multiplataforma de inventario y punto de venta para pequeños negocios.

- **Backend:** FastAPI (Python) + SQLAlchemy
- **Frontend:** React + TypeScript
- **Base de datos:** SQLite (local) / PostgreSQL (nube)
- **Hosting inicial:** local en la PC, sin costos de servidor

## Funcionalidades (v1.1)

### Módulos
- **Login** con roles `admin` y `mesero` (hash SHA-256), redirección según rol
- **Inventario:** alta, edición, ajuste de stock (+/−), eliminación, **búsqueda**, **paginación** y filtro por categoría
- **Categorías:** CRUD de categorías (Bebidas, Comidas...) con filtro rápido en el POS
- **Mesas:** creación, estado (disponible/ocupada), apertura directa del pedido con mesa preseleccionada, importe pendiente en vivo y refresco automático cada 15 s
- **Pedidos:** carrito con control de stock, total automático, **edición de pedidos abiertos** (+/− por línea) y cobro con forma de pago
- **Cuentas por mesa:** total en vivo, detalle por pedido y por división, cierre con confirmación (Aceptar / Liberar mesa) sin liberar la mesa por defecto
- **División de cuenta:** reparto entre clientes con alias, cantidad exacta por producto, subtotales por cliente, resto de la cuenta conservado como bloque único y cobro individual de cada alias
- **Liberación controlada:** una mesa con cuentas pendientes no se puede liberar; se muestra el aviso *"La mesa aún tiene un pedido abierto."* con acceso directo al pedido abierto
- **Transferencia de cuenta:** mueve el pedido abierto y las divisiones pendientes a otra mesa (cambio de mesa de los clientes)
- **Corte de caja:** apertura/cierre de turno con totales por **forma de pago** (efectivo / tarjeta / transferencia), observaciones e historial de turnos
- **Reportes:** gráficos (línea de ventas por día, barra de top de productos, dona de formas de pago) + KPIs + **exportación CSV**
- **Historial de ventas:** filtros por rango de fechas, mesa, producto y forma de pago, con paginación y exportación CSV
- **PWA instalable:** "Añadir a pantalla de inicio" en Android (manifest + service worker)

### Flujo de trabajo del mesero
```
Panel Mesas
 ├─ [Pedido]  → pedidos con la mesa ya seleccionada
 │              └─ +/− por línea para corregir cantidades
 ├─ [Cuenta]  → ┌─ Dividir cuenta ────► alias con cantidades por producto
 │              ├─ Cerrar división ───► cobra 1 cliente, los demás siguen
 │              ├─ Transferir cuenta ─► mueve la cuenta a otra mesa
 │              └─ Cerrar cuenta ─────► [Aceptar | Liberar mesa] + forma de pago
 └─ [Liberar]  → si hay pendientes: aviso + "Ver el pedido abierto"
```

### API (31 endpoints)
| Módulo | Endpoints |
|---|---|
| Usuarios | `POST /login`, `POST /`, `GET /` |
| Mesas | `POST /`, `GET /`, `PUT /{id}/estado`, `POST /{id}/liberar` |
| Inventario | `GET /` (búsqueda+paginación), `POST /`, `PUT /{id}`, `PUT /{id}/stock`, `DELETE /{id}` |
| Categorías | `GET /`, `POST /`, `PUT /{id}`, `DELETE /{id}` |
| Pedidos | `POST /`, `GET /`, `GET /mesa/{id}`, `PUT /{id}/cerrar`, `PUT /{id}/items/{item_id}` |
| Cuentas | `GET /mesa/{id}`, `POST /mesa/{id}/cerrar`, `POST /mesa/{id}/transferir`, `POST /dividir`, `POST /division/{id}/pagar`, `POST /participante/{id}/pagar`, `GET /mesa/{id}/divisiones` |
| Caja | `GET /turno-actual`, `POST /abrir`, `POST /cerrar`, `GET /turnos`, `GET /resumen`, `GET /ventas-por-dia`, `GET /historial` |
| Config | `GET /api/config` (IP, puerto, modo, versión) |

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

## Ejecutable de escritorio (Windows)

`InventarioPOS.exe` es un **archivo único** que incluye el backend (FastAPI) y el frontend (React compilado). Al ejecutarlo:

- Levanta el servidor en `http://localhost:8000` y **abre el navegador solo**
- Muestra en consola la IP local para conectar el celular: `http://192.168.1.6:8000`
- Guarda los datos en `%LOCALAPPDATA%\InventarioPOS\inventario.db` (portable)
- Se puede copiar a otra PC y funciona sin instalar Python ni Node.js

```powershell
# Construir el .exe (recompila el frontend y empaqueta)
scripts\build_exe.bat

# Crear acceso directo en el escritorio
scripts\crear_acceso_directo.bat
```

## Aplicación Android (APK)

```powershell
# Compilar el APK (requiere Android Studio instalado)
scripts\build_apk.bat

# Instalar en el celular conectado por USB
adb install -r frontend\android\app\build\outputs\apk\debug\app-debug.apk
```

- El APK se conecta al servidor de la PC (`http://<IP_PC>:8000` en `frontend/capacitor.config.json`)
- **En el Xiaomi/MIUI** hay que activar: *Ajustes → Ajustes adicionales → Opciones de desarrollador → "Instalar por USB"* y *"Depuración USB (ajustes de seguridad)"*
- La misma APK sirve en tablet (el diseño es responsivo)
- Para cambiar la IP de destino, edita `frontend/capacitor.config.json` y vuelve a compilar

## PWA (instalar desde el navegador)

En el celular, abre `http://<IP_PC>:8000` en Chrome → menú **⋮** → **"Añadir a pantalla de inicio"**. Queda como una app instalada con icono propio.

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
