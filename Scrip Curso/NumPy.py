# Operaciones Básicas con Arrays
# 1. Instrucción: Crea dos arrays de 1D con valores enteros y realiza las operaciones de suma, resta, multiplicación, y división entre ellos.

import numpy as np

array1 = np.array([10, 20, 30, 40])
array2 = np.array([1, 2, 3, 4])

suma = array1 + array2
resta = array1 - array2
multiplicacion = array1 * array2
division = array1 / array2

print("---------------------------------------------")
print("Operaciones Básicas con Arrays")
print("Suma:", suma)
print("Resta:", resta)
print("Multiplicación:", multiplicacion)
print("División:", division)
print("---------------------------------------------")

# Cálculos Estadísticos en Arrays
# 2. Instrucción: Dado un array de datos, calcula la media, mediana, varianza, y desviación estándar.

import numpy as np

datos = np.array([23, 76, 35, 67, 89, 45, 68, 79, 35])

media = np.mean(datos)
mediana = np.median(datos)
varianza = np.var(datos)
desviacion = np.std(datos)

print("Cálculos Estadísticos en Arrays")
print("Media:", media)
print("Mediana:", mediana)
print("Varianza:", varianza)
print("Desviación estándar:", desviacion)
print("---------------------------------------------")

# Operaciones Matriciales
# 3. Instrucción: Crea dos matrices de 2x2 y realiza las operaciones de suma, resta, multiplicación (producto matricial) y cálculo de la inversa de una de ellas.

import numpy as np

matriz1 = np.array([[1, 2], [3, 4]])
matriz2 = np.array([[5, 6], [7, 8]])

suma_matrices = matriz1 + matriz2
resta_matrices = matriz1 - matriz2
producto_matrices = np.dot(matriz1, matriz2)
inversa_matriz1 = np.linalg.inv(matriz1)

print("Operaciones Matriciales")
print("Suma de matrices:\n", suma_matrices)
print("Resta de matrices:\n", resta_matrices)
print("Producto de matrices:\n", producto_matrices)
print("Inversa de la matriz 1:\n", inversa_matriz1)
print("---------------------------------------------")

# Resolución de un Sistema de Ecuaciones Lineales
# 4. Instrucción: Resuelve el sistema de ecuaciones lineales dado por Ax=b, donde A es una matriz 2x2 y b es un vector de 2 elementos. Ax=bAx = b

import numpy as np

A = np.array([[2, 3], [1, 2]])
b = np.array([8, 5])

x = np.linalg.solve(A, b)
print("Resolución de un Sistema de Ecuaciones Lineales")
print("Solución del sistema de ecuaciones:", x)
print("---------------------------------------------")

# Simulación de Datos
# 5. Instrucción: Genera un array de 1000 números aleatorios que sigan una distribución normal con media 0 y desviación estándar 1. Calcula la media y desviación estándar del array generado.

import numpy as np

datos_simulados = np.random.normal(0, 1, 1000)
media_simulada = np.mean(datos_simulados)
desviacion_simulada = np.std(datos_simulados)

print("Simulación de Datos")
print("Media de los datos simulados:", media_simulada)
print("Desviación estándar de los datos simulados:", desviacion_simulada)
print("---------------------------------------------")