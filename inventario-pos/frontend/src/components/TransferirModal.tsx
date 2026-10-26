/**
 * Ventana para transferir una cuenta abierta entre mesas y plazas de barra.
 * La cuenta puede originarse en una mesa o en una plaza de barra.
 */

import { useEffect, useMemo, useState } from "react";
import { api } from "../services/api";
import { formatearPrecio } from "../utils/format";

interface PosicionBarra {
  id: number;
  posicion: number;
  estado: string;
  total_cuenta: number;
}

interface Mesa {
  id: number;
  numero: number;
  estado: string;
  tipo: string;
  grupo: string | null;
  posicion: number;
  tiene_cuenta_pendiente?: boolean;
  posiciones?: PosicionBarra[];
}

interface Destino {
  id: number;
  label: string;
  tipo: "mesa" | "barra";
}

interface Props {
  /** Cuenta de mesa o plaza de barra que se transfiere. */
  mesaId?: number;
  /** Numero de barra: permite elegir entre sus cuentas abiertas. */
  barraNumero?: number;
  onClose: () => void;
  onTransferido?: () => void;
}

export default function TransferirModal({
  mesaId,
  barraNumero,
  onClose,
  onTransferido,
}: Props) {
  const [mesas, setMesas] = useState<Mesa[]>([]);
  const [origen, setOrigen] = useState<number | "">(mesaId ?? "");
  const [destino, setDestino] = useState<number | "">("");
  const [error, setError] = useState<string | null>(null);
  const [procesando, setProcesando] = useState(false);

  useEffect(() => {
    const cargar = async () => {
      try {
        const data: any = await api.getMesas();
        setMesas(data);
      } catch (err: any) {
        setError(err.message);
      }
    };
    cargar();
  }, []);

  /** Cuentas abiertas de la barra cuando el origen es una barra completa. */
  const cuentasOrigen = useMemo(() => {
    if (barraNumero == null) return [];
    const barra = mesas.find(
      (m) => m.tipo === "barra" && m.numero === barraNumero
    );
    if (!barra?.posiciones) return [];
    return barra.posiciones
      .filter((p) => p.total_cuenta > 0)
      .map((p) => ({
        id: p.id,
        posicion: p.posicion,
        total: p.total_cuenta,
      }));
  }, [mesas, barraNumero]);

  useEffect(() => {
    if (mesaId != null) {
      setOrigen(mesaId);
    } else if (cuentasOrigen.length > 0) {
      setOrigen(cuentasOrigen[0].id);
    }
  }, [mesaId, cuentasOrigen]);

  const origenInfo = useMemo(() => {
    if (origen === "") return null;
    const id = Number(origen);
    for (const mesa of mesas) {
      if (mesa.tipo === "barra") {
        const posicion = mesa.posiciones?.find((p) => p.id === id);
        if (posicion) return { mesa, posicion };
      } else if (mesa.id === id) {
        return { mesa, posicion: null };
      }
    }
    return null;
  }, [mesas, origen]);

  const etiquetaOrigen = origenInfo
    ? origenInfo.posicion
      ? `Barra ${origenInfo.mesa.numero} · Plaza ${origenInfo.posicion.posicion}`
      : `Mesa ${origenInfo.mesa.numero}`
    : "la cuenta seleccionada";

  /** Mesas y plazas de barra libres para recibir la cuenta. */
  const destinos = useMemo(() => {
    const libres: Destino[] = [];
    for (const mesa of mesas) {
      if (mesa.tipo === "barra") {
        const posiciones = mesa.posiciones || [];

        // La barra de origen nunca se ofrece como destino (ni sus otras plazas).
        if (barraNumero != null && mesa.numero === barraNumero) {
          continue;
        }

        // Si la barra está ocupada (aunque sea en otra plaza) no se ofrece
        // como destino: evita sumar dos cuentas en la misma barra.
        if (
          mesa.estado !== "disponible" ||
          mesa.tiene_cuenta_pendiente ||
          posiciones.some((p) => p.estado === "ocupada" || p.total_cuenta > 0)
        ) {
          continue;
        }

        // Tampoco se ofrece otra plaza de la misma barra de origen.
        if (posiciones.some((p) => p.id === Number(origen))) {
          continue;
        }

        posiciones.forEach((p, indice) => {
          if (p.estado === "ocupada" || p.total_cuenta > 0) return;
          libres.push({
            id: p.id,
            label: `Barra ${mesa.numero} · Plaza ${p.posicion ?? indice + 1}`,
            tipo: "barra",
          });
        });
        continue;
      }
      if (Number(origen) === mesa.id) continue;
      if (mesa.tiene_cuenta_pendiente) continue;
      libres.push({
        id: mesa.id,
        label: `Mesa ${mesa.numero}`,
        tipo: "mesa",
      });
    }
    return libres;
  }, [mesas, origen]);

  const etiquetaDestino =
    destinos.find((d) => d.id === Number(destino))?.label ||
    "la cuenta de destino";

  const transferir = async () => {
    if (!origen) {
      setError("Selecciona la cuenta de origen");
      return;
    }
    if (!destino) {
      setError("Selecciona la cuenta de destino");
      return;
    }
    setProcesando(true);
    try {
      await api.transferirCuenta(Number(origen), Number(destino));
      setError(null);
      onTransferido?.();
      onClose();
    } catch (err: any) {
      setError(err.message);
      setProcesando(false);
    }
  };

  const sinCuentasOrigen =
    barraNumero != null && cuentasOrigen.length === 0;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3>Transferir cuenta</h3>
          <button className="btn-icon" onClick={onClose} title="Cerrar">
            ×
          </button>
        </div>

        {error && <p className="error-msg">{error}</p>}

        {barraNumero != null && cuentasOrigen.length > 1 && (
          <div className="form-group">
            <label>Cuenta de la barra a transferir</label>
            <select
              value={origen}
              onChange={(e) =>
                setOrigen(e.target.value ? Number(e.target.value) : "")
              }
            >
              {cuentasOrigen.map((c) => (
                <option key={c.id} value={c.id}>
                  Plaza {c.posicion} — {formatearPrecio(c.total)}
                </option>
              ))}
            </select>
          </div>
        )}

        {sinCuentasOrigen && (
          <p className="muted small">
            Esta barra no tiene cuentas abiertas para transferir.
          </p>
        )}

        <p className="muted small">
          Se moverán el pedido abierto y las divisiones pendientes de{" "}
          <strong>{etiquetaOrigen}</strong> a <strong>{etiquetaDestino}</strong>.
        </p>

        <div className="form-group">
          <label>Cuenta de destino</label>
          <select
            value={destino}
            onChange={(e) =>
              setDestino(e.target.value ? Number(e.target.value) : "")
            }
            disabled={sinCuentasOrigen}
          >
            <option value="">— Seleccionar mesa o barra —</option>
            {destinos.some((d) => d.tipo === "mesa") && (
              <optgroup label="Mesas">
                {destinos
                  .filter((d) => d.tipo === "mesa")
                  .map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.label}
                    </option>
                  ))}
              </optgroup>
            )}
            {destinos.some((d) => d.tipo === "barra") && (
              <optgroup label="Barras (plazas libres)">
                {destinos
                  .filter((d) => d.tipo === "barra")
                  .map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.label}
                    </option>
                  ))}
              </optgroup>
            )}
          </select>
        </div>

        {destinos.length === 0 && !sinCuentasOrigen && (
          <p className="muted small">
            No hay mesas ni plazas de barra libres para recibir la cuenta.
          </p>
        )}

        <div className="modal-actions">
          <button className="btn-secondary" onClick={onClose} disabled={procesando}>
            Cancelar
          </button>
          <button
            className="btn-primary"
            onClick={transferir}
            disabled={procesando || !origen || !destino || sinCuentasOrigen}
          >
            {procesando ? "Transfiriendo..." : "Transferir cuenta"}
          </button>
        </div>
      </div>
    </div>
  );
}
