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
    Usuario,
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

    def stock_de(self, producto: dict) -> int:
        respuesta = self.client.get("/api/inventario/?limite=500")
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        fila = next(
            p for p in respuesta.json()["items"] if p["id"] == producto["id"]
        )
        return int(fila["stock"])

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

    def crear_usuario_bartender(self, alias: str) -> dict:
        respuesta = self.client.post(
            "/api/usuarios/",
            json={
                "alias": alias,
                "nombre": alias,
                "rol": "bartender",
                "password": "1234",
            },
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        return respuesta.json()

    def test_permiso_editar_cantidades(self):
        mesa = self.crear_mesa(105)
        respuesta = self.crear_pedido(
            mesa["id"], [(self.p1, 2), (self.p2, 1)]
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        pedido = respuesta.json()
        item_hamburguesa = next(
            i for i in pedido["items"] if i["producto_id"] == self.p1["id"]
        )

        bartender = self.crear_usuario_bartender("Bartender Cantidades")
        self.assertFalse(bartender["editar_cantidades"])
        url = (
            f"/api/pedidos/{pedido['id']}/items/{item_hamburguesa['id']}"
            f"?usuario_id={bartender['id']}"
        )

        # Sin permiso, el backend rechaza el ajuste.
        respuesta = self.client.put(url, json={"cantidad": 3})
        self.assertEqual(respuesta.status_code, 403, respuesta.text)

        # El administrador habilita el permiso y ahora sí puede ajustar.
        respuesta = self.client.put(
            f"/api/usuarios/{bartender['id']}",
            json={"editar_cantidades": True},
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        self.assertTrue(respuesta.json()["editar_cantidades"])

        respuesta = self.client.put(url, json={"cantidad": 3})
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        self.assertEqual(respuesta.json()["total"], 30.0)

        respuesta = self.client.put(url, json={"cantidad": 2})
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        self.assertEqual(respuesta.json()["total"], 21.0)

    def test_alias_ajuste_y_cierre_general_independiente(self):
        total_inicial = self.resumen_total()
        mesa = self.crear_mesa(106)
        respuesta = self.crear_pedido(mesa["id"], [(self.p1, 1)])
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        pedido_general = respuesta.json()

        # Crear alias vacío desde el panel de la cuenta.
        respuesta = self.client.post(
            "/api/cuentas/alias",
            json={
                "mesa_id": mesa["id"],
                "usuario_id": 1,
                "alias": "Cliente Vacío",
            },
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        division = respuesta.json()
        self.assertEqual(division["total"], 0.0)
        self.assertEqual(
            [p["alias"] for p in division["participantes"]], ["Cliente Vacío"]
        )

        # El mismo alias no se puede duplicar en la cuenta.
        respuesta = self.client.post(
            "/api/cuentas/alias",
            json={
                "mesa_id": mesa["id"],
                "usuario_id": 1,
                "alias": "cliente vacío",
            },
        )
        self.assertEqual(respuesta.status_code, 409, respuesta.text)

        # Crear alias directamente al cargar un pedido desde Pedidos.
        respuesta = self.client.post(
            "/api/pedidos/",
            json={
                "mesa_id": mesa["id"],
                "usuario_id": 1,
                "nuevo_alias": "Cliente Pedido",
                "items": [{"producto_id": self.p3["id"], "cantidad": 1}],
            },
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        pedido_alias = respuesta.json()
        self.assertEqual(pedido_alias["estado"], "dividido")
        self.assertEqual(pedido_alias["alias"], "Cliente Pedido")
        self.assertIsNotNone(pedido_alias["participante_id"])

        cuenta = self.cuenta(mesa["id"])
        self.assertEqual(len(cuenta["divisiones"]), 1)
        aliases = {
            p["alias"]: p for p in cuenta["divisiones"][0]["participantes"]
        }
        self.assertEqual(set(aliases), {"Cliente Vacío", "Cliente Pedido"})
        cliente_pedido = aliases["Cliente Pedido"]
        item_alias = cliente_pedido["items"][0]

        bartender = self.crear_usuario_bartender("Bartender Alias")
        url_ajuste = (
            f"/api/cuentas/participante-item/{item_alias['participante_item_id']}"
            f"?usuario_id={bartender['id']}"
        )
        respuesta = self.client.put(url_ajuste, json={"cantidad": 2})
        self.assertEqual(respuesta.status_code, 403, respuesta.text)

        respuesta = self.client.put(
            f"/api/usuarios/{bartender['id']}",
            json={"editar_cantidades": True},
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        stock_antes_ajuste = self.stock_de(self.p3)
        respuesta = self.client.put(url_ajuste, json={"cantidad": 2})
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        ajuste = respuesta.json()
        self.assertFalse(ajuste["eliminado"])
        self.assertEqual(ajuste["subtotal"], 4.0)
        self.assertEqual(ajuste["total_division"], 4.0)
        # Aumentar la cantidad descuenta la diferencia del inventario.
        self.assertEqual(self.stock_de(self.p3), stock_antes_ajuste - 1)

        # El pedido vinculado y su total también se actualizan.
        db = SessionLocal()
        try:
            pedido_db = db.query(Pedido).filter(Pedido.id == pedido_alias["id"]).first()
            self.assertEqual(pedido_db.total, 4.0)
            item_db = next(
                i for i in pedido_db.items if i.producto_id == self.p3["id"]
            )
            self.assertEqual(item_db.cantidad, 2)
        finally:
            db.close()

        # Cobrar primero la Cuenta General no toca las divisiones ni libera la mesa.
        respuesta = self.client.post(
            f"/api/cuentas/mesa/{mesa['id']}/cerrar-general"
            f"?forma_pago=efectivo&usuario_id={bartender['id']}"
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        cuenta = respuesta.json()
        self.assertEqual(cuenta["total_general"], 0.0)
        self.assertEqual(cuenta["total_divisiones"], 4.0)
        self.assertEqual(cuenta["estado_mesa"], "ocupada")
        self.assertEqual(len(cuenta["divisiones"]), 1)

        # El pedido general quedó auditado con el usuario que cobró.
        db = SessionLocal()
        try:
            pedido_db = (
                db.query(Pedido)
                .filter(Pedido.id == pedido_general["id"])
                .first()
            )
            self.assertEqual(pedido_db.estado, "cerrado")
            self.assertEqual(pedido_db.usuario_cierre_id, bartender["id"])
            pedido_alias_db = (
                db.query(Pedido).filter(Pedido.id == pedido_alias["id"]).first()
            )
            self.assertEqual(pedido_alias_db.estado, "dividido")
        finally:
            db.close()

        # Cobrar el alias tampoco duplica el cobro general.
        respuesta = self.client.post(
            f"/api/cuentas/participante/{cliente_pedido['id']}/pagar"
            f"?forma_pago=tarjeta&usuario_id={bartender['id']}"
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        pagado = respuesta.json()
        self.assertTrue(pagado["pagado"])
        self.assertEqual(pagado["forma_pago"], "tarjeta")
        self.assertIsNotNone(pagado["fecha_pago"])

        db = SessionLocal()
        try:
            cliente_db = (
                db.query(Participante)
                .filter(Participante.id == cliente_pedido["id"])
                .first()
            )
            pago_db = (
                db.query(Pedido)
                .filter(Pedido.id == cliente_db.pedido_pago_id)
                .first()
            )
            self.assertEqual(pago_db.total, 4.0)
            self.assertEqual(pago_db.usuario_cierre_id, bartender["id"])
            self.assertEqual(pago_db.participante_id, cliente_pedido["id"])
            pago_id = pago_db.id
        finally:
            db.close()

        # La división sigue pendiente por el alias vacío y la mesa ocupada.
        cuenta = self.cuenta(mesa["id"])
        self.assertEqual(cuenta["estado_mesa"], "ocupada")
        self.assertEqual(len(cuenta["divisiones"]), 1)
        self.assertEqual(cuenta["divisiones"][0]["total_pendiente"], 0.0)

        # Caja suma exactamente la cuenta general (9) y el alias (4).
        self.assertAlmostEqual(
            self.resumen_total() - total_inicial, 13.0, places=2
        )

        # El ticket del alias aparece una sola vez y el pago financiero no.
        tickets = self.client.get("/api/caja/tickets").json()["tickets"]
        self.assertTrue(
            any(
                t["id"] == f"participante-{cliente_pedido['id']}"
                for t in tickets
            )
        )
        self.assertTrue(
            any(t["id"] == f"pedido-{pedido_general['id']}" for t in tickets)
        )
        # El pedido financiero del alias no genera un ticket duplicado.
        self.assertFalse(any(t["id"] == f"pedido-{pago_id}" for t in tickets))

    def test_eliminar_linea_alias_limpia_division_y_mesa(self):
        mesa = self.crear_mesa(107)
        respuesta = self.crear_pedido(mesa["id"], [(self.p1, 1)])
        self.assertEqual(respuesta.status_code, 201, respuesta.text)

        respuesta = self.dividir(
            [
                {
                    "alias": "Cliente Único",
                    "items": [{"producto_id": self.p1["id"], "cantidad": 1}],
                }
            ],
            mesa_id=mesa["id"],
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        division = respuesta.json()
        participante = division["participantes"][0]
        item_id = participante["items"][0]["id"]

        # El pedido descontó 1 unidad; dividir no vuelve a tocar el stock.
        stock_con_pedido = self.stock_de(self.p1)

        respuesta = self.client.put(
            f"/api/cuentas/participante-item/{item_id}?usuario_id=1",
            json={"cantidad": 0},
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        ajuste = respuesta.json()
        self.assertTrue(ajuste["eliminado"])

        # Al eliminar la línea se devuelve la unidad al inventario.
        self.assertEqual(self.stock_de(self.p1), stock_con_pedido + 1)
        self.assertIsNone(ajuste["participante_id"])
        self.assertIsNone(ajuste["division_id"])
        self.assertEqual(ajuste["total_division"], 0.0)

        db = SessionLocal()
        try:
            self.assertEqual(
                db.query(Division).filter(Division.id == division["id"]).count(),
                0,
            )
            mesa_db = db.query(Mesa).filter(Mesa.id == mesa["id"]).first()
            self.assertEqual(mesa_db.estado, "disponible")
            self.assertIsNone(mesa_db.fecha_ocupacion)
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
        self.assertTrue(fila["tiene_cuenta_pendiente"])
        # Las tarjetas ya no muestran el detalle textual de pendientes.
        self.assertEqual(fila["detalle_pendiente"], "")


    def test_primer_pedido_puede_iniciar_division_sin_cuenta_general(self):
        mesa = self.crear_mesa(108)

        # El primer pedido de la mesa puede nacer directamente en un alias:
        # no se crea una Cuenta General previa.
        respuesta = self.client.post(
            "/api/pedidos/",
            json={
                "mesa_id": mesa["id"],
                "usuario_id": 1,
                "nuevo_alias": "John",
                "items": [{"producto_id": self.p1["id"], "cantidad": 2}],
            },
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        pedido = respuesta.json()
        self.assertEqual(pedido["estado"], "dividido")
        self.assertEqual(pedido["alias"], "John")
        self.assertIsNotNone(pedido["participante_id"])

        cuenta = self.cuenta(mesa["id"])
        self.assertEqual(cuenta["total_general"], 0.0)
        self.assertEqual(cuenta["total_divisiones"], 18.0)
        self.assertEqual(cuenta["total"], 18.0)
        self.assertEqual(cuenta["estado_mesa"], "ocupada")
        self.assertEqual(len(cuenta["divisiones"]), 1)
        participantes = cuenta["divisiones"][0]["participantes"]
        self.assertEqual([p["alias"] for p in participantes], ["John"])
        self.assertEqual(participantes[0]["subtotal"], 18.0)
        self.assertEqual(len(participantes[0]["items"]), 1)

        # Los pedidos posteriores pueden elegir Cuenta General o el alias John.
        respuesta = self.crear_pedido(mesa["id"], [(self.p3, 1)])
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        self.assertEqual(respuesta.json()["estado"], "abierto")

        respuesta = self.crear_pedido(
            mesa["id"],
            [(self.p3, 1)],
            participante_id=pedido["participante_id"],
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        self.assertEqual(respuesta.json()["estado"], "dividido")

        cuenta = self.cuenta(mesa["id"])
        self.assertEqual(cuenta["total_general"], 2.0)
        self.assertEqual(cuenta["total_divisiones"], 20.0)
        self.assertEqual(cuenta["total"], 22.0)

    def test_administrador_siempre_puede_editar_cantidades(self):
        mesa = self.crear_mesa(109)
        respuesta = self.crear_pedido(mesa["id"], [(self.p1, 1)])
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        pedido = respuesta.json()
        item = pedido["items"][0]

        # El Administrador no depende del permiso de edición de pedidos.
        db = SessionLocal()
        try:
            admin = db.query(Usuario).filter(Usuario.id == 1).first()
            self.assertEqual(admin.rol, "admin")
            self.assertFalse(bool(admin.editar_cantidades))
        finally:
            db.close()

        respuesta = self.client.put(
            f"/api/pedidos/{pedido['id']}/items/{item['id']}?usuario_id=1",
            json={"cantidad": 2},
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        self.assertEqual(respuesta.json()["total"], 18.0)


if __name__ == "__main__":
    unittest.main()
