/** Pantalla de Login - Acceso al sistema */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../services/api";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const response = await api.login(email, password);
      // Guardar sesión localmente (simplificado)
      localStorage.setItem("user", JSON.stringify(response));
      navigate("/admin"); // Redirigir al dashboard admin
    } catch (err: any) {
      setError("Credenciales incorrectas. Intenta nuevamente.");
      console.error("Error en login:", err);
    }
  };

  return (
    <div className="login-page">
      <h2>SISTEMA INVENTARIO Y PUNTO DE VENTA</h2>
      <form onSubmit={handleLogin} className="login-form">
        <div className="form-group">
          <label htmlFor="email">Correo Electrónico</label>
          <input
            type="email"
            id="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="password">Contraseña</label>
          <input
            type="password"
            id="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>

        <button type="submit" className="btn-primary">
          INICIAR SESIÓN
        </button>

        {error && <p className="error-message">{error}</p>}
      </form>

      <p className="login-note">
        Roles: <strong>admin</strong> (administrador) | <strong>mesero</strong> (mesero)
      </p>
    </div>
  );
}