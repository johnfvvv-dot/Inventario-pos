/** Punto de entrada y enrutamiento principal de la aplicación React. */

import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import "./App.css";

import AdminLayout from "./layouts/AdminLayout";
import MeseroLayout from "./layouts/MeseroLayout";
import LoginPage from "./pages/LoginPage";
import InventarioPage from "./pages/InventarioPage";
import MesasPage from "./pages/MesasPage";
import PedidoMesaPage from "./pages/PedidoMesaPage";
import ReportesPage from "./pages/ReportesPage";
import CorteCajaPage from "./pages/CorteCajaPage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LoginPage />} />

        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<InventarioPage />} />
          <Route path="mesas" element={<MesasPage />} />
          <Route path="pedidos" element={<PedidoMesaPage />} />
          <Route path="reportes" element={<ReportesPage />} />
          <Route path="corte-caja" element={<CorteCajaPage />} />
        </Route>

        <Route path="/mesero" element={<MeseroLayout />}>
          <Route index element={<PedidoMesaPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
