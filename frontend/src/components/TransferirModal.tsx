/**
 * Ventana para transferir la cuenta abierta de una mesa a otra mesa.
 * Útil cuando los clientes cambian de mesa durante el servicio.
 */

import { useEffect, useState } from "react";
import { api } from "../services/api";

interface Mesa {
  id: number;
  numero: number;
  estado: string;
  tiene_cuenta_pendiente?: boolean;
}

interface Props {
  mesaId: number;
  onClose: () => void;
  onTransferido?: () => void;
}

export default function TransferirModal({ mesaId, onClose, onTransferido }: Props) {
  const [mesas, setMesas] = useState<Mesa[]>([]);
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

  const origen = mesas.find((m) => m.id === mesaId);

  const transferir = async () => {
    if (!destino) {
      setError("Selecciona la mesa de destino");
      return;
    }
    setProcesando(true);
    try {
      const res: any = await api.transferirCuenta(mesaId, Number(destino));
      setError(null);
      onTransferido?.();
      onClose();
      if (res?.mensaje) {
        // mensaje devuelto por la API
      }
    } catch (err: any) {
      setError(err.message);
      setProcesando(false);
    }
  };

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

        <p className="muted small">
          Se moverán el pedido abierto y las divisiones pendientes de la mesa{" "}
          <strong>Mesa {origen?.numero ?? "?"}</strong> a la mesa de destino.
        </p>

        <div className="form-group">
          <label>Mesa de destino</label>
          <select value={destino} onChange={(e) => setDestino(e.target.value ? Number(e.target.value) : "")}>
            <option value="">— Seleccionar mesa —</option>
            {mesas
              .filter((m) => m.id !== mesaId && !m.tiene_cuenta_pendiente)
              .map((m) => (
                <option key={m.id} value={m.id}>
                  Mesa {m.numero} ({m.estado})
                </option>
              ))}
          </select>
        </div>

        {mesas.filter((m) => m.id !== mesaId && m.tiene_cuenta_pendiente).length > 0 && (
          <p className="muted small">
            Las mesas con cuenta abierta no aparecen como destino.
          </p>
        )}

        <div className="modal-actions">
          <button className="btn-secondary" onClick={onClose} disabled={procesando}>
            Cancelar
          </button>
          <button
            className="btn-primary"
            onClick={transferir}
            disabled={procesando || !destino}
          >
            {procesando ? "Transfiriendo..." : "Transferir cuenta"}
          </button>
        </div>
      </div>
    </div>
  );
}
