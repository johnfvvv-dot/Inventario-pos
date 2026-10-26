# Inventario POS - Ficha de Contexto

**Versión actual:** 1.1.0

**Última actualización:** 23/10/2026

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
- **Base de datos:** SQLite por defecto.
  - Desarrollo: `backend/data/inventario.db`.
  - Ejecutable: `%LOCALAPPDATA%\InventarioPOS\inventario.db`.
  - Nube: PostgreSQL definiendo `DATABASE_URL`.
- **Frontend:** React 18 + TypeScript (Create React App), React Router y Chart.js.
  Código en `frontend/src/`.
- **Autenticación:** usuario + clave con hash SHA-256. El login valida el campo
  `usuario`; el usuario autenticado se guarda en `localStorage`; no se usa JWT.
  Roles: `admin` y `bartender`. Las rutas `/admin` y `/bartender` están
  protegidas en el cliente (`RutaAdmin`/`RutaBartender` en `App.tsx`); la API
  no valida roles ni usa tokens.
- **API:** prefijo `/api`; documentación interactiva en `/docs`; salud en
  `/health`; configuración de red en `/api/config`.
- **Empaquetado:** PyInstaller (`dist/InventarioPOS.exe`) y Capacitor
  (`frontend/android/`).

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

## 5. Reglas de trabajo

- Resolver una tarea a la vez.
- Evitar reescrituras completas de código; usar cambios puntuales.
- No analizar carpetas de dependencias (`node_modules`, `venv`), builds ni
  binarios.
- Mantener los cambios sin commitear hasta que el usuario lo solicite.
