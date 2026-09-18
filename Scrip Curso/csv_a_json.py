import csv
import json

# Abrir el archivo CSV
with open('Panel_Medico_CSA.csv', mode='r', encoding='utf-8') as file:
    csv_reader = csv.DictReader(file, delimiter=",")  # tu archivo usa comas
    data = list(csv_reader)  # convertir todas las filas a una lista de diccionarios

# Guardar como JSON
with open('Panel_Medico_CSA.json', mode='w', encoding='utf-8') as json_file:
    json.dump(data, json_file, indent=4, ensure_ascii=False)

print("Archivo convertido a Panel_Medico_CSA.json")
