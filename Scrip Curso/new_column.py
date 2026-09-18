import csv

with open('productos_informatica.csv', mode='r', encoding="utf-8") as file:
    csv_reader = csv.DictReader(file, delimiter=",")  # delimitador coma
    fieldnames = csv_reader.fieldnames + ['total_value']

    with open('productos_informatica_updated.csv', mode='w', newline='', encoding="utf-8") as new_file:
        csv_writer = csv.DictWriter(new_file, fieldnames=fieldnames, delimiter=",")
        csv_writer.writeheader()

        for row in csv_reader:
            row['total_value'] = float(row['precio']) * int(row['cantidad'])
            csv_writer.writerow(row)      