from random import randint
import numpy as np

prices = np.array([100,200,300])
discount = np.array([0.9])
discount_prices = prices * discount
print(discount_prices) 

print("----------------------------------------------")

prices1 = np.random.randint(100,500, size=(5,5))
discount1 = np.array([10,20,30,15,25])
discount_prices1 = prices1 + discount1
print(prices1)
print("----------------------------------------------")
print(discount_prices1)