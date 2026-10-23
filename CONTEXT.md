# Inventario POS - Ficha de Contexto

## 1. Stack y Arquitectura
- Backend: Python (FastAPI/Flask) en `./backend/app/` (`main.py`, `models.py`, `routes/`).
- Frontend: Interfaz en `./frontend/`.
- Build: PyInstaller (`dist/InventarioPOS.exe`).

## 2. Tareas Pendientes (Módulo Mesas y Barras)
1. **Transferencia de cuentas:** Permitir transferir cuentas abiertas bidireccionalmente (barra <-> mesa).
2. **Menú de pedidos:** Añadir filtro visual de barras disponibles (replicar comportamiento de mesas).
3. **Eliminación de barras:** Permitir eliminar la barra completa en bloque, no plaza por plaza.
4. **Cierre de cuenta en barra:** 
   - Cambiar etiqueta del botón en ventana de cuenta a "Liberar barra".
   - Corregir bug: al liberar, la barra sigue figurando como ocupada en el menú principal (sincronizar backend/frontend).

## 3. Reglas de Trabajo
- Resolver una tarea a la vez para cuidar tokens.
- No reescribir archivos completos; devolver solo bloques modificados o diffs.
- No analizar carpetas de dependencias, builds ni binarios.
