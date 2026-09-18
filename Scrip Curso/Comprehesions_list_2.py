# Numeros Impares
Lista_impares = [x for x in range(1,21) if x%2 >0]
print("Lista impares")
print(Lista_impares)

# Numeros Pares
Lista_pares = [x for x in range(1,21) if x%2 ==0]
print("Lista pares")
print(Lista_pares)
#Separador
separador = ('---------------------------------------------------') 
print (separador)

matrix =[[1,2,3],
         [4,5,6],
         [7,8,9]]

tranposed =[[row[i] for row in matrix] for i in range(len(matrix[1]))]

print (matrix)
print(tranposed)