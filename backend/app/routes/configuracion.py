"""Personalización visual del negocio: nombre y logotipo.

El nombre oficial del sistema sigue siendo "Inventario POS". Esta
configuración solo cambia lo que se muestra en la cabecera y en los tickets.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ConfiguracionNegocio
from app.schemas import ConfiguracionNegocioIn, ConfiguracionNegocioOut
from app.tiempo import ahora_local

router = APIRouter(tags=["configuracion"])

NOMBRE_POR_DEFECTO = "Inventario POS"
PREFIJOS_LOGO = (
    "data:image/png;base64,",
    "data:image/jpeg;base64,",
    "data:image/webp;base64,",
)


def _configuracion(db: Session) -> ConfiguracionNegocio | None:
    return db.query(ConfiguracionNegocio).filter(ConfiguracionNegocio.id == 1).first()


def _salida(config: ConfiguracionNegocio | None) -> ConfiguracionNegocioOut:
    if not config:
        return ConfiguracionNegocioOut(nombre_negocio=NOMBRE_POR_DEFECTO, logo=None)
    return ConfiguracionNegocioOut(
        nombre_negocio=config.nombre_negocio or NOMBRE_POR_DEFECTO,
        logo=config.logo or None,
        actualizado_en=config.actualizado_en,
    )


@router.get("/", response_model=ConfiguracionNegocioOut)
def obtener_configuracion(db: Session = Depends(get_db)):
    """Devuelve el nombre y el logo configurados (valores por defecto si no hay)."""
    return _salida(_configuracion(db))


@router.put("/", response_model=ConfiguracionNegocioOut)
def actualizar_configuracion(
    datos: ConfiguracionNegocioIn, db: Session = Depends(get_db)
):
    """Guarda el nombre del negocio y un logotipo cuadrado opcional."""
    nombre = (datos.nombre_negocio or "").strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre del negocio es obligatorio")

    logo = (datos.logo or "").strip() or None
    if logo and not logo.startswith(PREFIJOS_LOGO):
        raise HTTPException(
            status_code=400,
            detail="El logotipo debe ser una imagen PNG, JPEG o WebP",
        )

    config = _configuracion(db)
    if not config:
        config = ConfiguracionNegocio(id=1, nombre_negocio=nombre, logo=logo)
        db.add(config)
    else:
        config.nombre_negocio = nombre
        config.logo = logo
        config.actualizado_en = ahora_local()

    db.commit()
    db.refresh(config)
    return _salida(config)
