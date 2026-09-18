#Iteradores y Generadores em Py: Uso eficiente de memoria

#Iterar en Cadenas

#crando la Cadena
text = "Hola Mundo"

#Creando el objeto iterador
iter_text = iter(text)

#Iterar en la cadena
for char in iter_text:
    print(char)