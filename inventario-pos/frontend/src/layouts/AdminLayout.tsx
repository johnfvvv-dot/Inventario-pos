/** Layout del panel de administración. */

import { Outlet, useNavigate } from "react-router-dom";
import { TurnoProvider } from "../context/TurnoContext";
import MenuLink from "../components/MenuLink";
import UserMenu from "../components/UserMenu";
import { useConfiguracionNegocio } from "../hooks/useConfiguracionNegocio";

export default function AdminLayout() {
  const navigate = useNavigate();
  const usuario = JSON.parse(localStorage.getItem("user") || "{}");
  const negocio = useConfiguracionNegocio();

  const cerrarSesion = () => {
    localStorage.removeItem("user");
    navigate("/");
  };

  return (
    <TurnoProvider>
      <div className="admin-layout">
        <header className="admin-header">
          <div className="admin-brand">
            {negocio.logo && (
              <img
                className="admin-brand-logo"
                src={negocio.logo}
                alt="Logotipo del negocio"
              />
            )}
            <div>
              <h1 title={negocio.nombre_negocio}>{negocio.nombre_negocio}</h1>
              <p className="muted">Panel de Administración</p>
            </div>
          </div>
          <div className="user-info">
            <UserMenu
              nombre={usuario.alias || usuario.nombre || "Administrador"}
              rol={usuario.rol || "admin"}
              onCerrarSesion={cerrarSesion}
            />
          </div>
        </header>

        <div className="admin-body">
          <nav className="admin-nav">
            <MenuLink
              to="/admin/inventario"
              rutas={["/admin"]}
              icono="inventario"
            >
              Inventario
            </MenuLink>
            <MenuLink to="/admin/mesas" icono="mesas">
              Mesas
            </MenuLink>
            <MenuLink to="/admin/pedidos" icono="pedidos">
              Pedidos
            </MenuLink>
            <MenuLink to="/admin/reportes" icono="reportes">
              Reportes
            </MenuLink>
            <MenuLink to="/admin/corte-caja" icono="corte">
              Corte de caja
            </MenuLink>
            <MenuLink to="/admin/historial" icono="historial">
              Historial
            </MenuLink>
            <MenuLink to="/admin/personalizacion" icono="personalizacion">
              Personalización
            </MenuLink>
            <MenuLink to="/admin/usuarios" icono="usuarios">
              Usuarios
            </MenuLink>
          </nav>

          <main className="admin-content">
            <Outlet context={{ ingresoStockHabilitado: usuario.rol === "admin" }} />
          </main>
        </div>
      </div>
    </TurnoProvider>
  );
}
