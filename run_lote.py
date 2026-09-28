"""
Procesa un lote de CVs contra una oferta y muestra el resultado de cada uno.
Ajusta CARPETA_CVS y OFERTA_KEY según lo que quieras probar.
"""
import os
from extraction import extract_text_from_pdf, extract_skills
from ofertas import OFERTAS
from compatibilidad_produccion import calcular_compatibilidad

CARPETA_CVS = "cvs"  # carpeta con los PDFs a procesar
OFERTA_KEY = "oferta_salud_clinica"  # cambiar según el lote (ver ofertas.py)

oferta = OFERTAS[OFERTA_KEY]
skills_oferta = sorted(extract_skills(oferta["texto"]).keys())

for archivo in sorted(os.listdir(CARPETA_CVS)):
    if not archivo.lower().endswith(".pdf"):
        continue
    path = os.path.join(CARPETA_CVS, archivo)
    texto_cv = extract_text_from_pdf(path)
    skills_cv = sorted(extract_skills(texto_cv).keys())
    resultado = calcular_compatibilidad(skills_cv, skills_oferta)

    print("=" * 80)
    print(f"CV: {archivo}")
    print(f"Oferta: {oferta['titulo']}")
    print(f"Puntaje: {resultado['puntaje']}%")
    print(f"Coincidentes: {[c[0] for c in resultado['coincidentes']]}")
    print(f"Faltantes: {resultado['faltantes']}")
    print(f"Excedentes: {resultado['excedentes']}")
    print()
