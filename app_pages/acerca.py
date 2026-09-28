from pathlib import Path

import streamlit as st

DIAGRAMA = Path(__file__).resolve().parents[1] / "assets" / "arquitectura.png"

st.subheader(":material/info: Acerca del sistema")
st.markdown(
    """
    El sistema compara un currículum con una oferta laboral **a nivel de habilidad
    individual**, y explica el resultado en lugar de devolver solo un puntaje.

    1. **Preprocesamiento**: extracción del texto del PDF con pdfplumber, respetando
       los CVs diseñados en dos columnas.
    2. **Extracción**: identificación de habilidades con spaCy (`es_core_news_md`) y un
       gazetteer propio por sector.
    3. **Representación semántica**: embeddings Sentence-BERT multilingües
       (`paraphrase-multilingual-MiniLM-L12-v2`).
    4. **Cálculo de compatibilidad**: similitud coseno habilidad por habilidad, con un
       umbral más estricto para siglas. Los requisitos obligatorios pesan el doble.
    5. **Explicación**: habilidades coincidentes, faltantes y excedentes.
    """
)
if DIAGRAMA.exists():
    st.image(str(DIAGRAMA), caption="Arquitectura del sistema.")

st.markdown("#### Secciones de la aplicación")
st.markdown(
    """
    - **Individual** y **Masiva**: evaluación de uno o muchos CVs, ranking con filtros e informes
      en PDF y Excel.
    - **Tablero**: distribución de puntajes, mapa de calor candidatos × requisitos, brechas de
      habilidades y talento adicional del lote.
    - **Comparar**: perfil por área (radar) y cara a cara entre finalistas.
    - **Laboratorio PLN**: mapa semántico de los embeddings, detalle de similitudes, sensibilidad
      al umbral y texto con las habilidades resaltadas.
    - **Validación**: Kappa de Cohen contra el evaluador humano y curva de concordancia según el umbral.
    """
)
st.caption("Herramienta de apoyo académico: no reemplaza el criterio de un reclutador humano.")
