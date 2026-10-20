/** Punto de entrada principal de la aplicación React + TypeScript */

import { BrowserRouter as Router, Route, Routes, Link } from "react-router-dom";
import "./App.css";

// Pantallas
import LoginPage from "./pages/LoginPage";
import InventarioPage from "./pages/InventarioPage";
import MesasPage from "./pages/MesasPage";
import PedidoMesaPage from "./pages/PedidoMesaPage";
import ReportesPage from "./pages/ReportesPage";

// Layouts
import AdminLayout from "./layouts/AdminLayout";
import MeseroLayout from "./layouts/MeseroLayout";

function App() {
  return (
    <Router>
      <nav className="app-nav">
        <Link to="/">Inventario POS</Link>
        {/* Mostrar enlaces según sea necesario, aquí simplificado */}
      </nav>

      <Routes>
        {/* Ruta pública - Login */}
        <Route path="/" element={<LoginPage />} />

        {/* Rutas protegidas - Admin */}
        <Route path="/admin/*" element={<AdminLayout />}>
          <Route index path="/admin" element={<InventarioPage />} />
          <Route path="/admin/mesas" element={<MesasPage />} />
          <Route path="/admin/pedidos" element={<PedidoMesaPage />} />
          <Route path="/admin/reportes" element={<ReportesPage />} />
        </Route>

        {/* Rutas protegidas - Mesero */}
        <Route path="/mesero/*" element={<MeseroLayout />}>
          <Route index path="/mesero" element={<PedidoMesaPage />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;