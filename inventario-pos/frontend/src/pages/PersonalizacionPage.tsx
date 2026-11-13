/**
 * Personalización visual del negocio.
 *
 * El nombre oficial del sistema sigue siendo "Inventario POS"; esta pantalla
 * solo cambia el nombre y el logotipo que se muestran en la cabecera y en los
 * tickets internos.
 */

import { ChangeEvent, FormEvent, useEffect, useRef, useState } from "react";
import {
  notificarConfiguracion,
  useConfiguracionNegocio,
} from "../hooks/useConfiguracionNegocio";
import { api } from "../services/api";
import Icon from "../components/Icon";

const TAMANO_MAXIMO = 8 * 1024 * 1024;
const LADO_LOGO = 256;

/** Recorta la imagen al centro en un cuadrado y la exporta como PNG. */
function recortarLogo(archivo: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const lector = new FileReader();

    lector.onerror = () => reject(new Error("No se pudo leer la imagen"));
    lector.onload = () => {
      const imagen = new Image();
      imagen.onerror = () => reject(new Error("El archivo no es una imagen válida"));
      imagen.onload = () => {
        const lado = Math.min(imagen.width, imagen.height);
        if (!lado) {
          reject(new Error("La imagen está vacía"));
          return;
        }

        const lienzo = document.createElement("canvas");
        lienzo.width = LADO_LOGO;
        lienzo.height = LADO_LOGO;
        const ctx = lienzo.getContext("2d");
        if (!ctx) {
          reject(new Error("El navegador no pudo procesar la imagen"));
          return;
        }

        ctx.drawImage(
          imagen,
          (imagen.width - lado) / 2,
          (imagen.height - lado) / 2,
          lado,
          lado,
          0,
          0,
          LADO_LOGO,
          LADO_LOGO
        );
        resolve(lienzo.toDataURL("image/png"));
      };
      imagen.src = String(lector.result);
    };

    lector.readAsDataURL(archivo);
  });
}

export default function PersonalizacionPage() {
  const actual = useConfiguracionNegocio();
  const [nombre, setNombre] = useState(actual.nombre_negocio);
  const [logo, setLogo] = useState<string | null>(actual.logo);
  const [error, setError] = useState<string | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);
  const inputLogo = useRef<HTMLInputElement>(null);
  const editado = useRef(false);

  useEffect(() => {
    // Solo se sincroniza mientras el usuario no haya empezado a editar,
    // para no borrar lo que está escribiendo cuando llega la carga inicial.
    if (!editado.current) {
      setNombre(actual.nombre_negocio);
      setLogo(actual.logo);
    }
  }, [actual.nombre_negocio, actual.logo]);

  const elegirLogo = async (evento: ChangeEvent<HTMLInputElement>) => {
    const archivo = evento.target.files?.[0];
    evento.target.value = "";
    if (!archivo) return;

    setError(null);
    setMensaje(null);

    if (!archivo.type.startsWith("image/")) {
      setError("Selecciona una imagen PNG, JPEG o WebP.");
      return;
    }
    if (archivo.size > TAMANO_MAXIMO) {
      setError("La imagen es demasiado grande. Usa una de menos de 8 MB.");
      return;
    }

    try {
      const dataUrl = await recortarLogo(archivo);
      editado.current = true;
      setLogo(dataUrl);
    } catch (err: any) {
      setError(err?.message || "No se pudo procesar la imagen.");
    }
  };

  const quitarLogo = () => {
    editado.current = true;
    setLogo(null);
    setError(null);
    setMensaje(null);
  };

  const guardar = async (evento?: FormEvent) => {
    evento?.preventDefault();
    setError(null);
    setMensaje(null);

    const nombreLimpio = nombre.trim();
    if (!nombreLimpio) {
      setError("Escribe el nombre del negocio.");
      return;
    }

    setGuardando(true);
    try {
      const datos: any = await api.updateConfiguracionNegocio({
        nombre_negocio: nombreLimpio,
        logo,
      });
      const config = {
        nombre_negocio: datos?.nombre_negocio || nombreLimpio,
        logo: datos?.logo || null,
      };
      notificarConfiguracion(config);
      editado.current = false;
      setNombre(config.nombre_negocio);
      setLogo(config.logo);
      setMensaje("Personalización guardada correctamente.");
    } catch (err: any) {
      setError(err?.message || "No se pudo guardar la personalización.");
    } finally {
      setGuardando(false);
    }
  };

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h2>Personalización</h2>
          <p className="page-subtitulo">
            Cambia el nombre y el logotipo que identifican al negocio en la
            cabecera y en los tickets internos. El nombre oficial del sistema
            continúa siendo <strong>Inventario POS</strong>.
          </p>
        </div>
      </div>

      {error && <p className="error-msg">{error}</p>}
      {mensaje && <p className="success-msg">{mensaje}</p>}

      <section className="panel panel-acento panel-acento--azul">
        <h3>
          <Icon nombre="paleta" size={15} />
          Identidad del negocio
        </h3>

        <div className="personalizacion-grid">
          <form onSubmit={guardar}>
            <div className="form-group">
              <label htmlFor="nombre-negocio">Nombre del negocio</label>
              <input
                id="nombre-negocio"
                type="text"
                value={nombre}
                maxLength={80}
                placeholder="Ej.: La Lechucha"
                onChange={(evento) => {
                  editado.current = true;
                  setNombre(evento.target.value);
                  setMensaje(null);
                }}
                disabled={guardando}
              />
              <small className="muted">
                Se muestra en la esquina superior derecha, en lugar de
                "Inventario POS".
              </small>
            </div>

            <div className="form-group">
              <label>Logotipo</label>
              <div className="logo-acciones">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => inputLogo.current?.click()}
                  disabled={guardando}
                >
                  <Icon nombre="imagen" size={16} />
                  Elegir imagen
                </button>
                {logo && (
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={quitarLogo}
                    disabled={guardando}
                  >
                    <Icon nombre="eliminar" size={16} />
                    Quitar logo
                  </button>
                )}
                <input
                  ref={inputLogo}
                  type="file"
                  accept="image/*"
                  className="logo-input-oculto"
                  onChange={elegirLogo}
                  disabled={guardando}
                />
              </div>
              <small className="muted">
                Se recorta automáticamente en un cuadrado pequeño. Formatos:
                PNG, JPEG o WebP.
              </small>
            </div>

            {logo && (
              <div className="logo-vista">
                <img src={logo} alt="Vista previa del logotipo" />
                <span className="muted small">Vista previa del logo</span>
              </div>
            )}

            <button className="btn-primary" type="submit" disabled={guardando}>
              <Icon nombre="check" size={16} />
              {guardando ? "Guardando..." : "Guardar cambios"}
            </button>
          </form>

          <div className="personalizacion-preview" aria-hidden="true">
            <p className="muted small">Vista previa de la cabecera</p>
            <div className="preview-cabecera">
              <div className="admin-brand">
                {logo && (
                  <img
                    className="admin-brand-logo"
                    src={logo}
                    alt=""
                  />
                )}
                <div>
                  <h1>{nombre.trim() || "Inventario POS"}</h1>
                  <p className="muted">Panel de Administración</p>
                </div>
              </div>
              <span className="preview-usuario">Administrador</span>
            </div>
          </div>
        </div>
      </section>

      <section className="panel panel-aviso panel-aviso--cian">
        <h3>
          <Icon nombre="info" size={15} />
          Alcance de la personalización
        </h3>
        <p className="muted small">
          El nombre y el logo se guardan en la base de datos del sistema y se
          comparten entre el equipo local y la nube. Los tickets internos se
          generan bajo demanda desde <strong>Corte de caja</strong> y no se
          almacenan en el servidor.
        </p>
      </section>
    </div>
  );
}
