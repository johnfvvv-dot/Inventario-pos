import os
from google import genai

def leer_oferta():
    if not os.path.exists("oferta_actual.txt"):
        print("❌ No se encontró el archivo 'oferta_actual.txt'. Créalo en la misma carpeta y pega la descripción de la oferta ahí.")
        return None
    with open("oferta_actual.txt", "r", encoding="utf-8") as f:
        return f.read()

def generar_datos_cv(texto_oferta):
    print("🤖 Analizando la oferta y adaptando tu CV con Gemini...")
    
    prompt_sistema = """
    Eres un asistente experto en ingeniería de datos y optimización de CVs en Colombia.
    Tu único trabajo es adaptar el contenido interno (el texto descriptivo) de un diccionario de Python basándote en la oferta de empleo proporcionada, pero MANTENIENDO EXACTAMENTE la misma estructura, formato y claves originales.

    DEBES USAR ESTA PLANTILLA EXACTA (rellenando únicamente los valores de texto según la oferta, sin cambiar los nombres de las llaves ni la estructura de comentarios):

    # ==========================================
    # DATOS DE LA VACANTE (ADAPTADO AUTOMÁTICAMENTE)
    # Redacción natural y fluida basada en el CV original de John Fredy Santamaria Peña
    # ==========================================
    nuevos_datos = {
        "[PERFIL]": "...",
        "[HABILIDADES]": "...",
        "[EXPERIENCIA_1]": "...",
        "[EXPERIENCIA_2]": "...",
        "[EXPERIENCIA_3]": "...",
        "[EXPERIENCIA_4]": "...",
        "[EXPERIENCIA_5]": "...",
        "[EDUCACION]": "..."
    }

    REGLAS ESTRICTAS:
    1. NO inventes experiencia en áreas que el usuario no tiene (como marketing, mercadeo o estudios de mercado).
    2. Usa un lenguaje natural y fluido, adaptando sutilmente la experiencia a los requerimientos de la oferta.
    3. No utilices tecnicismos innecesariamente complejos.
    4. Omite menciones a plataformas Cloud (AWS, Azure, GCP).
    5. Devuelve ÚNICAMENTE el bloque de código Python limpio, empezando exactamente desde los comentarios y el diccionario `nuevos_datos = {`. No agregues texto adicional fuera del código.
    """

    client = genai.Client(api_key="<GEMINI_API_KEY>")
    
    response = client.models.generate_content(
        model='gemini-3.6-flash',
        contents=f"{prompt_sistema}\n\nAquí está la descripción de la oferta de empleo:\n\n{texto_oferta}"
    )
    
    return response.text

def guardar_en_datos_cv(codigo_diccionario):
    # Limpiamos bloques de markdown si los trae
    codigo_limpio = codigo_diccionario.replace("```python", "").replace("```", "").strip()

    # Escribimos el bloque exacto devuelto por la IA directamente en el archivo
    with open("datos_cv.py", "w", encoding="utf-8") as f:
        f.write(codigo_limpio)
        
    print("✅ Archivo 'datos_cv.py' actualizado manteniendo tu estructura exacta.")

def main():
    oferta = leer_oferta()
    if not oferta:
        return
        
    diccionario_ia = generar_datos_cv(oferta)
    guardar_en_datos_cv(diccionario_ia)
    
    print("🎉 ¡Proceso finalizado con éxito! Tu CV está adaptado y listo para compilar.")

if __name__ == "__main__":
    main()