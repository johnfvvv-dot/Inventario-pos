/** Layout del panel de administración. */

import { Link, Outlet, useNavigate } from "react-router-dom";
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
          <Link to="/admin">Inventario</Link>
          <Link to="/admin/mesas">Mesas</Link>
          <Link to="/admin/pedidos">Pedidos</Link>
          <Link to="/admin/reportes">Reportes</Link>
          <Link to="/admin/corte-caja">Corte de caja</Link>
          <Link to="/admin/historial">Historial</Link>
          <Link to="/admin/usuarios">Usuarios</Link>
        </nav>

        <main className="admin-content">
          <Outlet context={{ ingresoStockHabilitado: usuario.rol === "admin" }} />
        </main>
      </div>
    </div>
  );
}
