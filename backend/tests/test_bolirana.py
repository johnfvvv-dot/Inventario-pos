"""Pruebas de integración del módulo de Bolirana.

Cubre el flujo completo: activación del módulo, candados de mesas, carga de
bebidas, liquidación entre perdedores y cobro del cargo de un jugador libre.
"""

import unittest

# La configuración de la base debe existir antes de importar app.database.
from tests import _entorno  # noqa: F401,E402

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


class BoliranaTest(unittest.TestCase):
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
        cls.refresco = cls.productos["Refresco"]
        cls.hamburguesa = cls.productos["Hamburguesa"]

    @classmethod
    def tearDownClass(cls):
        cls.client_ctx.__exit__(None, None, None)

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

    def ocupar_mesa(self, mesa_id: int) -> None:
        respuesta = self.client.post(f"/api/mesas/{mesa_id}/ocupar")
        self.assertEqual(respuesta.status_code, 200, respuesta.text)

    def crear_bolirana(self, nombre: str, usuario_id: int = 1) -> dict:
        respuesta = self.client.post(
            "/api/boliranas/",
            json={"nombre": nombre, "usuario_id": usuario_id},
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        return respuesta.json()

    def iniciar_partida(self, bolirana_id: int, participantes: list) -> dict:
        respuesta = self.client.post(
            f"/api/boliranas/{bolirana_id}/iniciar",
            json={"usuario_id": 1, "participantes": participantes},
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        return respuesta.json()

    # ------------------------------------------------------------------
    # Configuración
    # ------------------------------------------------------------------
    def test_01_configuracion_modulo_solo_admin(self):
        # El bartender no puede cambiar el interruptor global.
        bartender = self.client.post(
            "/api/usuarios/",
            json={"alias": "BartenderBolirana", "rol": "bartender"},
        )
        self.assertEqual(bartender.status_code, 201, bartender.text)
        bartender_id = bartender.json()["id"]

        respuesta = self.client.put(
            "/api/configuracion/modulos",
            json={"usuario_id": bartender_id, "modulo_bolirana": True},
        )
        self.assertEqual(respuesta.status_code, 403, respuesta.text)

        respuesta = self.client.put(
            "/api/configuracion/modulos",
            json={"usuario_id": 1, "modulo_bolirana": True},
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        self.assertTrue(respuesta.json()["modulo_bolirana"])

        config = self.client.get("/api/configuracion/").json()
        self.assertTrue(config["modulo_bolirana"])

    def test_01b_desactivar_modulo_quita_candados(self):
        """Al desactivar el módulo, las mesas dejan de estar bloqueadas."""
        self.client.put(
            "/api/configuracion/modulos",
            json={"usuario_id": 1, "modulo_bolirana": True},
        )
        mesa = self.crear_mesa(902)
        self.ocupar_mesa(mesa["id"])
        bolirana = self.crear_bolirana("Bolirana Candado")

        partida = self.iniciar_partida(
            bolirana["id"],
            [
                {"tipo": "mesa", "mesa_id": mesa["id"]},
                {"tipo": "alias", "alias": "Jugador Candado"},
            ],
        )
        participantes = partida["partida"]["participantes"]

        listado = self.client.get("/api/mesas/").json()
        fila = next(m for m in listado if m["id"] == mesa["id"])
        self.assertTrue(fila["en_bolirana"])

        # Desactivar el módulo elimina avisos y candados de cierre.
        respuesta = self.client.put(
            "/api/configuracion/modulos",
            json={"usuario_id": 1, "modulo_bolirana": False},
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.text)

        listado = self.client.get("/api/mesas/").json()
        fila = next(m for m in listado if m["id"] == mesa["id"])
        self.assertFalse(fila["en_bolirana"])

        cierre = self.client.post(
            f"/api/cuentas/mesa/{mesa['id']}/cerrar",
            params={"forma_pago": "efectivo", "liberar_mesa": "true"},
        )
        self.assertEqual(cierre.status_code, 200, cierre.text)

        # Se reactiva y se liquida la partida (sin bebidas) para limpiar.
        self.client.put(
            "/api/configuracion/modulos",
            json={"usuario_id": 1, "modulo_bolirana": True},
        )
        liquidar = self.client.post(
            f"/api/boliranas/{bolirana['id']}/finalizar",
            json={
                "usuario_id": 1,
                "perdedores": [p["id"] for p in participantes],
            },
        )
        self.assertEqual(liquidar.status_code, 200, liquidar.text)
        self.assertEqual(liquidar.json()["estado"], "disponible")

        eliminada = self.client.delete(
            f"/api/boliranas/{bolirana['id']}", params={"usuario_id": 1}
        )
        self.assertEqual(eliminada.status_code, 200, eliminada.text)

    def test_02_flujo_completo_de_partida(self):
        self.client.put(
            "/api/configuracion/modulos",
            json={"usuario_id": 1, "modulo_bolirana": True},
        )
        mesa = self.crear_mesa(901)
        self.ocupar_mesa(mesa["id"])
        bolirana = self.crear_bolirana("Bolirana Test 1")

        partida = self.iniciar_partida(
            bolirana["id"],
            [
                {"tipo": "mesa", "mesa_id": mesa["id"]},
                {"tipo": "alias", "alias": "Carlos"},
            ],
        )
        self.assertEqual(partida["estado"], "en_partida")
        participantes = partida["partida"]["participantes"]
        self.assertEqual(len(participantes), 2)
        mesa_participante = next(p for p in participantes if p["tipo"] == "mesa")
        alias_participante = next(p for p in participantes if p["tipo"] == "alias")

        # El listado de mesas avisa que la mesa está en una partida.
        listado = self.client.get("/api/mesas/").json()
        mesa_listada = next(m for m in listado if m["id"] == mesa["id"])
        self.assertTrue(mesa_listada["en_bolirana"])
        self.assertEqual(mesa_listada["bolirana_nombre"], "Bolirana Test 1")

        # Candado: no se puede cerrar la cuenta de la mesa participante.
        cierre = self.client.post(
            f"/api/cuentas/mesa/{mesa['id']}/cerrar",
            params={"forma_pago": "efectivo"},
        )
        self.assertEqual(cierre.status_code, 409, cierre.text)
        self.assertIn("partida activa en Bolirana", cierre.json()["detail"])

        # Candado: tampoco se puede cerrar el turno.
        cierre_turno = self.client.post("/api/caja/cerrar", json={"observaciones": ""})
        self.assertEqual(cierre_turno.status_code, 409, cierre_turno.text)

        # No se puede iniciar otra partida en la misma bolirana.
        repetida = self.client.post(
            f"/api/boliranas/{bolirana['id']}/iniciar",
            json={
                "usuario_id": 1,
                "participantes": [
                    {"tipo": "mesa", "mesa_id": mesa["id"]},
                    {"tipo": "alias", "alias": "Otro"},
                ],
            },
        )
        self.assertEqual(repetida.status_code, 409, repetida.text)

        # Cargar bebidas descuenta stock.
        stock_antes = self.refresco["stock"]
        carga = self.client.post(
            f"/api/boliranas/{bolirana['id']}/pedidos",
            json={
                "usuario_id": 1,
                "items": [
                    {"producto_id": self.refresco["id"], "cantidad": 2},
                ],
            },
        )
        self.assertEqual(carga.status_code, 200, carga.text)
        total_ronda = carga.json()["partida"]["total_bebidas"]
        self.assertAlmostEqual(total_ronda, self.refresco["precio"] * 2, places=2)

        inventario = self.client.get("/api/inventario/?limite=500").json()["items"]
        producto = next(p for p in inventario if p["id"] == self.refresco["id"])
        self.assertEqual(producto["stock"], stock_antes - 2)

        # Liquidar: ambos pierden y el total se divide en partes iguales.
        liquidar = self.client.post(
            f"/api/boliranas/{bolirana['id']}/finalizar",
            json={
                "usuario_id": 1,
                "perdedores": [mesa_participante["id"], alias_participante["id"]],
            },
        )
        self.assertEqual(liquidar.status_code, 200, liquidar.text)
        self.assertEqual(liquidar.json()["estado"], "disponible")
        esperado = round(total_ronda / 2, 2)

        # Con un cargo de bolirana pendiente tampoco se puede cerrar el turno.
        cierre_turno = self.client.post(
            "/api/caja/cerrar", json={"observaciones": ""}
        )
        self.assertEqual(cierre_turno.status_code, 409, cierre_turno.text)
        self.assertIn("cargos de Bolirana", cierre_turno.json()["detail"])

        # La mesa recibe el cargo en su cuenta general con el concepto.
        cuenta = self.client.get(f"/api/cuentas/mesa/{mesa['id']}").json()
        cargos = [
            p
            for p in cuenta["pedidos"]
            if p["concepto"] and "Bolirana" in p["concepto"]
        ]
        self.assertEqual(len(cargos), 1)
        self.assertAlmostEqual(cargos[0]["total"], esperado, places=2)
        self.assertEqual(
            cargos[0]["concepto"], "Consumo Bolirana Test 1 (Partida)"
        )

        # El alias libre queda como cargo pendiente y se cobra de forma mixta.
        pendientes = self.client.get("/api/boliranas/cargos-pendientes").json()
        cargo_alias = next(c for c in pendientes if c["alias"] == "Carlos")
        self.assertAlmostEqual(cargo_alias["total"], esperado, places=2)

        pago = self.client.post(
            f"/api/boliranas/cargos/{cargo_alias['pedido_id']}/pagar",
            json={
                "usuario_id": 1,
                "pagos": [
                    {"forma_pago": "efectivo", "monto": round(esperado / 2, 2)},
                    {"forma_pago": "tarjeta", "monto": round(esperado / 2, 2)},
                ],
            },
        )
        self.assertEqual(pago.status_code, 200, pago.text)
        pendientes = self.client.get("/api/boliranas/cargos-pendientes").json()
        self.assertFalse(any(c["alias"] == "Carlos" for c in pendientes))

        # Ya sin partida activa, la mesa puede cobrarse y liberarse.
        cierre = self.client.post(
            f"/api/cuentas/mesa/{mesa['id']}/cerrar",
            params={"forma_pago": "efectivo", "liberar_mesa": "true"},
        )
        self.assertEqual(cierre.status_code, 200, cierre.text)

        # El consumo se registra una sola vez en el historial del turno.
        historial = self.client.get(
            "/api/caja/historial",
            params={"limite": 50, "origen": ""},
        ).json()["items"]
        cargos_historial = [
            h
            for h in historial
            if h.get("concepto") == "Consumo Bolirana Test 1 (Partida)"
        ]
        self.assertEqual(len(cargos_historial), 2)

        # La bolirana con historial se elimina lógicamente.
        eliminada = self.client.delete(
            f"/api/boliranas/{bolirana['id']}", params={"usuario_id": 1}
        )
        self.assertEqual(eliminada.status_code, 200, eliminada.text)
        activas = self.client.get("/api/boliranas/").json()
        self.assertFalse(any(b["id"] == bolirana["id"] for b in activas))

    def test_03_bolirana_no_admin_no_administra(self):
        bartender = self.client.post(
            "/api/usuarios/",
            json={"alias": "BartenderOpera", "rol": "bartender"},
        )
        self.assertEqual(bartender.status_code, 201, bartender.text)
        bartender_id = bartender.json()["id"]

        crear = self.client.post(
            "/api/boliranas/",
            json={"nombre": "Bolirana Bartender", "usuario_id": bartender_id},
        )
        self.assertEqual(crear.status_code, 403, crear.text)

    def test_04_cierre_turno_sin_pendientes(self):
        """Al final del flujo no quedan partidas ni cargos de bolirana."""
        boliranas = self.client.get("/api/boliranas/").json()
        self.assertTrue(all(b["estado"] == "disponible" for b in boliranas))
        self.assertEqual(self.client.get("/api/boliranas/cargos-pendientes").json(), [])

        respuesta = self.client.post("/api/caja/cerrar", json={"observaciones": ""})
        if respuesta.status_code != 200:
            # Otras pruebas pueden dejar mesas ocupadas; lo que importa aquí
            # es que el cierre no esté bloqueado por Bolirana.
            self.assertNotIn("Bolirana", respuesta.json().get("detail", ""))


if __name__ == "__main__":
    unittest.main()
