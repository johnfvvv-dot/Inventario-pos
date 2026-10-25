"""Utilidades centrales para fechas y horas del sistema.

La aplicación guarda y muestra la hora local del equipo donde corre el
servidor. Los valores se almacenan como datetime "naive" (sin zona horaria)
para que lo que se ve en pantalla coincida con el reloj del dispositivo.

Regla: no usar datetime.utcnow() para registrar pedidos, divisiones, turnos
ni usuarios. Usar siempre ahora_local().
"""

from datetime import datetime, timezone


def ahora_local() -> datetime:
    """Hora actual del reloj local del servidor (sin zona horaria)."""
    return datetime.now().replace(tzinfo=None)


def utc_a_local(valor: datetime | None) -> datetime | None:
    """Convierte una marca UTC antigua a la hora local del equipo.

    Las versiones anteriores guardaban datetime.utcnow() (UTC naive). Esta
    función interpreta ese valor como UTC y lo lleva a la zona horaria local.
    Si el valor ya tiene zona horaria, respeta su instante original.
    """
    if valor is None:
        return None
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=timezone.utc)
    return valor.astimezone().replace(tzinfo=None)
