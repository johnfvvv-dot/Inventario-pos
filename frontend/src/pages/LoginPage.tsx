/** Pantalla de Login - Acceso al sistema. */

import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../services/api";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setCargando(true);

    try {
      const usuario: any = await api.login(email.trim(), password);
      localStorage.setItem("user", JSON.stringify(usuario));
      navigate(usuario.rol === "admin" ? "/admin" : "/mesero");
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
        <p className="muted">Ingresa con tus credenciales</p>

        <form onSubmit={handleLogin} className="login-form">
          <div className="form-group">
            <label htmlFor="email">Correo electrónico</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@localpos.com"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Contraseña</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="admin123"
              required
            />
          </div>

          <button type="submit" className="btn-primary btn-block" disabled={cargando}>
            {cargando ? "Ingresando..." : "Iniciar sesión"}
          </button>

          {error && <p className="error-msg">{error}</p>}
        </form>

        <div className="login-hint">
          <strong>Usuarios de prueba</strong>
          <span>Admin: admin@localpos.com / admin123</span>
          <span>Mesero: mesero@localpos.com / mesero123</span>
        </div>
      </div>
    </div>
  );
}
