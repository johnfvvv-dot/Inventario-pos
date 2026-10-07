import os
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt
from docx2pdf import convert

def generar_cv_pdf(ruta_base, ruta_temp_docx, ruta_salida_pdf, datos):
    doc = Document(ruta_base)
    
    def reemplazar_texto(parrafos):
        # Usamos list() para no confundir al script al crear nuevos párrafos dinámicamente
        for p in list(parrafos):
            for clave, valor in datos.items():
                if clave in p.text:
                    # Separamos cada viñeta/función en párrafos individuales reales
                    lineas = valor.split('\n')
                    
                    # 1. El párrafo original asume el texto de la ÚLTIMA viñeta/línea
                    p.text = p.text.replace(clave, lineas[-1])
                    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                    p.paragraph_format.space_after = Pt(4) # Espacio mínimo entre funciones
                    
                    for run in p.runs:
                        run.font.name = 'Calibri'
                        run.font.size = Pt(11)
                        
                    # 2. Insertamos las líneas anteriores JUSTO ANTES, manteniendo el orden
                    for linea in lineas[:-1]:
                        nuevo_p = p.insert_paragraph_before(linea)
                        nuevo_p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                        nuevo_p.paragraph_format.space_after = Pt(4) # Espacio mínimo
                        for run in nuevo_p.runs:
                            run.font.name = 'Calibri'
                            run.font.size = Pt(11)

    # Buscar y reemplazar en texto normal
    reemplazar_texto(doc.paragraphs)
    
    # Buscar y reemplazar dentro de tablas
    for tabla in doc.tables:
        for fila in tabla.rows:
            for celda in fila.cells:
                reemplazar_texto(celda.paragraphs)

    # Guardar el archivo Word temporal
    doc.save(ruta_temp_docx)
    print(f"Borrador DOCX generado: {ruta_temp_docx}")
    
    # Convertir a PDF
    print("Convirtiendo a PDF... (esto puede tomar unos segundos)")
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

# ==========================================
# DATOS DE LA VACANTE (CATEGORIZADO CORREGIDO)
# ==========================================
nuevos_datos = {
    "[PERFIL]": "Ingeniero Industrial con 6 años de experiencia impulsando la eficiencia operativa a través de análisis de datos, Business Intelligence y optimización de procesos. Especializado en diseño, automatización y seguimiento de KPIs, desarrollo de dashboards y transformación de datos para fortalecer la toma de decisiones, mejorar el desempeño organizacional y garantizar la integridad de la información en entornos financieros y corporativos. Experiencia comprobada liderando reportes regulatorios, conciliaciones, auditoría de procesos internos y validación de información crítica, contribuyendo a la trazabilidad y control operativo. Enfoque que combina pensamiento analítico, precisión técnica y visión integral del negocio para transformar datos en información estratégica.",
    
    "[HABILIDADES]": "• Herramientas BI y Visualización: Power BI (Avanzado), Tableau, DAX.\n• Análisis y Gestión de Datos: Excel Avanzado (Power Query, Macros), Microsoft Access (Avanzado), SQL, Python, R, Modelado de Bases de Datos.\n• Optimización y Control: ETL y Transformación de Datos, Automatización de Reportes, Reportes Regulatorios, Auditoría de Procesos Internos, Conciliación Financiera.\n• Sistemas Corporativos: SAP SuccessFactors, Microsoft Dynamics, Dolibarr ERP.",
    
    "[EXPERIENCIA_1]": "• Diseñé e implementé dashboards interactivos y modelos de visualización en Power BI, permitiendo el monitoreo de KPIs de productividad y desempeño comercial.\n• Optimicé procesos de transformación, limpieza y consolidación de datos mediante Power Query y Excel Avanzado.\n• Automaticé reportes gerenciales y operativos, fortaleciendo la agilidad en la generación de insights.\n• Lideré procesos de auditoría y validación de registros comerciales, garantizando integridad y trazabilidad.\n• Realicé análisis de tendencias, patrones de comportamiento y oportunidades de mejora.",
    
    "[EXPERIENCIA_2]": "• Ejecuté procesos de validación, conciliación y aplicación de recaudos provenientes de múltiples medios de pago.\n• Gestioné grandes volúmenes de información mediante Excel avanzado, Access y consultas SQL para depuración de datos.\n• Diseñé dashboards e indicadores en Power BI para monitoreo de recaudos y productividad operativa.\n• Identifiqué desviaciones, inconsistencias y riesgos operativos, implementando acciones correctivas.",
    
    "[EXPERIENCIA_3]": "• Generé, revisé y validé reportes regulatorios bajo lineamientos normativos de la SFC.\n• Diseñé dashboards e indicadores en Power BI y Tableau para monitoreo de cumplimiento regulatorio y eficiencia operativa.\n• Analicé el comportamiento de pagos y niveles de morosidad de cartera, identificando alertas tempranas de riesgo.\n• Implementé controles de calidad sobre la información, reduciendo reprocesos.",
    
    "[EXPERIENCIA_4]": "• Administré la estructura organizacional en SAP SuccessFactors Employee Central, asegurando la consistencia de la información maestra.\n• Ejecuté cargues masivos mediante archivos planos y Excel avanzado, optimizando actualizaciones de datos.\n• Generé y analicé reportes de estructura organizacional para apoyar procesos de auditoría interna y toma de decisiones.",
    
    "[EXPERIENCIA_5]": "• Administré el ERP Dolibarr CRM y configuré módulos, usuarios y permisos.\n• Diseñé plantillas en Excel avanzado para gestión y cargue masivo de inventario en bases de datos relacionales (SQL/MySQL).\n• Elaboré reportes e indicadores de facturación, compras e inventario.",
    
    "[EDUCACION]": "• Ingeniería Industrial — Universidad ECCI (2013 - 2019)\n• Tecnólogo en Gestión de Producción Industrial — SENA (2013)\n• Programación en R: Introduction to R (DataCamp, 2026) | Curso Intermedio de R (En progreso)\n• Certificaciones en Datos (Platzi / Santander): Power BI Avanzado, Python, Curso Práctico de SQL, PostgreSQL Aplicado a Ciencia de Datos, Ciencia de Datos para Análisis de Negocio, DAX."
}

if __name__ == "__main__":
    generar_cv_pdf(ruta_base, ruta_temp, ruta_pdf, nuevos_datos)