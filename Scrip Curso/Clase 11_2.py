X = 5
Y = 5

if X > 15 and Y > 25:
    print("X es mayor que 15 y Y es mayor que 25")
elif X > 15 and Y < 25:
    print("X es mayor que 15 y Y es menor que 25")
elif X < 15 and Y > 25:
    print("X es menor que 15 y Y es meyor que 25")
elif X == 15 and Y == 25:
    print("X es igual que 15 y Y es igual que 25")
elif X > 15 and Y == 25:
    print("X es mayor que 15 y Y es igual que 25")
elif X < 15 and Y == 25:
    print("X es menor que 15 y Y es igual que 25")
elif X == 15 and Y > 25:
    print("X es igual que 15 y Y es mayor que 25")
elif X == 15 and Y < 25:
    print("X es igual que 15 y Y es menor que 25")
else: 
    print("X es menor que 15 y Y es menor que 25")