import csv

#Leer un archivo csv
"""with open('Panel_Medico_CSA.csv', 'r', encoding="utf-8") as file:
    csv_reader = csv.DictReader(file)
    for row in csv_reader:
        print(row)"""

#mostrar la informacion por columnas
with open('Panel_Medico_CSA.csv', 'r', encoding="utf-8") as file:
    csv_reader = csv.DictReader(file)
    for row in csv_reader:
        print(f"Nombre:{row['NOMBRE']}, Apellido: {row['APELLIDO']}")
