import csv
new_nombre ={
    'NIT':'',
    'N° CLIENT ODELLA':'',
    'KAM DERMO':'',
    'KAM DEVICES':'',
    'KAM INYECTABLES':'',
    'DBM':'',
    'BUSINESS PARTNER':'',
    'CLIENTE / RAZÓN SOCIAL':'',
    'NOMBRE': 'TATIANA',
    'APELLIDO': 'REYES'
}
with open('productos_informatica.csv', 'a', newline='') as file:
    #file.write('\n')
    csv_writer = csv.DictWriter(file, fieldnames= new_nombre.keys())
    csv_writer.writerow(new_nombre)
