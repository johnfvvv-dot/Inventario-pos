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
- **Autenticación:** alias + clave con hash SHA-256. El usuario se guarda en
  `localStorage`; no se usa JWT. Roles: `admin` y `bartender`.
- **API:** prefijo `/api`; documentación interactiva en `/docs`; salud en
  `/health`; configuración de red en `/api/config`.
- **Empaquetado:** PyInstaller (`dist/InventarioPOS.exe`) y Capacitor
  (`frontend/android/`).

## 3. Estado actual y ajustes recientes

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
- Se agregó la columna **"Ingreso de stock"**: campo numérico + botón verde
  **"Agregar"** que **suma** la cantidad al stock existente
  (ej. 50 + 10 = 60). También se confirma con Enter.
- Se conservan los botones **"−"** y **"+"** para ajustes incrementales.
- El campo solo acepta dígitos y valida cantidades mayores a cero.
- El rol `bartender` mantiene el inventario en modo solo lectura.

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
- La transferencia valida que el destino esté libre y no ofrece barras ocupadas
  como destino.
- Reportes con KPIs, gráficos y exportación CSV; historial con filtros por
  fecha, mesa/barra, producto y forma de pago.
- Migraciones ligeras al iniciar: columnas faltantes, alias de usuarios y
  etiquetas históricas.

## 4. Pendientes por corregir / completar

1. **Recompilar `dist/InventarioPOS.exe`**: el binario actual es anterior a los
   últimos ajustes de barras, inventario y pedidos. Regenerar también el APK.
2. **Ingreso de stock atómico:** hoy el frontend envía `stock_actual + cantidad`
   al endpoint `PUT /api/inventario/{id}/stock`. Conviene un endpoint de
   incremento en el backend para evitar condiciones de carrera con varios
   usuarios.
3. **Script de instalación para Windows:** `scripts/start.bat` menciona
   `scripts/install.bat`, pero ese archivo no existe; crear el `.bat` o corregir
   el mensaje.
4. **`start_dev.sh`:** crea/activa el entorno virtual en la raíz pero luego
   espera `backend/venv`; unificar la ruta.
5. **Pruebas automatizadas:** agregar pruebas de backend/frontend y validar la
   migración de etiquetas históricas sobre una base de datos antigua.
6. **Nota de desarrollo:** si `npm run build` reporta un error de sintaxis
   inexistente en `HistorialPage.tsx`, borrar `frontend/node_modules/.cache` y
   volver a compilar.

## 5. Reglas de trabajo

- Resolver una tarea a la vez.
- Evitar reescrituras completas de código; usar cambios puntuales.
- No analizar carpetas de dependencias (`node_modules`, `venv`), builds ni
  binarios.
- Mantener los cambios sin commitear hasta que el usuario lo solicite.
