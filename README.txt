INVENTARIO POS
==============

Sistema de inventario y punto de venta para pequeños negocios (bares,
restaurantes y cafeterías). Integra productos, mesas, barras, clientes
individuales, pedidos, ventas Para llevar, cuentas, Bolirana, caja, tickets,
reportes e historial en una sola aplicación.

Versión actual: 1.6.3


REQUISITOS
----------
- Python 3.10 o superior
- Node.js 18 o superior (incluye npm)
- Git (opcional)


INSTALACIÓN Y EJECUCIÓN
-----------------------
1) Backend (Windows PowerShell):

   cd backend
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   uvicorn app.main:app --host 0.0.0.0 --port 8000

   En Linux o macOS:

   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --host 0.0.0.0 --port 8000

2) Frontend (en otra terminal):

   cd frontend
   npm install
   npm start

   También se puede usar yarn install / yarn start.


ACCESO
------
- Aplicación:    http://localhost:3000
- API:           http://localhost:8000
- Documentación: http://localhost:8000/docs
- Salud:         http://localhost:8000/health

La base de datos se crea automáticamente:
- SQLite local: backend/data/inventario.db
- Producción:   Neon PostgreSQL (modo híbrido)


USUARIO INICIAL
---------------
Usuario: Admin
Clave:   1234

Cambia la clave desde Usuarios > Cambiar clave al empezar a usar el sistema
en producción. Los usuarios nuevos también nacen con la clave 1234.


MÓDULOS Y COLORES
-----------------
La interfaz usa tarjetas blancas con una pestaña de color por módulo:

- Inventario        emerald-500  Productos, categorías y stock.
- Mesas             cyan-500     Mesas, barras y clientes individuales.
- Pedidos           blue-500     Carrito, Para llevar y cobro.
- Bolirana          orange-500   Partidas, equipos, bebidas y cargos.
- Reportes          indigo-500   KPIs, gráficos y exportación CSV.
- Corte de caja     amber-500    Turnos, tickets y cierre.
- Historial         violet-500   Ventas y exportación CSV.
- Personalización   pink-500     Nombre, logo e interruptor de Bolirana.
- Usuarios          sky-600      Roles y permisos por usuario.


ROLES
-----
- Administrador (admin):
  Acceso total. Configura Personalización, activa Bolirana, administra
  inventario, usuarios, permisos, reportes e historial.

- Bartender:
  Inventario en solo lectura (puede ingresar stock si el Administrador le
  habilita el permiso), Mesas, Pedidos, Para llevar, clientes individuales,
  Bolirana (si está activa) y Corte de caja. No accede a Reportes, Historial,
  Personalización ni Usuarios. Puede editar cantidades solo con el permiso
  "Edición de pedidos".


FLUJOS PRINCIPALES
------------------
- Mesas y barras:
  Crear, ocupar, pedir, dividir la cuenta, transferir y cobrar. Una barra se
  muestra como "Barra N" y cada plaza conserva su cuenta.

- Para llevar:
  Venta de mostrador sin ocupar mesa. Se elige "Para llevar" en Pedidos, se
  puede asignar un nombre opcional y se cobra al instante con efectivo,
  tarjeta, transferencia o pago mixto. Aparece como "Mostrador" en el historial.

- Clientes individuales:
  Se crean desde Mesas, tienen cuenta propia y pueden participar en Bolirana.
  Al quedar saldados se archivan y desaparecen de la operación diaria, pero su
  historial y sus tickets se conservan.

- Bolirana:
  Módulo opcional. Partidas directas o por equipos entre mesas, barras y
  clientes individuales. Los aliases siempre se vinculan a una cuenta de origen;
  no existen jugadores libres. Las bebidas descuentan stock y al finalizar los
  perdedores reciben un cargo en su cuenta con número de máquina, equipo,
  fracción y bebidas. Los cargos de una misma cuenta se agrupan como
  "Bolirana #1 · Fabio y Camilo (Equipo B)" y "2/3 de: ...".

- Tickets:
  Un solo comprobante por cuenta cobrada, con productos agrupados, cargos de
  Bolirana agrupados por partida, un único total y una única forma de pago (o
  desglose mixto). Se pueden imprimir/guardar como PDF o descargar como PNG.

- Corte de caja e historial:
  Apertura/cierre de turno por forma de pago, historial de turnos, filtros por
  fecha, mesa/barra, producto y pago, y exportación CSV.


REGLAS DE PROTECCIÓN
--------------------
1. El stock se descuenta una sola vez por venta. Los cargos de Bolirana no
   vuelven a descontar stock ni crean una segunda venta.
2. Caja e historial cuadran: los tickets consolidados solo agrupan visualmente;
   no duplican ingresos ni unidades vendidas.
3. Los pedidos cerrados no se editan ni eliminan desde la operación normal. Las
   etiquetas históricas conservan "Mesa N" o "Barra N" aunque se elimine el
   lugar.
4. Todo participante de Bolirana proviene de una mesa, barra o cliente
   individual. No se permiten jugadores libres.
5. Una cuenta en partida activa no se cobra, divide, transfiere ni libera; el
   turno no cierra con partidas activas o cargos pendientes.
6. Antes de publicar: 27 pruebas de backend, npx tsc --noEmit y build de
   producción sin errores.


NOTAS
-----
- El ejecutable de Windows es dist/InventarioPOS.exe.
- Para compilar el ejecutable: scripts\build_exe.bat
- Para compilar el APK: scripts\build_apk.bat
- Para publicar el frontend: scripts\build_pages.ps1 -Deploy
- Más detalles en README.md, CONTEXT.md y EXECUTION_GUIDE.md.
