/** Layout del panel de Bartender: acceso operativo sin edición. */

import { Link, Outlet, useNavigate } from "react-router-dom";

export default function BartenderLayout() {
  const navigate = useNavigate();
  const usuario = JSON.parse(localStorage.getItem("user") || "{}");

  const cerrarSesion = () => {
    localStorage.removeItem("user");
    navigate("/");
  };

  return (
    <div className="mesero-layout">
      <header className="admin-header">
        <div>
          <h1>Inventario POS</h1>
          <p className="muted">Panel de Bartender</p>
        </div>
        <div className="user-info">
          <span>{usuario.alias || usuario.nombre || "Bartender"}</span>
          <button className="btn-logout" onClick={cerrarSesion}>
            Cerrar sesión
          </button>
        </div>
      </header>

      <div className="admin-body">
        <nav className="admin-nav">
          <Link to="/bartender/pedidos">Pedidos</Link>
          <Link to="/bartender/mesas">Mesas</Link>
          <Link to="/bartender/inventario">Inventario</Link>
          <Link to="/bartender/corte-caja">Corte de caja</Link>
        </nav>

        <main className="admin-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
