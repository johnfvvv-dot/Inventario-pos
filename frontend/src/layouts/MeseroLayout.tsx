/** Layout del panel de mesero. */

import { Link, Outlet, useNavigate } from "react-router-dom";

export default function MeseroLayout() {
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
          <p className="muted">Panel de Mesero</p>
        </div>
        <div className="user-info">
          <span>{usuario.nombre || "Mesero"}</span>
          <button className="btn-logout" onClick={cerrarSesion}>
            Cerrar sesión
          </button>
        </div>
      </header>

      <div className="admin-body">
        <nav className="admin-nav">
          <Link to="/mesero">Pedidos</Link>
        </nav>

        <main className="admin-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
