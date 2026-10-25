/** Punto de entrada y enrutamiento principal de la aplicación React. */

import { ReactNode } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import "./App.css";

import AdminLayout from "./layouts/AdminLayout";
import BartenderLayout from "./layouts/BartenderLayout";
import LoginPage from "./pages/LoginPage";
import InventarioPage from "./pages/InventarioPage";
import MesasPage from "./pages/MesasPage";
import PedidoMesaPage from "./pages/PedidoMesaPage";
import ReportesPage from "./pages/ReportesPage";
import CorteCajaPage from "./pages/CorteCajaPage";
import HistorialPage from "./pages/HistorialPage";
import UsuariosPage from "./pages/UsuariosPage";

/** Solo el Administrador puede entrar al panel y a la gestión de usuarios. */
function RutaAdmin({ children }: { children: ReactNode }) {
  const usuario = JSON.parse(localStorage.getItem("user") || "{}");
  if (usuario?.rol === "admin") return <>{children}</>;
  return (
    <Navigate to={usuario?.rol === "bartender" ? "/bartender" : "/"} replace />
  );
}

/** El panel operativo es exclusivo del Bartender. */
function RutaBartender({ children }: { children: ReactNode }) {
  const usuario = JSON.parse(localStorage.getItem("user") || "{}");
  if (usuario?.rol === "bartender") return <>{children}</>;
  return <Navigate to={usuario?.rol === "admin" ? "/admin" : "/"} replace />;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LoginPage />} />

        <Route
          path="/admin"
          element={
            <RutaAdmin>
              <AdminLayout />
            </RutaAdmin>
          }
        >
          <Route index element={<InventarioPage />} />
          <Route path="inventario" element={<InventarioPage />} />
          <Route path="mesas" element={<MesasPage />} />
          <Route path="pedidos" element={<PedidoMesaPage />} />
          <Route path="reportes" element={<ReportesPage />} />
          <Route path="corte-caja" element={<CorteCajaPage />} />
          <Route path="historial" element={<HistorialPage />} />
          <Route path="usuarios" element={<UsuariosPage />} />
        </Route>

        {/* Bartender: acceso operativo, inventario en solo lectura */}
        <Route
          path="/bartender"
          element={
            <RutaBartender>
              <BartenderLayout />
            </RutaBartender>
          }
        >
          <Route index element={<PedidoMesaPage />} />
          <Route path="pedidos" element={<PedidoMesaPage />} />
          <Route path="mesas" element={<MesasPage />} />
          <Route path="inventario" element={<InventarioPage />} />
          <Route path="corte-caja" element={<CorteCajaPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
