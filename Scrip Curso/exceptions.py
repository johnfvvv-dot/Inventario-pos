try:
    divisor = int(input("Ingresa un Numero Divisor"))
    result = 8200/divisor
    print(result)
except ZeroDivisionError as e:
    print("Error: El divisor no pude ser cero" )
    print("Has ingresado: ", e)
except ValueError as e:
    print("Error: Debes introducir valor numerio 1...9")
    print("has ingresado: ", e)
