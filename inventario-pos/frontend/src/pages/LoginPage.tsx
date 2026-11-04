/** Pantalla de Login - Acceso por usuario. */

import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  api,
  ApiInfo,
  getApiInfo,
  redetectarApiLocal,
  resolverApiBase,
} from "../services/api";
import { APP_VERSION } from "../version";

export default function LoginPage() {
  const [usuario, setUsuario] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);
  const [servidor, setServidor] = useState<ApiInfo | null>(getApiInfo());
  const [buscandoLocal, setBuscandoLocal] = useState(false);
  const [avisoLocal, setAvisoLocal] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    let vigente = true;
    resolverApiBase()
      .then((info) => {
        if (vigente) setServidor(info);
      })
      .catch(() => {
        /* si falla la sonda, el login mostrará el error correspondiente */
      });
    return () => {
      vigente = false;
    };
  }, []);

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setCargando(true);

    try {
      const sesion: any = await api.login(usuario.trim(), password);
      localStorage.setItem("user", JSON.stringify(sesion));
      navigate(sesion.rol === "admin" ? "/admin" : "/bartender");
    } catch (err: any) {
      setError(err.message || "No se pudo iniciar sesión");
    } finally {
      setCargando(false);
    }
  };

  const buscarServidorLocal = async () => {
    setBuscandoLocal(true);
    setAvisoLocal(null);
    try {
      const info = await redetectarApiLocal();
      if (info) {
        setServidor(info);
        setAvisoLocal("Servidor local conectado. Ya puedes iniciar sesión.");
      } else {
        setAvisoLocal(
          "No se encontró el servidor local. Verifica que InventarioPOS.exe esté abierto."
        );
      }
    } finally {
      setBuscandoLocal(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <h1>Sistema Inventario y Punto de Venta</h1>
        <p className="muted">Ingresa con tu usuario y clave</p>

        <form onSubmit={handleLogin} className="login-form">
          <div className="form-group">
            <label htmlFor="usuario">Usuario</label>
            <input
              id="usuario"
              type="text"
              value={usuario}
              onChange={(e) => setUsuario(e.target.value)}
              placeholder="Usuario"
              autoCapitalize="none"
              autoComplete="username"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Clave</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••"
              autoComplete="current-password"
              required
            />
          </div>

          <button type="submit" className="btn-primary btn-block" disabled={cargando}>
            {cargando ? "Ingresando..." : "Iniciar sesión"}
          </button>

          {error && <p className="error-msg">{error}</p>}
        </form>

        <p className="muted api-servidor" title={servidor?.base}>
          {servidor
            ? servidor.mode === "local"
              ? "Servidor local activo"
              : "Servidor en la nube (Render)"
            : "Detectando servidor..."}
        </p>

        {servidor && (
          <p className="muted small api-base" title={servidor.base}>
            {servidor.base}
          </p>
        )}
        <p className="muted api-version">Inventario POS v{APP_VERSION}</p>

        {servidor?.mode === "cloud" && (
          <div className="api-local-retry">
            <button
              type="button"
              className="btn-link"
              onClick={buscarServidorLocal}
              disabled={buscandoLocal}
            >
              {buscandoLocal
                ? "Buscando servidor local..."
                : "¿Estás en el PC del negocio? Conectar al servidor local"}
            </button>
            <p className="muted small">
              Si Chrome lo solicita, permite el acceso a la red local. En el
              celular, abre http://IP_DEL_PC:8000 dentro de la misma WiFi.
            </p>
            {avisoLocal && <p className="muted small">{avisoLocal}</p>}
          </div>
        )}
      </div>
    </div>
  );
}
