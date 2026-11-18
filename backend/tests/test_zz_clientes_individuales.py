"""Pruebas de integración de los clientes individuales.

Cubren creación, validación de nombres duplicados, pedidos, cobro con
eliminación de la tarjeta activa, historial y transferencia a una mesa.
"""

import unittest

# La configuración de la base debe existir antes de importar app.database.
from tests import _entorno  # noqa: F401,E402

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


class ClientesIndividualesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client_ctx = TestClient(app)
        cls.client = cls.client_ctx.__enter__()
        # La suite completa puede dejar un turno abierto de otro módulo.
        turno = cls.client.get("/api/caja/turno-actual")
        if not (turno.status_code == 200 and turno.json()):
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
    def crear_individual(self, nombre: str) -> dict:
        respuesta = self.client.post(
            "/api/mesas/individual", json={"nombre": nombre}
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        return respuesta.json()

    def listar_individuales(self) -> list:
        respuesta = self.client.get("/api/mesas/")
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        return [m for m in respuesta.json() if m["tipo"] == "individual"]

    def crear_pedido(self, mesa_id: int, producto: dict, cantidad: int = 1):
        return self.client.post(
            "/api/pedidos/",
            json={
                "mesa_id": mesa_id,
                "usuario_id": 1,
                "items": [
                    {"producto_id": producto["id"], "cantidad": cantidad}
                ],
            },
        )

    def stock_de(self, producto: dict) -> int:
        respuesta = self.client.get("/api/inventario/?limite=500")
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        fila = next(
            p for p in respuesta.json()["items"] if p["id"] == producto["id"]
        )
        return int(fila["stock"])

    def historial(self, limite: int = 500) -> list:
        respuesta = self.client.get(f"/api/caja/historial?limite={limite}")
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        return respuesta.json()["items"]

    # ------------------------------------------------------------------
    # Casos
    # ------------------------------------------------------------------
    def test_01_creacion_listado_y_nombre_duplicado(self):
        cliente = self.crear_individual("Carlos Test")
        self.assertEqual(cliente["tipo"], "individual")
        self.assertEqual(cliente["nombre"], "Carlos Test")
        self.assertEqual(cliente["estado"], "ocupada")
        self.assertLess(cliente["numero"], 0)

        # El mismo nombre no puede repetirse activo, sin distinguir mayúsculas.
        repetido = self.client.post(
            "/api/mesas/individual", json={"nombre": "carlos test"}
        )
        self.assertEqual(repetido.status_code, 400, repetido.text)

        listado = self.listar_individuales()
        fila = next((m for m in listado if m["id"] == cliente["id"]), None)
        self.assertIsNotNone(fila)
        self.assertEqual(fila["nombre"], "Carlos Test")
        self.assertEqual(fila["total_cuenta"], 0.0)
        self.assertFalse(fila["tiene_cuenta_pendiente"])

        # Saldo $0: se puede eliminar y desaparece de la vista activa.
        eliminado = self.client.delete(f"/api/mesas/{cliente['id']}")
        self.assertEqual(eliminado.status_code, 200, eliminado.text)
        self.assertFalse(
            any(m["id"] == cliente["id"] for m in self.listar_individuales())
        )

        # El nombre queda libre al archivarse la tarjeta anterior.
        nuevo = self.crear_individual("Carlos Test")
        self.assertNotEqual(nuevo["id"], cliente["id"])

    def test_02_pedido_cobro_e_historial_como_individual(self):
        cliente = self.crear_individual("Ana Test")
        stock_inicial = self.stock_de(self.refresco)

        pedido = self.crear_pedido(cliente["id"], self.refresco, 2)
        self.assertEqual(pedido.status_code, 201, pedido.text)
        datos = pedido.json()
        self.assertEqual(datos["estado"], "abierto")
        self.assertEqual(datos["alias"], "Ana Test")
        self.assertEqual(self.stock_de(self.refresco), stock_inicial - 2)

        cuenta = self.client.get(f"/api/cuentas/mesa/{cliente['id']}")
        self.assertEqual(cuenta.status_code, 200, cuenta.text)
        detalle = cuenta.json()
        self.assertEqual(detalle["mesa_tipo"], "individual")
        self.assertEqual(detalle["mesa_nombre"], "Ana Test")
        self.assertGreater(detalle["total"], 0)

        # Con saldo pendiente no se puede eliminar la tarjeta.
        bloqueado = self.client.delete(f"/api/mesas/{cliente['id']}")
        self.assertEqual(bloqueado.status_code, 400, bloqueado.text)

        cierre = self.client.post(
            f"/api/cuentas/mesa/{cliente['id']}/cerrar",
            params={
                "liberar_mesa": True,
                "forma_pago": "efectivo",
                "usuario_id": 1,
            },
        )
        self.assertEqual(cierre.status_code, 200, cierre.text)
        self.assertEqual(cierre.json()["estado_mesa"], "cerrada")
        self.assertEqual(cierre.json()["total"], 0.0)

        self.assertFalse(
            any(m["id"] == cliente["id"] for m in self.listar_individuales())
        )

        fila = next(
            (p for p in self.historial() if p["id"] == datos["id"]), None
        )
        self.assertIsNotNone(fila)
        self.assertEqual(fila["mesa_etiqueta"], "Individual")
        self.assertEqual(fila["alias"], "Ana Test")

    def test_03_pago_de_alias_archiva_al_individual(self):
        cliente = self.crear_individual("Div Test")
        pedido = self.client.post(
            "/api/pedidos/",
            json={
                "mesa_id": cliente["id"],
                "usuario_id": 1,
                "nuevo_alias": "Amigo Div",
                "items": [
                    {
                        "producto_id": self.hamburguesa["id"],
                        "cantidad": 1,
                    }
                ],
            },
        )
        self.assertEqual(pedido.status_code, 201, pedido.text)
        self.assertEqual(pedido.json()["estado"], "dividido")

        cuenta = self.client.get(f"/api/cuentas/mesa/{cliente['id']}").json()
        self.assertEqual(len(cuenta["divisiones"]), 1)
        participante = cuenta["divisiones"][0]["participantes"][0]
        self.assertEqual(participante["alias"], "Amigo Div")

        pago = self.client.post(
            f"/api/cuentas/participante/{participante['id']}/pagar",
            params={"forma_pago": "efectivo", "usuario_id": 1},
        )
        self.assertEqual(pago.status_code, 200, pago.text)

        self.assertFalse(
            any(m["id"] == cliente["id"] for m in self.listar_individuales())
        )

        pagos = [
            p
            for p in self.historial()
            if p["alias"] == "Amigo Div" and p["mesa_etiqueta"] == "Individual"
        ]
        self.assertTrue(pagos, "El pago del alias debe quedar en el historial")

    def test_04_transferencia_desde_individual_y_destino_rechazado(self):
        cliente = self.crear_individual("Luis Test")
        pedido = self.crear_pedido(cliente["id"], self.refresco, 1)
        self.assertEqual(pedido.status_code, 201, pedido.text)

        mesa = self.client.post(
            "/api/mesas/",
            json={"numero": 777, "capacidad": 4, "estado": "disponible"},
        )
        self.assertEqual(mesa.status_code, 201, mesa.text)
        mesa_id = mesa.json()["id"]

        transferencia = self.client.post(
            f"/api/cuentas/mesa/{cliente['id']}/transferir",
            params={"destino_id": mesa_id},
        )
        self.assertEqual(transferencia.status_code, 200, transferencia.text)
        self.assertGreater(transferencia.json()["total_transferido"], 0)

        self.assertFalse(
            any(m["id"] == cliente["id"] for m in self.listar_individuales())
        )
        cuenta_mesa = self.client.get(f"/api/cuentas/mesa/{mesa_id}")
        self.assertEqual(cuenta_mesa.status_code, 200, cuenta_mesa.text)
        self.assertEqual(len(cuenta_mesa.json()["pedidos"]), 1)

        # Un cliente individual no puede ser destino de una transferencia.
        destino = self.crear_individual("Destino Test")
        mesa_origen = self.client.post(
            "/api/mesas/",
            json={"numero": 778, "capacidad": 4, "estado": "disponible"},
        )
        self.assertEqual(mesa_origen.status_code, 201, mesa_origen.text)
        origen_id = mesa_origen.json()["id"]
        self.crear_pedido(origen_id, self.refresco, 1)

        rechazo = self.client.post(
            f"/api/cuentas/mesa/{origen_id}/transferir",
            params={"destino_id": destino["id"]},
        )
        self.assertEqual(rechazo.status_code, 400, rechazo.text)


if __name__ == "__main__":
    unittest.main()
