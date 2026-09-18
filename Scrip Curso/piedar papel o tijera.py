piedraplayer_1 = input("Player 1, Ingrese Piedra, Tijera, Papel: "    )

player_2 = input("Player 2, Ingrese Piedra, Tijera, Papel: "    )

if player_1 == player_2:

    print("Empate")

elif (player_1 == "Piedra" and player_2 == "Tijera") or (player_1 == "Tijera" and player_2 == "Papel") or (player_1 == "Papel" and player_2 == "Piedra"):

    print("Gana jugador 1")

else:

    print("Gana jugador 2")

   