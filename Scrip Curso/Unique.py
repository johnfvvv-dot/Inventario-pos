import numpy as np

# Supongamos que tenemos la variable 'respuestas' con las opiniones de los clientes
respuestas = np.array(['bueno', 'excelente', 'malo', 'bueno', 'excelente', 'bueno', 'malo', 'excelente'])

# Utilizamos el método unique para encontrar los elementos únicos
elementos_unicos = np.unique(respuestas)
print(elementos_unicos)

print("----------------------------------------------")

elementos_unicos, conteos = np.unique(respuestas, return_counts=True)
print(elementos_unicos)
print(conteos)

print("----------------------------------------------")

x = np.arange(10)
vista = x[1:3]

print(x)
print(vista)

# Modificar la vista
x[1:3] = [10, 11]
print(x)
print(vista)

print("----------------------------------------------")

# Crear una copia de la porción del array
copia = x[1:3].copy()

# Hacer cambios en el array original
x[1:3] = [12, 13]
print(x)
print(copia)