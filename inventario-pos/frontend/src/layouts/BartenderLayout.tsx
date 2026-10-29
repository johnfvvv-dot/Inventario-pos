/** Layout del panel de Bartender: acceso operativo sin edición. */

import { useEffect, useState } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import MenuLink from "../components/MenuLink";
import UserMenu from "../components/UserMenu";
import AvisoTurnoModal from "../components/AvisoTurnoModal";
import { api } from "../services/api";

export default function BartenderLayout() {
  const navigate = useNavigate();
  const usuario = JSON.parse(localStorage.getItem("user") || "{}");
  const usuarioId = usuario?.id;
  // El permiso lo define el Administrador desde Usuarios y se guarda en la
  // base. Por defecto el Bartender solo consulta el inventario.
  const [ingresoStock, setIngresoStock] = useState<boolean>(
    Boolean(usuario?.ingreso_stock)
  );

  useEffect(() => {
    if (!usuarioId) return;
    let vigente = true;

    const consultarPermiso = async () => {
      try {
        const datos: any = await api.getUsuario(usuarioId);
        if (!vigente) return;

        const habilitado = Boolean(datos?.ingreso_stock);
        setIngresoStock(habilitado);

        // Mantiene sincronizada la sesión guardada en el navegador.
        const sesion = JSON.parse(localStorage.getItem("user") || "{}");
        if (Boolean(sesion.ingreso_stock) !== habilitado) {
          localStorage.setItem(
            "user",
            JSON.stringify({ ...sesion, ingreso_stock: habilitado })
          );
        }
      } catch {
        // Si el servidor no responde, se conserva el último estado conocido.
      }
    };

    consultarPermiso();
    // Refresco periódico para reflejar cambios del Administrador sin recargar.
    const intervalo = window.setInterval(consultarPermiso, 5000);

    const alVolverALaVentana = () => {
      if (document.visibilityState === "visible") consultarPermiso();
    };
    document.addEventListener("visibilitychange", alVolverALaVentana);
    window.addEventListener("focus", consultarPermiso);

    return () => {
      vigente = false;
      window.clearInterval(intervalo);
      document.removeEventListener("visibilitychange", alVolverALaVentana);
      window.removeEventListener("focus", consultarPermiso);
    };
  }, [usuarioId]);

  const cerrarSesion = () => {
    localStorage.removeItem("user");
    navigate("/");
  };

  return (
    <div className="mesero-layout">
      {/* Pregunta por la apertura del turno solo la primera vez del día */}
      <AvisoTurnoModal />

      <header className="admin-header">
        <div>
          <h1>Inventario POS</h1>
          <p className="muted">Panel de Bartender</p>
        </div>
        <div className="user-info">
          <UserMenu
            nombre={usuario.alias || usuario.nombre || "Bartender"}
            rol={usuario.rol || "bartender"}
            onCerrarSesion={cerrarSesion}
          />
        </div>
      </header>

      <div className="admin-body">
        <nav className="admin-nav">
          <MenuLink to="/bartender/pedidos" rutas={["/bartender"]}>
            Pedidos
          </MenuLink>
          <MenuLink to="/bartender/mesas">Mesas</MenuLink>
          <MenuLink to="/bartender/inventario">Inventario</MenuLink>
          <MenuLink to="/bartender/corte-caja">Corte de caja</MenuLink>
        </nav>

        <main className="admin-content">
          <Outlet context={{ ingresoStockHabilitado: ingresoStock }} />
        </main>
      </div>
    </div>
  );
}
