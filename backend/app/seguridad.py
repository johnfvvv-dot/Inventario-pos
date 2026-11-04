"""Hash y verificacion de claves de usuario.

Formato nuevo (PBKDF2-HMAC-SHA256 con sal):
    pbkdf2_sha256$iteraciones$sal_hex$hash_hex

Por compatibilidad se aceptan los hashes SHA-256 sin sal de versiones
anteriores. Al iniciar sesion con uno de ellos se reemplaza automaticamente
por el formato nuevo.
"""

import hashlib
import hmac
import secrets

ALGORITMO = "pbkdf2_sha256"
ITERACIONES = 260_000


def hash_password(password: str) -> str:
    """Genera un hash PBKDF2 con una sal aleatoria nueva."""
    sal = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(sal),
        ITERACIONES,
    )
    return f"{ALGORITMO}${ITERACIONES}${sal}${digest.hex()}"


def verificar_password(password: str, almacenado: str) -> bool:
    """Compara una clave con el hash guardado (nuevo o SHA-256 legado)."""
    if not almacenado:
        return False

    if almacenado.startswith(f"{ALGORITMO}$"):
        try:
            _, iteraciones, sal, esperado = almacenado.split("$", 3)
            digest = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                bytes.fromhex(sal),
                int(iteraciones),
            )
            return hmac.compare_digest(digest.hex(), esperado)
        except (ValueError, TypeError):
            return False

    # Compatibilidad con el esquema anterior (SHA-256 sin sal).
    legado = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(legado, almacenado)


def necesita_rehash(almacenado: str) -> bool:
    """True si el hash es legado y conviene actualizarlo al iniciar sesion."""
    return not (almacenado or "").startswith(f"{ALGORITMO}$")
