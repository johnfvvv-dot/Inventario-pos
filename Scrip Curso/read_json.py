import json

#Lectura del archivo
with open('productos_informatica.json', mode='r') as file:
    products = json.load(file)

#Mostrar el contenido
for product in products:
    #print(product)
    print(f"Producto: {product['nombre']}, Precio:{product['precio']}")