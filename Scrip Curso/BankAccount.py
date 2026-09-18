class BankAcount:
    def __init__(self, account_holder, balance):
        self.account_holder = account_holder
        self. balance = balance
        self.is_active = True

    def deposit(self, amount):
        if self.is_active:
            self.balance = amount
            print(f("se ha depositado {amount}. Saldo actual {selt.balance}"))
        else:
            print("No se puede depositarm Cuneta inactiva")