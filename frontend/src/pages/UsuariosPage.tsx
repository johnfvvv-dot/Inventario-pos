/** Pantalla de Usuarios - solo para Administrador. */

import { FormEvent, useEffect, useState } from "react";
import { api } from "../services/api";
import CambiarClaveModal from "../components/CambiarClaveModal";
import ConfirmModal from "../components/ConfirmModal";
import Icon from "../components/Icon";
import { formatearFechaHora } from "../utils/format";

interface Usuario {
  id: number;
  alias: string;
  nombre?: string | null;
  rol: string;
  activo: boolean;
  ingreso_stock: boolean;
  editar_cantidades: boolean;
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

  /** Habilita o deshabilita la columna de ingreso de stock del Bartender. */
  const alternarIngresoStock = async (u: Usuario) => {
    if (u.rol !== "bartender") return;
    try {
      await api.updateUsuario(u.id, { ingreso_stock: !u.ingreso_stock });
      setMensaje(
        `Ingreso de stock de "${u.alias}" ${
          u.ingreso_stock ? "deshabilitado" : "habilitado"
        }`
      );
      await cargar();
    } catch (err: any) {
      setError(err.message);
    }
  };

  /** Habilita o deshabilita la edición de pedidos en pedidos y alias. */
  const alternarEditarCantidades = async (u: Usuario) => {
    if (u.rol !== "bartender") return;
    try {
      await api.updateUsuario(u.id, {
        editar_cantidades: !u.editar_cantidades,
      });
      setMensaje(
        `Edición de pedidos de "${u.alias}" ${
          u.editar_cantidades ? "deshabilitada" : "habilitada"
        }`
      );
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
        <div>
          <h2>Usuarios del sistema</h2>
          <p className="page-subtitulo">
            Administración de cuentas de acceso, roles y permisos operativos en
            tiempo real
          </p>
        </div>
        <button className="btn-secondary" onClick={cargar}>
          <Icon nombre="actualizar" size={16} />
          Actualizar
        </button>
      </div>

      {error && <p className="error-msg">{error}</p>}
      {mensaje && <p className="success-msg">{mensaje}</p>}

      {/* Crear usuario */}
      <section className="panel panel-acento panel-acento--azul usuarios-crear">
        <div className="usuarios-crear-head">
          <span className="usuarios-crear-icono">
            <Icon nombre="usuario" size={18} />
          </span>
          <div>
            <h3>Crear usuario</h3>
            <p className="muted small">
              Alta de cuentas con rol y clave de acceso
            </p>
          </div>
        </div>
        <form className="usuarios-form" onSubmit={crearUsuario}>
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
          <button type="submit" className="btn-primary usuarios-crear-btn" disabled={cargando}>
            <Icon nombre="mas" size={16} />
            {cargando ? "Creando..." : "Crear usuario"}
          </button>
        </form>
        <p className="muted small usuarios-nota">
          <Icon nombre="info" size={14} />
          Si no se indica clave, el usuario se crea con la clave inicial{" "}
          <strong>1234</strong>, que podrás cambiar luego desde la lista.
        </p>
      </section>

      {/* Lista de usuarios */}
      <section className="panel tabla-card usuarios-lista">
        <div className="usuarios-lista-head">
          <div>
            <h3>
              <Icon nombre="usuarios" size={15} />
              Usuarios registrados
            </h3>
            <p className="muted small">
              El ingreso de stock y la edición de pedidos están desactivados por
              defecto para los Bartenders. Habilitalos por usuario cuando los
              necesiten; el cambio se refleja en su sesión sin recargar la
              página. El Administrador siempre puede editar pedidos.
            </p>
          </div>
          <span className="badge badge-neutral">
            {usuarios.length} usuario{usuarios.length !== 1 ? "s" : ""}
          </span>
        </div>
        <div className="table-wrap">
          <table className="usuarios-tabla">
            <thead>
              <tr>
                <th>Alias / Nombre</th>
                <th>Rol</th>
                <th>Ingreso de Stock</th>
                <th>Edición de pedidos</th>
                <th>Estado</th>
                <th>Creado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {usuarios.map((u) => (
                <tr key={u.id}>
                  <td>
                    <div className="usuario-identidad">
                      <span className="usuario-avatar">
                        {(u.alias || "?").charAt(0).toUpperCase()}
                      </span>
                      <span>
                        <strong>{u.alias}</strong>
                        <span className="muted small usuario-nombre">
                          {u.nombre || "Sin nombre visible"}
                        </span>
                      </span>
                    </div>
                  </td>
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
                    {u.rol === "bartender" ? (
                      <button
                        type="button"
                        className={`permiso-stock${
                          u.ingreso_stock ? " activo" : ""
                        }`}
                        role="switch"
                        aria-checked={u.ingreso_stock}
                        aria-label={`Ingreso de stock para ${u.alias}`}
                        title={
                          u.ingreso_stock
                            ? "Deshabilitar el ingreso de stock"
                            : "Habilitar el ingreso de stock"
                        }
                        onClick={() => alternarIngresoStock(u)}
                      >
                        <span
                          className={`toggle${
                            u.ingreso_stock ? " activo" : ""
                          }`}
                          aria-hidden="true"
                        >
                          <span className="toggle-bola" />
                        </span>
                        <span>
                          {u.ingreso_stock ? "Habilitado" : "Solo lectura"}
                        </span>
                      </button>
                    ) : (
                      <span className="badge badge-success">
                        Siempre activo
                      </span>
                    )}
                  </td>
                  <td>
                    {u.rol === "bartender" ? (
                      <button
                        type="button"
                        className={`permiso-stock${
                          u.editar_cantidades ? " activo" : ""
                        }`}
                        role="switch"
                        aria-checked={u.editar_cantidades}
                        aria-label={`Edición de pedidos para ${u.alias}`}
                        title={
                          u.editar_cantidades
                            ? "Deshabilitar la edición de pedidos"
                            : "Habilitar la edición de pedidos"
                        }
                        onClick={() => alternarEditarCantidades(u)}
                      >
                        <span
                          className={`toggle${
                            u.editar_cantidades ? " activo" : ""
                          }`}
                          aria-hidden="true"
                        >
                          <span className="toggle-bola" />
                        </span>
                        <span>
                          {u.editar_cantidades ? "Habilitado" : "Solo lectura"}
                        </span>
                      </button>
                    ) : (
                      <span className="badge badge-success">
                        Siempre activo
                      </span>
                    )}
                  </td>
                  <td>
                    <span
                      className={u.activo ? "badge badge-success" : "badge badge-danger"}
                    >
                      {u.activo ? "Activo" : "Inactivo"}
                    </span>
                  </td>
                  <td className="muted small usuarios-creado">
                    {formatearFechaHora(u.creado_en)}
                  </td>
                  <td className="actions usuarios-acciones">
                    <button
                      className="btn-secondary btn-small"
                      onClick={() => setCambiarClaveDe(u)}
                    >
                      <Icon nombre="candado" size={14} />
                      Cambiar clave
                    </button>
                    <button
                      className="btn-secondary btn-small"
                      onClick={() => alternarActivo(u)}
                    >
                      <Icon
                        nombre={u.activo ? "cerrar" : "check"}
                        size={14}
                      />
                      {u.activo ? "Desactivar" : "Activar"}
                    </button>
                    <button
                      className="btn-icon danger"
                      title="Eliminar"
                      onClick={() => setPorEliminar(u)}
                    >
                      <Icon nombre="eliminar" size={15} />
                    </button>
                  </td>
                </tr>
              ))}
              {usuarios.length === 0 && (
                <tr>
                  <td colSpan={7} className="empty-state">
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
      <section className="panel usuarios-permisos">
        <div className="usuarios-lista-head">
          <div>
            <h3>
              <Icon nombre="escudo" size={15} />
              Permisos por rol
            </h3>
            <p className="muted small">
              Alcance operativo de cada tipo de cuenta dentro del sistema
            </p>
          </div>
        </div>
        <div className="permisos-grid">
          <div className="permisos-bloque permisos-bloque--admin">
            <div className="permisos-bloque-head">
              <span className="permisos-bloque-icono">
                <Icon nombre="escudo" size={18} />
              </span>
              <div>
                <h4>Administrador</h4>
                <span className="badge badge-success">Acceso total</span>
              </div>
            </div>
            <ul>
              <li>
                <Icon nombre="check" size={14} />
                Acceso completo a todos los módulos
              </li>
              <li>
                <Icon nombre="check" size={14} />
                Inventario: crear, editar y eliminar
              </li>
              <li>
                <Icon nombre="check" size={14} />
                Mesas, Pedidos y Cuentas
              </li>
              <li>
                <Icon nombre="check" size={14} />
                Edición de pedidos y alias siempre habilitada
              </li>
              <li>
                <Icon nombre="check" size={14} />
                Reportes e Historial de ventas
              </li>
              <li>
                <Icon nombre="check" size={14} />
                Corte de caja
              </li>
              <li>
                <Icon nombre="check" size={14} />
                Creación y gestión de usuarios
              </li>
            </ul>
          </div>
          <div className="permisos-bloque permisos-bloque--bartender">
            <div className="permisos-bloque-head">
              <span className="permisos-bloque-icono">
                <Icon nombre="usuario" size={18} />
              </span>
              <div>
                <h4>Bartender</h4>
                <span className="badge badge-neutral">Acceso operativo</span>
              </div>
            </div>
            <ul>
              <li>
                <Icon nombre="check" size={14} />
                Mesas, Pedidos y Cuentas
              </li>
              <li>
                <Icon nombre="check" size={14} />
                Inventario en modo lectura; el Administrador puede habilitarle
                el ingreso de stock desde esta pantalla
              </li>
              <li>
                <Icon nombre="check" size={14} />
                Edición de pedidos en modo lectura; el Administrador puede
                habilitarlo por usuario
              </li>
              <li>
                <Icon nombre="check" size={14} />
                Corte de caja
              </li>
              <li className="permisos-item--no">
                <Icon nombre="cerrar" size={14} />
                Sin acceso a Reportes, Historial ni Usuarios
              </li>
            </ul>
          </div>
        </div>
      </section>
    </div>
  );
}
