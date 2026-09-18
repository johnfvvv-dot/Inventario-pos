import random

print("""Seleccion Aleatoria de operacion (lambda version), se generaran valores aleatorios entre 0 y 100
      0 - Suma
      1 - Resta
      2 - Multiplicacion
      3 - DivisionExacta (decimal)
      4 - DivisionEntera
      5 - Potencia
      6 - Modulo""")

print()
print("----------------------------")
print()

opcion = random.randint(0, 6)   # mejor 0..6 porque solo tienes 7 opciones
operacion = ""
valor1 = random.randint(0, 101)
valor2 = random.randint(0, 101)

if(opcion == 0):
    operacion = "Suma"
    resultado = lambda a, b: a + b
elif(opcion == 1):
    operacion = "Resta"
    resultado = lambda a, b: a - b
elif(opcion == 2):
    operacion = "Multiplicacion"
    resultado = lambda a, b: a * b
elif(opcion == 3):
    operacion = "Division Exacta"
    if valor2 == 0:
        valor2 = 1
    resultado = lambda a, b: a / b
elif(opcion == 4):
    operacion = "Division Entera"
    if valor2 == 0:
        valor2 = 1
    resultado = lambda a, b: a // b
elif(opcion == 5):
    operacion = "Cuadrado"
    resultado = lambda x: x ** 2
else:
    operacion = "Modulo"
    if valor2 == 0:
        valor2 = 1
    resultado = lambda a, b: a % b

if(opcion == 5):
    print(f"Valor: {valor1}, operacion: {operacion}, resultado: {resultado(valor1)}")
else:
    print(f"Valor1: {valor1} - Valor2: {valor2}, operacion: {operacion}, resultado: {resultado(valor1, valor2)}")


print()
print("--------------------")
print("Y el quintuplicador")
print()
def miFuncion(n):
    return lambda valor : valor * n

quintuplicador = miFuncion(5)

print(f"Funcion quintuplicada con valor: {valor1}, resultado: {quintuplicador(valor1)}")