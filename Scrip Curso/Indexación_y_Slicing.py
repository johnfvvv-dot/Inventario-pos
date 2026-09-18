import numpy as np

# Crear un array de ejemplo
arr = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

arr1_20 = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20])

arr8dt = np.array([1, 20, 35, 15, 8, 9, 6, 26])

# Acceder a elementos específicos:
# 1. Crea un arreglo de 10 números y accede al cuarto y penúltimo elemento usando índices positivos y negativos

print(arr[[4,-2]])
print("----------------------------------------------")

# Slicing de arreglos:
# 2. Dado un arreglo de números del 1 al 20, extrae los elementos entre las posiciones 3 y 7, y luego los elementos de las últimas 5 posiciones.

print(arr1_20[3:7])
print("----------------------------------------------")
print(arr1_20[15:20])
print("----------------------------------------------")

# Indexing con booleanos:
# 3. Crea un arreglo de números aleatorios entre 0 y 100. Usa una expresión booleana para acceder solo a los números mayores a 50.

arr_random = np.random.randint(0, 100, 100)
print(arr_random)
print("----------------------------------------------")
bool_index = arr_random > 50
print(bool_index)
print("----------------------------------------------")
print(arr_random[bool_index])
print("----------------------------------------------")

# Indexación con múltiples índices:
# 4. Dado un arreglo de 8 elementos, crea una lista de índices para acceder a los elementos en las posiciones 1, 4, y 6.

print(arr8dt[[1,4,6]])
print("----------------------------------------------")

# Matrices bidimensionales:
# 5. Genera una matriz 4x4 de números aleatorios entre 10 y 50, y accede a la submatriz de 2x2 ubicada en la esquina inferior derecha.

arr_randomm = np.random.randint(10, 50, size= (4,4))
print(arr_randomm)
print("----------------------------------------------")
print(arr_randomm[2:,2:])