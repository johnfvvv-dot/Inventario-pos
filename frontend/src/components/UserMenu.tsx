/** Menú desplegable del usuario en el encabezado. */

import { useEffect, useRef, useState } from "react";

interface UserMenuProps {
  nombre: string;
  rol: string;
  onCerrarSesion: () => void;
}

export default function UserMenu({
  nombre,
  rol,
  onCerrarSesion,
}: UserMenuProps) {
  const [abierto, setAbierto] = useState(false);
  const contenedor = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!abierto) return;

    const alHacerClick = (evento: MouseEvent) => {
      if (
        contenedor.current &&
        !contenedor.current.contains(evento.target as Node)
      ) {
        setAbierto(false);
      }
    };
    const alPresionarTecla = (evento: KeyboardEvent) => {
      if (evento.key === "Escape") setAbierto(false);
    };

    document.addEventListener("mousedown", alHacerClick);
    document.addEventListener("keydown", alPresionarTecla);
    return () => {
      document.removeEventListener("mousedown", alHacerClick);
      document.removeEventListener("keydown", alPresionarTecla);
    };
  }, [abierto]);

  const nombreVisible = nombre || "Usuario";
  const inicial = nombreVisible.trim().charAt(0).toUpperCase() || "U";
  const esBartender = rol !== "admin";

  return (
    <div className="user-menu" ref={contenedor}>
      <button
        type="button"
        className="user-menu-trigger"
        aria-haspopup="menu"
        aria-expanded={abierto}
        aria-label="Menú de usuario"
        onClick={() => setAbierto((valor) => !valor)}
      >
        <span className="user-menu-avatar">{inicial}</span>
        <span className="user-menu-nombre">{nombreVisible}</span>
        <span className={`user-menu-flecha${abierto ? " abierta" : ""}`}>
          ▾
        </span>
      </button>

      {abierto && (
        <div className="user-menu-dropdown" role="menu">
          <div className="user-menu-cabecera">
            <strong>{nombreVisible}</strong>
            <small>{esBartender ? "Bartender" : "Administrador"}</small>
          </div>

          <div className="user-menu-separador" />
          <button
            type="button"
            className="user-menu-opcion danger"
            role="menuitem"
            onClick={onCerrarSesion}
          >
            Cerrar sesión
          </button>
        </div>
      )}
    </div>
  );
}
