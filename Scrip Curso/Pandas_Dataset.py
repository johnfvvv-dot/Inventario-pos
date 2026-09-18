import pandas as pd

path = 'C:/Users/XR-18/Desktop/Python/Scrip Curso/Online_retail.csv'
#path = '/Desktop/Python/Scrip Curso/Online_retail.csv'
retail_data = pd.read_csv(path, encoding='latin1')
#print(type(retail_data))
print(retail_data.head())


# 1. Imputar las edades vacías con el promedio
df['edad'] = df['edad'].fillna(df['edad'].mean())

# 2. Filtrar para mantener salarios mayores a 4.5M
df = df[df['salario_mensual'] > 4500000]

# 3. Crear la columna calculada del salario anual
df['salario_anual'] = df['salario_mensual'] * 12