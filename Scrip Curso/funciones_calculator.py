def add (a,b):
    return a + b

def substract(a,b):
    return a - b

def multiply(a,b):
    return a * b

def divide(a,b):
    return a / b

def calculator():
    while True:
        print("Seleccione un a operacion")
        print("+ Suma")
        print("- Resta")
        print("* Multiplicacion")
        print("/ Divicion")
        print("S Salir")

        option = input("Ingrese su opcion (+,-,*,/,S):")

        if option == "S":
            print("Saliendo de la calculadora")
            break

        if option in ["+","-","*","/"]:
            num1 = float(input("Ingrese el primer numero: "))
            num2= float(input("Ingrese el primer segundo: "))
            if option == "+":
                print("la suma es:", add(num1, num2))
            elif option == "-":
                print("la resta es:", substract(num1, num2))
            elif option == "*":
                print("la multiplicacion es:", multiply(num1, num2))
            elif option == "/":
                print("la divicion es:", divide(num1, num2))

        else:
            print("Opcion no valida, por favor intenta nuevamente")   

calculator()                
