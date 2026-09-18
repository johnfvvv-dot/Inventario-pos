import json

file_path = 'productos_informatica.json'

new_product ={
    'nombre':'Xbox Series X',
    'precio':'790',
    'cantidad':'15',
    'marca':'Microsoft',
    'categoría':'Video Juegos',
    'fecha_entrada':'2026-08-03'
}
with open(file_path, 'r') as file:
    products = json.load(file)

products.append(new_product)

with open(file_path, 'w') as file:
    json.dump(products, file, indent=21)
