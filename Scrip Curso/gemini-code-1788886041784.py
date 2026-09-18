import os
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

doc = Document()

# Title / Name
name_p = doc.add_paragraph()
name_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
name_run = name_p.add_run("JOHN FREDY SANTAMARIA PEÑA")
name_run.bold = True
name_run.font.size = Pt(20)
name_run.font.color.rgb = RGBColor(0, 51, 102)

# Contact Info
contact_p = doc.add_paragraph()
contact_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
contact_run = contact_p.add_run("3502299795 - 3138374664 | johnfvvv@gmail.com | Bogotá\nlinkedin.com/in/john-santamariap\nCC 1073156666 de Madrid, Cundinamarca")
contact_run.font.size = Pt(10)
contact_run.font.color.rgb = RGBColor(89, 89, 89)

doc.add_paragraph() # Spacing

# Section Function
def add_section_header(text):
    p = doc.add_paragraph()
    run = p.add_run(text.upper())
    run.bold = True
    run.font.size = Pt(13)
    run.font.color.rgb = RGBColor(0, 51, 102)
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(6)

# Perfil Profesional
add_section_header("Perfil Profesional")
doc.add_paragraph("Analista de datos orientado a resultados con sólida capacidad para transformar información compleja en soluciones estratégicas útiles. Experiencia comprobada en el diseño de flujos de trabajo ETL, análisis estadístico y creación de reportes dinámicos. Dominio técnico de herramientas como Python, R, SQL y Power BI. Enfoque analítico orientado a la optimización de procesos y a la toma de decisiones fundamentada en datos.")

# Habilidades Técnicas
add_section_header("Habilidades Técnicas")
skills = [
    ("Visualización y Reportes: ", "Power BI, Excel Avanzado (Power Query, Dashboards)."),
    ("Lenguajes de Programación: ", "Python (Análisis exploratorio de datos, Pandas, NumPy), R (Manipulación de datos, funciones estadísticas), SQL."),
    ("Gestión de Datos: ", "Procesos ETL, Administración de Bases de Datos relacionales."),
    ("Desarrollo Profesional: ", "Uso de herramientas de Inteligencia Artificial aplicadas al análisis y eficiencia operativa.")
]
for bold_text, normal_text in skills:
    p = doc.add_paragraph(style='List Bullet')
    p.add_run(bold_text).bold = True
    p.add_run(normal_text)

# Experiencia Profesional
add_section_header("Experiencia Profesional")

exp1_p = doc.add_paragraph()
exp1_p.add_run("Analista de Datos Freelance | Upwork").bold = True
exp1_p.add_run("\nAgosto 2026 - Presente | Remoto")

doc.add_paragraph("Desarrollo de soluciones de análisis de datos, integrando procesos de extracción, transformación y carga (ETL).", style='List Bullet')
doc.add_paragraph("Implementación de scripts en Python y R para el procesamiento eficiente de bases de datos.", style='List Bullet')
doc.add_paragraph("Diseño de tableros interactivos e informes en Power BI para facilitar la visualización de KPIs.", style='List Bullet')

# Educación y Certificaciones
add_section_header("Educación y Certificaciones")
edu = [
    ("Introducción a R", "Agosto 2026", "Certificación Técnica"),
    ("Análisis Exploratorio de Datos en Python", "Oct. - Nov. 2025", "SENA"),
    ("Administración de Bases de Datos", "Octubre 2025", "SENA"),
    ("Programa Académico", "[Año de Grado]", "Universidad ECCI")
]
for title, date, inst in edu:
    p = doc.add_paragraph(style='List Bullet')
    p.add_run(f"{title} ").bold = True
    p.add_run(f"— {inst} ({date})")

# Footer / Date
footer = doc.add_paragraph("\nBogotá D.C. septiembre 2026")
footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT

filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "CV_Prueba_John_Santamaria.docx")
doc.save(filepath)
print(f"File generated: {filepath}")