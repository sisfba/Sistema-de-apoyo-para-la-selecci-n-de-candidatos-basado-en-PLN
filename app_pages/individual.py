import streamlit as st

import reportes
from motor import FORMATOS_CV, analizar_cv
from ui_comun import ctx, encabezado, mostrar_detalle, nombre_legible, registrar_cv, resultado

o = ctx()
encabezado(
    "Evaluación individual",
    "Compare un currículum con la oferta seleccionada en la barra lateral.",
    ":material/person_search:",
)
st.markdown(f"**Oferta seleccionada:** {o['titulo']}")

archivo_cv = st.file_uploader("Currículum vitae (PDF o Word)", type=FORMATOS_CV, key="cv_individual")

if st.button(
    "Calcular compatibilidad",
    type="primary",
    icon=":material/search:",
    disabled=archivo_cv is None or not o["requisitos"],
    key="btn_individual",
):
    with st.spinner("Extrayendo habilidades y calculando compatibilidad..."):
        registrar_cv(archivo_cv.name, *analizar_cv(archivo_cv.getvalue(), archivo_cv.name))
    st.session_state.individual = archivo_cv.name

actual = st.session_state.get("individual")
if actual and archivo_cv is not None and actual == archivo_cv.name:
    res = resultado(actual)
    nombre = nombre_legible(actual)

    with st.container(horizontal=True, vertical_alignment="bottom"):
        st.subheader(nombre)
        st.download_button(
            "Informe PDF",
            data=reportes.pdf_candidato(nombre, actual, o["titulo"], res, o["ajustes"], o["logo"]),
            file_name=f"informe_{nombre.replace(' ', '_')}.pdf",
            mime="application/pdf",
            icon=":material/picture_as_pdf:",
            key="pdf_individual",
        )
    st.caption(f"Comparado contra: {o['titulo']} · {o['ajustes']}")
    mostrar_detalle(res, "individual")
    st.page_link(
        "app_pages/laboratorio.py",
        label="Ver el análisis semántico de este CV en el Laboratorio PLN",
        icon=":material/hub:",
    )
