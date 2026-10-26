/** Pantalla de Login - Acceso por usuario. */

import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../services/api";

export default function LoginPage() {
  const [usuario, setUsuario] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);
  const navigate = useNavigate();

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
      </div>
    </div>
  );
}
