/** Layout para el rol de Administrador */
import { useEffect } from "react";
import { useSelector, useDispatch } from "react-redux"; // Opcional, usando contexto simple
import { api } from "../services/api";
import { Link } from "react-router-dom";

// Simulación de contexto de usuario (en producción usaríamos Redux o Context API simple)
const UserContext = {
  user: JSON.parse(localStorage.getItem("user") || "{}"),
  isAdmin: true, // Simplificado - en producción verificar rol
};

export default function AdminLayout() {
  const user = UserContext.user;

  useEffect(() => {
    // Verificar autenticación al cargar
    if (!user || !user.id) {
      // Si no hay usuario, ir al login
      window.location.href = "/";
    }
  }, [user]);

  return (
    <div className="admin-layout">
      <header className="admin-header">
        <h1>Panel de Administración</h1>
        <div className="user-info">
          <span>Bienvenido, {user.nombre || "Admin"}</span>
          <Link to="/">Cerrar Sesión</Link>
        </div>
      </header>

      <main className="admin-main">
        <nav className="admin-nav">
          <Link to="/admin">Inventario</Link>
          <Link to="/admin/mesas">Mesas</Link>
          <Link to="/admin/pedidos">Pedidos</Link>
          <Link to="/admin/reportes">Reportes</Link>
        </nav>

        <div className="admin-content">
          {this.props.children}
        </div>
      </main>
    </div>
  );
}