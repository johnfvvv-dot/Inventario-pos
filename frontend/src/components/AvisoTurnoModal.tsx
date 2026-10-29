/**
 * Aviso de apertura de turno del día.
 *
 * Se muestra una sola vez por día (la primera vez que se entra a la sesión)
 * y únicamente cuando no existe ningún turno abierto:
 *
 *  - Un turno abierto desde la noche anterior que continúa en la madrugada
 *    hace que `/caja/turno-actual` devuelva datos y el aviso no aparece.
 *  - El día queda marcado en `localStorage` al comprobarlo, de modo que un
 *    segundo inicio de sesión el mismo día no vuelve a preguntar.
 *  - Si el backend no responde, el día NO se marca y se vuelve a comprobar
 *    en el siguiente inicio de sesión.
 */

import { useEffect, useState } from "react";
import { api } from "../services/api";
import { fechaParaArchivo } from "../utils/format";
import ConfirmModal from "./ConfirmModal";

/** Último día en que se resolvió el aviso (YYYY-MM-DD, hora local). */
const CLAVE_AVISO = "turno_aviso_fecha";

export default function AvisoTurnoModal() {
  const [mostrar, setMostrar] = useState(false);
  const [procesando, setProcesando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let vigente = true;

    const revisar = async () => {
      const hoy = fechaParaArchivo();
      // Ya se resolvió el aviso en el día de hoy.
      if (localStorage.getItem(CLAVE_AVISO) === hoy) return;

      try {
        const turno = await api.getTurnoActual();
        if (!vigente) return;

        // Se marca el día aunque haya turno: la solicitud solo corresponde
        // al primer ingreso del día cuando no hay turno abierto.
        localStorage.setItem(CLAVE_AVISO, hoy);
        if (!turno) setMostrar(true);
      } catch {
        // Sin respuesta del backend no se marca el día, para que el aviso
        // se evalúe de nuevo en el siguiente inicio de sesión.
      }
    };

    revisar();
    return () => {
      vigente = false;
    };
  }, []);

  if (!mostrar) return null;

  const abrirTurno = async () => {
    setProcesando(true);
    setError(null);
    try {
      const sesion = JSON.parse(localStorage.getItem("user") || "{}");
      await api.abrirTurno(Number(sesion?.id) || 1);
      setMostrar(false);
    } catch (err: any) {
      setError(err.message || "No se pudo abrir el turno");
    } finally {
      setProcesando(false);
    }
  };

  return (
    <ConfirmModal
      titulo="Apertura de turno"
      mensaje="¿Desea abrir el turno del día?"
      aceptar="Aceptar"
      cancelar="Cancelar"
      onConfirmar={abrirTurno}
      onCancelar={() => setMostrar(false)}
      procesando={procesando}
      error={error}
    />
  );
}
