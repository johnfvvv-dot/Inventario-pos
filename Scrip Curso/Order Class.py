"""
Crear un método estático para verificar si el monto de un pedido es mayor a un mínimo permitido (50$ en este caso)
Crear un método clase que permita crear un pedido aplicando un descuento global
"""

class Order:
    global_discount = 10

    @staticmethod
    def min_amount(amount):
        if amount < 50:
            raise ValueError('Your orden must be minimun 50$')
        else:
            return amount
        
    @classmethod
    def new_order(cls, amount):
        if cls.min_amount(amount):
            print(f'Your orden has been created. You have a discount of {cls.global_discount}%. Total of your order: {amount - (amount * (cls.global_discount/100))}')

Order.new_order(60)