/** Layout del panel de administración. */

import { Outlet, useNavigate } from "react-router-dom";
import MenuLink from "../components/MenuLink";
import UserMenu from "../components/UserMenu";

export default function AdminLayout() {
  const navigate = useNavigate();
  const usuario = JSON.parse(localStorage.getItem("user") || "{}");

  const cerrarSesion = () => {
    localStorage.removeItem("user");
    navigate("/");
  };

  return (
    <div className="admin-layout">
      <header className="admin-header">
        <div>
          <h1>Inventario POS</h1>
          <p className="muted">Panel de Administración</p>
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
          <MenuLink to="/admin/inventario" rutas={["/admin"]}>
            Inventario
          </MenuLink>
          <MenuLink to="/admin/mesas">Mesas</MenuLink>
          <MenuLink to="/admin/pedidos">Pedidos</MenuLink>
          <MenuLink to="/admin/reportes">Reportes</MenuLink>
          <MenuLink to="/admin/corte-caja">Corte de caja</MenuLink>
          <MenuLink to="/admin/historial">Historial</MenuLink>
          <MenuLink to="/admin/usuarios">Usuarios</MenuLink>
        </nav>

        <main className="admin-content">
          <Outlet context={{ ingresoStockHabilitado: usuario.rol === "admin" }} />
        </main>
      </div>
    </div>
  );
}
