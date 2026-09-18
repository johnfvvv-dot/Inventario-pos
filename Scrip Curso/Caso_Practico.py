
import numpy as np

# Paso 1: Crear arrays con datos de ventas mensuales
meses = np.array(['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'])
ventas_A = np.array([150, 200, 250, 300, 220, 210, 180, 190, 230, 240, 280, 300])
ventas_B = np.array([180, 210, 230, 250, 270, 260, 240, 250, 270, 290, 310, 330])
ventas_C = np.array([200, 220, 240, 260, 280, 300, 320, 340, 360, 380, 400, 420])

# Paso 2: Transformaciones básicas con NumPy
# Estadísticas básicas
media_A = np.mean(ventas_A)
suma_A = np.sum(ventas_A)
media_B = np.mean(ventas_B)
suma_B = np.sum(ventas_B)
media_C = np.mean(ventas_C)
suma_C = np.sum(ventas_C)

print(f"Media de ventas Producto A: {media_A}")
print(f"Suma de ventas Producto A: {suma_A}")
print(f"Media de ventas Producto B: {media_B}")
print(f"Suma de ventas Producto B: {suma_B}")
print(f"Media de ventas Producto C: {media_C}")
print(f"Suma de ventas Producto C: {suma_C}")

# Paso 3: Manipulación y análisis de datos
# Calcular el total de ventas por mes
total_ventas_por_mes = ventas_A + ventas_B + ventas_C

# Calcular el promedio de ventas por producto
promedio_ventas_productos = np.array([media_A, media_B, media_C])

# Identificar el mes con mayor y menor ventas
mes_mayor_ventas = meses[np.argmax(total_ventas_por_mes)]
mes_menor_ventas = meses[np.argmin(total_ventas_por_mes)]

print("Total de ventas por mes:", total_ventas_por_mes)
print("Promedio de ventas por producto:", promedio_ventas_productos)
print(f"Mes con mayor ventas: {mes_mayor_ventas}")
print(f"Mes con menor ventas: {mes_menor_ventas}")

# Paso 4: Operaciones avanzadas con NumPy
# Reshape y Transposición
ventas_matrix = np.array([ventas_A, ventas_B, ventas_C])
ventas_reshaped = ventas_matrix.reshape(3, 4, 3)
ventas_transposed = ventas_matrix.T

print("Ventas Matrix:\n", ventas_matrix)
print("Ventas Reshaped (3, 4, 3):\n", ventas_reshaped)
print("Ventas Transposed:\n", ventas_transposed)

# Invertir arrays y aplanar matrices
ventas_inverted = ventas_matrix[:, ::-1]
ventas_flattened = ventas_matrix.flatten()

print("Ventas Invertidas:\n", ventas_inverted)
print("Ventas Aplanadas:\n", ventas_flattened)

# Paso 5: Análisis de elementos únicos y sus conteos
unique_ventas, counts_ventas = np.unique(ventas_flattened, return_counts=True)
print("Elementos únicos en las ventas:", unique_ventas)
print("Conteos de elementos únicos en las ventas:", counts_ventas)

# Paso 6: Indexación y slicing
# Seleccionar ventas del primer trimestre
ventas_primer_trimestre = ventas_matrix[:, :3]
print("Ventas del primer trimestre:\n", ventas_primer_trimestre)

# Indexación booleana para seleccionar meses con ventas totales superiores a 800
meses_altas_ventas = meses[total_ventas_por_mes > 800]
ventas_altas = total_ventas_por_mes[total_ventas_por_mes > 800]
print("Meses con ventas totales superiores a 800:", meses_altas_ventas)
print("Ventas totales superiores a 800:", ventas_altas)

# Selección avanzada
indices = [0, 2, 4, 6, 8, 10]
ventas_indices_seleccionados = ventas_matrix[:, indices]
print("Ventas en meses seleccionados:\n", ventas_indices_seleccionados)