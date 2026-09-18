# Funcion que suma dos números
def add(a, b):
    return a + b

# Funcion que resta dos números
def subtract(a, b):
    return a - b

# Funcion que multiplica dos números
def multiply(a, b):
    return a * b

# Funcion que divide dos números
def divide(a, b):
    if b == 0:
        raise ValueError("No se puede dividir por cero")
    return a / b


if __name__ == "__main__":
  print("Calculadora")
  print("Operadores disponibles: +, -, *, /")

  operadores_validos = {"+", "-", "*", "/"}

  while True:
    try:
      a = float(input("Ingresa el primer número: "))
      break
    except ValueError:
      print("Número no válido. Ingresa un valor numérico")

  while True:
    operador = input("Ingresa el operador (+, -, *, /): ").strip()
    if operador in operadores_validos:
      break
    print("Operador no válido. Usa +, -, *, /")

  while True:
    try:
      b = float(input("Ingresa el segundo número: "))
      if operador == "/" and b == 0:
        print("No se puede dividir por cero")
      else:
        break
    except ValueError:
      print("Número no válido. Ingresa un valor numérico")

  if operador == "+":
    result = add(a, b)
  elif operador == "-":
    result = subtract(a, b)
  elif operador == "*":
    result = multiply(a, b)
  else:
    result = divide(a, b)

  print(f"Resultado: {result}")
