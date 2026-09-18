import statistics
import csv

#Leer los datos de ventas mensuales desde un archivo CSV
mothly_sales={}
with open('yearly_sales.csv','r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        month = row['month']
        sales = int(row['sales'])
        mothly_sales[month]=sales

sales=list(mothly_sales.values())
print(sales)

#Hallar la media de la ventas
mean_sales=statistics.mean(sales)
print(f"La media es: {mean_sales}")

#Hallar la mediana 
median_sales=statistics.median(sales)
print(f"La mediana es: {median_sales}")

#Hallar la moda 
mode_sales=statistics.mode(sales)
print(f"La moda es: {mode_sales}")

#Hallar la desviación estándar
stdev_sales=statistics.stdev(sales)
print(f"La desviación estándar es: {stdev_sales}")

#Hallar la varianza
variance_sales=statistics.variance(sales)
print(f"La desviación varianza es: {variance_sales}")

max_sales = max(sales)
min_sales = min(sales)

range_sales=max_sales-min_sales
print(max_sales)
print(min_sales)
print(f"Rango de ventas: {range_sales}")