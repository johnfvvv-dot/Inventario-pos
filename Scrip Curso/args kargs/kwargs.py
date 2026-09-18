def print_info(**kwargs):
    for key, value in kwargs.items():
        print(f"{key}: {value}")


print_info(name="John", age=30, city="Bogota")
print_info(name="Jane", age=25, city="Los Angeles")
print_info(name="Jim", age=35, city="Chicago")