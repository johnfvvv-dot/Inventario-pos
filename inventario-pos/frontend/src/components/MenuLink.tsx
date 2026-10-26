/** Enlace del menú lateral con resaltado de la sección activa. */

import { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";

interface MenuLinkProps {
  to: string;
  children: ReactNode;
  /** Rutas adicionales que también deben marcar este enlace como activo. */
  rutas?: string[];
}

export default function MenuLink({ to, children, rutas = [] }: MenuLinkProps) {
  const { pathname } = useLocation();
  const rutaActual = pathname.replace(/\/+$/, "") || "/";
  const activo = [to, ...rutas].includes(rutaActual);

  return (
    <Link
      to={to}
      className={activo ? "activo" : undefined}
      aria-current={activo ? "page" : undefined}
    >
      {children}
    </Link>
  );
}
