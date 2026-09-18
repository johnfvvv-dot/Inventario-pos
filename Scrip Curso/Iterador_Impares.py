#Iteradores y Generadores em Py: Uso eficiente de memoria
#Crear iterador para los numeros impares

#Limite
limit = 10

#Crear iterador
odd_iter = iter(range(1,limit+1,2))

#Usar el iterador
for num in odd_iter:
    print(num)

#Separador impares y pares
separador = ('---------------------------------------------------')
print (separador) 

#Crear iterador para los numeros pares

#Limite
limit = 10

#Crear iterador
odd_iter = iter(range(0,limit+1,2))

#Usar el iterador
for num in odd_iter:
    print(num)