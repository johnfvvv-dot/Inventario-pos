to_do = ["Dirigirnos al hotel",
         "Ir a almorzar",
         "Visitar el museo",
         "Volver al hotel"]
print (to_do)
numbers = [1, 2, 3, 4, "cinco"]
print (type(numbers))
mix = ["uno", 2, 3.14, True, [11, 2, 3], 1+7]
print (mix)
print (len(mix))
print ("Primer elemento", mix [0])
print ("Segundo elemento", mix [1])
print ("Tercero elemento", mix [2])
print ("Cuarto elemento", mix [3])
print ("Quinto elemento", mix [-2])
print ("Sexto elemento", mix [-1])
string = "Hola Mundo"
print ("Elemento:", string [0])
print ("Elemento:", string [1])
print ("Elemento:", string [2])
print ("Elemento:", string [3])
print ("Elemento:", string [-6])
print ("Elemento:", string [5])
print ("Elemento:", string [6])
print ("Elemento:", string [7])
print ("Elemento:", string [-2])
print ("Elemento;", string [-1])
print (mix[2:4])
print (mix[2:])
print (mix[2:-1])
print (mix)
mix.append (False)
print (mix)
mix.append (["a", "b"])
print (mix)
mix.insert (1,["a", "b"])
print (mix)
print (mix.index(False))
numbers = [1, 2, 100, 90.45, 3, 4, 5]
print   ("Mayor:", max(numbers))
print   ("Menor:", min(numbers))
del numbers [-2]
print (numbers)
del numbers [:2]
print (numbers)
del numbers
print (numbers)