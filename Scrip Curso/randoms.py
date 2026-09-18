import random

#Generar un numero entero aleatorio 1
random_number_1 = random.randint(1,8)
print(random_number_1)

#Generar un numero entero aleatorio 2
random_number_2 = random.randint(9,17)
print(random_number_2)

#Generar un numero entero aleatorio 3
random_number_3 = random.randint(18,25)
print(random_number_3)

#Generar un numero entero aleatorio 4
random_number_4 = random.randint(26,33)
print(random_number_4)

#Generar un numero entero aleatorio 5
random_number_5 = random.randint(34,43)
print(random_number_5)

#Generar un numero entero aleatorio superbalota
random_number_sb = random.randint(1,16)
print(random_number_sb)

#Elegir color aleatorio
colors = ['Verde','Azul','Negro','Morado','Amarillo']
random_colors=random.choice(colors)
print(random_colors)

#Barajar una lista de cartas
cards = ['A','K','Q','J','10']
random.shuffle(cards)
print(cards)