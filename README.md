# Inventario POS

Sistema web y de escritorio de inventario y punto de venta para pequeños
negocios (bares, restaurantes y cafeterías). Integra inventario, mesas, barras,
pedidos, cuentas, caja, reportes e historial en una sola aplicación.

**Versión actual:** 1.2.2

- **Backend:** FastAPI (Python) + SQLAlchemy
- **Frontend:** React 18 + TypeScript
- **Base de datos:** Neon PostgreSQL (modo híbrido) / SQLite (respaldo local)
- **Ejecución:** `.exe` local + Render Free como respaldo + Cloudflare Pages

## Modo híbrido (v1.2.2)

El negocio opera con un único `InventarioPOS.exe` en el PC del mostrador y el
frontend siempre publicado en Cloudflare Pages:

- El `.exe` levanta FastAPI en `0.0.0.0:8000` y conecta directamente con
  **Neon** (la misma base que Render).
- Al arrancar abre **Chrome o Edge en una ventana nueva con una sola pestaña**
  en la URL fija
  `https://inventario-pos-bfw.pages.dev/admin/usuarios`. Si no encuentra esos
  navegadores, usa el navegador predeterminado del sistema.
- Mientras la ventana del `.exe` esté abierta, el backend local sigue activo.
  No se instala como servicio de Windows: si se cierra la consola, el backend
  se detiene y el frontend pasa a Render.
- El login solo muestra **`Inventario POS v1.2.2`**. No hay botón de conexión ni
  textos sobre el servidor activo; la detección es transparente.

### Lógica de detección

Al cargar la página (la primera llamada, normalmente el login) el frontend
prueba los candidatos locales **en paralelo** y respeta este orden. La elección
se conserva durante esa carga; al recargar se vuelve a detectar.

| Orden | Candidato | Uso |
|---|---|---|
| 1 | `http://localhost:8000/api` | PC del negocio (mismo equipo) |
| 2 | `http://127.0.0.1:8000/api` | Alternativa si `localhost` falla |
| 3 | `http://<IP_LAN>:8000/api` | IP del PC grabada al compilar Pages |
| 4 | `https://inventario-pos-api-pqju.onrender.com/api` | Respaldo en la nube |

1. Se consulta `GET /health` en cada candidato local con un tiempo máximo de
   3,5 s. Gana el primero que responda `status: healthy`.
2. Si ninguno responde, se usa Render automáticamente. El login y las
   operaciones siguen funcionando, con el arranque en frío de Render (30–60 s).
3. Si el backend local se cae a mitad de una sesión, solo se reintentan
   automáticamente operaciones seguras (`GET`, `HEAD`, login). Un `POST` de
   venta o cobro **no** se repite para evitar duplicados.
4. `REACT_APP_API_URL` se ignora por seguridad. La URL de Render se valida al
   compilar y se descartan valores HTTP, `localhost`, IP privadas o `ngrok`.

### Acceso desde el PC

El `.exe` abre Pages en Chrome. Como esa página es HTTPS, para consultar
`http://localhost:8000` Chrome 142+ puede pedir el permiso **Local Network
Access**. Si se concede, la sesión usa el backend local; si se deniega o el
backend no está activo, la sesión usa Render sin mostrar mensajes adicionales.

### Acceso desde celular o tablet en la misma WiFi

> **Limitación del navegador:** una página HTTPS de Cloudflare Pages **no puede
> llamar por HTTP a `http://IP_LAN:8000`**. Chrome lo bloquea por **Mixed
> Content** aunque se conceda el permiso de red local. `localhost` sí funciona
> con ese permiso porque el navegador lo trata como un origen seguro, pero la
> IP LAN no. Sin un túnel HTTPS con dominio propio no es posible que Pages use
> el backend local desde el celular.

Opciones reales para el celular en la misma WiFi:

1. **Abrir directamente el backend local:** `http://IP_LAN:8000` (por ejemplo,
   `http://192.168.1.14:8000`). Es la opción recomendada para uso interno: el
   `.exe` sirve el frontend empaquetado y la API desde el mismo origen, sin
   Mixed Content ni dependencia de Render.
2. **Usar Cloudflare Pages:** `https://inventario-pos-bfw.pages.dev`. Funciona
   siempre, pero el celular usará **Render** porque el navegador bloquea la IP
   LAN por HTTP.

Para habilitar la opción 1, permite el puerto **8000** en el firewall de
Windows para redes privadas. La consola del `.exe` muestra la IP LAN activa.

## Funcionalidades (v1.2.2)

### Módulos

- **Login** con roles `admin` y `bartender` (clave con hash PBKDF2-HMAC-SHA256
  con sal) y redirección según el rol.
- **Navegación:** el menú lateral resalta la sección activa con los mismos
  verdes de una mesa disponible: fondo `#e5f7ed` y texto `var(--success)`
  (`#27ae60`), tanto en el panel del Administrador como en el del Bartender.
- **Inventario:** alta, edición, eliminación con confirmación, búsqueda,
  paginación y filtro por categoría. La columna **Stock es de solo lectura**;
  la columna **"Ingreso de Stock"** tiene un campo numérico y un botón verde
  **"Agregar"** que **suma** la cantidad al stock existente. El Administrador
  siempre la ve, junto con los botones **"−"** y **"+"**. El Bartender inicia
  en solo lectura y el Administrador puede habilitarle la columna por usuario
  desde **Usuarios** (sin botones incrementales).
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
  El resumen usa **días calendario**: **Hoy** abarca de 00:00 a la hora actual,
  **Ayer** el día completo y **7/30 días** incluyen hoy. Su **TOTAL** es la suma
  de efectivo + tarjeta + transferencia de los pedidos cerrados en ese rango.
  El historial muestra el **día de la semana de apertura** de cada turno.
- **Tickets internos:** desde **Corte de caja** (turno abierto o cerrado) se
  abre una ventana emergente con un comprobante por cada pedido cobrado y por
  cada alias que pagó su parte de una división. Incluye nombre del negocio,
  mesa/barra, fecha de ocupación, fecha de pago, alias del cliente, productos
  (nombre, cantidad y precio) y forma de pago. No incluye total ni impuestos,
  no se guarda en el servidor y puede imprimirse/guardarse como PDF o
  descargarse como imagen PNG.
- **Personalización (solo Administrador):** permite cambiar el nombre del
  negocio y agregar un logotipo cuadrado en la cabecera. El nombre oficial del
  sistema sigue siendo **Inventario POS**; los valores se guardan en la tabla
  `configuracion_negocio` y también identifican los tickets internos.
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

### Formato de fechas y horas

Las fechas del historial, los reportes, los turnos de caja y los usuarios usan
siempre la **hora local del servidor** (el reloj del equipo donde corre la
aplicación), con el formato `DD/MM/YYYY, HH:mm:ss`:

- `2026-10-24T22:52:46` → `24/10/2026, 22:52:46`

Al cerrar un pedido de mesa o de barra se guarda `fecha_cierre` con la hora
local exacta. Las fechas creadas por versiones anteriores (que se guardaban en
UTC) se convierten una sola vez al iniciar; la tabla `migraciones_sistema`
registra que esa conversión ya se aplicó para no desplazarlas dos veces.

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
| Usuarios | `POST /usuarios/login`, `GET /usuarios/`, `GET /usuarios/{id}`, `POST /usuarios/`, `PUT /usuarios/{id}` (incluye `ingreso_stock`), `PUT /usuarios/{id}/clave`, `DELETE /usuarios/{id}` |
| Mesas y barras | `GET /mesas/`, `POST /mesas/`, `POST /mesas/barra`, `POST /mesas/{id}/ocupar`, `PUT /mesas/{id}/estado`, `POST /mesas/{id}/liberar`, `DELETE /mesas/{id}` |
| Inventario | `GET /inventario/` (búsqueda + paginación), `POST /inventario/`, `PUT /inventario/{id}`, `PUT /inventario/{id}/stock`, `POST /inventario/{id}/stock/ajuste` (delta atómico), `DELETE /inventario/{id}` |
| Categorías | `GET /categorias/`, `POST /categorias/`, `PUT /categorias/{id}`, `DELETE /categorias/{id}` |
| Pedidos | `GET /pedidos/`, `POST /pedidos/`, `GET /pedidos/mesa/{id}`, `PUT /pedidos/{id}/items/{item_id}`, `PUT /pedidos/{id}/cerrar` |
| Cuentas | `GET /cuentas/mesa/{id}`, `GET /cuentas/barra/{numero}`, `POST /cuentas/mesa/{id}/cerrar`, `POST /cuentas/barra/{numero}/cerrar`, `POST /cuentas/mesa/{id}/transferir`, `POST /cuentas/dividir`, `POST /cuentas/participante/{id}/pagar`, `POST /cuentas/division/{id}/pagar`, `GET /cuentas/mesa/{id}/divisiones` |
| Caja | `GET /caja/turno-actual`, `POST /caja/abrir`, `POST /caja/cerrar`, `GET /caja/turnos`, `GET /caja/tickets?turno_id=<id>` (turno abierto o cerrado), `GET /caja/resumen?dias=N&offset_dias=M`, `GET /caja/ventas-por-dia`, `GET /caja/historial` |
| Personalización | `GET /configuracion/` y `PUT /configuracion/` (nombre del negocio y logo data URL) |
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

- En desarrollo, si no se define `DATABASE_URL`, se crea automáticamente
  `backend/data/inventario.db` con usuarios, productos y mesas de ejemplo.
- El `.exe` híbrido usa **Neon** por defecto: la cadena se incrusta al compilar
  desde `inventario-pos.env`, `backend/.env` o la variable `DATABASE_URL`.
- Orden de prioridad del `.exe`:
  1. Variable de entorno `DATABASE_URL`.
  2. Archivo `inventario-pos.env` junto al ejecutable.
  3. Cadena compilada en el propio `.exe`.
  4. SQLite local en `%LOCALAPPDATA%\InventarioPOS\inventario.db` (solo si no
     hay ninguna cadena; la consola muestra un aviso).
- Para cambiar la cadena sin recompilar, crea `inventario-pos.env` junto al
  `.exe`:

  ```env
  DATABASE_URL=postgresql://usuario:clave@host-pooler.../neondb?sslmode=require
  ```

> El `.exe` contiene la cadena de Neon. No lo publiques ni lo compartas fuera
> del negocio. Si se filtra, rota la clave del usuario de Neon y recompila.

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

No se usan correos: el acceso es por **usuario** + **clave**. El login envía
el campo `usuario` al endpoint `POST /api/usuarios/login`.

### Usuario inicial

| Usuario | Clave | Rol |
|---|---|---|
| `Admin` | `1234` | Administrador |

> `1234` es solo la clave inicial de una instalación local nueva. El despliegue
> público usa claves fuertes para `Admin` y `Yeison`; cámbialas desde
> **Usuarios → Cambiar clave** si alguna vez se comparten.

### Permisos

| Módulo | Administrador | Bartender |
|---|---|---|
| Inventario | Crear, editar, eliminar, ingresar stock | **Solo lectura** (ingreso de stock opcional) |
| Mesas / Pedidos / Cuenta | ✅ | ✅ |
| Corte de caja | ✅ | ✅ |
| Reportes / Historial | ✅ | ❌ |
| Usuarios (crear, roles, claves) | ✅ | ❌ |

El acceso a las rutas de administración está restringido en la interfaz: un
Bartender que intente abrir `/admin` es redirigido a su propio panel. La API
local no usa tokens; el control de roles es de interfaz.

### Ingreso de stock del Bartender

El Bartender abre el inventario en **modo lectura**: no puede crear, editar ni
eliminar productos y no ve los botones **"−"** ni **"+"**. Por defecto tampoco
ve la columna **"Ingreso de Stock"**.

El Administrador decide qué Bartenders pueden cargar stock desde
**Usuarios → Usuarios registrados**, con el interruptor de la columna
**"Ingreso de Stock"**. El permiso se guarda en la base (`usuarios.ingreso_stock`,
apagado por defecto) y se aplica por usuario. Cuando está habilitado, la vista
del Bartender muestra la columna con un campo numérico y el botón verde
**"Agregar"**; la cantidad se suma al stock existente y se refleja al instante.
El Bartender consulta su permiso cada 5 segundos, por lo que los cambios del
Administrador aparecen sin recargar la página (también se actualizan al volver
a la ventana). El Administrador mantiene la columna siempre activa, con el
mismo botón **"Agregar"** y los ajustes de una unidad.

El ajuste se envía a `POST /api/inventario/{id}/stock/ajuste` como
`{ "delta": N }` y el backend aplica `max(0, stock + N)` de forma atómica, sin
sobrescribir cambios concurrentes.

### Menú de Usuarios (solo Administrador)

`/admin/usuarios` permite crear usuarios con alias y rol, cambiar rol,
activar/desactivar, cambiar clave y eliminar. En **Usuarios registrados** cada
Bartender tiene un interruptor de **Ingreso de Stock**; el Administrador
aparece como **"Siempre activo"**. Todos los usuarios nuevos nacen con la
**clave inicial `1234`** (cambiable después) y con el ingreso de stock
desactivado.

## Acceso desde celular o tablet (misma WiFi)

Resumen: en el celular abre `http://IP_LAN:8000` para usar el backend local, o
`https://inventario-pos-bfw.pages.dev` si aceptas que use Render. La página HTTPS
de Pages no puede llamar por HTTP a la IP LAN (Mixed Content), aunque Chrome
conceda el permiso de red local. Los detalles están en
[Modo híbrido](#modo-híbrido-v121).

## Solución de problemas

### "Method Not Allowed" al liberar una barra

El botón **Liberar barra** envía `POST /api/cuentas/barra/{n}/cerrar`, una ruta
que existe en el backend actual. Si aparece **"Method Not Allowed"**, el
frontend está actualizado pero el backend que está corriendo es una versión
anterior (por ejemplo, un `InventarioPOS.exe` viejo). La petición no coincide
con ninguna ruta POST y termina en el fallback del frontend.

Para corregirlo:

1. Cierra la instancia anterior del backend/ejecutable.
2. Regenera el frontend y el ejecutable con
   `scripts\build_pages.ps1 -Deploy` y `scripts\build_hybrid_exe.bat`.
3. Abre la aplicación nueva y recarga el navegador con `Ctrl + F5`.

El comportamiento esperado es:

- **Aceptar:** cobra la cuenta y la barra queda **ocupada**.
- **Liberar barra:** cobra la cuenta y deja **todas las plazas disponibles**.

### Aparece una URL de ngrok o un backend viejo

Si el mensaje de error muestra `*.ngrok-free.dev`, `inventario-pos.onrender.com`
u otra URL distinta de `https://inventario-pos-api-pqju.onrender.com/api`, el
navegador, la PWA o el APK está ejecutando un **build anterior**. La versión
1.2.1 ignora `REACT_APP_API_URL` y valida la URL de Render, así que un build
nuevo no puede apuntar a ngrok.

1. Abre https://inventario-pos-bfw.pages.dev y confirma al pie del login que
   diga **Inventario POS v1.2.2**.
2. Si aparece la versión vieja, cierra todas las pestañas, borra los datos del
   sitio (o desinstala la PWA) y vuelve a abrir la URL.
3. En el PC, cierra cualquier `InventarioPOS.exe` viejo y usa el nuevo de
   `dist\InventarioPOS.exe`.
4. En Android, el APK no se actualiza solo: hay que recompilarlo e instalarlo
   de nuevo.

> La URL correcta de Render es
> `https://inventario-pos-api-pqju.onrender.com/api`. El host
> `inventario-pos.onrender.com` ya no responde.

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

`InventarioPOS.exe` es un archivo único que incluye el backend (FastAPI) y una
copia de respaldo del frontend (React compilado). En modo híbrido:

- Levanta FastAPI en `0.0.0.0:8000` y conecta con **Neon** (la misma base que
  Render) usando la cadena incrustada.
- Abre **Chrome/Edge** con `--new-window` en la URL fija
  `https://inventario-pos-bfw.pages.dev/admin/usuarios`. Si no los encuentra,
  usa el navegador predeterminado.
- El frontend de Pages detecta este backend por `localhost`; si no responde,
  usa Render.
- La copia del frontend incluida en el `.exe` sigue disponible en
  `http://IP_LAN:8000` como respaldo para celulares en la misma WiFi.
- Muestra en consola la IP LAN activa y la base configurada.
- Si no hay cadena de Neon, cae en SQLite
  (`%LOCALAPPDATA%\InventarioPOS\inventario.db`) y muestra un aviso.
- No requiere Python ni Node.js en el PC del negocio.
- Debe permanecer abierto mientras el negocio esté operando. No se registra
  como servicio de Windows: al cerrar la consola se detiene el backend local.

```powershell
# 1. Compilar y desplegar el frontend en Cloudflare Pages
#    (detecta la IP LAN activa y la incluye como candidato local)
scripts\build_pages.ps1 -Deploy

# 2. Compilar el .exe híbrido (backend + Neon + frontend de respaldo)
scripts\build_hybrid_exe.bat

# También se puede pasar la cadena directamente
scripts\build_hybrid_exe.bat -DatabaseUrl "postgresql://..."

# Crear acceso directo en el escritorio
scripts\crear_acceso_directo.bat
```

El script `build_pages.ps1`:

1. Detecta la IP LAN activa del PC.
2. Compila con `REACT_APP_CLOUD_API_URL` (Render) y
   `REACT_APP_LOCAL_API_URL=http://<IP_LAN>:8000/api`.
3. Elimina `REACT_APP_API_URL` para que ningún build use un endpoint forzado.
4. Con `-Deploy`, publica en Cloudflare Pages con Wrangler.

El script `build_hybrid_exe.bat`:

1. Lee `DATABASE_URL` desde `-DatabaseUrl`, la variable de entorno,
   `inventario-pos.env` (raíz) o `backend/.env`.
2. Genera temporalmente `backend/app/_build_defaults.py` con la cadena.
3. Compila el frontend de respaldo.
4. Ejecuta PyInstaller con `build_exe.spec`.
5. Borra `_build_defaults.py` para no dejar la clave en el árbol de trabajo.

`backend/app/_build_defaults.py`, `inventario-pos.env` y `neon_url.txt` están en
`.gitignore`. El ejecutable final queda en `dist\InventarioPOS.exe`.

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
pantalla de inicio"**. Queda como una app instalada con icono propio y usa el
backend local. También puedes instalarla desde
`https://inventario-pos-bfw.pages.dev`, pero en ese caso usará Render.

## Pendientes por corregir

1. **Recompilar el APK**: el `.exe` ya incluye los últimos ajustes, pero el APK
   de Android debe regenerarse para incorporarlos.
2. **Instalador de Windows:** `scripts/start.bat` menciona
   `scripts/install.bat`, pero ese archivo no existe; crearlo o corregir el
   mensaje.
3. **`start_dev.sh`:** unificar la ruta del entorno virtual (hoy crea/activa
   `venv` en la raíz pero espera `backend/venv`).
4. **Pruebas automatizadas:** agregar pruebas de backend/frontend y validar la
   migración de etiquetas históricas en una base antigua.
5. **Nota de desarrollo:** si `npm run build` reporta un error de sintaxis
   inexistente en `HistorialPage.tsx`, borrar `frontend/node_modules/.cache` y
   reconstruir.
6. **Despliegue público e híbrido:** completado el 30/10/2026 y actualizado el
   03/11/2026 con Neon + Render Free + Cloudflare Pages. El flujo 1.2.1 fue
   validado con 7/7 pruebas locales, 7/7 Pages→local y 7/7 Pages→Render. Ver
   [Despliegue en la nube](#despliegue-en-la-nube).
7. **Render en frío:** ya no se envía ping. La operación interna usa el `.exe`;
   Render solo se usa para accesos externos y puede tardar 30–60 s en despertar.
8. **Retirar el servicio Render antiguo (opcional):** `Inventario-pos` (rama
   `main`) sigue activo; eliminarlo cuando se confirme que el nuevo despliegue
   es el definitivo.
9. **Celular en la misma WiFi:** una página HTTPS de Pages no puede llamar por
   HTTP a `http://IP_LAN:8000` (Mixed Content). Queda elegir entre abrir
   `http://IP_LAN:8000` en el celular o configurar un túnel HTTPS con dominio
   propio. Mientras no exista túnel, Pages usa Render en el celular.
10. **Autoarranque del `.exe`:** hoy el backend local vive solo mientras la
    consola del ejecutable esté abierta. Si se requiere que siga activo tras
    reiniciar Windows, crear una tarea programada o un servicio.

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
| `v1.1.0` | — | Mejoras de barras, ingreso de stock, cantidades manuales en pedidos, totales con formato y fechas en hora local |
| `v1.2.0` | — | Modo híbrido: `.exe` con Neon, detección local/Render, botón de conexión local y respaldo en Cloudflare Pages |
| `v1.2.1` | — | Elimina el endpoint forzado por `REACT_APP_API_URL`, rechaza URLs ngrok, limpia caché del service worker y muestra la versión en el login. Incluye personalización visual del negocio y tickets internos desde Corte de caja |
| `v1.2.2` (actual) | — | Estandariza la tipografía del modal de apertura, aplica máscara de miles sin decimales al Fondo Inicial de Caja y permite imprimir todos los tickets del turno con salto de página |

## Despliegue en la nube

**Estado (03/11/2026):** modo híbrido implementado y validado. El `.exe`
conecta a Neon, la detección local/Render funciona y el frontend público quedó
desplegado en Cloudflare Pages.

### Arquitectura

| Componente | Servicio | Plan | Región | URL |
|---|---|---|---|---|
| Operación interna | `InventarioPOS.exe` en el PC | — | Local | `http://localhost:8000` / `http://IP-LAN:8000` |
| Frontend fijo | Cloudflare Pages | Free | Global | https://inventario-pos-bfw.pages.dev |
| Base de datos | Neon PostgreSQL | Free | `aws-us-east-2` | Cadena *pooled* privada |
| Backend respaldo | Render (Docker) | Free | Ohio | https://inventario-pos-api-pqju.onrender.com |

- **Neon Free:** 0.5 GB, sin tarjeta. Se usa la cadena *pooled* con
  `sslmode=require&channel_binding=require`. La misma cadena la usan el `.exe`
  y Render; la cadena completa vive en la variable `DATABASE_URL` de Render y
  se incrusta al compilar el ejecutable, nunca en el repositorio.
  `GET /api/config` expone `base_datos_id`, una huella SHA-256 truncada de
  host/base que permite comparar ambos backends sin revelar credenciales.
  En este despliegue ambos responden `base_datos_id: "d22e416b6276"`.
- **Render Free:** sin tarjeta. El servicio se suspende a los 15 minutos sin
  tráfico y despierta en 30–60 s. Se usa como respaldo externo; la operación
  interna no depende de él mientras el `.exe` esté abierto. No se configura
  ping.
- **Cloudflare Pages:** el frontend se compila con
  `scripts/build_pages.ps1`, que define `REACT_APP_CLOUD_API_URL` (Render),
  `REACT_APP_LOCAL_API_URL` (IP LAN activa) y elimina `REACT_APP_API_URL`.
  Salida `build`, fallback de SPA con `frontend/public/_redirects`.

### Variables del backend

| Variable | Valor actual |
|---|---|
| `DATABASE_URL` | Cadena *pooled* de Neon (`sslmode=require&channel_binding=require`) |
| `TZ` | `America/Bogota` |
| `APP_TIMEZONE` | `America/Bogota` |
| `CORS_ORIGINS` | `https://inventario-pos-bfw.pages.dev` |
| `PORT` | Lo inyecta Render; el Dockerfile usa `${PORT:-8000}` |

`CORS_ORIGINS` debe llevar el origen exacto del frontend, sin `/` final. Si se
publica un dominio nuevo o un preview de Cloudflare Pages, se agrega separado
por comas y se redeploya el backend.

`ADMIN_PASSWORD` solo se usa al ejecutar la migración; no debe quedar como
variable permanente del hosting.

### 1. Base de datos Neon

1. Crear un proyecto en [Neon](https://neon.tech) (plan Free) en
   `aws-us-east-2` (Ohio).
2. Copiar la cadena **pooled** de conexión.
3. Desde `backend/`, ejecutar la migración (no modifica la SQLite original):

   ```bash
   export DATABASE_URL="postgresql://...-pooler.../neondb?sslmode=require"
   export ADMIN_PASSWORD="una-clave-segura"
   python scripts/migrate_sqlite_to_postgres.py --reset
   ```

4. Verificar que los conteos coincidan. El script conserva IDs y ajusta las
   secuencias.
5. Cambiar también la clave de los demás usuarios antes de publicar. En este
   despliegue `Admin` y `Yeison` usan claves fuertes; sus hashes están en Neon y
   las claves no se guardan en el repositorio. La SQLite local no se modifica.

### 2. Backend en Render

1. Crear una cuenta en [Render](https://dashboard.render.com) con GitHub (no
   pide tarjeta para el plan Free).
2. **New → Web Service** y conectar el repositorio
   `johnfvvv-dot/Inventario-pos`.
3. Configurar:
   - **Branch:** `deploy/neon`
   - **Root Directory:** `backend`
   - **Runtime:** Docker
   - **Dockerfile Path:** `./Dockerfile`
   - **Plan:** Free
   - **Region:** Ohio
   - **Health Check Path:** `/health`
4. Agregar las variables de la tabla anterior y desplegar.
5. Anotar la URL `https://<servicio>.onrender.com`.

La rama `deploy/neon` tiene el proyecto en la raíz del repositorio para que
Render encuentre `backend/`; la rama `master` conserva la carpeta
`inventario-pos/`.

**Nota sobre el plan Free:** tras 15 minutos sin tráfico la instancia se
suspende. La primera petición externa tarda 30–60 s y las siguientes responden
normal. En el modo híbrido **no se envía ping**: la operación interna usa el
`.exe` local y Render solo atiende accesos externos. Si se quisiera evitar el
arranque en frío, un ping cada 10 minutos consumiría horas-instancia (dentro de
las 750 h/mes), pero no es necesario.

### 3. Frontend en Cloudflare Pages

1. Crear el proyecto `inventario-pos` en Cloudflare Pages.
2. Configuración:
   - **Root directory:** `frontend`
   - **Build command:** `npm run build`
   - **Build output:** `build`
   - **Variables:** `REACT_APP_CLOUD_API_URL` con la URL de Render y
     `REACT_APP_LOCAL_API_URL` con la IP LAN activa.
3. El archivo `frontend/public/_redirects` ya incluye el fallback de la SPA.
4. Publicar con el script reproducible (detecta la IP LAN y compila):

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\build_pages.ps1 -Deploy
   ```

   O manualmente:

   ```bash
   cd frontend
   REACT_APP_CLOUD_API_URL=https://inventario-pos-api-pqju.onrender.com/api \
   REACT_APP_LOCAL_API_URL=http://192.168.1.14:8000/api \
   npm run build
   npx wrangler pages deploy build --project-name inventario-pos --branch main
   ```

5. Agregar la URL de Pages a `CORS_ORIGINS` del backend y redeployar Render.

> `REACT_APP_API_URL` se ignora por seguridad. Para el despliegue normal usa
> `scripts/build_pages.ps1`, que define ambas URLs válidas y descarta cualquier
> valor HTTP público, local no permitido o con `ngrok`. Si cambia la IP del PC,
> vuelve a compilar y desplegar Pages.

### 4. Pruebas después de publicar

- `GET https://inventario-pos-api-pqju.onrender.com/health` responde `200`.
- `GET /api/config` en local y Render devuelve el mismo `base_datos_id`
  (`d22e416b6276` en este despliegue).
- Login con `Admin` y con `Yeison` en local y en Render.
- Inventario: 4 productos y stock 159.
- Reportes: filtros Hoy/Semana/Mes/Turno de ayer, gráficas y CSV.
- Crear una venta de prueba, cobrarla y verificar stock (158), historial,
  turno y ganancia (`$1.600`).
- Revisar la consola del navegador: sin errores CORS ni HTTP 5xx.

Resultado: **29/29 pruebas públicas** (30/10/2026) y **21/21 pruebas del flujo
híbrido** en la versión 1.2.1 (03/11/2026: 7 local, 7 Pages→local con permiso
LNA y 7 Pages→Render sin permiso). Después de validar, la base se dejó limpia:
4 productos (stock 159), 9 mesas, 2 usuarios y 0 pedidos de prueba.

### 5. Operación

- **Cold start:** la primera visita externa tras 15 minutos de inactividad puede
  tardar 30–60 s. El health check de Render despierta el servicio. No se
  configura ping: la operación interna usa el `.exe`.
- **CORS:** si el frontend cambia de dominio, actualizar `CORS_ORIGINS` y
  redeployar. El backend local responde con `Access-Control-Allow-Origin: *` y
  `Access-Control-Allow-Private-Network: true` para que funcione desde
  `localhost` y desde la IP LAN.
- **Red local:** Chrome 142+ puede mostrar el permiso **Local Network Access**
  cuando una página pública consulta `localhost`. Si se concede, Pages usa el
  backend local; si no, usa Render. Para la IP LAN el permiso no basta: el
  navegador bloquea `http://IP_LAN:8000` por Mixed Content. Para uso interno en
  celular abre `http://IP-LAN:8000`.
- **Datos:** la SQLite local `backend/data/inventario.db` se conserva como
  respaldo de desarrollo; la operación híbrida persiste en Neon.
- **Seguridad del `.exe`:** contiene la cadena de Neon. No compartirlo, no
  subirlo a repositorios ni enviarlo por canales públicos. Para rotar la clave,
  actualiza Neon, Render y recompila el ejecutable.
- **Contraseñas:** se guardan con PBKDF2-HMAC-SHA256 (260 000 iteraciones, sal
  aleatoria). Los hashes SHA-256 antiguos se aceptan una vez y se reemplazan
  automáticamente al iniciar sesión.
- **Servicio antiguo:** el servicio Render `Inventario-pos` (rama `main`,
  Python, Oregón) se conserva sin cambios hasta confirmar que ya no se necesita.

### Pruebas del modo híbrido

| Prueba | Resultado |
|---|---|
| `/health` del `.exe` con `database: postgresql` | OK |
| Login `Admin` y `Yeison` contra Neon desde el `.exe` y Render | OK |
| Inventario: 4 productos, stock 159 | OK |
| `http://localhost:8000` detecta servidor local y login | 7/7 OK |
| Pages en el PC, permiso LNA concedido, usa localhost | 7/7 OK |
| Pages sin backend local, usa Render y login | 7/7 OK |
| Huella Neon local/Render (`base_datos_id`) | `d22e416b6276` en ambos |
| Hashes de `Admin` y `Yeison` | `pbkdf2_sha256`, longitud 118 |
| Preflight CORS/LNA del backend local | `allow-private-network: true` |

> En celular, Pages sigue bloqueando `http://IP_LAN:8000` por Mixed Content.
> La prueba LAN ya no forma parte del flujo Pages; para ese caso se abre
> directamente `http://IP_LAN:8000`.

### Alternativas descartadas (30/10/2026)

- **Northflank Sandbox:** aunque el plan es gratis, exige agregar una tarjeta
  para verificar identidad antes de crear servicios.
- **Hugging Face Docker Spaces:** responde `402 Payment Required`; los Spaces
  Docker en `cpu-basic` requieren suscripción PRO.
- **Koyeb:** ya no ofrece capa gratuita para servicios web (octubre 2026).
- **Google Cloud Run y Oracle Always Free:** tienen cuota gratuita, pero exigen
  cuenta de facturación o tarjeta.

### URLs finales

| Servicio | URL |
|---|---|
| Frontend fijo | https://inventario-pos-bfw.pages.dev |
| Arranque del `.exe` | https://inventario-pos-bfw.pages.dev/admin/usuarios |
| Backend respaldo (API) | https://inventario-pos-api-pqju.onrender.com |
| Documentación API | https://inventario-pos-api-pqju.onrender.com/docs |
| Salud (Render) | https://inventario-pos-api-pqju.onrender.com/health |
| Operación local | `http://localhost:8000` / `http://IP-LAN:8000` |
| Neon | Proyecto Free en `aws-us-east-2` (host *pooled* privado) |
