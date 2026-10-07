import os

from google import genai

# La clave se toma de una variable de entorno para no quedar guardada en el código
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

response = client.models.generate_content(
    model='gemini-3.6-flash',  # Usando el modelo exacto que exige tu API key actual
    contents='Hola Gemini, respóndeme solo con un: "¡Conexión exitosa!"'
)

print(response.text)