import numpy as np

def calculadora(operacion, a=0, b=0, lista_digitos=None):
    operacion = operacion.lower().strip()
    
    # Operaciones Aritméticas Básicas
    if operacion == "sumar":
        return a + b
    if operacion == "restar":
        return a - b
    if operacion == "multiplicar":
        return a * b
    if operacion == "dividir":
        if b == 0:
            return "Error: No se puede dividir por cero"
        return a / b
        
    # Operaciones Estadísticas
    operaciones_estadisticas = ["media", "desviacion estandar", "bollinger", "minimo", "maximo"]
    
    if operacion in operaciones_estadisticas:
        if lista_digitos is None or len(lista_digitos) != 10:
            return "Error: Se requiere una lista de exactamente 10 dígitos."
            
        arr = np.array(lista_digitos)
        
        if operacion == "media":
            return float(np.mean(arr))
        if operacion == "desviacion estandar":
            return float(np.std(arr, ddof=1))  # ddof=1 → desviación estándar muestral
        if operacion == "minimo":
            return float(np.min(arr))
        if operacion == "maximo":
            return float(np.max(arr))
        if operacion == "bollinger":
            media = np.mean(arr)
            std = np.std(arr, ddof=1)
            return {
                "Banda Superior": float(media + (2*std)),
                "Banda Inferior": float(media - (2*std))
            }
            
    return "Operación no reconocida"

# Pruebas
print(calculadora("sumar", a=5, b=3))  
print(calculadora("dividir", a=10, b=0))  
print(calculadora("media", lista_digitos=[12,14,15,11,16,12,14,15,13,14]))  
print(calculadora("bollinger", lista_digitos=[12,14,15,11,16,12,14,15,13,14]))
