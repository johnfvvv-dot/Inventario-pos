empleados = [
                {'name': 'Iris', 'age': '43', 'salary': 1000},
                {'name': 'Ivan', 'age': '45', 'salary': 200},
                {'name': 'Andres', 'age': '25', 'salary': 300},
                {'name': 'Nohelia', 'age': '21', 'salary': 1200},
                {'name': 'Samuel', 'age': '27', 'salary': 500 },
                {'name': 'David', 'age': '33', 'salary': 600 },
                {'name': 'Sarahi', 'age': '30', 'salary': 700},
                {'name': 'Jesus', 'age': '54', 'salary': 800},
                {'name': 'Haydee', 'age': '34', 'salary': 900},
                {'name': 'Francisco', 'age': '43', 'salary': 1000}
            ] # Variable global

def empleados_con_mejor_sueldo(empleados,sueldo):
    empleados_superan_sueldo = [] # Variable local
    empleados_superan_sueldo = [empleado["name"] for empleado in empleados if empleado["salary"]>= sueldo]
    return empleados_superan_sueldo

sueldo = 800
print(f'Los empleados con suledo superior a {sueldo} son:  {empleados_con_mejor_sueldo(empleados, sueldo)}')