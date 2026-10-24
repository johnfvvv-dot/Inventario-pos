INVENTARIO POS
==============

Sistema de inventario y punto de venta para pequeños negocios (bares,
restaurantes y cafeterías). Permite gestionar productos, mesas, barras,
pedidos, cuentas, caja, reportes e historial desde una sola aplicación.

Versión actual: 1.1.0


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
- Aplicación:  http://localhost:3000
- API:         http://localhost:8000
- Documentación: http://localhost:8000/docs

La base de datos se crea automáticamente en backend/data/inventario.db.


USUARIO INICIAL
---------------
Alias: Admin
Clave: 1234

Cambia la clave desde Usuarios > Cambiar clave al empezar a usar el sistema
en producción.


MÓDULOS PRINCIPALES
-------------------
- Inventario: productos, categorías y stock. El stock se consulta en la
  columna Stock y se aumenta con el campo "Ingreso de stock" + botón Agregar.
- Mesas y barras: creación, ocupación, pedidos, cuentas y liberación.
- Pedidos: cantidades manuales o con el botón +, con control de stock.
- Caja: apertura y cierre de turno.
- Reportes e historial: consultas, gráficos y exportación CSV.
- Usuarios: roles administrador y bartender.


NOTAS
-----
- El ejecutable de Windows es dist/InventarioPOS.exe.
- Para compilar el ejecutable: scripts\build_exe.bat
- Para compilar el APK: scripts\build_apk.bat
- Más detalles en README.md y CONTEXT.md.
