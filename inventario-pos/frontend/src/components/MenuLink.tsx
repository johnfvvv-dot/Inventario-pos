/** Enlace del menú lateral con resaltado de la sección activa. */

import { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import Icon, { type NombreIcono } from "./Icon";

interface MenuLinkProps {
  to: string;
  children: ReactNode;
  /** Rutas adicionales que también deben marcar este enlace como activo. */
  rutas?: string[];
  /** Icono representativo del módulo. */
  icono?: NombreIcono;
}

export default function MenuLink({
  to,
  children,
  rutas = [],
  icono,
}: MenuLinkProps) {
  const { pathname } = useLocation();
  const rutaActual = pathname.replace(/\/+$/, "") || "/";
  const activo = [to, ...rutas].includes(rutaActual);
  const modulo = to.split("/").filter(Boolean).pop() ?? "general";

  return (
    <Link
      to={to}
      className={`menu-link--${modulo}${activo ? " activo" : ""}`}
      aria-current={activo ? "page" : undefined}
    >
      {icono && (
        <span className="menu-link-icono">
          <Icon nombre={icono} size={17} />
        </span>
      )}
      <span className="menu-link-texto">{children}</span>
    </Link>
  );
}
