#Leer un archivo sin interlineas
"""with open('Caperucita_Roja.txt', 'r') as file:
    for line in file:   # mejor usar 'line' en singular
        print(line.strip())"""

#Leer un archivo
"""with open('Caperucita_Roja.txt', 'r') as file:
    for line in file:   # mejor usar 'line' en singular
        print(line)"""

#Leer un archivo todas las lineas pero en lista
"""with open('Caperucita_Roja.txt', 'r') as file:
    lines = file.readlines()
    print(lines)"""

#anadir texto al archivo
"""with open('Caperucita_Roja.txt', 'a') as file:
    file.write("\n\nBy:ChatGPT")"""

#Sobreescribir el texto
"""with open('Caperucita_Roja_W.txt', 'w') as file:
    file.write("\n\nBy:ChatGPT")"""

#Leer Lineas
with open('Caperucita_Roja.txt', 'r') as file:
    lines = file.readlines()
    print(len(lines))