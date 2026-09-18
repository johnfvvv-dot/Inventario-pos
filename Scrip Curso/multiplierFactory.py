class multiplierFactory:

    def __new__(cls, factor: int):
        print(f"Creando instancia con factor: {factor}")
        return super(multiplierFactory, cls).__new__(cls)

    def __init__(self, factor: int):
        print(f"inicializando con factor: {factor}")
        self.factor = factor

    def __call__(self, number: int) -> int:
        return number * self.factor

if __name__ == "__main__":
  while True:
    try:
      factor = float(input("Ingresa el factor: "))
      break
    except ValueError:
      print("Número no válido. Ingresa un valor numérico")

  multiplier = multiplierFactory(factor)

  while True:
    try:
      number = float(input("Ingresa el número a multiplicar: "))
      break
    except ValueError:
      print("Número no válido. Ingresa un valor numérico")

  result = multiplier(number)
  print(f"Resultado: {result}")