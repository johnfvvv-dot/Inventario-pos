class Persona:
    def __init__(self, nombre, edad):
        self.nombre = nombre
        self.edad = edad

    def __lt__(self, otra_persona):
        return self.edad < otra_persona.edad

p1 = Persona("Ana", 30)
p2 = Persona("Luis", 35)

print(p1 < p2)  # Output: True (Ana es menor que Luis)clear
