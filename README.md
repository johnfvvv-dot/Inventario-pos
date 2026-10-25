# Inventario POS

Sistema web y de escritorio de inventario y punto de venta para pequeños
negocios (bares, restaurantes y cafeterías). Integra inventario, mesas, barras,
pedidos, cuentas, caja, reportes e historial en una sola aplicación.

**Versión actual:** 1.1.0

- **Backend:** FastAPI (Python) + SQLAlchemy
- **Frontend:** React 18 + TypeScript
- **Base de datos:** SQLite (local) / PostgreSQL (nube)
- **Ejecución inicial:** local en la PC, sin costos de servidor

## Funcionalidades (v1.1.0)

### Módulos

- **Login** con roles `admin` y `bartender` (clave con hash SHA-256) y
  redirección según el rol.
- **Inventario:** alta, edición, eliminación con confirmación, búsqueda,
  paginación y filtro por categoría. La columna **Stock es de solo lectura**;
  los ingresos se registran en el campo **"Ingreso de stock"** con un botón
  verde **"Agregar"** que **suma** la cantidad al stock existente. Se conservan
  los botones **"−"** y **"+"** para ajustes de una unidad.
- **Categorías:** CRUD de categorías (Bebidas, Comidas, etc.) con filtro rápido
  en el POS.
- **Mesas:** creación, eliminación, estado (disponible/ocupada), apertura
  directa del pedido con la mesa preseleccionada, importe pendiente en vivo y
  refresco automático cada 15 s.
- **Barras:** creación de **Barra N** con número y capacidad; se muestran como
  una tarjeta más del panel y cada plaza guarda su propia cuenta. En el
  selector de pedidos y en el historial aparecen como **"Barra N"**.
- **Pedidos:** carrito con control de stock, total automático, edición de
  pedidos abiertos y cobro con forma de pago. La lista de productos muestra
  **máximo 8 filas visibles con scroll**; cada producto tiene un campo numérico
  + botón verde **"Agregar"** para cantidades manuales, además del botón **"+"**
  incremental.
- **Cuentas por mesa y barra:** total en vivo, detalle por pedido y por
  división, cierre con confirmación (Aceptar / Liberar mesa o barra) sin liberar
  la mesa/barra por defecto. Las barras se cierran y liberan con el mismo flujo
  que las mesas.
- **División de cuenta:** reparto entre clientes con alias, cantidad exacta por
  producto, subtotales por cliente, resto de la cuenta conservado como bloque
  único y cobro individual de cada alias. Funciona en mesas y en la cuenta
  agregada de una barra.
- **Liberación controlada:** una mesa o barra con cuentas pendientes no se puede
  liberar; se muestra el aviso correspondiente con acceso directo al pedido
  abierto.
- **Transferencia de cuenta:** mueve el pedido abierto y las divisiones
  pendientes a otra mesa o plaza libre. Una barra ocupada no puede ser destino
  de transferencia.
- **Corte de caja:** apertura/cierre de turno con totales por forma de pago
  (efectivo / tarjeta / transferencia), observaciones e historial de turnos.
- **Reportes:** gráficos (ventas por día, top de productos, formas de pago),
  KPIs y exportación CSV.
- **Historial de ventas:** filtros por rango de fechas, mesa/barra, producto y
  forma de pago, con paginación y exportación CSV. Las etiquetas históricas
  conservan "Mesa N" o "Barra N" aunque la mesa/barra se elimine.
- **PWA instalable:** "Añadir a pantalla de inicio" en Android (manifest +
  service worker).

### Formato de precios

Todos los precios de la aplicación (inventario, pedidos, cuentas, divisiones,
reportes, historial y caja) se muestran con **separador de miles** y **sin
decimales**:

- `$3800.00` → `$3.800`
- `$100000.00` → `$100.000`
- `$1234567.00` → `$1.234.567`

### Flujo de mesas y barras

```
Panel Mesas
 ├─ [Crear mesa]      → mesa numerada (Mesa 1, Mesa 2, ...)
 ├─ [Crear barra]     → Barra N con capacidad C (C plazas)
 │                      la barra se muestra como una tarjeta más, igual que
 │                      una mesa, y cada plaza guarda su propia cuenta
 ├─ [Pedido]  → pedidos con la mesa/barra ya seleccionada
 │              └─ cantidad manual o +/− por producto
 ├─ [Cuenta]  → ┌─ Dividir cuenta ────► alias con cantidades por producto
 │              ├─ Cerrar división ───► cobra 1 cliente, los demás siguen
 │              ├─ Transferir cuenta ─► mueve la cuenta a otra mesa/plaza libre
 │              └─ Cerrar cuenta ─────► [Aceptar | Liberar mesa/barra] + pago
 ├─ [Liberar]  → si hay pendientes: aviso + "Ver el pedido abierto"
 └─ [×]         → eliminar mesa o barra completa (solo sin cuentas pendientes)
```

## API principal

Todos los endpoints usan el prefijo `/api`. La documentación interactiva está
disponible en `http://localhost:8000/docs`.

| Módulo | Endpoints principales |
|---|---|
| Usuarios | `POST /usuarios/login`, `GET /usuarios/`, `POST /usuarios/`, `PUT /usuarios/{id}`, `PUT /usuarios/{id}/clave`, `DELETE /usuarios/{id}` |
| Mesas y barras | `GET /mesas/`, `POST /mesas/`, `POST /mesas/barra`, `POST /mesas/{id}/ocupar`, `PUT /mesas/{id}/estado`, `POST /mesas/{id}/liberar`, `DELETE /mesas/{id}` |
| Inventario | `GET /inventario/` (búsqueda + paginación), `POST /inventario/`, `PUT /inventario/{id}`, `PUT /inventario/{id}/stock`, `DELETE /inventario/{id}` |
| Categorías | `GET /categorias/`, `POST /categorias/`, `PUT /categorias/{id}`, `DELETE /categorias/{id}` |
| Pedidos | `GET /pedidos/`, `POST /pedidos/`, `GET /pedidos/mesa/{id}`, `PUT /pedidos/{id}/items/{item_id}`, `PUT /pedidos/{id}/cerrar` |
| Cuentas | `GET /cuentas/mesa/{id}`, `GET /cuentas/barra/{numero}`, `POST /cuentas/mesa/{id}/cerrar`, `POST /cuentas/barra/{numero}/cerrar`, `POST /cuentas/mesa/{id}/transferir`, `POST /cuentas/dividir`, `POST /cuentas/participante/{id}/pagar`, `POST /cuentas/division/{id}/pagar`, `GET /cuentas/mesa/{id}/divisiones` |
| Caja | `GET /caja/turno-actual`, `POST /caja/abrir`, `POST /caja/cerrar`, `GET /caja/turnos`, `GET /caja/resumen`, `GET /caja/ventas-por-dia`, `GET /caja/historial` |
| Configuración | `GET /config` (bajo `/api`) y `GET /health` (sin prefijo) |

## Requisitos previos

- **Python 3.10 o superior**
- **Node.js 18 o superior** (incluye `npm`); también se puede usar `yarn`
- **Git** (opcional, para clonar el repositorio)
- Para el APK: Android Studio y SDK de Android (opcional)

## Instalación y ejecución

### 1. Backend

**Windows (PowerShell):**

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Linux / macOS:**

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

> Si PowerShell bloquea la activación del entorno virtual, ejecuta
> `Set-ExecutionPolicy -Scope Process Bypass` o usa `cmd` con
> `venv\Scripts\activate.bat`.

### 2. Frontend (en otra terminal)

```bash
cd frontend
npm install
npm start
```

Con yarn:

```bash
cd frontend
yarn install
yarn start
```

> Si ya existía una instalación previa y hay problemas, elimina
> `node_modules` y `package-lock.json`, y vuelve a ejecutar `npm install`.

### 3. Acceso

- Frontend: http://localhost:3000
- API: http://localhost:8000
- Documentación interactiva: http://localhost:8000/docs
- Estado del servicio: http://localhost:8000/health

### 4. Base de datos

- En desarrollo se crea automáticamente en `backend/data/inventario.db` con
  usuarios, productos y mesas de ejemplo la primera vez que arranca el backend.
- El ejecutable de Windows guarda los datos en
  `%LOCALAPPDATA%\InventarioPOS\inventario.db`.
- Para usar PostgreSQL, define la variable de entorno `DATABASE_URL` antes de
  iniciar el backend.

## Ejemplos de uso básico

### Abrir el inventario y agregar stock

1. Inicia sesión con el usuario administrador.
2. Entra a **Inventario**.
3. La columna **Stock** solo muestra la cantidad actual.
4. Escribe, por ejemplo, `10` en **"Ingreso de stock"** y pulsa el botón verde
   **"Agregar"**. Si el stock era 50, quedará en 60.
5. Usa **"−"** o **"+"** para ajustar una unidad; el stock no se edita
   directamente en la columna.

### Crear un pedido

1. Entra a **Mesas**.
2. Elige una mesa o una barra (por ejemplo, **Barra 1**) y pulsa **Pedido**.
3. Agrega productos con el botón **"+"** o escribe una cantidad y pulsa
   **"Agregar"**. La lista muestra 8 productos visibles y permite desplazarse.
4. Revisa el carrito y registra el pedido.

### Cobrar y cerrar una cuenta

1. En **Mesas**, pulsa **Cuenta** sobre la mesa o barra.
2. Desde allí puedes **Dividir cuenta**, **Transferir cuenta** o **Cerrar
   cuenta**.
3. Al cerrar, elige la forma de pago y si deseas **Liberar mesa/barra**.

### Generar un reporte

1. Entra a **Reportes**.
2. Selecciona el rango de fechas.
3. Consulta los KPIs y gráficos.
4. Usa **Exportar CSV** para descargar la información. El **Historial** permite
   filtrar por mesa/barra, producto y forma de pago.

## Usuarios y roles

No se usan correos: el acceso es por **alias** + **clave**.

### Usuario inicial

| Alias | Clave | Rol |
|---|---|---|
| `Admin` | `1234` | Administrador |

> Cambia la clave desde **Usuarios → Cambiar clave** en cuanto arranques en
> producción.

### Permisos

| Módulo | Administrador | Bartender |
|---|---|---|
| Inventario | Crear, editar, eliminar, ingresar stock | **Solo lectura** |
| Mesas / Pedidos / Cuenta | ✅ | ✅ |
| Corte de caja | ✅ | ✅ |
| Reportes / Historial | ✅ | ❌ |
| Usuarios (crear, roles, claves) | ✅ | ❌ |

### Menú de Usuarios (solo Administrador)

`/admin/usuarios` permite crear usuarios con alias y rol, cambiar rol,
activar/desactivar, cambiar clave y eliminar. Todos los usuarios nuevos nacen
con la **clave inicial `1234`** (cambiable después).

## Acceso desde celular o tablet (misma WiFi)

1. Obtén la IP de la PC con `ipconfig` (Windows).
2. Inicia el backend con `--host 0.0.0.0`.
3. Abre en el dispositivo: `http://IP_DE_LA_PC:3000` (desarrollo) o
   `http://IP_DE_LA_PC:8000` (build/ejecutable).
4. El frontend detecta automáticamente la IP del host; si necesitas fijarla,
   define `REACT_APP_API_URL=http://IP_DE_LA_PC:8000/api` antes de compilar.
5. Permite los puertos 3000 y 8000 en el firewall de Windows.

## Solución de problemas

### "Method Not Allowed" al liberar una barra

El botón **Liberar barra** envía `POST /api/cuentas/barra/{n}/cerrar`, una ruta
que existe en el backend actual. Si aparece **"Method Not Allowed"**, el
frontend está actualizado pero el backend que está corriendo es una versión
anterior (por ejemplo, un `InventarioPOS.exe` viejo). La petición no coincide
con ninguna ruta POST y termina en el fallback del frontend.

Para corregirlo:

1. Cierra la instancia anterior del backend/ejecutable.
2. Compila el frontend con `npm run build` dentro de `frontend/`.
3. Regenera el ejecutable con `pyinstaller build_exe.spec --noconfirm`.
4. Abre la aplicación nueva y recarga el navegador con `Ctrl + F5`.

El comportamiento esperado es:

- **Aceptar:** cobra la cuenta y la barra queda **ocupada**.
- **Liberar barra:** cobra la cuenta y deja **todas las plazas disponibles**.

## Estructura del proyecto

```
inventario-pos/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI, CORS, SPA, migraciones y datos iniciales
│   │   ├── database.py      # SQLite / PostgreSQL
│   │   ├── models.py        # Usuario, Producto, Mesa, Pedido, Cuenta, Caja...
│   │   ├── schemas.py       # Validaciones Pydantic
│   │   └── routes/          # usuarios, mesas, inventario, pedidos, cuentas,
│   │                        # caja y categorías
│   ├── data/                # Base SQLite generada (ignorada por git)
│   ├── requirements.txt
│   └── run.py               # Entrada del ejecutable
├── frontend/
│   ├── public/              # index.html, manifest, service worker, iconos
│   ├── src/
│   │   ├── pages/           # Login, Inventario, Mesas, Pedidos, Caja,
│   │   │                    # Reportes, Historial, Usuarios
│   │   ├── components/      # Modales de cuenta, división, cobro, etc.
│   │   ├── layouts/         # Admin y Bartender
│   │   └── services/api.ts  # Cliente HTTP
│   ├── android/             # Proyecto Capacitor
│   └── package.json
├── scripts/                 # install/start/build para Linux y Windows
├── docs/                    # Documentación adicional (reservada)
├── build_exe.spec           # Configuración de PyInstaller
├── start_dev.sh             # Script de desarrollo Linux/macOS
├── requirements.txt
├── CONTEXT.md
├── README.md
└── README.txt
```

## Ejecutable de escritorio (Windows)

`InventarioPOS.exe` es un archivo único que incluye el backend (FastAPI) y el
frontend (React compilado). Al ejecutarlo:

- Levanta el servidor en `http://localhost:8000` y abre el navegador.
- Muestra en consola la IP local para conectar el celular.
- Guarda los datos en `%LOCALAPPDATA%\InventarioPOS\inventario.db`.
- Se puede copiar a otra PC y funciona sin instalar Python ni Node.js.

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

- El APK se conecta al servidor de la PC indicado en
  `frontend/capacitor.config.json`.
- En Xiaomi/MIUI hay que activar *Ajustes → Ajustes adicionales → Opciones de
  desarrollador → "Instalar por USB"* y *"Depuración USB (ajustes de
  seguridad)"*.
- La misma APK sirve en tablet (el diseño es responsivo).
- Para cambiar la IP de destino, edita `frontend/capacitor.config.json` y vuelve
  a compilar.

## PWA (instalar desde el navegador)

En el celular, abre `http://<IP_PC>:8000` en Chrome → menú **⋮** → **"Añadir a
pantalla de inicio"**. Queda como una app instalada con icono propio.

## Pendientes por corregir

1. **Recompilar `dist/InventarioPOS.exe`**: el binario actual es anterior a los
   últimos ajustes de barras, inventario y pedidos. Regenerar también el APK.
2. **Ingreso de stock atómico:** el frontend envía `stock_actual + cantidad` a
   `PUT /api/inventario/{id}/stock`; conviene un endpoint de incremento en el
   backend para evitar condiciones de carrera.
3. **Instalador de Windows:** `scripts/start.bat` menciona
   `scripts/install.bat`, pero ese archivo no existe; crearlo o corregir el
   mensaje.
4. **`start_dev.sh`:** unificar la ruta del entorno virtual (hoy crea/activa
   `venv` en la raíz pero espera `backend/venv`).
5. **Pruebas automatizadas:** agregar pruebas de backend/frontend y validar la
   migración de etiquetas históricas en una base antigua.
6. **Nota de desarrollo:** si `npm run build` reporta un error de sintaxis
   inexistente en `HistorialPage.tsx`, borrar `frontend/node_modules/.cache` y
   reconstruir.

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

| Versión | Commit | Contenido |
|---|---|---|
| `v1.0.0` | `e8a5325` | Primera versión estable: inventario, mesas, pedidos, cuentas, división por alias, liberación controlada y transferencia de cuenta |
| `v1.1.0` (actual) | — | Mejoras de barras, ingreso de stock, cantidades manuales en pedidos y totales con formato |

## Escalado a la nube

1. Crear una base PostgreSQL (Supabase, Neon, Railway, etc.).
2. Definir la variable de entorno `DATABASE_URL=postgresql://...`.
3. Desplegar el backend en Render/Railway/Fly.io.
4. Desplegar el frontend en Vercel/Netlify apuntando `REACT_APP_API_URL` al
   backend público.
5. Migrar los datos de SQLite con un script de exportación/importación.
