from google import genai

# Inicializamos el cliente pasando la clave directamente para evitar líos con PowerShell
client = genai.Client(api_key="<GEMINI_API_KEY>")

response = client.models.generate_content(
    model='gemini-3.6-flash',  # Usando el modelo exacto que exige tu API key actual
    contents='Hola Gemini, respóndeme solo con un: "¡Conexión exitosa!"'
)

print(response.text)