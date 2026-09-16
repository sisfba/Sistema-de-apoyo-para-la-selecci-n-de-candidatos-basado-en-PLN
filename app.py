"""
Interfaz del sistema de apoyo a la selección de candidatos basado en PLN.

Para correrla:
    streamlit run app.py

Requiere que extraction.py, gazetteer.py, ofertas.py y
compatibilidad_produccion.py estén en la misma carpeta.
"""
import tempfile
import os
import streamlit as st

from extraction import extract_text_from_pdf, extract_skills
from ofertas import OFERTAS
from compatibilidad_produccion import calcular_compatibilidad

st.set_page_config(
    page_title="Sistema de apoyo a la selección de candidatos",
    page_icon="🧩",
    layout="wide",
)

st.title("🧩 Sistema de apoyo a la selección de candidatos")
st.caption(
    "Proyecto Integrador · Curso de Procesamiento de Lenguaje Natural · "
    "Maestría en Inteligencia Artificial, UCV"
)

with st.expander("ℹ️ Cómo funciona", expanded=False):
    st.markdown(
        """
        1. Cargue un **CV en PDF**.
        2. Elija una **oferta laboral** de ejemplo, o pegue el texto de una propia.
        3. El sistema extrae las habilidades de ambos documentos (spaCy + gazetteer),
           las compara mediante embeddings semánticos (Sentence-BERT multilingüe),
           y muestra un puntaje de compatibilidad junto con el detalle de qué
           habilidades **coinciden**, cuáles **faltan** y cuáles son **excedentes**.
        """
    )

col_izq, col_der = st.columns(2)

# ------------------------- Columna izquierda: CV -------------------------
with col_izq:
    st.subheader("1. Currículum vitae")
    archivo_cv = st.file_uploader("Cargar CV en PDF", type=["pdf"])

    texto_cv = ""
    if archivo_cv is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(archivo_cv.read())
            ruta_temporal = tmp.name
        try:
            texto_cv = extract_text_from_pdf(ruta_temporal)
            st.success(f"CV leído correctamente ({len(texto_cv)} caracteres extraídos).")
            with st.expander("Ver texto extraído del CV"):
                st.text(texto_cv[:3000] + ("..." if len(texto_cv) > 3000 else ""))
        finally:
            os.unlink(ruta_temporal)

# ------------------------- Columna derecha: Oferta -------------------------
with col_der:
    st.subheader("2. Oferta laboral")
    modo_oferta = st.radio(
        "Fuente de la oferta",
        ["Elegir una oferta de ejemplo", "Pegar texto de una oferta propia"],
        horizontal=False,
    )

    texto_oferta = ""
    if modo_oferta == "Elegir una oferta de ejemplo":
        clave_oferta = st.selectbox(
            "Oferta",
            options=list(OFERTAS.keys()),
            format_func=lambda k: OFERTAS[k]["titulo"],
        )
        texto_oferta = OFERTAS[clave_oferta]["texto"]
        with st.expander("Ver texto de la oferta"):
            st.text(texto_oferta)
    else:
        texto_oferta = st.text_area(
            "Pegue aquí el texto completo de la oferta laboral",
            height=280,
            placeholder="Ej.: Empresa busca... Requisitos: ...",
        )

st.divider()

# ------------------------- Botón de análisis -------------------------
if st.button("🔍 Calcular compatibilidad", type="primary", use_container_width=True):
    if not texto_cv:
        st.error("Carga un CV en PDF antes de continuar.")
    elif not texto_oferta.strip():
        st.error("Selecciona una oferta de ejemplo o pega el texto de una oferta.")
    else:
        with st.spinner("Extrayendo habilidades y calculando compatibilidad..."):
            skills_cv = sorted(extract_skills(texto_cv).keys())
            skills_oferta = sorted(extract_skills(texto_oferta).keys())
            resultado = calcular_compatibilidad(skills_cv, skills_oferta)

        st.subheader("Resultado")

        col_puntaje, col_resumen = st.columns([1, 3])
        with col_puntaje:
            st.metric("Puntaje de compatibilidad", f"{resultado['puntaje']}%")
        with col_resumen:
            n_coinciden = len(resultado["coincidentes"])
            n_faltan = len(resultado["faltantes"])
            n_total_oferta = n_coinciden + n_faltan
            st.write(
                f"El CV cumple **{n_coinciden} de {n_total_oferta}** requisitos "
                f"identificados en la oferta."
            )

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("### ✅ Coincidentes")
            if resultado["coincidentes"]:
                for hab_oferta, hab_cv, sim in resultado["coincidentes"]:
                    if hab_oferta == hab_cv:
                        st.markdown(f"- **{hab_oferta}**")
                    else:
                        st.markdown(f"- **{hab_oferta}** *(vía «{hab_cv}», similitud {sim})*")
            else:
                st.write("Ninguna.")

        with col2:
            st.markdown("### ❌ Faltantes")
            st.caption("La oferta las pide; no se encontraron en el CV.")
            if resultado["faltantes"]:
                for hab in resultado["faltantes"]:
                    st.markdown(f"- {hab}")
            else:
                st.write("Ninguna, el CV cubre todo lo solicitado.")

        with col3:
            st.markdown("### ➕ Excedentes")
            st.caption("El CV las tiene; la oferta no las pide.")
            if resultado["excedentes"]:
                for hab in resultado["excedentes"]:
                    st.markdown(f"- {hab}")
            else:
                st.write("Ninguna.")

st.divider()
st.caption(
    "Modelo de embeddings: paraphrase-multilingual-MiniLM-L12-v2 (Sentence-BERT). "
    "Extracción de habilidades: spaCy (es_core_news_md) + gazetteer propio. "
    "Proyecto Integrador de PLN — no reemplaza el criterio de un reclutador humano."
)
