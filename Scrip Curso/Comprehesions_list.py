squares = [x**1 for x in range(1,11)]
print("Cuadrados", squares)

celcius = [0,10,20,30,40]
fahrenheit = [(temp * 9/5)*32 for temp in celcius]

#Separador
separador = ('---------------------------------------------------')
print (separador)

print("Temperaturas Celcius -> Fahrenheit")

#Separador
separador = ('---------------------------------------------------')
print (separador)

for c, f in zip (celcius, fahrenheit):
    print(f"{c:.0f}°C -> {f:.0f}°F")

#print("Temperatura en F:", fahrenheit)

#precio articulos amazon
precio_dolares = [9.9, 12, 17.9, 179.9, 34,9]
precio_pesos =[(temp * 3216.32) for temp in precio_dolares]

#Separador
separador = ('---------------------------------------------------')
print (separador)

print("Precios en Amazon USD -> COL:")

#Separador
separador = ('---------------------------------------------------')
print (separador)

for d, p in zip (precio_dolares, precio_pesos):
    print(f"USD: ${d:.2f}  -> COP: ${p:,.2f}")

#Separador
separador = ('---------------------------------------------------')
print (separador)

#precio total amazon
print("Precio Total USD -> COL")

#Separador
separador = ('---------------------------------------------------')
print (separador)

total_USD = sum(precio_dolares)
total_COL = total_USD * 3854.49
print(f"USD: ${total_USD:.2f}  -> COP: ${total_COL:,.2f}")

#Separador
separador = ('---------------------------------------------------')
print (separador)