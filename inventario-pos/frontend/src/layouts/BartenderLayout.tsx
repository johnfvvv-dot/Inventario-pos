/** Layout del panel de Bartender: acceso operativo sin edición. */

import { useEffect, useState } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import { TurnoProvider } from "../context/TurnoContext";
import MenuLink from "../components/MenuLink";
import UserMenu from "../components/UserMenu";
import { useConfiguracionNegocio } from "../hooks/useConfiguracionNegocio";
import { api } from "../services/api";

export default function BartenderLayout() {
  const navigate = useNavigate();
  const usuario = JSON.parse(localStorage.getItem("user") || "{}");
  const usuarioId = usuario?.id;
  const negocio = useConfiguracionNegocio();
  // Los permisos los define el Administrador desde Usuarios y se guardan en
  // la base. Por defecto el Bartender solo consulta inventario y cantidades.
  const [ingresoStock, setIngresoStock] = useState<boolean>(
    Boolean(usuario?.ingreso_stock)
  );
  const [editarCantidades, setEditarCantidades] = useState<boolean>(
    Boolean(usuario?.editar_cantidades)
  );

  useEffect(() => {
    if (!usuarioId) return;
    let vigente = true;

    const consultarPermiso = async () => {
      try {
        const datos: any = await api.getUsuario(usuarioId);
        if (!vigente) return;

        const habilitadoStock = Boolean(datos?.ingreso_stock);
        const habilitadoCantidades = Boolean(datos?.editar_cantidades);
        setIngresoStock(habilitadoStock);
        setEditarCantidades(habilitadoCantidades);

        // Mantiene sincronizada la sesión guardada en el navegador. El evento
        // permite que las pantallas abiertas reaccionen sin recargar.
        const sesion = JSON.parse(localStorage.getItem("user") || "{}");
        const cambioStock = Boolean(sesion.ingreso_stock) !== habilitadoStock;
        const cambioCantidades =
          Boolean(sesion.editar_cantidades) !== habilitadoCantidades;
        if (cambioStock || cambioCantidades) {
          const actualizada = {
            ...sesion,
            ingreso_stock: habilitadoStock,
            editar_cantidades: habilitadoCantidades,
          };
          localStorage.setItem("user", JSON.stringify(actualizada));
          window.dispatchEvent(
            new CustomEvent("usuario-actualizado", { detail: actualizada })
          );
        }
      } catch {
        // Si el servidor no responde, se conserva el último estado conocido.
      }
    };

    consultarPermiso();
    // Refresco periódico para reflejar cambios del Administrador sin recargar.
    const intervalo = window.setInterval(consultarPermiso, 5000);

    const alVolverALaVentana = () => {
      if (document.visibilityState === "visible") consultarPermiso();
    };
    document.addEventListener("visibilitychange", alVolverALaVentana);
    window.addEventListener("focus", consultarPermiso);

    return () => {
      vigente = false;
      window.clearInterval(intervalo);
      document.removeEventListener("visibilitychange", alVolverALaVentana);
      window.removeEventListener("focus", consultarPermiso);
    };
  }, [usuarioId]);

  const cerrarSesion = () => {
    localStorage.removeItem("user");
    navigate("/");
  };

  return (
    <TurnoProvider>
      <div className="mesero-layout">
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
              <p className="muted">Panel de Bartender</p>
            </div>
          </div>
          <div className="user-info">
            <UserMenu
              nombre={usuario.alias || usuario.nombre || "Bartender"}
              rol={usuario.rol || "bartender"}
              onCerrarSesion={cerrarSesion}
            />
          </div>
        </header>

        <div className="admin-body">
          <nav className="admin-nav">
            <MenuLink
              to="/bartender/pedidos"
              rutas={["/bartender"]}
              icono="pedidos"
            >
              Pedidos
            </MenuLink>
            <MenuLink to="/bartender/mesas" icono="mesas">
              Mesas
            </MenuLink>
            <MenuLink to="/bartender/inventario" icono="inventario">
              Inventario
            </MenuLink>
            <MenuLink to="/bartender/corte-caja" icono="corte">
              Corte de caja
            </MenuLink>
          </nav>

          <main className="admin-content">
            <Outlet
              context={{
                ingresoStockHabilitado: ingresoStock,
                editarCantidadesHabilitado: editarCantidades,
              }}
            />
          </main>
        </div>
      </div>
    </TurnoProvider>
  );
}
