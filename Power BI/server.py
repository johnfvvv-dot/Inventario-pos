from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Prompt(BaseModel):
    prompt: str

@app.post("/generate_dashboard")
def generate_dashboard(prompt: Prompt):
    # Datos ficticios de prueba
    data = [
        {"Region": "Norte", "Ventas": 100},
        {"Region": "Sur", "Ventas": 150},
        {"Region": "Este", "Ventas": 200},
        {"Region": "Oeste", "Ventas": 130}
    ]
    return {"dataset": data, "message": f"Tablero generado para: {prompt.prompt}"}
