from math import gcd

class Fraccion:
    def __init__(self, numerador, denominador):
        self.numerador = numerador
        self.denominador = denominador

    def __add__(self, otra_fraccion):
        nuevo_num = self.numerador * otra_fraccion.denominador + otra_fraccion.numerador * self.denominador
        nuevo_den = self.denominador * otra_fraccion.denominador
        comun_divisor = gcd(nuevo_num, nuevo_den)
        return Fraccion(nuevo_num // comun_divisor, nuevo_den // comun_divisor)

    def __repr__(self):
        return f"{self.numerador}/{self.denominador}"

f1 = Fraccion(1, 5)
f2 = Fraccion(3, 2)

f3 = f1 + f2  # Suma de fracciones
print(f3)  # Output: 3/4