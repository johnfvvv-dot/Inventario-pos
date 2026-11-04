/**
 * Servicios de conexión con el backend FastAPI.
 *
 * Modo híbrido:
 *  1. Si la app se abre desde el ejecutable o desde la IP LAN del PC, usa el
 *     backend local (mismo origen). Así la operación interna no depende de
 *     Render ni de su arranque en frío.
 *  2. Si el backend local no responde, usa automáticamente el backend público
 *     de Render.
 *  3. La URL del backend NO se puede forzar desde el entorno: siempre se
 *     detecta local primero y Render es el respaldo. Así un build antiguo o
 *     una variable mal configurada no puede dejar la app apuntando a un túnel
 *     temporal (ngrok) ni a una IP obsoleta.
 *
 * Variables de compilación:
 *  - REACT_APP_CLOUD_API_URL: URL pública de Render (se valida).
 *  - REACT_APP_LOCAL_API_URL: URL local explícita (solo localhost/LAN).
 *  - REACT_APP_API_URL: ignorada por seguridad (compatibilidad con builds viejos).
 */
export type ApiMode = "local" | "cloud";

export interface ApiInfo {
  base: string;
  mode: ApiMode;
}

const CLOUD_API_FALLBACK = "https://inventario-pos-api-pqju.onrender.com/api";

function normalizarBase(url: string): string {
  const limpia = url.trim().replace(/\/+$/, "");
  return /\/api$/i.test(limpia) ? limpia : `${limpia}/api`;
}

function esUrlLocalPermitida(url: string): boolean {
  try {
    const { protocol, hostname } = new URL(url);
    return (protocol === "http:" || protocol === "https:") && esIPPrivada(hostname);
  } catch {
    return false;
  }
}

function esUrlNubeValida(url: string): boolean {
  try {
    const { protocol, hostname } = new URL(url);
    return (
      protocol === "https:" &&
      !esIPPrivada(hostname) &&
      !/ngrok/i.test(hostname) &&
      hostname !== "localhost"
    );
  } catch {
    return false;
  }
}

function construirCloudApiUrl(): string {
  const configurada = process.env.REACT_APP_CLOUD_API_URL;
  if (!configurada) return CLOUD_API_FALLBACK;

  const normalizada = normalizarBase(configurada);
  if (!esUrlNubeValida(normalizada)) {
    console.warn(
      "[API] REACT_APP_CLOUD_API_URL no es una URL HTTPS válida; usando Render oficial."
    );
    return CLOUD_API_FALLBACK;
  }
  return normalizada;
}

const CLOUD_API_URL = construirCloudApiUrl();

const LOCAL_API_OVERRIDE = (() => {
  const configurada = process.env.REACT_APP_LOCAL_API_URL;
  if (!configurada) return "";

  const normalizada = normalizarBase(configurada);
  if (!esUrlLocalPermitida(normalizada)) {
    console.warn(
      "[API] REACT_APP_LOCAL_API_URL no es localhost/LAN; se ignora."
    );
    return "";
  }
  return normalizada;
})();

/** La sonda local debe ser rápida: no queremos retrasar el login. */
const LOCAL_PROBE_TIMEOUT_MS = 2500;
/** Sonda manual: Chrome puede mostrar el permiso de red local y esperar. */
const LOCAL_MANUAL_PROBE_TIMEOUT_MS = 30000;
/** Peticiones al backend local (mismo PC o LAN). */
const LOCAL_REQUEST_TIMEOUT_MS = 15000;
/** Render Free puede tardar 30–60 s en despertar; damos margen. */
const CLOUD_REQUEST_TIMEOUT_MS = 75000;

function esIPPrivada(host: string): boolean {
  return (
    host === "localhost" ||
    host === "127.0.0.1" ||
    host === "::1" ||
    host.endsWith(".local") ||
    /^10\./.test(host) ||
    /^192\.168\./.test(host) ||
    /^172\.(1[6-9]|2\d|3[01])\./.test(host)
  );
}

function origenDeApi(base: string): string {
  return base.replace(/\/api\/?$/i, "");
}

type EstadoPermisoRed = "granted" | "denied" | "prompt" | "unsupported";

/**
 * Estado del permiso "Local Network Access" (Chrome 142+).
 *
 * Una página pública (HTTPS) necesita permiso para consultar localhost. No
 * disparamos la sonda automática si el permiso aún no se concedió: así los
 * visitantes externos van directo a Render y no ven un aviso de red local.
 * El botón "Conectar al servidor local" del login sí puede solicitarlo.
 */
async function estadoPermisoRedLocal(): Promise<EstadoPermisoRed> {
  try {
    const estado = await navigator.permissions.query({
      name: "local-network-access" as PermissionName,
    });
    return estado.state as EstadoPermisoRed;
  } catch {
    // Navegador sin Local Network Access: se intenta la sonda normal.
    return "unsupported";
  }
}

/** Candidatos locales, en orden de preferencia. */
function candidatosLocales(): string[] {
  const { protocol, hostname, port } = window.location;
  const lista: string[] = [];
  const agregar = (base: string) => {
    const normalizada = normalizarBase(base);
    if (!lista.includes(normalizada)) lista.push(normalizada);
  };

  if (LOCAL_API_OVERRIDE) agregar(LOCAL_API_OVERRIDE);

  if (esIPPrivada(hostname)) {
    // Mismo origen: el .exe sirve frontend y API en el mismo puerto.
    agregar(`${protocol}//${hostname}${port ? `:${port}` : ""}/api`);
    agregar(`http://${hostname}:8000/api`);
  }

  // En el PC del negocio, el backend local escucha en localhost:8000.
  if (hostname !== "localhost" && hostname !== "127.0.0.1" && hostname !== "::1") {
    agregar("http://localhost:8000/api");
    agregar("http://127.0.0.1:8000/api");
  }

  return lista;
}

/** Comprueba que el backend responde y que es realmente Inventario POS. */
async function probarSalud(
  base: string,
  timeoutMs: number = LOCAL_PROBE_TIMEOUT_MS
): Promise<boolean> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const respuesta = await fetch(`${origenDeApi(base)}/health`, {
      method: "GET",
      cache: "no-store",
      headers: { Accept: "application/json" },
      signal: controller.signal,
    });
    if (!respuesta.ok) return false;
    const datos: any = await respuesta.json();
    return datos?.status === "healthy";
  } catch {
    return false;
  } finally {
    window.clearTimeout(timer);
  }
}

let apiInfo: ApiInfo | null = null;
let deteccionEnCurso: Promise<ApiInfo> | null = null;

/** Última elección de backend (null mientras se está detectando). */
export function getApiInfo(): ApiInfo | null {
  return apiInfo;
}

/**
 * Resuelve una sola vez por carga de página qué backend usar.
 * La detección se puede repetir recargando la página.
 */
export function resolverApiBase(): Promise<ApiInfo> {
  if (apiInfo) return Promise.resolve(apiInfo);
  if (deteccionEnCurso) return deteccionEnCurso;

  deteccionEnCurso = (async () => {
    const enRedLocal = esIPPrivada(window.location.hostname);
    const permiso = enRedLocal ? "granted" : await estadoPermisoRedLocal();

    if (enRedLocal || permiso === "granted" || permiso === "unsupported") {
      for (const base of candidatosLocales()) {
        if (await probarSalud(base)) {
          apiInfo = { base, mode: "local" };
          console.info(`[API] Backend local detectado: ${base}`);
          return apiInfo;
        }
      }
    } else {
      console.info(
        `[API] Origen público sin permiso de red local (${permiso}); usando Render.`
      );
    }

    apiInfo = { base: CLOUD_API_URL, mode: "cloud" };
    console.info(`[API] Usando Render: ${CLOUD_API_URL}`);
    return apiInfo;
  })().finally(() => {
    deteccionEnCurso = null;
  });

  return deteccionEnCurso;
}

function usarNube(): ApiInfo {
  apiInfo = { base: CLOUD_API_URL, mode: "cloud" };
  return apiInfo;
}

/**
 * Reintenta la detección local desde un clic del usuario.
 *
 * Chrome 142+ exige el permiso "Local Network Access" para que una página
 * pública (HTTPS) consulte localhost o la red local. El clic del usuario
 * permite mostrar ese aviso y esperar a que lo conceda.
 */
export async function redetectarApiLocal(): Promise<ApiInfo | null> {
  for (const base of candidatosLocales()) {
    if (await probarSalud(base, LOCAL_MANUAL_PROBE_TIMEOUT_MS)) {
      apiInfo = { base, mode: "local" };
      console.info(`[API] Backend local detectado manualmente: ${base}`);
      return apiInfo;
    }
  }
  return null;
}

/** Error de red (no de negocio): permite reintentar contra Render. */
class ErrorRed extends Error {
  readonly esErrorRed = true;
}

/** Convierte los errores de validación de FastAPI en un texto legible. */
function detalleError(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item: any) => {
        const campo = Array.isArray(item?.loc)
          ? item.loc[item.loc.length - 1]
          : "";
        const mensaje = item?.msg || "Dato inválido";
        return campo ? `${campo}: ${mensaje}` : mensaje;
      })
      .join(" · ");
  }
  if (detail && typeof detail === "object") return JSON.stringify(detail);
  return "";
}

/**
 * Valida un identificador antes de construir la URL.
 *
 * Evita enviar `NaN`, `undefined` o cadenas vacías a rutas como
 * `/cuentas/barra/{n}/cerrar` o `/mesas/{id}/liberar`, que no coinciden con
 * la ruta del backend y terminan respondiendo "Method Not Allowed".
 */
function idPositivo(valor: number, nombre: string): number {
  const numero = Number(valor);
  if (!Number.isInteger(numero) || numero <= 0) {
    throw new Error(
      `${nombre} no válido. Cierra la ventana y vuelve a abrir la cuenta.`
    );
  }
  return numero;
}

async function ejecutarFetch<T>(
  info: ApiInfo,
  url: string,
  options: RequestInit
): Promise<T> {
  const timeout =
    info.mode === "cloud" ? CLOUD_REQUEST_TIMEOUT_MS : LOCAL_REQUEST_TIMEOUT_MS;
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeout);

  let response: Response;
  try {
    // Garantiza que la base no termine en slash y que url empiece con uno.
    const cleanBase = info.base.replace(/\/$/, "");
    const cleanUrl = url.startsWith("/") ? url : `/${url}`;

    response = await fetch(`${cleanBase}${cleanUrl}`, {
      headers: {
        "Content-Type": "application/json",
      },
      signal: controller.signal,
      ...options,
    });
  } catch (err: any) {
    if (err?.name === "AbortError") {
      throw new ErrorRed(
        `El backend no respondió en ${Math.round(timeout / 1000)} s ` +
          `(${info.base}).` +
          (info.mode === "cloud"
            ? " Render puede tardar 30–60 s en despertar; intenta de nuevo."
            : " Verifica que InventarioPOS.exe siga abierto.")
      );
    }
    throw new ErrorRed(
      `No se pudo conectar con el backend (${info.base}).` +
        (info.mode === "cloud"
          ? " Revisa la conexión a internet e intenta de nuevo."
          : " Verifica que InventarioPOS.exe esté abierto y que el celular esté en la misma WiFi.")
    );
  } finally {
    window.clearTimeout(timer);
  }

  if (!response.ok) {
    let detail = `Error ${response.status}`;
    try {
      const body = await response.json();
      detail = detalleError(body.detail) || detail;
    } catch {
      /* respuesta sin JSON */
    }
    throw new Error(detail);
  }

  return response.json() as Promise<T>;
}

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  let info = await resolverApiBase();

  try {
    return await ejecutarFetch<T>(info, url, options);
  } catch (err: any) {
    // Solo reintentamos operaciones seguras (lectura y login). Un POST de
    // venta no se repite automáticamente para no duplicar cobros.
    const metodo = (options.method || "GET").toUpperCase();
    const reintentable =
      metodo === "GET" || metodo === "HEAD" || url === "/usuarios/login";

    if (
      info.mode === "local" &&
      err?.esErrorRed === true &&
      reintentable
    ) {
      console.warn(
        "[API] El backend local dejó de responder; reintentando con Render."
      );
      info = usarNube();
      return ejecutarFetch<T>(info, url, options);
    }

    throw err;
  }
}

export const FORMAS_PAGO = [
  { id: "efectivo", label: "Efectivo" },
  { id: "tarjeta", label: "Tarjeta" },
  { id: "transferencia", label: "Transferencia" },
];

export const api = {
  // ---------- Configuración ----------
  getConfig: () => request("/config"),

  // ---------- Usuarios ----------
  login: (usuario: string, password: string) =>
    request("/usuarios/login", {
      method: "POST",
      body: JSON.stringify({ usuario, password }),
    }),

  getUsuarios: () => request("/usuarios/"),

  /** Consulta un usuario; sirve para refrescar permisos en la sesión activa. */
  getUsuario: (usuarioId: number) => request(`/usuarios/${usuarioId}`),

  createUsuario: (datos: {
    alias: string;
    nombre?: string;
    password?: string;
    rol: string;
  }) =>
    request("/usuarios/", {
      method: "POST",
      body: JSON.stringify(datos),
    }),

  updateUsuario: (
    usuarioId: number,
    datos: {
      alias?: string;
      nombre?: string;
      rol?: string;
      activo?: boolean;
      ingreso_stock?: boolean;
    }
  ) =>
    request(`/usuarios/${usuarioId}`, {
      method: "PUT",
      body: JSON.stringify(datos),
    }),

  cambiarClave: (usuarioId: number, password: string) =>
    request(`/usuarios/${usuarioId}/clave`, {
      method: "PUT",
      body: JSON.stringify({ password }),
    }),

  deleteUsuario: (usuarioId: number) =>
    request(`/usuarios/${usuarioId}`, { method: "DELETE" }),

  // ---------- Mesas ----------
  getMesas: () => request("/mesas/"),

  createMesa: (numero: number, capacidad: number) =>
    request("/mesas/", {
      method: "POST",
      body: JSON.stringify({ numero, capacidad, estado: "disponible" }),
    }),

  updateMesaEstado: (mesaId: number, nuevo_estado: string) =>
    request(`/mesas/${idPositivo(mesaId, "Mesa")}/estado`, {
      method: "PUT",
      body: JSON.stringify({ nuevo_estado }),
    }),

  /** Libera la mesa solo si no tiene cuentas pendientes */
  liberarMesa: (mesaId: number) =>
    request(`/mesas/${idPositivo(mesaId, "Mesa")}/liberar`, { method: "POST" }),

  /** Elimina una mesa o una barra completa (incluidas todas sus plazas) */
  deleteMesa: (mesaId: number) =>
    request(`/mesas/${idPositivo(mesaId, "Mesa")}`, { method: "DELETE" }),

  /** Crea una barra: una cuenta por cada plaza (cliente) */
  createBarra: (numero: number, capacidad: number) =>
    request("/mesas/barra", {
      method: "POST",
      body: JSON.stringify({ numero, capacidad }),
    }),

  /** Asigna un cliente a una mesa o a un puesto libre de la barra */
  ocuparMesa: (mesaId: number) =>
    request(`/mesas/${idPositivo(mesaId, "Mesa")}/ocupar`, { method: "POST" }),

  // ---------- Cuentas de mesa ----------
  getCuentaMesa: (mesaId: number) =>
    request(`/cuentas/mesa/${idPositivo(mesaId, "Mesa")}`),

  /** Cuenta agregada de una barra (todos sus puestos) */
  getCuentaBarra: (numeroBarra: number) =>
    request(`/cuentas/barra/${idPositivo(numeroBarra, "Barra")}`),

  /** Cierra la cuenta; con liberarMesa=true la mesa queda disponible */
  cerrarCuentaMesa: (mesaId: number, liberarMesa = false, formaPago = "efectivo") =>
    request(
      `/cuentas/mesa/${idPositivo(mesaId, "Mesa")}/cerrar?liberar_mesa=${liberarMesa}&forma_pago=${formaPago}`,
      { method: "POST" }
    ),

  /** Cierra la cuenta agregada de una barra; con liberarBarra=true queda disponible */
  cerrarCuentaBarra: (
    numeroBarra: number,
    liberarBarra = false,
    formaPago = "efectivo"
  ) =>
    request(
      `/cuentas/barra/${idPositivo(numeroBarra, "Barra")}/cerrar?liberar_barra=${liberarBarra}&forma_pago=${formaPago}`,
      { method: "POST" }
    ),

  /** Transfiere la cuenta abierta a otra mesa */
  transferirCuenta: (mesaId: number, destinoId: number) =>
    request(
      `/cuentas/mesa/${idPositivo(mesaId, "Mesa")}/transferir?destino_id=${idPositivo(
        destinoId,
        "Destino"
      )}`,
      { method: "POST" }
    ),

  // ---------- Inventario ----------
  /** Inventario con búsqueda, filtro por categoría y paginación */
  getProductos: (filtros: {
    buscar?: string;
    categoria_id?: number | null;
    limite?: number;
    offset?: number;
  } = {}) => {
    const params = new URLSearchParams();
    if (filtros.buscar) params.append("buscar", filtros.buscar);
    if (filtros.categoria_id) params.append("categoria_id", String(filtros.categoria_id));
    params.append("limite", String(filtros.limite ?? 50));
    params.append("offset", String(filtros.offset ?? 0));
    return request(`/inventario/?${params.toString()}`);
  },

  createProducto: (datos: {
    nombre: string;
    descripcion?: string;
    precio: number;
    precio_compra: number;
    stock: number;
    categoria_id?: number | null;
  }) =>
    request("/inventario/", {
      method: "POST",
      body: JSON.stringify(datos),
    }),

  updateProductoStock: (productoId: number, nuevo_stock: number) =>
    request(`/inventario/${productoId}/stock`, {
      method: "PUT",
      body: JSON.stringify({ nuevo_stock }),
    }),

  /** Suma (o resta) una cantidad al stock actual de forma atómica. */
  ajustarStock: (productoId: number, delta: number) =>
    request(`/inventario/${productoId}/stock/ajuste`, {
      method: "POST",
      body: JSON.stringify({ delta }),
    }),

  deleteProducto: (productoId: number) =>
    request(`/inventario/${productoId}`, { method: "DELETE" }),

  updateProducto: (productoId: number, datos: {
    nombre: string;
    descripcion?: string;
    precio: number;
    precio_compra: number;
    stock: number;
    categoria_id?: number | null;
  }) =>
    request(`/inventario/${productoId}`, {
      method: "PUT",
      body: JSON.stringify(datos),
    }),

  // ---------- Categorias ----------
  getCategorias: () => request("/categorias/"),

  createCategoria: (nombre: string) =>
    request("/categorias/", {
      method: "POST",
      body: JSON.stringify({ nombre }),
    }),

  actualizarCategoria: (categoriaId: number, nombre: string) =>
    request(`/categorias/${categoriaId}`, {
      method: "PUT",
      body: JSON.stringify({ nombre }),
    }),

  eliminarCategoria: (categoriaId: number) =>
    request(`/categorias/${categoriaId}`, { method: "DELETE" }),

  // ---------- Pedidos ----------
  getPedidos: () => request("/pedidos/"),

  getPedidosMesa: (mesaId: number) =>
    request(`/pedidos/mesa/${idPositivo(mesaId, "Mesa")}`),

  createPedido: (datos: {
    mesa_id: number;
    usuario_id: number;
    items: { producto_id: number; cantidad: number }[];
  }) =>
    request("/pedidos/", {
      method: "POST",
      body: JSON.stringify(datos),
    }),

  /** Ajusta la cantidad de una línea de un pedido abierto (0 = eliminar) */
  ajustarItemPedido: (pedidoId: number, itemId: number, cantidad: number) =>
    request(`/pedidos/${pedidoId}/items/${itemId}`, {
      method: "PUT",
      body: JSON.stringify({ cantidad }),
    }),

  closePedido: (pedidoId: number, formaPago = "efectivo") =>
    request(`/pedidos/${pedidoId}/cerrar?forma_pago=${formaPago}`, {
      method: "PUT",
    }),

  // ---------- División de cuenta ----------
  dividirCuenta: (datos: {
    mesa_id?: number;
    barra_numero?: number;
    usuario_id: number;
    participantes: { alias: string; items: { producto_id: number; cantidad: number }[] }[];
  }) =>
    request("/cuentas/dividir", {
      method: "POST",
      body: JSON.stringify(datos),
    }),

  getDivisionesMesa: (mesaId: number) =>
    request(`/cuentas/mesa/${idPositivo(mesaId, "Mesa")}/divisiones`),

  pagarDivision: (divisionId: number, formaPago = "efectivo") =>
    request(
      `/cuentas/division/${idPositivo(divisionId, "División")}/pagar?forma_pago=${formaPago}`,
      { method: "POST" }
    ),

  /** Cierra solo la cuenta de un alias (el cliente paga su parte) */
  pagarParticipante: (participanteId: number, formaPago = "efectivo") =>
    request(
      `/cuentas/participante/${idPositivo(
        participanteId,
        "Cliente"
      )}/pagar?forma_pago=${formaPago}`,
      { method: "POST" }
    ),

  // ---------- Corte de caja ----------
  getTurnoActual: () => request("/caja/turno-actual"),

  abrirTurno: (usuarioId = 1) =>
    request(`/caja/abrir?usuario_id=${usuarioId}`, { method: "POST" }),

  cerrarTurno: (observaciones?: string) =>
    request("/caja/cerrar", {
      method: "POST",
      body: JSON.stringify({ observaciones: observaciones || null }),
    }),

  getTurnos: (limite = 20) => request(`/caja/turnos?limite=${limite}`),

  /** Turno abierto ayer (se identifica por fecha de apertura). */
  getTurnoAyer: () => request("/caja/turno-ayer"),

  /** Años que tienen ventas registradas (para el filtro de Reportes). */
  getAniosVentas: (): Promise<number[]> => request("/caja/anios-ventas"),

  getResumenCaja: (dias = 1, offsetDias = 0, desde?: string, hasta?: string) => {
    const params = new URLSearchParams({
      dias: String(dias),
      offset_dias: String(offsetDias),
    });
    if (desde) params.append("desde", desde);
    if (hasta) params.append("hasta", hasta);
    return request(`/caja/resumen?${params.toString()}`);
  },

  getVentasPorDia: (
    dias = 14,
    offsetDias = 0,
    desde?: string,
    hasta?: string
  ) => {
    const params = new URLSearchParams({
      dias: String(dias),
      offset_dias: String(offsetDias),
    });
    if (desde) params.append("desde", desde);
    if (hasta) params.append("hasta", hasta);
    return request(`/caja/ventas-por-dia?${params.toString()}`);
  },

  /** Historial de ventas con filtros */
  getHistorial: (filtros: {
    desde?: string;
    hasta?: string;
    mesa?: number | null;
    producto?: number | null;
    forma_pago?: string | null;
    limite?: number;
    offset?: number;
  } = {}) => {
    const params = new URLSearchParams();
    if (filtros.desde) params.append("desde", filtros.desde);
    if (filtros.hasta) params.append("hasta", filtros.hasta);
    if (filtros.mesa) params.append("mesa", String(filtros.mesa));
    if (filtros.producto) params.append("producto", String(filtros.producto));
    if (filtros.forma_pago) params.append("forma_pago", filtros.forma_pago);
    params.append("limite", String(filtros.limite ?? 50));
    params.append("offset", String(filtros.offset ?? 0));
    return request(`/caja/historial?${params.toString()}`);
  },
};