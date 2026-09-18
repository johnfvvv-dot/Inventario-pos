import os

#Obtener el directorio actual
"""cwd = os.getcwd()
print("Directorio de trabajo actual", cwd)"""

#Listar los arcgivos .py
"""py_files = [f for f in os.listdir('.') if f.endswith('.py')]
print("Archivos py: ", py_files)"""

#Renombra Archivo
os. rename('Caperucita_Roja.txt', 'Cuento Caperucita Roja.txt')
print('Archivo Renombrado')

#Listar los arcgivos .txt
txt_files = [f for f in os.listdir('.') if f.endswith('.txt')]
print("Archivos txt: ", txt_files)