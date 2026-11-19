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

    def iniciar_partida(
        self, bolirana_id: int, participantes: list, modalidad: str = "directo"
    ) -> dict:
        respuesta = self.client.post(
            f"/api/boliranas/{bolirana_id}/iniciar",
            json={
                "usuario_id": 1,
                "modalidad": modalidad,
                "participantes": participantes,
            },
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

        # La cuenta tampoco queda marcada en modo solo consulta.
        cuenta = self.client.get(f"/api/cuentas/mesa/{mesa['id']}").json()
        self.assertFalse(cuenta["en_bolirana"])
        self.assertIsNone(cuenta["bolirana_nombre"])

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

    def test_01c_cuenta_barra_en_bolirana(self):
        """La cuenta de una barra en partida se consulta en modo solo lectura."""
        self.client.put(
            "/api/configuracion/modulos",
            json={"usuario_id": 1, "modulo_bolirana": True},
        )
        plazas = self.client.post(
            "/api/mesas/barra",
            json={"numero": 95, "capacidad": 2},
        ).json()
        self.ocupar_mesa(plazas[0]["id"])
        bolirana = self.crear_bolirana("Bolirana Barra")
        partida = self.iniciar_partida(
            bolirana["id"],
            [
                {"tipo": "barra", "barra_numero": 95},
                {"tipo": "alias", "alias": "Jugador Barra"},
            ],
        )
        participante_barra = next(
            p for p in partida["partida"]["participantes"] if p["tipo"] == "barra"
        )

        # La tarjeta agregada de la barra muestra la píldora con candado.
        listado = self.client.get("/api/mesas/").json()
        tarjeta = next(
            m for m in listado if m["tipo"] == "barra" and m["numero"] == 95
        )
        self.assertTrue(tarjeta["en_bolirana"])
        self.assertEqual(tarjeta["bolirana_nombre"], "Bolirana Barra")

        # La cuenta de la barra se puede consultar y llega marcada.
        cuenta = self.client.get("/api/cuentas/barra/95").json()
        self.assertTrue(cuenta["en_bolirana"])
        self.assertEqual(cuenta["bolirana_nombre"], "Bolirana Barra")

        # Liquidar con la barra como perdedora y cerrar su cuenta.
        liquidar = self.client.post(
            f"/api/boliranas/{bolirana['id']}/finalizar",
            json={
                "usuario_id": 1,
                "perdedores": [participante_barra["id"]],
            },
        )
        self.assertEqual(liquidar.status_code, 200, liquidar.text)

        cuenta = self.client.get("/api/cuentas/barra/95").json()
        self.assertFalse(cuenta["en_bolirana"])
        self.assertIsNone(cuenta["bolirana_nombre"])

        cierre = self.client.post(
            "/api/cuentas/barra/95/cerrar",
            params={"forma_pago": "efectivo", "liberar_barra": "true"},
        )
        self.assertEqual(cierre.status_code, 200, cierre.text)

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

        # La cuenta se puede consultar y llega marcada en modo solo consulta.
        cuenta = self.client.get(f"/api/cuentas/mesa/{mesa['id']}").json()
        self.assertTrue(cuenta["en_bolirana"])
        self.assertEqual(cuenta["bolirana_nombre"], "Bolirana Test 1")

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
        # Ya liquidada, la cuenta deja de estar en modo solo consulta.
        self.assertFalse(cuenta["en_bolirana"])
        self.assertIsNone(cuenta["bolirana_nombre"])
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

    def test_02b_alias_vinculado_a_mesa_carga_en_su_cuenta(self):
        """Un alias vinculado bloquea y cobra en la cuenta de su mesa."""
        self.client.put(
            "/api/configuracion/modulos",
            json={"usuario_id": 1, "modulo_bolirana": True},
        )
        mesa = self.crear_mesa(903)
        self.ocupar_mesa(mesa["id"])
        bolirana = self.crear_bolirana("Bolirana Alias")

        partida = self.iniciar_partida(
            bolirana["id"],
            [
                {
                    "tipo": "alias",
                    "alias": "Luis",
                    "origen_tipo": "mesa",
                    "origen_mesa_id": mesa["id"],
                },
                {"tipo": "alias", "alias": "Pedro"},
            ],
        )
        participantes = partida["partida"]["participantes"]
        luis = next(p for p in participantes if p["alias"] == "Luis")
        self.assertEqual(luis["etiqueta"], "Luis · Mesa 903")
        self.assertEqual(luis["origen_tipo"], "mesa")
        self.assertEqual(luis["origen_etiqueta"], "Mesa 903")

        # La mesa queda bloqueada aunque no sea participante directa.
        listado = self.client.get("/api/mesas/").json()
        fila = next(m for m in listado if m["id"] == mesa["id"])
        self.assertTrue(fila["en_bolirana"])
        self.assertEqual(fila["bolirana_nombre"], "Bolirana Alias")

        cuenta = self.client.get(f"/api/cuentas/mesa/{mesa['id']}").json()
        self.assertTrue(cuenta["en_bolirana"])
        cierre = self.client.post(
            f"/api/cuentas/mesa/{mesa['id']}/cerrar",
            params={"forma_pago": "efectivo"},
        )
        self.assertEqual(cierre.status_code, 409, cierre.text)

        carga = self.client.post(
            f"/api/boliranas/{bolirana['id']}/pedidos",
            json={
                "usuario_id": 1,
                "items": [{"producto_id": self.refresco["id"], "cantidad": 1}],
            },
        )
        self.assertEqual(carga.status_code, 200, carga.text)
        total = carga.json()["partida"]["total_bebidas"]

        liquidar = self.client.post(
            f"/api/boliranas/{bolirana['id']}/finalizar",
            json={"usuario_id": 1, "perdedores": [luis["id"]]},
        )
        self.assertEqual(liquidar.status_code, 200, liquidar.text)

        cuenta = self.client.get(f"/api/cuentas/mesa/{mesa['id']}").json()
        self.assertFalse(cuenta["en_bolirana"])
        cargos = [
            p
            for p in cuenta["pedidos"]
            if p["concepto"] and "Consumo Bolirana" in p["concepto"]
        ]
        self.assertEqual(len(cargos), 1)
        self.assertAlmostEqual(cargos[0]["total"], total, places=2)

        pendientes = self.client.get("/api/boliranas/cargos-pendientes").json()
        self.assertFalse(any(c["alias"] == "Luis" for c in pendientes))

        cierre = self.client.post(
            f"/api/cuentas/mesa/{mesa['id']}/cerrar",
            params={"forma_pago": "efectivo", "liberar_mesa": "true"},
        )
        self.assertEqual(cierre.status_code, 200, cierre.text)
        eliminada = self.client.delete(
            f"/api/boliranas/{bolirana['id']}", params={"usuario_id": 1}
        )
        self.assertEqual(eliminada.status_code, 200, eliminada.text)

    def test_02c_partida_por_equipos_reparte_y_carga_por_integrante(self):
        """El total se reparte entre equipos y luego entre sus integrantes."""
        self.client.put(
            "/api/configuracion/modulos",
            json={"usuario_id": 1, "modulo_bolirana": True},
        )
        mesa = self.crear_mesa(904)
        self.ocupar_mesa(mesa["id"])
        individual = self.client.post(
            "/api/mesas/individual", json={"nombre": "Cliente Equipos"}
        ).json()
        plazas = self.client.post(
            "/api/mesas/barra", json={"numero": 96, "capacidad": 2}
        ).json()
        self.ocupar_mesa(plazas[0]["id"])
        bolirana = self.crear_bolirana("Bolirana Equipos")

        # Un solo equipo no es una partida por equipos válida.
        invalida = self.client.post(
            f"/api/boliranas/{bolirana['id']}/iniciar",
            json={
                "usuario_id": 1,
                "modalidad": "equipos",
                "participantes": [
                    {"tipo": "mesa", "mesa_id": mesa["id"], "equipo": "Rojos"},
                    {"tipo": "alias", "alias": "Solo", "equipo": "Rojos"},
                ],
            },
        )
        self.assertEqual(invalida.status_code, 422, invalida.text)

        partida = self.iniciar_partida(
            bolirana["id"],
            [
                {"tipo": "mesa", "mesa_id": mesa["id"], "equipo": "Rojos"},
                {
                    "tipo": "alias",
                    "alias": "Ana",
                    "origen_tipo": "individual",
                    "origen_mesa_id": individual["id"],
                    "equipo": "Azules",
                },
                {"tipo": "alias", "alias": "Beto", "equipo": "Azules"},
                {"tipo": "barra", "barra_numero": 96, "equipo": "Azules"},
            ],
            modalidad="equipos",
        )
        self.assertEqual(partida["partida"]["modalidad"], "equipos")
        participantes = partida["partida"]["participantes"]
        ana = next(p for p in participantes if p["alias"] == "Ana")
        barra_participante = next(
            p for p in participantes if p["tipo"] == "barra"
        )
        self.assertEqual(ana["etiqueta"], "Ana · Individual")
        self.assertEqual(ana["origen_tipo"], "individual")
        self.assertEqual(ana["equipo"], "Azules")
        self.assertEqual(barra_participante["equipo"], "Azules")

        # Los candados alcanzan la cuenta individual y la barra.
        cuenta_individual = self.client.get(
            f"/api/cuentas/mesa/{individual['id']}"
        ).json()
        self.assertTrue(cuenta_individual["en_bolirana"])
        cierre_individual = self.client.post(
            f"/api/cuentas/mesa/{individual['id']}/cerrar",
            params={"forma_pago": "efectivo"},
        )
        self.assertEqual(
            cierre_individual.status_code, 409, cierre_individual.text
        )
        cuenta_barra = self.client.get("/api/cuentas/barra/96").json()
        self.assertTrue(cuenta_barra["en_bolirana"])

        carga = self.client.post(
            f"/api/boliranas/{bolirana['id']}/pedidos",
            json={
                "usuario_id": 1,
                "items": [{"producto_id": self.refresco["id"], "cantidad": 2}],
            },
        )
        self.assertEqual(carga.status_code, 200, carga.text)
        total = carga.json()["partida"]["total_bebidas"]

        # El equipo perdedor tiene 3 integrantes.
        liquidar = self.client.post(
            f"/api/boliranas/{bolirana['id']}/finalizar",
            json={"usuario_id": 1, "equipos_perdedores": ["Azules"]},
        )
        self.assertEqual(liquidar.status_code, 200, liquidar.text)
        self.assertEqual(liquidar.json()["estado"], "disponible")

        base = round(total / 3, 2)
        ultimo = round(total - base * 2, 2)

        cuenta_individual = self.client.get(
            f"/api/cuentas/mesa/{individual['id']}"
        ).json()
        self.assertFalse(cuenta_individual["en_bolirana"])
        cargos_individual = [
            p
            for p in cuenta_individual["pedidos"]
            if p["concepto"] and "Equipo perdedor" in p["concepto"]
        ]
        self.assertEqual(len(cargos_individual), 1)
        self.assertIn("Azules", cargos_individual[0]["concepto"])
        self.assertAlmostEqual(
            cargos_individual[0]["total"], base, places=2
        )

        cuenta_barra = self.client.get("/api/cuentas/barra/96").json()
        cargos_barra = [
            p
            for p in cuenta_barra["pedidos"]
            if p["concepto"] and "Equipo perdedor" in p["concepto"]
        ]
        self.assertEqual(len(cargos_barra), 1)
        self.assertAlmostEqual(cargos_barra[0]["total"], ultimo, places=2)

        pendientes = self.client.get("/api/boliranas/cargos-pendientes").json()
        cargo_beto = next(c for c in pendientes if c["alias"] == "Beto")
        self.assertAlmostEqual(cargo_beto["total"], base, places=2)
        self.assertIn("Azules", cargo_beto["concepto"])
        self.assertIn("Equipo perdedor", cargo_beto["concepto"])
        self.assertFalse(any(c["alias"] == "Ana" for c in pendientes))

        # El equipo ganador no recibe cargo.
        cuenta_mesa = self.client.get(
            f"/api/cuentas/mesa/{mesa['id']}"
        ).json()
        self.assertFalse(
            any(
                p["concepto"] and "Equipo perdedor" in p["concepto"]
                for p in cuenta_mesa["pedidos"]
            )
        )

        # Limpieza: cobrar el cargo libre y cerrar las cuentas participantes.
        pago = self.client.post(
            f"/api/boliranas/cargos/{cargo_beto['pedido_id']}/pagar",
            json={
                "usuario_id": 1,
                "pagos": [
                    {"forma_pago": "efectivo", "monto": cargo_beto["total"]}
                ],
            },
        )
        self.assertEqual(pago.status_code, 200, pago.text)
        cierre_individual = self.client.post(
            f"/api/cuentas/mesa/{individual['id']}/cerrar",
            params={"forma_pago": "efectivo"},
        )
        self.assertEqual(
            cierre_individual.status_code, 200, cierre_individual.text
        )
        cierre_barra = self.client.post(
            "/api/cuentas/barra/96/cerrar",
            params={"forma_pago": "efectivo", "liberar_barra": "true"},
        )
        self.assertEqual(cierre_barra.status_code, 200, cierre_barra.text)
        cierre_mesa = self.client.post(
            f"/api/cuentas/mesa/{mesa['id']}/cerrar",
            params={"forma_pago": "efectivo", "liberar_mesa": "true"},
        )
        self.assertEqual(cierre_mesa.status_code, 200, cierre_mesa.text)
        eliminada = self.client.delete(
            f"/api/boliranas/{bolirana['id']}", params={"usuario_id": 1}
        )
        self.assertEqual(eliminada.status_code, 200, eliminada.text)

    def test_02d_alias_vinculado_a_barra_carga_en_su_cuenta(self):
        """Un alias vinculado a una barra bloquea y cobra la barra completa."""
        self.client.put(
            "/api/configuracion/modulos",
            json={"usuario_id": 1, "modulo_bolirana": True},
        )
        plazas = self.client.post(
            "/api/mesas/barra", json={"numero": 97, "capacidad": 1}
        ).json()
        self.ocupar_mesa(plazas[0]["id"])
        bolirana = self.crear_bolirana("Bolirana Alias Barra")

        partida = self.iniciar_partida(
            bolirana["id"],
            [
                {
                    "tipo": "alias",
                    "alias": "Marta",
                    "origen_tipo": "barra",
                    "origen_barra_numero": 97,
                },
                {"tipo": "alias", "alias": "Nico"},
            ],
        )
        participantes = partida["partida"]["participantes"]
        marta = next(p for p in participantes if p["alias"] == "Marta")
        self.assertEqual(marta["etiqueta"], "Marta · Barra 97")
        self.assertEqual(marta["origen_tipo"], "barra")
        self.assertEqual(marta["origen_barra_numero"], 97)

        listado = self.client.get("/api/mesas/").json()
        tarjeta = next(
            m for m in listado if m["tipo"] == "barra" and m["numero"] == 97
        )
        self.assertTrue(tarjeta["en_bolirana"])
        self.assertEqual(tarjeta["bolirana_nombre"], "Bolirana Alias Barra")

        cuenta = self.client.get("/api/cuentas/barra/97").json()
        self.assertTrue(cuenta["en_bolirana"])
        cierre = self.client.post(
            "/api/cuentas/barra/97/cerrar",
            params={"forma_pago": "efectivo"},
        )
        self.assertEqual(cierre.status_code, 409, cierre.text)

        carga = self.client.post(
            f"/api/boliranas/{bolirana['id']}/pedidos",
            json={
                "usuario_id": 1,
                "items": [{"producto_id": self.refresco["id"], "cantidad": 1}],
            },
        )
        self.assertEqual(carga.status_code, 200, carga.text)
        total = carga.json()["partida"]["total_bebidas"]

        liquidar = self.client.post(
            f"/api/boliranas/{bolirana['id']}/finalizar",
            json={"usuario_id": 1, "perdedores": [marta["id"]]},
        )
        self.assertEqual(liquidar.status_code, 200, liquidar.text)

        cuenta = self.client.get("/api/cuentas/barra/97").json()
        self.assertFalse(cuenta["en_bolirana"])
        cargos = [
            p
            for p in cuenta["pedidos"]
            if p["concepto"] and "Consumo Bolirana" in p["concepto"]
        ]
        self.assertEqual(len(cargos), 1)
        self.assertAlmostEqual(cargos[0]["total"], total, places=2)

        pendientes = self.client.get("/api/boliranas/cargos-pendientes").json()
        self.assertFalse(any(c["alias"] == "Marta" for c in pendientes))

        cierre = self.client.post(
            "/api/cuentas/barra/97/cerrar",
            params={"forma_pago": "efectivo", "liberar_barra": "true"},
        )
        self.assertEqual(cierre.status_code, 200, cierre.text)
        eliminada = self.client.delete(
            f"/api/boliranas/{bolirana['id']}", params={"usuario_id": 1}
        )
        self.assertEqual(eliminada.status_code, 200, eliminada.text)

    def test_02e_equipos_con_dos_perdedores_reparte_el_total_exacto(self):
        """Dos equipos perdedores reparten el total sin perder centavos."""
        self.client.put(
            "/api/configuracion/modulos",
            json={"usuario_id": 1, "modulo_bolirana": True},
        )
        mesa_uno = self.crear_mesa(905)
        mesa_dos = self.crear_mesa(906)
        self.ocupar_mesa(mesa_uno["id"])
        self.ocupar_mesa(mesa_dos["id"])
        bolirana = self.crear_bolirana("Bolirana Dos Equipos")

        partida = self.iniciar_partida(
            bolirana["id"],
            [
                {
                    "tipo": "mesa",
                    "mesa_id": mesa_uno["id"],
                    "equipo": "Equipo Uno",
                },
                {"tipo": "alias", "alias": "Jugador Uno", "equipo": "Equipo Uno"},
                {
                    "tipo": "mesa",
                    "mesa_id": mesa_dos["id"],
                    "equipo": "Equipo Dos",
                },
                {"tipo": "alias", "alias": "Jugador Dos", "equipo": "Equipo Dos"},
            ],
            modalidad="equipos",
        )
        participantes = partida["partida"]["participantes"]

        carga = self.client.post(
            f"/api/boliranas/{bolirana['id']}/pedidos",
            json={
                "usuario_id": 1,
                "items": [{"producto_id": self.refresco["id"], "cantidad": 2}],
            },
        )
        self.assertEqual(carga.status_code, 200, carga.text)
        total = carga.json()["partida"]["total_bebidas"]

        liquidar = self.client.post(
            f"/api/boliranas/{bolirana['id']}/finalizar",
            json={
                "usuario_id": 1,
                "equipos_perdedores": ["Equipo Uno", "Equipo Dos"],
            },
        )
        self.assertEqual(liquidar.status_code, 200, liquidar.text)

        cuenta_uno = self.client.get(
            f"/api/cuentas/mesa/{mesa_uno['id']}"
        ).json()
        cuenta_dos = self.client.get(
            f"/api/cuentas/mesa/{mesa_dos['id']}"
        ).json()
        cargos_mesas = [
            p
            for p in cuenta_uno["pedidos"] + cuenta_dos["pedidos"]
            if p["concepto"] and "Equipo perdedor" in p["concepto"]
        ]
        self.assertEqual(len(cargos_mesas), 2)

        pendientes = self.client.get("/api/boliranas/cargos-pendientes").json()
        cargos_alias = [
            c
            for c in pendientes
            if c["alias"] in {"Jugador Uno", "Jugador Dos"}
        ]
        self.assertEqual(len(cargos_alias), 2)

        montos = [p["total"] for p in cargos_mesas] + [
            c["total"] for c in cargos_alias
        ]
        self.assertEqual(len(montos), len(participantes))
        self.assertAlmostEqual(sum(montos), total, places=2)

        for cargo in cargos_alias:
            pago = self.client.post(
                f"/api/boliranas/cargos/{cargo['pedido_id']}/pagar",
                json={
                    "usuario_id": 1,
                    "pagos": [
                        {"forma_pago": "efectivo", "monto": cargo["total"]}
                    ],
                },
            )
            self.assertEqual(pago.status_code, 200, pago.text)

        for mesa in (mesa_uno, mesa_dos):
            cierre = self.client.post(
                f"/api/cuentas/mesa/{mesa['id']}/cerrar",
                params={"forma_pago": "efectivo", "liberar_mesa": "true"},
            )
            self.assertEqual(cierre.status_code, 200, cierre.text)

        eliminada = self.client.delete(
            f"/api/boliranas/{bolirana['id']}", params={"usuario_id": 1}
        )
        self.assertEqual(eliminada.status_code, 200, eliminada.text)

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
