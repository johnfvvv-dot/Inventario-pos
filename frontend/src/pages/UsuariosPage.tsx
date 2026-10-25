/** Pantalla de Usuarios - solo para Administrador. */

import { FormEvent, useEffect, useState } from "react";
import { api } from "../services/api";
import CambiarClaveModal from "../components/CambiarClaveModal";
import ConfirmModal from "../components/ConfirmModal";
import { formatearFechaHora } from "../utils/format";

interface Usuario {
  id: number;
  alias: string;
  nombre?: string | null;
  rol: string;
  activo: boolean;
  creado_en: string;
}

export default function UsuariosPage() {
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [nuevo, setNuevo] = useState({
    alias: "",
    nombre: "",
    rol: "bartender",
    clave: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);
  const [cambiarClaveDe, setCambiarClaveDe] = useState<Usuario | null>(null);
  const [porEliminar, setPorEliminar] = useState<Usuario | null>(null);

  const cargar = async () => {
    try {
      const data: any = await api.getUsuarios();
      setUsuarios(data);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    }
  };

  useEffect(() => {
    cargar();
  }, []);

  const crearUsuario = async (e: FormEvent) => {
    e.preventDefault();
    setCargando(true);
    try {
      await api.createUsuario({
        alias: nuevo.alias.trim(),
        nombre: nuevo.nombre.trim() || undefined,
        rol: nuevo.rol,
        password: nuevo.clave.trim() || undefined, // si va vacío usa la clave inicial
      });
      setMensaje(
        `Usuario "${nuevo.alias.trim()}" creado${
          nuevo.clave.trim() ? "" : " con la clave inicial (1234)"
        }`
      );
      setNuevo({ alias: "", nombre: "", rol: "bartender", clave: "" });
      await cargar();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setCargando(false);
    }
  };

  const cambiarRol = async (u: Usuario, rol: string) => {
    try {
      await api.updateUsuario(u.id, { rol });
      await cargar();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const alternarActivo = async (u: Usuario) => {
    try {
      await api.updateUsuario(u.id, { activo: !u.activo });
      await cargar();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const guardarClave = async (clave: string) => {
    if (!cambiarClaveDe) return;
    setCargando(true);
    try {
      await api.cambiarClave(cambiarClaveDe.id, clave);
      setMensaje(`Clave de "${cambiarClaveDe.alias}" actualizada`);
      setCambiarClaveDe(null);
      await cargar();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setCargando(false);
    }
  };

  const eliminarUsuario = async () => {
    if (!porEliminar) return;
    try {
      await api.deleteUsuario(porEliminar.id);
      setMensaje(`Usuario "${porEliminar.alias}" eliminado`);
      setPorEliminar(null);
      await cargar();
    } catch (err: any) {
      setError(err.message);
      setPorEliminar(null);
    }
  };

  return (
    <div className="page">
      <div className="page-head">
        <h2>Usuarios del sistema</h2>
        <button className="btn-secondary" onClick={cargar}>
          Actualizar
        </button>
      </div>

      {error && <p className="error-msg">{error}</p>}
      {mensaje && <p className="success-msg">{mensaje}</p>}

      {/* Crear usuario */}
      <section className="panel">
        <h3>Crear usuario</h3>
        <form className="filtros-barra" onSubmit={crearUsuario}>
          <div className="form-group">
            <label>Alias *</label>
            <input
              value={nuevo.alias}
              onChange={(e) => setNuevo((n) => ({ ...n, alias: e.target.value }))}
              placeholder="Ej: Carla"
              required
              minLength={2}
            />
          </div>
          <div className="form-group">
            <label>Nombre visible</label>
            <input
              value={nuevo.nombre}
              onChange={(e) => setNuevo((n) => ({ ...n, nombre: e.target.value }))}
              placeholder="Ej: Carla Pérez"
            />
          </div>
          <div className="form-group">
            <label>Rol *</label>
            <select
              value={nuevo.rol}
              onChange={(e) => setNuevo((n) => ({ ...n, rol: e.target.value }))}
            >
              <option value="bartender">Bartender</option>
              <option value="admin">Administrador</option>
            </select>
          </div>
          <div className="form-group">
            <label>Clave (opcional)</label>
            <input
              type="password"
              value={nuevo.clave}
              onChange={(e) => setNuevo((n) => ({ ...n, clave: e.target.value }))}
              placeholder="1234 (por defecto)"
            />
          </div>
          <button type="submit" className="btn-primary" disabled={cargando}>
            {cargando ? "Creando..." : "+ Crear usuario"}
          </button>
        </form>
        <p className="muted small">
          Si no se indica clave, el usuario se crea con la clave inicial <strong>1234</strong>,
          que podrás cambiar luego desde la lista.
        </p>
      </section>

      {/* Lista de usuarios */}
      <section className="panel">
        <h3>Usuarios registrados</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Alias</th>
                <th>Nombre</th>
                <th>Rol</th>
                <th>Estado</th>
                <th>Creado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {usuarios.map((u) => (
                <tr key={u.id}>
                  <td>
                    <strong>{u.alias}</strong>
                  </td>
                  <td className="muted">{u.nombre || "-"}</td>
                  <td>
                    <select
                      value={u.rol}
                      onChange={(e) => cambiarRol(u, e.target.value)}
                      className="select-rol"
                    >
                      <option value="bartender">Bartender</option>
                      <option value="admin">Administrador</option>
                    </select>
                  </td>
                  <td>
                    <span
                      className={u.activo ? "badge badge-success" : "badge badge-danger"}
                    >
                      {u.activo ? "Activo" : "Inactivo"}
                    </span>
                  </td>
                  <td className="muted small">
                    {formatearFechaHora(u.creado_en)}
                  </td>
                  <td className="actions">
                    <button
                      className="btn-secondary btn-small"
                      onClick={() => setCambiarClaveDe(u)}
                    >
                      Cambiar clave
                    </button>
                    <button
                      className="btn-secondary btn-small"
                      onClick={() => alternarActivo(u)}
                    >
                      {u.activo ? "Desactivar" : "Activar"}
                    </button>
                    <button
                      className="btn-icon danger"
                      title="Eliminar"
                      onClick={() => setPorEliminar(u)}
                    >
                      ×
                    </button>
                  </td>
                </tr>
              ))}
              {usuarios.length === 0 && (
                <tr>
                  <td colSpan={6} className="empty-state">
                    No hay usuarios registrados.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* Cambio de clave */}
      {cambiarClaveDe && (
        <CambiarClaveModal
          alias={cambiarClaveDe.alias}
          onConfirmar={guardarClave}
          onCancelar={() => setCambiarClaveDe(null)}
          procesando={cargando}
          error={error}
        />
      )}

      {/* Confirmación de borrado */}
      {porEliminar && (
        <ConfirmModal
          titulo="Eliminar usuario"
          mensaje={`¿Eliminar el usuario "${porEliminar.alias}"?`}
          aceptar="Aceptar"
          cancelar="Cancelar"
          onConfirmar={eliminarUsuario}
          onCancelar={() => setPorEliminar(null)}
          error={error}
        />
      )}

      {/* Permisos por rol */}
      <section className="panel">
        <h3>Permisos por rol</h3>
        <div className="report-grid">
          <div className="permisos-bloque">
            <h4>Administrador</h4>
            <ul>
              <li>Acceso completo a todos los módulos</li>
              <li>Inventario: crear, editar y eliminar</li>
              <li>Mesas, Pedidos y Cuentas</li>
              <li>Reportes e Historial de ventas</li>
              <li>Corte de caja</li>
              <li>Creación y gestión de usuarios</li>
            </ul>
          </div>
          <div className="permisos-bloque">
            <h4>Bartender</h4>
            <ul>
              <li>Mesas, Pedidos y Cuentas</li>
              <li>Inventario en modo lectura (sin editar)</li>
              <li>Corte de caja</li>
              <li>Sin acceso a Reportes, Historial ni Usuarios</li>
            </ul>
          </div>
        </div>
      </section>
    </div>
  );
}
