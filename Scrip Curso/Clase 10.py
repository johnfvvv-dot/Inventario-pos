#Uso y manipulacion de datos
numbers = {1:"uno",2:"dos",3:"tres"}
print(numbers[2])
informacion ={"nombre":"John",
              "apellido":"Santamaria",
              "estatura":1.60,
              "edad":32}
print(informacion)
del informacion ["edad"]
print(informacion)
claves = informacion.keys()
print(claves)
print(type(claves))
values = informacion.values()
print(values)
pairs = informacion.items()
print(pairs)

contactos = {"John":{"apellido":"Santamaria",
              "estatura":1.75,
              "edad":32}, "Lorena":{"apellido":"Reyes",
              "estatura":1.60,
              "edad":24}}
print (contactos["Lorena"])