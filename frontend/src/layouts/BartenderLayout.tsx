/** Layout del panel de Bartender: acceso operativo sin edición. */

import { useState } from "react";
import { Link, Outlet, useNavigate } from "react-router-dom";
import UserMenu from "../components/UserMenu";

export default function BartenderLayout() {
  const navigate = useNavigate();
  const usuario = JSON.parse(localStorage.getItem("user") || "{}");
  // Por defecto el Bartender solo consulta el inventario. El menú de usuario
  // permite habilitar temporalmente la columna de ingreso de stock.
  const [ingresoStock, setIngresoStock] = useState(false);

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
          <UserMenu
            nombre={usuario.alias || usuario.nombre || "Bartender"}
            rol={usuario.rol || "bartender"}
            onCerrarSesion={cerrarSesion}
            ingresoStock={ingresoStock}
            onToggleIngresoStock={setIngresoStock}
          />
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
          <Outlet context={{ ingresoStockHabilitado: ingresoStock }} />
        </main>
      </div>
    </div>
  );
}
