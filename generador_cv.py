import os
from datetime import datetime
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt
from docx2pdf import convert

# Importamos los datos desde nuestro archivo independiente de la vacante
from datos_cv import nuevos_datos

def obtener_fecha_actual():
    """Genera automáticamente el mes en minúsculas y el año actual en español."""
    meses = {
        1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
        5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
        9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
    }
    ahora = datetime.now()
    nombre_mes = meses[ahora.month]
    anio_actual = str(ahora.year)
    return f"{nombre_mes} {anio_actual}"
def generar_cv_pdf(ruta_base, ruta_temp_docx, ruta_salida_pdf, datos):
    doc = Document(ruta_base)
    
    # Agregamos la etiqueta dinámica de la fecha actual al diccionario de datos
    datos_completos = datos.copy()
    datos_completos["[FECHA_ACTUAL]"] = obtener_fecha_actual()
    
    def reemplazar_texto(parrafos):
        for p in list(parrafos):
            for clave, valor in datos_completos.items():
                if clave in p.text:
                    lineas = valor.split('\n')
                    
                    # El párrafo original asume el texto de la última línea
                    p.text = p.text.replace(clave, lineas[-1])
                    
                    # Si es la etiqueta de la fecha, la centramos; de lo contrario, la justificamos
                    if clave == "[FECHA_ACTUAL]":
                        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    else:
                        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                        
                    p.paragraph_format.space_after = Pt(4)
                    
                    for run in p.runs:
                        run.font.name = 'Calibri'
                        run.font.size = Pt(11)
                        
                    # Insertamos las líneas anteriores manteniendo el orden
                    for linea in lineas[:-1]:
                        nuevo_p = p.insert_paragraph_before(linea)
                        nuevo_p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                        nuevo_p.paragraph_format.space_after = Pt(4)
                        for run in nuevo_p.runs:
                            run.font.name = 'Calibri'
                            run.font.size = Pt(11)

    # Reemplazar en texto normal y tablas
    reemplazar_texto(doc.paragraphs)
    for tabla in doc.tables:
        for fila in tabla.rows:
            for celda in fila.cells:
                reemplazar_texto(celda.paragraphs)

    doc.save(ruta_temp_docx)
    print(f"Borrador DOCX generado: {ruta_temp_docx}")
    
    print("Convirtiendo a PDF...")
    try:
        convert(ruta_temp_docx, ruta_salida_pdf)
        print(f"¡Éxito! Tu CV en PDF está listo en: {ruta_salida_pdf}")
    except Exception as e:
        print(f"Error al convertir a PDF: {e}")
        print("Nota: Asegúrate de tener Microsoft Word cerrado durante la conversión.")

# ==========================================
# CONFIGURACIÓN DE RUTAS
# ==========================================
carpeta_base = r"C:\Users\XR-18\Desktop\Python\Plantilla CV"
ruta_base = os.path.join(carpeta_base, "CV Base John Santamaria.docx")
ruta_temp = os.path.join(carpeta_base, "CV_Temporal.docx")

carpeta_pdf = r"C:\Users\XR-18\Desktop\Python\CVs PDF"
ruta_pdf = os.path.join(carpeta_pdf, "CV_John_Santamaria.pdf")

if not os.path.exists(carpeta_pdf):
    os.makedirs(carpeta_pdf)

if __name__ == "__main__":
    generar_cv_pdf(ruta_base, ruta_temp, ruta_pdf, nuevos_datos)
    