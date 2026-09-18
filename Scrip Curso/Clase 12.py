#Iteraciones y control de flujo con bucles en python
numbers = [1, 2, 3, 4, 5, 6]
for i in numbers:
    print("Aqui i es igual a:",i+0.5)

for i in range (1,14):
    print(i)

fruits = ["manzana", "pera", "uva", "naranja", "tomate"]
for fruit in fruits:
    print(fruit)
    if fruit == "pera":
        print("pera encontrada")