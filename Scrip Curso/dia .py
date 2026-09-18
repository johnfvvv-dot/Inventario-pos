# Caso en el que el usuario ingresa un día de la semana y el prograa responde con una actividad planificada para ese día.

dia = input("Ingresa un día de la semana (lunes, martes, miércoles, jueves, viernes, sábado o domingo): ").lower()

match dia:

  case "lunes":

    print("Ir al GYM")

  case "martes":

    print("Reunión team de trabajo")

  case "miercoles":

    print("Clase de cocina")

  case "jueves":

    print("Día de estudio")

  case "viernes":

    print("Salida con amigos")

  case "sabado":

    print("Salida al aire libre")


frutas = ["Manzana", "Banano", "Cereza"]
adjetivos = ["roja", "madura", "deliciosa"]
for fruta in frutas:
  for adjetivo in adjetivos:
    print(fruta,adjetivo)