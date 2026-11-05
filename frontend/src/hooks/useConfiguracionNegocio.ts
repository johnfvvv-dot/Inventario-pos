/**
 * Configuración visual del negocio (nombre y logotipo).
 *
 * Se comparte entre la cabecera del administrador, la del bartender y la
 * página de Personalización. Se guarda una copia en localStorage para que la
 * cabecera no parpadee mientras llega la respuesta del backend.
 */

import { useEffect, useState } from "react";
import { api } from "../services/api";

export interface ConfiguracionNegocio {
  nombre_negocio: string;
  logo: string | null;
  actualizado_en?: string | null;
}

export const CONFIGURACION_POR_DEFECTO: ConfiguracionNegocio = {
  nombre_negocio: "Inventario POS",
  logo: null,
};

const CLAVE_CACHE = "negocio_config";
export const EVENTO_CONFIGURACION = "negocio-config-actualizada";

function normalizar(datos: any): ConfiguracionNegocio {
  return {
    nombre_negocio: String(datos?.nombre_negocio || "").trim() || "Inventario POS",
    logo: datos?.logo || null,
    actualizado_en: datos?.actualizado_en || null,
  };
}

function leerCache(): ConfiguracionNegocio {
  try {
    const guardada = JSON.parse(localStorage.getItem(CLAVE_CACHE) || "null");
    if (guardada) return normalizar(guardada);
  } catch {
    /* copia local inválida */
  }
  return CONFIGURACION_POR_DEFECTO;
}

export function guardarCacheConfiguracion(config: ConfiguracionNegocio): void {
  try {
    localStorage.setItem(CLAVE_CACHE, JSON.stringify(config));
  } catch {
    /* localStorage no disponible */
  }
}

/** Avisa a las cabeceras abiertas que la personalización cambió. */
export function notificarConfiguracion(config: ConfiguracionNegocio): void {
  const limpia = normalizar(config);
  guardarCacheConfiguracion(limpia);
  window.dispatchEvent(
    new CustomEvent<ConfiguracionNegocio>(EVENTO_CONFIGURACION, {
      detail: limpia,
    })
  );
}

export function useConfiguracionNegocio(): ConfiguracionNegocio {
  const [config, setConfig] = useState<ConfiguracionNegocio>(leerCache);

  useEffect(() => {
    let vigente = true;

    const cargar = async () => {
      try {
        const datos = await api.getConfiguracionNegocio();
        if (!vigente) return;
        const limpia = normalizar(datos);
        setConfig(limpia);
        guardarCacheConfiguracion(limpia);
      } catch {
        // Sin conexión se conserva el último valor conocido.
      }
    };

    const alActualizar = (evento: Event) => {
      const detalle = (evento as CustomEvent<ConfiguracionNegocio>).detail;
      if (detalle) {
        const limpia = normalizar(detalle);
        setConfig(limpia);
        guardarCacheConfiguracion(limpia);
      } else {
        cargar();
      }
    };

    cargar();
    window.addEventListener(EVENTO_CONFIGURACION, alActualizar);
    return () => {
      vigente = false;
      window.removeEventListener(EVENTO_CONFIGURACION, alActualizar);
    };
  }, []);

  return config;
}
