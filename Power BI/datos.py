from datetime import date
import random
import openpyxl

wb = openpyxl.load_workbook("Avanzado - JOHN SANTAMARIA - 28092026v2.xlsx")
ws_cttes = wb["Cttes"]
ws_ben = wb["Beneficiarios"]

# Catálogos base tomados de las hojas Homologacion y Estados
planes = [
    ("PTC001", "PETAMIGO - 2020", "Petamigo"),
    ("PTC002", "PETAMIGO - LA ASCENSION", "Petamigo"),
    ("PTC003", "PETAMIGO COLECTIVO - 2019", "Petamigo"),
    ("PTI001", "PETPLAN INDIVIDUAL", "Petfiel"),
    ("PTP026", "PETFIEL - SUPERIOR - 2020", "Petfiel Superior"),
    ("PTP027", "PETFIEL - VIP - 2020", "Petfiel VIP"),
    ("PTP024", "PETAMIGO - GRANITOS Y MARMOLES SAS", "Petamigo Tradicional"),
]

sucursales = [
    "Bogotá Norte",
    "Bogotá Chapinero",
    "Medellín",
    "Cali Sur",
    "Bucaramanga",
    "Barranquilla",
]
convenios = [
    "PARTICULAR",
    "FONCOLOMBIA",
    "LA ASCENSION",
    "CLUSUPOL",
    "FEHOL-2640",
]
estados = [("ACT", "Activo"), ("CANC", "Cancelado"), ("SUSP", "Suspendido")]
nombres_mascotas = [
    "Rocky",
    "Luna",
    "Zeus",
    "Bella",
    "Milo",
    "Toby",
    "Max",
    "Nina",
    "Bruno",
    "Sasha",
    "Thor",
    "Kira",
    "Simona",
]

fila_cttes = 2
fila_ben = 2

for i in range(1, 31):
    doc_entry = 10000 + i
    num_contrato = f"CTR-{8000 + i}"
    cod_plan, nom_plan, proteccion = random.choice(planes)
    cod_est, nom_est = random.choices(
        estados, weights=[0.7, 0.2, 0.1]
    )[0]  # Mayoría activos
    sucursal = random.choice(sucursales)
    convenio = random.choice(convenios)
    valor_mensual = random.randrange(60000, 250000, 5000)
    num_mascotas = random.randint(1, 3)

    # 1. Escribir fila en Cttes
    ws_cttes.cell(row=fila_cttes, column=1, value=doc_entry)
    ws_cttes.cell(
        row=fila_cttes,
        column=2,
        value=(doc_entry - 500) if random.random() > 0.6 else None,
    )
    ws_cttes.cell(row=fila_cttes, column=4, value="Mascotas")
    ws_cttes.cell(row=fila_cttes, column=9, value=convenio)
    ws_cttes.cell(row=fila_cttes, column=10, value=date(2021, 5, 10))
    ws_cttes.cell(row=fila_cttes, column=14, value="CC")
    ws_cttes.cell(row=fila_cttes, column=15, value=num_contrato)
    ws_cttes.cell(row=fila_cttes, column=16, value=cod_est)
    ws_cttes.cell(row=fila_cttes, column=18, value=valor_mensual)
    ws_cttes.cell(row=fila_cttes, column=22, value=cod_plan)
    ws_cttes.cell(row=fila_cttes, column=23, value=nom_plan)
    ws_cttes.cell(row=fila_cttes, column=26, value=sucursal)
    ws_cttes.cell(
        row=fila_cttes, column=31, value=f"+57 31{random.randint(10000000, 99999999)}"
    )
    ws_cttes.cell(
        row=fila_cttes, column=32, value=f"usuario_{i}@serviciomail.com"
    )
    ws_cttes.cell(row=fila_cttes, column=35, value=proteccion)
    fila_cttes += 1

    # 2. Escribir beneficiarios vinculados
    for m in range(1, num_mascotas + 1):
        parentesco = "PET" if m == 1 else ("PET2" if m == 2 else "PET3")
        especie = "GATO" if parentesco == "PET3" else "PERRO"
        nombre_pet = random.choice(nombres_mascotas)

        ws_ben.cell(row=fila_ben, column=1, value=doc_entry)
        ws_ben.cell(row=fila_ben, column=2, value=cod_est)
        ws_ben.cell(row=fila_ben, column=3, value=nom_est)
        ws_ben.cell(row=fila_ben, column=4, value=convenio)
        ws_ben.cell(row=fila_ben, column=6, value=num_contrato)
        ws_ben.cell(row=fila_ben, column=7, value=sucursal)
        ws_ben.cell(row=fila_ben, column=10, value=parentesco)
        ws_ben.cell(
            row=fila_ben,
            column=12,
            value=round(valor_mensual / num_mascotas, 2),
        )
        ws_ben.cell(row=fila_ben, column=13, value=especie)
        ws_ben.cell(row=fila_ben, column=14, value=nombre_pet)
        ws_ben.cell(row=fila_ben, column=15, value=random.randint(1, 12))
        ws_ben.cell(row=fila_ben, column=22, value=especie.capitalize())
        ws_ben.cell(row=fila_ben, column=24, value=proteccion)
        fila_ben += 1

wb.save("Avanzado_JOHN_SANTAMARIA_Poblado.xlsx")
print(f"Completado: {fila_cttes-2} contratos y {fila_ben-2} beneficiarios.")