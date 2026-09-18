import numpy as np

A = np.array([[1, 2], [3, 4]])
B = np.array([[5, 6], [7, 8]])

suma = A + B
print("Suma de matrices:\n", suma)

producto = np.dot(A, B)
print("Producto de matrices:\n", producto)

determinante = np.linalg.det(A)
print("Determinante de A:", determinante)

inversa = np.linalg.inv(A)
print("Inversa de A:\n", inversa)

valores_propios, vectores_propios = np.linalg.eig(A)
print("Valores propios de A:\n", valores_propios)
print("Vectores propios de A:\n", vectores_propios)

B = np.array([1, 2])
X = np.linalg.solve(A, B)
print("Solución del sistema AX = B:\n", X)