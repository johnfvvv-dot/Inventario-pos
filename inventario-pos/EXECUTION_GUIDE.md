# Guía de Ejecución Local - Inventario POS

**Versión:** 1.6.3 · **Última actualización:** 23/11/2026

## Requisitos Previos para tu PC

### 1. Instalar Python 3.11+
- Descargar e instalar desde: https://www.python.org/downloads/
- **Importante**: Marcar la opción "Add Python to PATH" durante la instalación

### 2. Instalar Node.js y npm
- Descargar e instalar desde: https://nodejs.org/
- Versión recomendada: v20.x o superior

### 3. Instalar Git
- Descargar e instalar desde: https://git-scm.com/
- O usar el instalador de Windows

### 4. Instalar pip (gestor de paquetes Python)
Si no viene incluido con Python:
- Ejecutar: `python -m ensurepip --upgrade`
- O descargar get-pip.py desde: https://bootstrap.pypa.io/get-pip.py

### 5. Instalar python-venv (entorno virtual)
- Debian/Ubuntu: `sudo apt-get install python3-venv`
- Windows: Viene incluido con Python
- macOS: `python3 -m venv venv`

---

## Paso a Paso: Instalación y Ejecución

### Opción A: Instalación Completa (Recomendada)

#### 1. Clonar el repositorio
```bash
git clone https://github.com/TU_USUARIO/inventario-pos.git
cd inventario-pos
```

#### 2. Configurar Backend (Python/FastAPI)
```bash
# Entrar al directorio backend
cd backend

# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Iniciar el servidor FastAPI
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### 3. Configurar Frontend (React + TypeScript)
```bash
# Regresar a la carpeta principal
cd ..

# Entrar al directorio frontend
cd frontend

# Instalar dependencias
npm install

# Iniciar la aplicación React
npm start
```

#### 4. Acceder a la aplicación
- **Backend API**: http://localhost:8000
- **Documentación API (Swagger)**: http://localhost:8000/docs
- **Frontend**: http://localhost:3000
- **Login**: Usa cualquier correo y "admin123" como contraseña (o regístrate nuevo)

---

### Opción B: Usando el Script Incluido

El proyecto incluye scripts de ayuda:

```bash
# Script para Linux/Mac/WSL
chmod +x scripts/install.sh
bash scripts/install.sh

# Script para iniciar
bash scripts/start.sh
```

O en Windows:
```cmd
scripts\install.bat
scripts\start.bat
```

---

## Estructura de Carpetas

```
inventario-pos/
├── backend/              # Servidor FastAPI
│   ├── app/
│   │   ├── main.py       # Punto de entrada
│   │   ├── routes/       # Endpoints API
│   │   ├── models.py     # Modelos SQLAlchemy
│   │   ├── schemas.py    # Validaciones Pydantic
│   │   └── database.py   # Conexión BD
│   └── requirements.txt  # Dependencias Python
├── frontend/             # Aplicación React
│   ├── src/
│   │   ├── components/   # Componentes UI
│   │   ├── pages/        # Pantallas
│   │   ├── services/     # Conexión API
│   │   ├── App.tsx       # Enrutamiento
│   │   └── App.css       # Estilos
│   ├── package.json      # Dependencias Node
│   └── tsconfig.json     # Configuración TypeScript
├── scripts/              # Scripts de ayuda
│   ├── install.sh        # Instalación Linux/Mac/WSL
│   ├── start.sh          # Ejecución Linux/Mac/WSL
│   └── start.bat         # Ejecución Windows
├── .gitignore            # Archivos a excluir del versionado
├── README.md             # Documentación general
└── EXECUTION_GUIDE.md    # Esta guía
```

---

## Configuración de Base de Datos

### SQLite (Local - Recomendado para inicio)
- **Archivo**: `backend/inventario.db` (se crea automáticamente)
- **URL por defecto**: `sqlite:///./inventario.db`
- **Ventajas**: No requiere servidor, archivo único, compatible con Python
- **Desventajas**: Menor concurrencia, no ideal para múltiples usuarios simultáneos

### PostgreSQL (Para escalar a la nube)
- **URL de ejemplo**: `postgresql://usuario:password@localhost/inventario`
- **Ventajas**: Profesional, multi-usuario, compatible con Render/Fly.io/Heroku
- **Configuración**: Modificar `SQLALCHEMY_DATABASE_URL` en `backend/app/database.py`

### Migración de SQLite a PostgreSQL
```bash
# Exportar desde SQLite
sqlite3 inventario.db .dump > backup.sql

# Importar a PostgreSQL
psql -U usuario -d inventario -f backup.sql
```

---

## Acceso desde Dispositivos Móviles (Misma Red WiFi)

Para que otros dispositivos en tu red local puedan acceder:

1. **Encontrar la IP de tu PC**:
   - Windows: `ipconfig` -> buscar "Dirección IPv4"
   - Linux/macOS: `ifconfig` o `ip a`

2. **Usar la IP en lugar de localhost**:
   - Backend: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
   - Acceder desde celular: `http://192.168.1.XX:8000`
   - O desde el frontend: `http://192.168.1.XX:3000`

3. **Puntos de acceso**:
   - API: `http://192.168.1.XX:8000/api/...`
   - Docs: `http://192.168.1.XX:8000/docs`
   - Frontend: `http://192.168.1.XX:3000`

---

## Usuarios por Defecto

Al ejecutar por primera vez, el sistema crea un usuario administrador:

- **Usuario:** `Admin`
- **Clave inicial:** `1234` (cámbiala al empezar a operar)
- **Rol:** `admin`

Desde **Usuarios → Usuarios registrados** el Administrador crea Bartenders con
alias, rol y clave inicial `1234`, y habilita por usuario:

- **Ingreso de Stock:** muestra al Bartender la columna para sumar stock.
- **Edición de pedidos:** permite cambiar cantidades con los botones `− / +`.
- **Bolirana:** el interruptor global se controla desde Personalización; el
  Bartender solo opera partidas cuando está activo.

Otros roles:

- **`admin`:** acceso total, reportes, historial, personalización y usuarios.
- **`bartender`:** inventario en solo lectura, mesas/barras, pedidos, clientes
  individuales, Para llevar, Bolirana (si está activa) y corte de caja.

No se usan correos ni tokens JWT: el login valida el campo `usuario` y el
control de rutas se aplica en el cliente (`/admin` y `/bartender`).

---

## Escalado a la Nube

### Paso 1: Cambiar a PostgreSQL
1. Crear base de datos en Supabase, ElephantSQL o AWS RDS
2. Modificar `backend/app/database.py`:
   ```python
   SQLALCHEMY_DATABASE_URL = "postgresql://usuario:password@host/puerto/base_datos"
   ```

### Paso 2: Desplegar Backend
- **Render.com**: Subir repositorio GitHub, setear variables de entorno
- **Railway.app**: Conectar repositorio, desplegar automáticamente
- **Fly.io**: `fly launch` y `fly deploy`

### Paso 3: Desplegar Frontend
- **Vercel**: `vercel` desde la carpeta frontend
- **Netlify**: Arrastar carpeta `build` o conectar repositorio
- **GitHub Pages**: Configurar en package.json scripts

### Paso 4: Variables de Entorno Necesarias
```
DATABASE_URL=postgresql://...
PORT=8000 (o el puerto que el provider indique)
NODE_ENV=production
```

---

## Solución de Problemas Comunes

### Error: "ModuleNotFoundError: No module named 'fastapi'"
**Solución**: `pip install fastapi uvicorn`

### Error: "ModuleNotFoundError: No module named 'sqlalchemy'"
**Solución**: `pip install sqlalchemy`

### Error: "Address already in use" (puerto 8000 o 3000)
**Solución**:
- Detener cualquier proceso anterior que use esos puertos
- Cambiar los puertos en los scripts: `--port 8001` o `--port 3001`
- Usar `lsof -i :8000` para encontrar y matar el proceso

### Error: "CORS policy blocks the request" en el navegador
**Solución**: El backend FastAPI ya tiene configuración CORS básica. Si es necesario, instalar:
`pip install fastapi-cors` o agregar middleware CORS en main.py

### Error: No se pueden conectar desde el celular
**Solución**:
- Verificar que el firewall de Windows/macOS permita los puertos 8000 y 3000
- Asegurarse de que tanto PC como celular estén en la misma red WiFi (no solo misma casa)
- Probar con `http://IP_DE_PC:8000` en el navegador del celular primero

---

## Comandos Útiles

### Ver procesos en puerto
```bash
# Linux/Mac
lsof -i :8000
# Windows
netstat -ano | findstr :8000
```

### Detener procesos
```bash
# Linux/Mac: Ctrl+C en la terminal donde está corriendo
# Windows: Cerrar la terminal o usar Task Manager
```

### Reiniciar la aplicación
```bash
# Detener (Ctrl+C) y volver a ejecutar:
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Backup y Recuperación

### Backup de la base de datos SQLite
```bash
# El archivo es inventario.db en la carpeta backend/
cp backend/inventario.db ~/backup/inventario_fecha.db
```

### Recuperar después
 simplemente copiar el archivo de regreso a `backend/inventario.db` y reiniciar la aplicación.

---

## Módulos, colores y flujos principales

La interfaz usa tarjetas blancas con pestaña de color por módulo. El menú
lateral repite el acento pastel del módulo activo:

| Módulo | Color | Contenido |
|---|---|---|
| Inventario | `emerald-500` | Productos, categorías y stock |
| Mesas | `cyan-500` | Mesas, barras y clientes individuales |
| Pedidos | `blue-500` | Carrito, Para llevar y cobro |
| Bolirana | `orange-500` | Partidas, equipos, bebidas y cargos |
| Reportes | `indigo-500` | KPIs, gráficos y CSV |
| Corte de caja | `amber-500` | Turnos, tickets y cierre |
| Historial | `violet-500` | Ventas y exportación |
| Personalización | `pink-500` | Nombre, logo e interruptor de Bolirana |
| Usuarios | `sky-600` | Roles y permisos por usuario |

Flujos que conviene probar después de instalar:

1. **Mesa/barra:** crear, ocupar, pedido, cuenta, dividir, transferir y cobrar.
2. **Para llevar:** elegir el destino, agregar productos, cobrar con pago simple
   o mixto y verificar que no se ocupa ninguna mesa.
3. **Cliente individual:** crearlo en Mesas, agregar pedidos, cobrar y confirmar
   que la tarjeta se archiva sin perder historial ni ticket.
4. **Bolirana:** activar el módulo en Personalización, crear una bolirana,
   iniciar una partida con cuentas de origen, cargar bebidas, finalizar con
   perdedores y comprobar el cargo agrupado en Cuenta y Tickets.
5. **Caja:** abrir turno, cobrar, revisar tickets consolidados y cerrar el turno.

## Reglas de protección

- El stock se descuenta una sola vez por venta. Los cargos de Bolirana no
  vuelven a descontar stock ni crean una segunda venta.
- Los pedidos cerrados no se editan ni eliminan desde la operación normal; sus
  etiquetas históricas se conservan aunque la mesa/barra se elimine.
- Todo participante de Bolirana proviene de una mesa, barra o cliente
  individual; no se permiten jugadores libres.
- Una cuenta en partida activa no se cobra, divide, transfiere ni libera, y el
  turno no cierra con partidas activas o cargos pendientes.
- Antes de publicar: 27 pruebas de backend, `npx tsc --noEmit` y build de
  producción sin errores.

---

## Características del Sistema

✅ **Multi-usuario**: Roles `admin` y `bartender` con permisos por usuario
✅ **Inventario**: Registro de entrada y salida automática
✅ **Gestión de mesas**: Asignar pedidos, consumo por mesa, dividir cuentas
✅ **Para llevar**: Venta de mostrador con pago simple o mixto
✅ **Clientes individuales**: Cuenta propia y archivo automático al saldar
✅ **Bolirana**: Partidas, equipos, bebidas y cargos por cuenta
✅ **Reportes**: Ventas e inventario con KPIs
✅ **Tickets consolidados**: Un comprobante por cuenta cobrada
✅ **Responsive**: Funciona en PC, tablet y smartphone
✅ **Local-first**: Sin costos de servidor iniciales
✅ **Escalable**: Migración a PostgreSQL y hosting en la nube
✅ **Versionado**: Git con ramas main, dev, feature/*