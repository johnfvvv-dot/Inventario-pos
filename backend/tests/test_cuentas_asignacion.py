"""Pruebas de integración de cuentas divididas y asignación de pedidos.

Se ejecutan con la base SQLite temporal configurada antes de importar la app:

    backend/venv/Scripts/python.exe -m unittest discover -s backend/tests -v
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

# La configuración de la base debe existir antes de importar app.database.
_TEMP_DIR = tempfile.mkdtemp(prefix="inventario_pos_test_")
_DB_PATH = Path(_TEMP_DIR) / "cuentas.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH.as_posix()}"
os.environ.setdefault("APP_TIMEZONE", "America/Bogota")

from fastapi.testclient import TestClient  # noqa: E402

from app.database import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    Division,
    Mesa,
    Participante,
    Pedido,
    PedidoItem,
)


class CuentasAsignacionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client_ctx = TestClient(app)
        cls.client = cls.client_ctx.__enter__()
        respuesta = cls.client.post(
            "/api/caja/abrir-turno",
            json={"usuario_id": 1, "fondo_inicial": 0},
        )
        assert respuesta.status_code == 200, respuesta.text
        productos = cls.client.get("/api/inventario/?limite=500").json()["items"]
        cls.productos = {p["nombre"]: p for p in productos}
        cls.p1 = cls.productos["Hamburguesa"]
        cls.p2 = cls.productos["Papas fritas"]
        cls.p3 = cls.productos["Refresco"]

    @classmethod
    def tearDownClass(cls):
        cls.client_ctx.__exit__(None, None, None)
        engine.dispose()
        shutil.rmtree(_TEMP_DIR, ignore_errors=True)

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------
    def crear_mesa(self, numero: int) -> dict:
        respuesta = self.client.post(
            "/api/mesas/",
            json={"numero": numero, "capacidad": 4, "estado": "disponible"},
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        return respuesta.json()

    def crear_barra(self, numero: int, capacidad: int = 2) -> list:
        respuesta = self.client.post(
            "/api/mesas/barra",
            json={"numero": numero, "capacidad": capacidad},
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        return respuesta.json()

    def crear_pedido(self, mesa_id: int, items: list, participante_id=None):
        cuerpo = {
            "mesa_id": mesa_id,
            "usuario_id": 1,
            "items": [
                {"producto_id": producto["id"], "cantidad": cantidad}
                for producto, cantidad in items
            ],
        }
        if participante_id is not None:
            cuerpo["participante_id"] = participante_id
        return self.client.post("/api/pedidos/", json=cuerpo)

    def dividir(self, participantes: list, mesa_id=None, barra_numero=None):
        cuerpo = {"usuario_id": 1, "participantes": participantes}
        if barra_numero is not None:
            cuerpo["barra_numero"] = barra_numero
        else:
            cuerpo["mesa_id"] = mesa_id
        return self.client.post("/api/cuentas/dividir", json=cuerpo)

    def cuenta(self, mesa_id: int) -> dict:
        respuesta = self.client.get(f"/api/cuentas/mesa/{mesa_id}")
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        return respuesta.json()

    def resumen_total(self) -> float:
        respuesta = self.client.get("/api/caja/resumen?dias=1")
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        return float(respuesta.json()["totales"]["total"])

    # ------------------------------------------------------------------
    # Casos
    # ------------------------------------------------------------------
    def test_asignacion_pagos_tickets_y_cierre(self):
        total_inicial = self.resumen_total()
        mesa = self.crear_mesa(101)

        # Cuenta general inicial: 2 hamburguesas + 1 papas = 21.
        respuesta = self.crear_pedido(
            mesa["id"], [(self.p1, 2), (self.p2, 1)]
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        pedido_original = respuesta.json()
        self.assertEqual(pedido_original["estado"], "abierto")

        # Pedro toma 1 hamburguesa; Juan toma 1 hamburguesa y las papas.
        respuesta = self.dividir(
            [
                {
                    "alias": "Pedro",
                    "items": [{"producto_id": self.p1["id"], "cantidad": 1}],
                },
                {
                    "alias": "Juan",
                    "items": [
                        {"producto_id": self.p1["id"], "cantidad": 1},
                        {"producto_id": self.p2["id"], "cantidad": 1},
                    ],
                },
            ],
            mesa_id=mesa["id"],
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        division = respuesta.json()
        participantes = {p["alias"]: p for p in division["participantes"]}
        pedro_id = participantes["Pedro"]["id"]
        juan_id = participantes["Juan"]["id"]
        self.assertEqual(participantes["Pedro"]["subtotal"], 9.0)
        self.assertEqual(participantes["Juan"]["subtotal"], 12.0)

        cuenta = self.cuenta(mesa["id"])
        self.assertEqual(cuenta["total_general"], 0.0)
        self.assertEqual(cuenta["total_divisiones"], 21.0)
        self.assertEqual(cuenta["total"], 21.0)

        # Nuevo pedido asignado a Pedro: 2 refrescos = 4.
        respuesta = self.crear_pedido(
            mesa["id"], [(self.p3, 2)], participante_id=pedro_id
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        pedido_pedro = respuesta.json()
        self.assertEqual(pedido_pedro["estado"], "dividido")
        self.assertEqual(pedido_pedro["participante_id"], pedro_id)
        self.assertEqual(pedido_pedro["alias"], "Pedro")
        self.assertEqual(pedido_pedro["total"], 4.0)

        cuenta = self.cuenta(mesa["id"])
        self.assertEqual(cuenta["total_general"], 0.0)
        self.assertEqual(cuenta["total_divisiones"], 25.0)
        pedro_cuenta = next(
            p
            for d in cuenta["divisiones"]
            for p in d["participantes"]
            if p["id"] == pedro_id
        )
        self.assertEqual(pedro_cuenta["subtotal"], 13.0)
        self.assertEqual(len(pedro_cuenta["items"]), 2)
        self.assertEqual(
            next(
                d["total"]
                for d in cuenta["divisiones"]
                if any(p["id"] == pedro_id for p in d["participantes"])
            ),
            25.0,
        )

        # Un pedido a la cuenta general no modifica los alias.
        respuesta = self.crear_pedido(mesa["id"], [(self.p2, 1)])
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        cuenta = self.cuenta(mesa["id"])
        self.assertEqual(cuenta["total_general"], 3.0)
        self.assertEqual(cuenta["total_divisiones"], 25.0)
        self.assertEqual(cuenta["total"], 28.0)

        # Pedro paga su parte: se materializa un pedido cerrado para caja.
        respuesta = self.client.post(
            f"/api/cuentas/participante/{pedro_id}/pagar?forma_pago=efectivo"
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        self.assertTrue(respuesta.json()["pagado"])

        db = SessionLocal()
        try:
            pedro = db.query(Participante).filter(Participante.id == pedro_id).first()
            self.assertIsNotNone(pedro.pedido_pago_id)
            pago_pedro = (
                db.query(Pedido)
                .filter(Pedido.id == pedro.pedido_pago_id)
                .first()
            )
            self.assertIsNotNone(pago_pedro)
            self.assertEqual(pago_pedro.estado, "cerrado")
            self.assertEqual(pago_pedro.es_pago_division, 1)
            self.assertEqual(pago_pedro.participante_id, pedro_id)
            self.assertEqual(pago_pedro.total, 13.0)
            self.assertEqual(pago_pedro.forma_pago, "efectivo")
            items_pago = (
                db.query(PedidoItem)
                .filter(PedidoItem.pedido_id == pago_pedro.id)
                .all()
            )
            self.assertEqual(
                round(sum(i.subtotal for i in items_pago), 2), 13.0
            )
            fecha_pago_pedro = pedro.fecha_pago
            pago_pedro_id = pago_pedro.id
        finally:
            db.close()

        # El ticket del alias incluye el pedido nuevo y no se duplica con el
        # ticket del pedido financiero.
        tickets = self.client.get("/api/caja/tickets").json()["tickets"]
        ticket_pedro = next(
            t for t in tickets if t["id"] == f"participante-{pedro_id}"
        )
        self.assertEqual(ticket_pedro["alias"], "Pedro")
        self.assertEqual(
            sum(i["cantidad"] for i in ticket_pedro["items"]), 3
        )
        self.assertFalse(
            any(t["id"] == f"pedido-{pago_pedro_id}" for t in tickets)
        )

        # Un alias pagado no admite nuevos pedidos.
        respuesta = self.crear_pedido(
            mesa["id"], [(self.p3, 1)], participante_id=pedro_id
        )
        self.assertEqual(respuesta.status_code, 409, respuesta.text)

        # Cerrar la cuenta cobra solo a Juan; el pago de Pedro no se toca.
        respuesta = self.client.post(
            f"/api/cuentas/mesa/{mesa['id']}/cerrar"
            "?liberar_mesa=true&forma_pago=tarjeta"
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.text)

        db = SessionLocal()
        try:
            pedro = db.query(Participante).filter(Participante.id == pedro_id).first()
            juan = db.query(Participante).filter(Participante.id == juan_id).first()
            division_db = db.query(Division).filter(Division.id == division["id"]).first()
            self.assertEqual(pedro.forma_pago, "efectivo")
            self.assertEqual(pedro.fecha_pago, fecha_pago_pedro)
            self.assertEqual(juan.forma_pago, "tarjeta")
            self.assertIsNotNone(juan.pedido_pago_id)
            self.assertEqual(division_db.estado, "pagada")
        finally:
            db.close()

        mesa_db = SessionLocal()
        try:
            estado_mesa = (
                mesa_db.query(Mesa).filter(Mesa.id == mesa["id"]).first().estado
            )
            self.assertEqual(estado_mesa, "disponible")
        finally:
            mesa_db.close()

        # Caja suma los dos pagos de alias y la cuenta general: 28.
        self.assertAlmostEqual(self.resumen_total() - total_inicial, 28.0, places=2)

        # Historial identifica el pago de Pedro con su alias.
        historial = self.client.get("/api/caja/historial?limite=100").json()["items"]
        pago_historial = next(
            h for h in historial if h["id"] == pago_pedro_id
        )
        self.assertEqual(pago_historial["alias"], "Pedro")
        self.assertEqual(pago_historial["total"], 13.0)

    def test_barra_asignacion_y_cuenta_agregada(self):
        barra = self.crear_barra(21, 2)
        posiciones = self.client.get("/api/mesas/").json()
        grupo = next(
            m for m in posiciones if m["tipo"] == "barra" and m["numero"] == 21
        )
        plaza_origen, plaza_alterna = grupo["posiciones"][0], grupo["posiciones"][1]

        respuesta = self.crear_pedido(
            plaza_origen["id"], [(self.p1, 1)]
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)

        respuesta = self.dividir(
            [
                {
                    "alias": "Ana",
                    "items": [{"producto_id": self.p1["id"], "cantidad": 1}],
                }
            ],
            barra_numero=21,
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        division = respuesta.json()
        ana_id = division["participantes"][0]["id"]

        # El pedido se crea en la plaza de la división, aunque el usuario esté
        # trabajando en otra plaza de la misma barra.
        respuesta = self.crear_pedido(
            plaza_alterna["id"], [(self.p3, 1)], participante_id=ana_id
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        pedido = respuesta.json()
        self.assertEqual(pedido["mesa"]["id"], division["mesa_id"])
        self.assertEqual(pedido["alias"], "Ana")

        pedidos_barra = self.client.get("/api/pedidos/barra/21").json()
        self.assertTrue(
            any(
                p["id"] == pedido["id"]
                and p["estado"] == "dividido"
                and p["participante_id"] == ana_id
                for p in pedidos_barra
            )
        )

        cuenta = self.client.get("/api/cuentas/barra/21").json()
        self.assertEqual(cuenta["total_general"], 0.0)
        self.assertEqual(cuenta["total_divisiones"], 11.0)
        self.assertEqual(cuenta["total"], 11.0)

        respuesta = self.client.post(
            f"/api/cuentas/participante/{ana_id}/pagar?forma_pago=transferencia"
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.text)

        cuenta = self.client.get("/api/cuentas/barra/21").json()
        self.assertEqual(cuenta["total"], 0.0)
        self.assertEqual(cuenta["estado_mesa"], "disponible")

    def test_transferencia_mueve_pedidos_asignados(self):
        origen = self.crear_mesa(102)
        destino = self.crear_mesa(103)

        respuesta = self.crear_pedido(origen["id"], [(self.p1, 1)])
        self.assertEqual(respuesta.status_code, 201, respuesta.text)

        respuesta = self.dividir(
            [
                {
                    "alias": "Luis",
                    "items": [{"producto_id": self.p1["id"], "cantidad": 1}],
                }
            ],
            mesa_id=origen["id"],
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        luis_id = respuesta.json()["participantes"][0]["id"]

        respuesta = self.crear_pedido(
            origen["id"], [(self.p3, 2)], participante_id=luis_id
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        pedido_asignado_id = respuesta.json()["id"]

        respuesta = self.client.post(
            f"/api/cuentas/mesa/{origen['id']}/transferir"
            f"?destino_id={destino['id']}"
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.text)

        db = SessionLocal()
        try:
            pedido = db.query(Pedido).filter(Pedido.id == pedido_asignado_id).first()
            division = (
                db.query(Division)
                .filter(Division.participantes.any(Participante.id == luis_id))
                .first()
            )
            self.assertEqual(pedido.mesa_id, destino["id"])
            self.assertEqual(division.mesa_id, destino["id"])
            origen_db = db.query(Mesa).filter(Mesa.id == origen["id"]).first()
            destino_db = db.query(Mesa).filter(Mesa.id == destino["id"]).first()
            self.assertEqual(origen_db.estado, "disponible")
            self.assertEqual(destino_db.estado, "ocupada")
        finally:
            db.close()

    def test_resumen_mesa_solo_muestra_pendiente(self):
        mesa = self.crear_mesa(104)
        respuesta = self.crear_pedido(mesa["id"], [(self.p1, 2)])
        self.assertEqual(respuesta.status_code, 201, respuesta.text)

        respuesta = self.dividir(
            [
                {
                    "alias": "Marta",
                    "items": [{"producto_id": self.p1["id"], "cantidad": 1}],
                },
                {
                    "alias": "Carlos",
                    "items": [{"producto_id": self.p1["id"], "cantidad": 1}],
                },
            ],
            mesa_id=mesa["id"],
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        participantes = {
            p["alias"]: p for p in respuesta.json()["participantes"]
        }

        respuesta = self.client.post(
            f"/api/cuentas/participante/{participantes['Marta']['id']}/pagar"
            "?forma_pago=efectivo"
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.text)

        listado = self.client.get("/api/mesas/").json()
        fila = next(m for m in listado if m["id"] == mesa["id"])
        self.assertEqual(fila["total_cuenta"], 9.0)
        self.assertIn("1 cliente pendiente", fila["detalle_pendiente"])


if __name__ == "__main__":
    unittest.main()
