# Inventario POS - Ficha de Contexto

**Versión actual:** 1.6.3

**Última actualización:** 23/11/2026

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
  responde usa Render. El login solo muestra `Inventario POS v1.6.3`; no hay
  botón de conexión ni estado del servidor. El fallback seguro solo reintenta
  `GET`, `HEAD` y login.
- **1.2.2 (05/11/2026):** tipografía uniforme en el modal de apertura, máscara de miles sin decimales para el Fondo Inicial de Caja e impresión de todos los tickets del turno con salto de página.
- **1.3.0 (10/11/2026):** asignación de pedidos nuevos a alias activos o a la
  Cuenta General; pago de divisiones materializado como pedido cerrado para
  caja, ganancia e historial; totales separados de cuenta general y divisiones;
  tickets sin duplicados y bloqueo de alias ya pagados.
- **1.4.0 (10/11/2026):** tarjetas de mesa/barra sin textos de pendientes;
  panel de Pedidos con Cuenta General y todas las divisiones/ítems; edición de
  cantidades con permiso `editar_cantidades`; creación de alias desde el panel
  y el modal de asignación; cierre independiente de Cuenta General o de cada
  alias con modal de pago; auditoría en `pedidos.usuario_cierre_id` y columna
  "Cobrado por" en Historial.
- **1.5.0 (11/2026):** ventas **Para llevar** con cobro inmediato y pago
  simple/mixto, clientes individuales con cuenta propia, rediseño visual con
  tarjetas blancas y pestaña de color por módulo, y módulo de Bolirana.
- **1.6.0–1.6.2 (11/2026):** participantes de Bolirana siempre vinculados a una
  cuenta de origen (mesa, barra o cliente individual), partidas por equipos con
  validación de integrantes, varios jugadores por mesa/barra y bloqueo de
  cuentas mientras la partida está activa.
- **1.6.3 (23/11/2026):** cargos de Bolirana unificados y tickets consolidados
  por cuenta; títulos compactos (`Bolirana #N · Jugador (Equipo)`), fracciones
  cortas (`½`, `1/3`, `2/3`), agrupación de perdedores de una misma cuenta y
  supresión del prefijo `1 ×` en cargos de Cuenta, Tickets e Historial.
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

### Módulos, colores y roles (1.6.3)

- **Estética:** fondo claro, tarjetas blancas con borde superior de color por
  módulo (`panel-acento`) y menú lateral con el mismo acento pastel en el ítem
  activo. No se usan degradados ni tarjetas oscuras.
- **Colores de referencia:** Inventario `emerald-500` (`#10b981`), Mesas
  `cyan-500` (`#06b6d4`), Pedidos `blue-500` (`#3b82f6`), Bolirana
  `orange-500` (`#f97316`), Reportes `indigo-500` (`#6366f1`), Corte de caja
  `amber-500` (`#f59e0b`), Historial `violet-500` (`#8b5cf6`),
  Personalización `pink-500` (`#ec4899`) y Usuarios `sky-600` (`#0284c7`).
- **Administrador:** accede a todos los módulos, configura el interruptor de
  Bolirana, crea/edita usuarios, asigna permisos por Bartender y administra
  inventario, precios, personalización y reportes. Puede abrir `/admin`.
- **Bartender:** trabaja en `/bartender` con Inventario (solo lectura salvo
  `ingreso_stock`), Mesas, Pedidos, Bolirana (si está habilitado) y Corte de
  caja. No ve Reportes, Historial, Personalización ni Usuarios. Puede editar
  cantidades solo con `editar_cantidades = 1`.
- **Permisos por usuario:** `ingreso_stock` y `editar_cantidades` viven en la
  tabla `usuarios`, se administran desde **Usuarios → Usuarios registrados** y
  el Bartender los refresca cada 5 s. El Administrador siempre los tiene
  activos.

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

### Para llevar y clientes individuales (1.5.0)

- **Para llevar:** se elige como destino en **Pedidos**, no ocupa mesa ni
  bloquea plazas. El cobro es inmediato desde `CobroParaLlevarModal`, admite
  efectivo, tarjeta, transferencia o pago mixto y descuenta el stock al
  confirmar. El cliente es opcional; si se escribe un nombre, aparece en el
  ticket y en el Historial. El pedido se guarda con
  `mesa_etiqueta_historica = "Para llevar"` y sin `mesa_id`.
- **Clientes individuales:** se crean desde **Mesas → Crear cliente
  individual** y reciben una tarjeta propia con tipo `individual`. Tienen cuenta
  general, divisiones, pedidos, cobro total, transferencia y participación en
  Bolirana como cualquier cuenta. El nombre es único entre clientes
  individuales.
- Al quedar saldado, el cliente individual se archiva: la fila de `Mesa`
  conserva `estado = "cerrada"` para que el historial y los tickets mantengan
  su origen, pero la tarjeta desaparece de la operación diaria. Los pedidos
  conservan `mesa_id` y `fecha_cierre` para consolidar su ticket.
- Un cliente individual puede tener aliases vinculados; el alias siempre
  pertenece a esa cuenta y no puede quedar como jugador libre.

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
- **Asignación por pedido (1.3.0):** ante alias activos, `AsignarPedidoModal`
  pregunta **"¿A quién deseas asignar este pedido?"** y ofrece cada alias más la
  **Cuenta General de la Mesa/Barra**. El pedido completo tiene un solo destino.
  - Alias: `POST /api/pedidos/` con `participante_id`; el pedido nace
    `dividido`, se copian sus líneas a `participante_items` con `pedido_id` y
    se recalculan subtotal y división.
  - Cuenta general: pedido `abierto` con `participante_id = NULL`; no toca los
    alias.
  - Los alias con `pagado = 1` se muestran deshabilitados como **Pagado** y el
    backend responde `409` si se intenta asignarles un pedido.
  - En barras, `GET /api/pedidos/barra/{numero}` lista los pedidos de todas las
    plazas para que la pantalla muestre también los guardados en otra plaza.

### Bolirana (1.6.x)

- Módulo opcional que el **Administrador** activa/desactiva desde
  **Personalización** (`modulo_bolirana`). Cuando está activo aparece el ítem
  **Bolirana** con acento `orange-500`; el Bartender puede operar partidas pero
  no crear/eliminar boliranas ni cambiar la configuración.
- Cada **bolirana** tiene nombre visible (`Bolirana #N` se deriva del primer
  número del nombre o, si no tiene, de su id). Las partidas admiten modalidad
  **directa** o **equipos**.
- **Participantes:** solo `mesa`, `barra` o `alias`. Los aliases deben declarar
  una cuenta de origen (`origen_tipo` + `origen_mesa_id` o
  `origen_barra_numero`); no existen jugadores libres. En una misma cuenta no
  se repite el mismo alias ni se duplica la cuenta como participante directa y
  como alias.
- **Equipos:** se exigen al menos dos equipos y al menos un integrante en cada
  equipo. Los equipos perdedores se reparten el total de la ronda y luego cada
  equipo reparte entre sus integrantes, ajustando centavos para que la suma sea
  exacta.
- **Consumo:** las bebidas se cargan a la partida como pedidos
  `estado = "bolirana"`, descuentan stock una sola vez y forman
  `total_bebidas`. No se pueden cargar consumos después de finalizar.
- **Liquidación:** al finalizar se marcan los perdedores y se crea un `Pedido`
  de cargo por participante en la cuenta de su origen (mesa, barra o individual)
  con `bolirana_partida_id`, número, equipo, fracción (`num`/`den`) y bebidas.
  El cargo no crea líneas de producto ni vuelve a descontar stock: solo
  transfiere el consumo ya registrado.
- **Formato visible:** título `Bolirana #1 · Fabio (Equipo B)`; sub-línea
  `Ronda completa: ...`, `½ de: ...`, `1/3 de: ...`, `2/3 de: ...`,
  `1/4 de: ...`, etc. Las bebidas se separan con ` · `.
- **Agrupación:** los cargos de una misma partida y cuenta se muestran como una
  sola fila, sumando montos y fracciones: `Bolirana #1 · Fabio y Camilo
  (Equipo B)` con `2/3 de: ...` o `Ronda completa: ...`. Si los cargos no
  tienen metadatos (histórico antiguo), se conserva el texto original.
- **Candados:** mientras la cuenta tenga una partida activa no se puede cobrar,
  cerrar, dividir, transferir ni liberar; el corte de caja tampoco puede cerrar
  con partidas activas o cargos pendientes. Al finalizar, la cuenta se libera
  para cobro normal.
- Se conservan los endpoints legacy `/api/boliranas/cargos-pendientes` y
  `/api/boliranas/cargos/{id}/pagar` para compatibilidad, aunque la interfaz
  actual ya no los usa: los cargos se cobran dentro de la cuenta de origen.

### Cuentas, caja y reportes

- División de cuenta por alias, cobro individual, transferencia entre mesas y
  plazas de barra, cierre con o sin liberación y corte de caja por turno.
- **Pagos de divisiones (1.3.0):** al cobrar un alias,
  `registrar_pago_participante()` crea un `Pedido` cerrado con
  `es_pago_division = 1`, `participante_id` y la forma de pago. Ese pedido es la
  fuente para el corte de caja, la ganancia y el historial. El ticket del alias
  sigue saliendo de `participante_items`, y la generación de tickets excluye el
  pedido financiero para no duplicarlo.
- **Cierres independientes (1.4.0):** `POST /api/cuentas/mesa/{id}/cerrar-general`
  y `POST /api/cuentas/barra/{n}/cerrar-general` cobran solo los pedidos
  generales (`participante_id IS NULL`). Si quedan divisiones pendientes, la
  mesa/barra sigue ocupada. `POST /api/cuentas/participante/{id}/pagar` cobra
  solo el alias seleccionado y registra el pago con forma de pago, fecha/hora y
  `usuario_cierre_id`. El cierre completo sigue disponible como "Cobrar cuenta
  total" (con opción de liberar la mesa o barra).
- **Edición de pedidos (1.4.0):** `PUT /api/pedidos/{id}/items/{item_id}` y
  `PUT /api/cuentas/participante-item/{item_id}` ajustan la línea; cantidad `0`
  la elimina y devuelve el stock. El Administrador siempre puede; el Bartender
  requiere `usuarios.editar_cantidades = 1`. Sin permiso el backend responde
  `403` y el frontend muestra solo lectura.
- **Creación de alias (1.4.0):** se crea desde **Pedido actual** enviando
  `nuevo_alias` en `POST /api/pedidos/`, que reutiliza
  `obtener_o_crear_division_pendiente()` y `crear_participante()` y asigna el
  pedido al alias en la misma transacción. El alias se agrega a la división
  pendiente más reciente de la cuenta o se crea una nueva. `POST
  /api/cuentas/alias` queda como soporte interno, sin botón en la interfaz.
- **Auditoría (1.4.0):** `pedidos.usuario_cierre_id` guarda el usuario que
  cobró (sin ForeignKey para evitar relaciones ambiguas con `Usuario.pedidos`).
  El Historial muestra `usuario_cierre_nombre` en la columna "Cobrado por".
- **Tarjetas de mesa/barra (1.4.0):** `MesaListadoOut.detalle_pendiente` queda
  vacío; ya no se muestran "N pedidos abiertos" ni "N clientes pendientes". Se
  conservan estado, `total_cuenta` y botones.
- Un pago ya realizado no se sobrescribe al cerrar la cuenta: se conservan su
  forma de pago y su fecha. Los alias pendientes se cobran con la forma elegida.
- `CuentaMesaOut` incluye `total_general` y `total_divisiones`; el total
  pendiente es la suma de pedidos abiertos más partes impagas. Las tarjetas de
  mesa/barra usan la misma regla y muestran solo el valor pendiente.
- Transferencia: además de los pedidos generales y las divisiones pendientes, se
  mueven los pedidos `dividido` asignados a sus alias; los pedidos financieros
  cerrados no se mueven.
- No se hace backfill de pagos de divisiones anteriores a 1.3.0. Un rescate
  histórico requeriría autorización y respaldo previo.
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

### Personalización y tickets internos (1.6.3)

- **Personalización:** nuevo ítem del menú del Administrador en
  `/admin/personalizacion`. Cambia el nombre visible de la cabecera, agrega un
  logotipo cuadrado de 256×256 (data URL PNG/JPEG/WebP) y controla el
  interruptor del módulo **Bolirana**. El nombre oficial del sistema sigue
  siendo **Inventario POS** y el login conserva `Inventario POS v1.6.3`.
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
- **Consolidación por cuenta (1.6.3):** todos los pedidos de una misma cuenta
  cobrados en el mismo `fecha_cierre` generan **un solo ticket**. Los productos
  se agrupan por nombre y precio; los cargos de Bolirana se agrupan por
  `bolirana_partida_id` y se imprimen con su título/fracción combinada. El
  ticket muestra un único total y una única forma de pago (o el desglose
  `Mixto: ...`). Los clientes individuales conservan además su ticket
  `individual-...` con nombre y origen **Individual**.
- Cada comprobante incluye nombre del negocio, folio, mesa/barra, alias del
  cliente, fecha de ocupación, fecha de pago, líneas y forma de pago. Los
  cargos llevan `es_cargo = true` para no mostrar `1 ×`; los productos sí
  muestran cantidad y precio unitario. No se guardan en la base.
- Los pedidos históricos sin mesa y los cargos legacy sin metadatos conservan
  su ticket individual y su texto anterior como respaldo.
- Marcas temporales nuevas: `Mesa.fecha_ocupacion`, `Pedido.fecha_ocupacion`,
  `Division.fecha_ocupacion` y `Participante.fecha_pago`. `Pedido.fecha_cierre`
  sigue siendo la fecha de pago de los pedidos completos.
- Descarga: **Imprimir / PDF** usa la impresión del navegador con estilos
  `@media print`; cada tarjeta tiene **Descargar imagen**, que genera un PNG
  local con canvas (`utils/ticketImagen.ts`). Al cerrar el modal desaparecen.
- **Historial:** una fila por pedido/cargo para que el cuadre de caja siga
  siendo verificable. Los títulos de Bolirana son cortos (`Bolirana #N · ...`),
  el detalle muestra la fracción y las bebidas, y el CSV usa los mismos textos
  sin prefijo `1 ×` en cargos.

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
- **Validación 1.6.3 (23/11/2026):** 27/27 pruebas de integración del backend,
  `npx tsc --noEmit` y build de producción del frontend sin errores. Se
  mantiene la validación histórica del modo híbrido (local, Pages→local y
  Pages→Render). La base de producción conserva solo los datos reales; las
  pruebas usan SQLite temporal.
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
4. **Pruebas automatizadas:** la suite de integración cubre 27 pruebas
   (Bolirana, cuentas divididas y clientes individuales) en
   `backend/tests/`; falta ampliar la cobertura de frontend y validar la
   migración de etiquetas históricas sobre una base de datos antigua.
5. **Nota de desarrollo:** si `npm run build` reporta un error de sintaxis
   inexistente en `HistorialPage.tsx`, borrar `frontend/node_modules/.cache` y
   volver a compilar.
6. **Despliegue público e híbrido:** completado el 30/10/2026 y actualizado el
   23/11/2026 con Neon + Render Free + Cloudflare Pages. La versión 1.6.3
   consolida los tickets por cuenta, unifica los cargos de Bolirana y mantiene
   el panel de Cuenta General/divisiones, la edición de cantidades con permiso,
   la creación de alias y los cierres independientes con auditoría. Queda
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

### Reglas de protección del negocio

- **Una sola fuente de verdad:** el stock se descuenta al registrar la venta
  (`PedidoItem` + movimiento de inventario). Los cargos de Bolirana solo
  transfieren un consumo ya registrado; nunca vuelven a descontar stock ni
  crean una segunda venta.
- **Caja e historial cuadran:** los pedidos cerrados y los pagos de divisiones
  son la fuente de los ingresos. Un cargo de Bolirana se suma una sola vez al
  total de la cuenta y no se duplica como venta independiente.
- **Cuentas históricas protegidas:** no se edita ni elimina un pedido cerrado
  desde la operación normal; los reportes, tickets y el historial conservan sus
  etiquetas históricas (`mesa_etiqueta_historica`, `mesa_numero_historico`) aunque
  la mesa, barra o cliente se elimine después.
- **Sin jugadores libres:** todo participante de Bolirana debe provenir de una
  mesa, barra o cliente individual. Los aliases siempre tienen cuenta de origen
  y no se pueden cobrar por fuera de ella.
- **Sin cambios durante partidas activas:** una cuenta bloqueada por Bolirana
  no se cobra, divide, transfiere ni libera; el turno tampoco cierra con
  partidas activas o cargos pendientes.
- **Cargos trazables:** cada cargo guarda `bolirana_partida_id`, número de
  máquina, equipo, fracción y bebidas. Si faltan metadatos (datos antiguos), se
  usa el texto legacy como respaldo, sin romper el cuadre.
- **Antes de desplegar:** ejecutar las 27 pruebas del backend, `npx tsc --noEmit`
  y el build de producción. No publicar con pruebas rojas ni con cálculos de
  totales modificados sobre datos reales.
