import numpy as np
matrix = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
transposed_matrix = matrix.T
print("Matriz original:\n", matrix)
print("Matriz transpuesta:\n", transposed_matrix)

print("----------------------------------------------")

# Crea un array con los números del 1 al 12
array = np.arange(1, 13)  
# Cambia la forma del array a una matriz de 3 filas y 4 columnas
reshaped_array = array.reshape(3, 4)  
print("Array original:", array)
print("Array reshaped a 3x4:\n", reshaped_array)

print("----------------------------------------------")

# Crea un array con los números del 1 al 5
array = np.array([1, 2, 3, 4, 5])  
# Invierte el array
reversed_array = array[::-1]  
print("Array original:", array)
print("Array invertido:", reversed_array)

print("----------------------------------------------")

 # Crea un array 2D
multi_array = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]]) 
# Aplana el array 2D a 1D
flattened_array = multi_array.flatten()  
print("Array multidimensional:\n", multi_array)
print("Array aplanado:", flattened_array)