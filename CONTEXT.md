# Inventario POS - Ficha de Contexto

**Versión actual:** 1.2.1

**Última actualización:** 05/11/2026

## 1. Propósito del sistema

Inventario POS es una aplicación web/escritorio para pequeños negocios (bares,
restaurantes, cafeterías) que integra en un solo lugar:

- Gestión de **inventario y categorías** de productos.
- Administración de **mesas** y **barras** con plazas independientes.
- Toma de **pedidos** con control de stock.
- **Cuentas por mesa/barra**, división entre clientes, transferencias y cobro.
- **Corte de caja** por turno y forma de pago.
- **Reportes**, historial de ventas y exportación CSV.
- **Usuarios y roles** (`admin` / `bartender`).

Funciona de forma local (sin servidor externo), puede instalarse como PWA y
también empaquetarse como ejecutable de Windows o APK de Android.

## 2. Stack y arquitectura

- **Backend:** Python 3.10+, FastAPI, SQLAlchemy, Pydantic.
  Código en `backend/app/` (`main.py`, `models.py`, `schemas.py`, `routes/`).
- **Base de datos:** Neon PostgreSQL en el modo híbrido.
  - `.exe` híbrido y Render: misma cadena *pooled* de Neon.
  - Respaldo/desarrollo: SQLite en `backend/data/inventario.db` o
    `%LOCALAPPDATA%\InventarioPOS\inventario.db`.
  - La cadena del `.exe` se incrusta al compilar (`_build_defaults.py`) y se
    puede sobrescribir con `DATABASE_URL` o `inventario-pos.env` junto al
    ejecutable.
- **Frontend:** React 18 + TypeScript (Create React App), React Router y Chart.js.
  Código en `frontend/src/`.
- **Autenticación:** usuario + clave con hash **PBKDF2-HMAC-SHA256** (260 000
  iteraciones y sal aleatoria). Los hashes SHA-256 sin sal de versiones
  anteriores se aceptan y se reemplazan automáticamente al iniciar sesión. El
  login valida el campo `usuario`; el usuario autenticado se guarda en
  `localStorage`; no se usa JWT. Roles: `admin` y `bartender`. Las rutas
  `/admin` y `/bartender` están protegidas en el cliente
  (`RutaAdmin`/`RutaBartender` en `App.tsx`); la API no valida roles ni usa
  tokens.
- **API:** prefijo `/api`; documentación interactiva en `/docs`; salud en
  `/health`; configuración de red en `/api/config` (incluye `base_datos_id`,
  huella SHA-256 truncada de host/base para comparar local y Render sin exponer
  credenciales).
- **Empaquetado:** PyInstaller (`dist/InventarioPOS.exe`) y Capacitor
  (`frontend/android/`).
- **Modo híbrido (03/11/2026):** el `.exe` levanta FastAPI en `0.0.0.0:8000`,
  conecta a Neon y abre Chrome/Edge con `--new-window` en la URL fija
  `https://inventario-pos-bfw.pages.dev/admin/usuarios`. El frontend siempre se
  sirve desde Cloudflare Pages; al iniciar sesión prueba en paralelo
  `localhost:8000`, `127.0.0.1:8000` y la IP LAN compilada, y si ninguna
  responde usa Render. El login solo muestra `Inventario POS v1.2.1`; no hay
  botón de conexión ni estado del servidor. El fallback seguro solo reintenta
  `GET`, `HEAD` y login.
- **1.2.1 (03/11/2026):** se elimina el endpoint forzado por
  `REACT_APP_API_URL` (se ignora aunque venga definido). `REACT_APP_CLOUD_API_URL`
  solo se acepta si es HTTPS, sin `ngrok`, sin localhost ni IP privada; en caso
  contrario se usa la URL oficial de Render. `REACT_APP_LOCAL_API_URL` solo se
  acepta si apunta a localhost/LAN. Se retira la cabecera de ngrok, se sube el
  service worker a `inventario-pos-v3` y el login muestra únicamente la versión.
- **Acceso móvil (limitación):** una página HTTPS de Pages no puede llamar por
  HTTP a `http://IP_LAN:8000`; Chrome lo bloquea por **Mixed Content** aunque se
  conceda el permiso *Local Network Access*. `localhost` sí funciona con ese
  permiso. Para usar el backend local desde el celular hay que abrir
  `http://IP_LAN:8000` directamente; desde Pages el celular usa Render.
- **Despliegue público (30/10/2026):** Neon PostgreSQL (Free, `aws-us-east-2`) +
  Render (Docker, Free, Ohio) + Cloudflare Pages. Frontend:
  https://inventario-pos-bfw.pages.dev; API:
  https://inventario-pos-api-pqju.onrender.com. Ver
  "Despliegue en la nube" en `README.md`.

## 3. Estado actual y ajustes recientes

### Navegación

- `MenuLink` (`frontend/src/components/MenuLink.tsx`) resalta el ítem activo
  del menú lateral con la paleta de una mesa disponible: fondo `#e5f7ed`
  (`.badge-success`) y texto `var(--success)` = `#27ae60`.
- Usa `useLocation` y compara la ruta normalizada; las rutas índice `/admin` y
  `/bartender` activan **Inventario** y **Pedidos** respectivamente.
- Solo un enlace recibe la clase `activo` y `aria-current="page"`. Aplica en
  los paneles de Administrador y Bartender, también en el modo móvil.

### Mesas y barras

- Las barras se muestran como **"Barra N"** en el selector de pedidos y en el
  historial, no como números de plaza (`101`, `201`, etc.).
- La etiqueta histórica se conserva en `Pedido.mesa_etiqueta_historica` y se
  calcula con `Mesa.etiqueta_historial()`. Los pedidos antiguos se completan al
  arrancar mediante `_migrar_etiquetas_historial()`.
- Cada pedido guarda también `Pedido.mesa_numero_historico` al crearse,
  cerrarse o transferirse (`Pedido.guardar_origen()`), de modo que el historial
  siempre muestra "Mesa N" o "Barra N" junto con el total.
- Las barras cerradas o eliminadas conservan su etiqueta "Barra N" en el
  historial.
- Una barra **ocupada no puede ser destino de transferencia**; se valida el
  grupo completo de plazas, no solo una plaza.
- El cierre y la liberación de una barra replican el flujo de las mesas:
  `POST /api/cuentas/barra/{numero}/cerrar` y
  `POST /api/mesas/{id}/liberar`, con botón **"Liberar barra"** en la cuenta.
- `CuentaModal` recibe `barraNumero` tanto desde **Mesas** como desde
  **Pedidos**, de modo que el botón siempre usa la cuenta agregada de la barra
  y no la de una plaza aislada.
- `api.ts` valida los identificadores antes de construir la URL; un id
  inválido muestra un mensaje claro en lugar de enviar `/NaN` al backend.
- Las rutas `/api/...` inexistentes responden `404` con un detalle JSON (el
  fallback del frontend ya no devuelve "Method Not Allowed" a un POST).
- Los totales pendientes de las tarjetas de mesa/barra se muestran en **verde**
  con el formato único de precios (ej. `$30.400`).
- Todos los precios del sistema usan el mismo formato: separador de miles y
  sin decimales (ej. `$3.800`).

### Inventario

- La columna **Stock es de solo lectura** y muestra únicamente la cantidad
  actual mediante un badge (rojo/amarillo/verde según el nivel).
- La columna **"Ingreso de Stock"** tiene un campo numérico + botón verde
  **"Agregar"** que **suma** la cantidad al stock existente
  (ej. 50 + 10 = 60). También se confirma con Enter. El campo solo acepta
  dígitos y valida cantidades mayores a cero.
- El **Administrador** siempre ve la columna de ingreso, junto con los botones
  incrementales **"−"** y **"+"** y las acciones de crear, editar y eliminar.
- El **Bartender** inicia en **solo lectura**, sin acciones de productos ni
  botones incrementales. El permiso de ingreso de stock es **por usuario** y lo
  controla el Administrador desde **Usuarios → Usuarios registrados**; se guarda
  en `usuarios.ingreso_stock` (0 por defecto). Al habilitarlo, el Bartender ve
  únicamente el campo numérico + botón **"Agregar"**.
- `BartenderLayout` consulta `GET /api/usuarios/{id}` al cargar y cada **5 s**
  (además de `focus` y `visibilitychange`), comparte el permiso con
  `InventarioPage` por `Outlet context` y mantiene sincronizado el
  `localStorage`. Así el cambio del Administrador aparece sin recargar.
- El ajuste usa `POST /api/inventario/{id}/stock/ajuste` con `{ delta }`, que
  aplica `max(0, stock + delta)` de forma atómica en la base. Se usa tanto para
  "Agregar" como para los botones **"−"** y **"+"**. Se conserva
  `PUT /api/inventario/{id}/stock` por compatibilidad.
- La tabla de **Usuarios registrados** incluye la columna "Ingreso de Stock":
  interruptor por Bartender y badge "Siempre activo" para el Administrador.
- El menú de usuario es el componente reutilizable `UserMenu`; ya no contiene
  el interruptor de stock y solo muestra la sesión y "Cerrar sesión".

### Pedidos

- La lista de productos muestra **como máximo 8 filas visibles** con scroll
  vertical y encabezado fijo.
- Cada producto tiene un campo numérico + botón verde **"Agregar"** para
  ingresar una cantidad manual; se mantiene el botón **"+"** para sumar una
  unidad.
- Enter en el campo también agrega la cantidad indicada.
- Se valida el stock considerando lo que ya está en el carrito y se muestran
  mensajes de error claros.
- Los campos de cantidad se limpian al agregar y al cambiar de mesa/barra.

### Cuentas, caja y reportes

- División de cuenta por alias, cobro individual, transferencia entre mesas y
  plazas de barra, cierre con o sin liberación y corte de caja por turno.
- El **resumen de ventas** filtra por días calendario: `Hoy` va de las 00:00 a
  la hora actual, `Ayer` cubre el día completo y `7/30 días` incluyen hoy. Los
  totales, pedidos cerrados, mesas y operaciones usan el mismo rango; el
  **TOTAL** siempre es `efectivo + tarjeta + transferencia` (pedidos cerrados).
- El **historial de turnos** muestra la columna `Día` antes de `Abierto`, con el
  día completo en español calculado solo desde `fecha_apertura` (helper
  `formatearDiaSemana`). Un turno abierto el sábado y cerrado el domingo sigue
  mostrando **Sábado**.
- La transferencia valida que el destino esté libre y no ofrece barras ocupadas
  como destino.
- Reportes con KPIs, gráficos y exportación CSV; historial con filtros por
  fecha, mesa/barra, producto y forma de pago.
- Todas las fechas se guardan y muestran en **hora local** con formato
  `DD/MM/YYYY, HH:mm:ss` (helper `backend/app/tiempo.py` y
  `frontend/src/utils/format.ts`). El cierre de pedidos de mesa y barra usa
  `ahora_local()`.
- Migraciones ligeras al iniciar: columnas faltantes (incluida
  `usuarios.ingreso_stock`), alias de usuarios, etiquetas históricas y
  conversión única UTC → hora local
  (`migraciones_sistema.fechas_locales_v1`).
- El filtro "Hasta" del historial incluye el día completo.

### Personalización y tickets internos (05/11/2026)

- **Personalización:** nuevo ítem del menú del Administrador en
  `/admin/personalizacion`. Cambia el nombre visible de la cabecera y agrega un
  logotipo cuadrado de 256×256 (data URL PNG/JPEG/WebP). El nombre oficial del
  sistema sigue siendo **Inventario POS** y el login conserva
  `Inventario POS v1.2.1`.
- Los valores se guardan en la tabla `configuracion_negocio` (fila única
  `id=1`). La cabecera del Administrador y la del Bartender los leen mediante
  `useConfiguracionNegocio`, con copia en `localStorage` y evento
  `negocio-config-actualizada` para actualizarse sin recargar.
- El logo mide 36 px en escritorio y 30 px en móvil; no aumenta la altura de la
  barra superior, solo desplaza el título a la derecha.
- **Tickets internos:** botón **Tickets** en el turno actual y **Ver tickets**
  en el historial de turnos (abiertos o cerrados). El modal
  `TicketsModal` llama a `GET /api/caja/tickets?turno_id=<id>` (sin `turno_id`
  usa el turno abierto) y arma los comprobantes en memoria.
- Un ticket por pedido cerrado y uno por cada participante pagado de una
  división. Muestran nombre del negocio, folio, mesa/barra, alias del cliente,
  fecha de ocupación, fecha de pago, productos (nombre, cantidad y precio) y
  forma de pago. **No incluyen total ni impuestos** y no se guardan en la base.
- Marcas temporales nuevas: `Mesa.fecha_ocupacion`, `Pedido.fecha_ocupacion`,
  `Division.fecha_ocupacion` y `Participante.fecha_pago`. `Pedido.fecha_cierre`
  sigue siendo la fecha de pago de los pedidos completos.
- Descarga: **Imprimir / PDF** usa la impresión del navegador con estilos
  `@media print`; cada tarjeta tiene **Descargar imagen**, que genera un PNG
  local con canvas (`utils/ticketImagen.ts`). Al cerrar el modal desaparecen.

### Despliegue público

- **Base:** Neon Free en `aws-us-east-2`, cadena *pooled* con
  `sslmode=require&channel_binding=require`. La SQLite local
  (`backend/data/inventario.db`) sigue intacta como respaldo. El `.exe` y Render
  usan la misma cadena; `GET /api/config` devuelve `base_datos_id` para
  verificarlo. En este despliegue ambos responden `d22e416b6276`.
- **Backend:** Render Free (Docker, Ohio, rama `deploy/neon`, root `backend`,
  health check `/health`). Variables: `DATABASE_URL`, `TZ=America/Bogota`,
  `APP_TIMEZONE=America/Bogota`, `CORS_ORIGINS` con el origen exacto de Pages.
  El plan Free se suspende a los 15 min sin tráfico; el arranque en frío tarda
  30–60 s. No se usa SQLite ni disco persistente en Render. No se configura ping.
- **Frontend:** Cloudflare Pages (`inventario-pos`). Se compila con
  `scripts/build_pages.ps1`, que define
  `REACT_APP_CLOUD_API_URL=https://inventario-pos-api-pqju.onrender.com/api` y
  `REACT_APP_LOCAL_API_URL=http://<IP_LAN>:8000/api` (IP activa detectada),
  además de eliminar `REACT_APP_API_URL`. `frontend/public/_redirects` mantiene
  el fallback de la SPA. La única selección de backend es la detección
  automática local → Render.
- **Ejecutable híbrido:** `scripts/build_hybrid_exe.ps1` (y `.bat`) genera
  `backend/app/_build_defaults.py` desde `DATABASE_URL`/`inventario-pos.env`,
  compila el frontend de respaldo, ejecuta PyInstaller y borra el archivo
  temporal. El `.exe` usa Neon, mantiene el backend local activo mientras la
  consola esté abierta y lanza Chrome/Edge con `--new-window` en la URL fija de
  Pages. No se registra como servicio de Windows.
- **Validación:** 29/29 pruebas públicas (30/10/2026) y 21/21 pruebas del flujo
  híbrido en la 1.2.1 (03/11/2026: 7 local, 7 Pages→local con permiso LNA y 7
  Pages→Render sin permiso). Admin y Yeison inician sesión en local y Render con
  hashes `pbkdf2_sha256` (longitud 118). La base quedó sin ventas de prueba:
  4 productos (stock 159), 9 mesas y 2 usuarios.
- **Limitación móvil:** Pages HTTPS bloquea `http://IP_LAN:8000` por Mixed
  Content; el permiso LNA solo habilita `localhost` en el navegador de prueba.
  Para el celular en la misma WiFi se abre `http://IP_LAN:8000`; si se usa
  Pages, el tráfico va a Render. No hay túnel HTTPS porque la cuenta Cloudflare
  no tiene zonas/dominio propio (solo `pages.dev`).
- **Corrección de Reportes:** `isoAhora()` en `ReportesPage.tsx` ahora incluye
  milisegundos. Antes truncaba a segundos y una venta cobrada en el mismo
  segundo en que se cargaba la página podía quedar fuera del rango
  `desde`/`hasta` (los KPIs mostraban `$0` aunque el historial y el turno sí
  reflejaban la venta).
- **Alternativas descartadas:** Northflank Sandbox exige tarjeta para
  verificar identidad; Hugging Face Docker Spaces responde `402` y requiere
  PRO; Cloud Run y Oracle Always Free también piden tarjeta.

## 4. Pendientes por corregir / completar

1. **Recompilar el APK**: el `.exe` ya incluye los últimos ajustes, pero el APK
   de Android debe regenerarse para incorporarlos.
2. **Script de instalación para Windows:** `scripts/start.bat` menciona
   `scripts/install.bat`, pero ese archivo no existe; crear el `.bat` o corregir
   el mensaje.
3. **`start_dev.sh`:** crea/activa el entorno virtual en la raíz pero luego
   espera `backend/venv`; unificar la ruta.
4. **Pruebas automatizadas:** agregar pruebas de backend/frontend y validar la
   migración de etiquetas históricas sobre una base de datos antigua.
5. **Nota de desarrollo:** si `npm run build` reporta un error de sintaxis
   inexistente en `HistorialPage.tsx`, borrar `frontend/node_modules/.cache` y
   volver a compilar.
6. **Despliegue público e híbrido:** completado el 30/10/2026 y actualizado el
   03/11/2026 con Neon + Render Free + Cloudflare Pages. La versión 1.2.1
   elimina cualquier posibilidad de forzar un endpoint temporal (ngrok), abre
   Pages en una ventana nueva y muestra solo la versión en el login. Queda
   opcional eliminar el servicio Render antiguo `Inventario-pos` cuando se
   confirme el nuevo. No se envía ping a Render: la operación interna usa el
   `.exe`.
7. **Celular en la misma WiFi:** definir si se acepta Render en el celular o se
   monta un túnel HTTPS con dominio propio para que Pages alcance el backend
   local. Sin túnel, la única vía local es abrir `http://IP_LAN:8000`.
8. **Autoarranque del backend:** el `.exe` no se registra como servicio; si se
   requiere que siga activo tras reiniciar Windows, crear una tarea programada.
9. **Decisión pendiente:** el `.exe` conserva el frontend empaquetado como
   respaldo para `http://IP_LAN:8000`; si no se usará, se puede retirar del
   build y reducir el tamaño del archivo.

## 5. Reglas de trabajo

- Resolver una tarea a la vez.
- Evitar reescrituras completas de código; usar cambios puntuales.
- No analizar carpetas de dependencias (`node_modules`, `venv`), builds ni
  binarios.
- Mantener los cambios sin commitear hasta que el usuario lo solicite.
