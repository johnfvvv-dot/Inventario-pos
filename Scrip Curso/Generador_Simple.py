#Iteradores y Generadores em Py: Uso eficiente de memoria

def my_generador():
    yield 1
    yield 2
    yield 3

for value in my_generador():
    print(value)
