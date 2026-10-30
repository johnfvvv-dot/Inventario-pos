"""Utilidades centrales para fechas y horas del sistema.

La aplicación guarda y muestra la hora local del negocio. Los valores se
almacenan como datetime "naive" (sin zona horaria) para que lo que se ve en
pantalla coincida con el reloj del dispositivo.

La zona horaria se toma de ``APP_TIMEZONE`` (por defecto
``America/Bogota``). Así el servidor en la nube no depende de la zona del
sistema operativo y el contenedor puede seguir usando ``TZ`` para otras
herramientas.

Regla: no usar datetime.utcnow() para registrar pedidos, divisiones, turnos
ni usuarios. Usar siempre ahora_local().
"""

import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def _cargar_zona() -> ZoneInfo | None:
    nombre = os.getenv("APP_TIMEZONE", "America/Bogota").strip()
    if not nombre:
        return None
    try:
        return ZoneInfo(nombre)
    except ZoneInfoNotFoundError:
        return None


_ZONA = _cargar_zona()


def ahora_local() -> datetime:
    """Hora actual en la zona del negocio (sin zona horaria)."""
    if _ZONA is not None:
        return datetime.now(_ZONA).replace(tzinfo=None)
    return datetime.now().replace(tzinfo=None)


def utc_a_local(valor: datetime | None) -> datetime | None:
    """Convierte una marca UTC antigua a la hora local del negocio.

    Las versiones anteriores guardaban datetime.utcnow() (UTC naive). Esta
    función interpreta ese valor como UTC y lo lleva a la zona configurada.
    Si el valor ya tiene zona horaria, respeta su instante original.
    """
    if valor is None:
        return None
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=timezone.utc)
    if _ZONA is not None:
        return valor.astimezone(_ZONA).replace(tzinfo=None)
    return valor.astimezone().replace(tzinfo=None)
