#Iteradores y Generadores em Py: Uso eficiente de memoria

# Inicio fibonacci
inicio = ('-----------------------------FIBONACCI------------------------------')
print(inicio)

#Fibonacci
# 0 1 1 2 3 5 8 13 21...

def fibonacci (limit):
    a, b = 0, 1
    while a< limit:
        yield a
        a, b = b, a+b

for num in fibonacci(22):
    print(num)

# Separador fibonacci y impares
separador=('-------------------------------IMPARES-------------------------------')
print(separador)

#Impares
# 1 3 5 7 9 11 13....

def impares (limit):
    imp = 1
    while imp<limit:
        yield imp
        imp = imp + 2

for imp in impares(22 ):
    print(imp)

# Separador impares y pares
separador_2=('--------------------------------PARES--------------------------------')
print(separador_2)

#Pares
# 0 2 4 6 8 10 12 14....

def pares (limit):
    par = 0
    while par<limit:
        yield par
        par = par + 2

for par in pares(21):
    print(par)

# Fin
fin=('---------------------------------FIN---------------------------------')
print(fin)