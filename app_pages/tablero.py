import streamlit as st

import graficos
from ui_comun import ctx, encabezado, lote, requiere_lote, resultado, tabla_detalle_lote, tabla_ranking

o = ctx()
encabezado(
    "Tablero del lote",
    "Vista general de la última evaluación masiva frente a la oferta seleccionada.",
    ":material/dashboard:",
)
requiere_lote()

ranking = tabla_ranking(lote())
detalle = tabla_detalle_lote(lote())
cumplimiento = detalle.groupby("Requisito")["Cumple"].mean()

st.markdown(f"**Oferta:** {o['titulo']} · {o['ajustes']}")
with st.container(horizontal=True):
    st.metric("CVs evaluados", len(ranking), border=True)
    st.metric("Compatibilidad promedio", f"{ranking['Compatibilidad'].mean():.1f}%", border=True)
    st.metric("Mediana", f"{ranking['Compatibilidad'].median():.1f}%", border=True)
    st.metric(f"Más cubierto: {cumplimiento.idxmax()}", f"{cumplimiento.max():.0%}",
              "de los CVs lo cumple", delta_color="off", delta_arrow="off", border=True)
    st.metric(f"Mayor brecha: {cumplimiento.idxmin()}", f"{cumplimiento.min():.0%}",
              "de los CVs lo cumple", delta_color="off", delta_arrow="off", border=True)

col1, col2 = st.columns([3, 2])
with col1.container(border=True):
    st.markdown("**Distribución de puntajes**")
    st.altair_chart(graficos.distribucion(ranking))
with col2.container(border=True):
    st.markdown("**Candidatos por nivel**")
    st.altair_chart(graficos.dona_niveles(ranking))

with st.container(border=True):
    st.markdown("**Mapa de calor: candidatos × requisitos**")
    st.caption(
        "El color indica la similitud entre el requisito y la habilidad más cercana del CV; "
        "✓ marca los requisitos que el sistema considera cumplidos con el umbral actual."
    )
    maximo = len(ranking)
    top = st.slider("Candidatos a mostrar (los de mayor puntaje)", 1, maximo, min(25, maximo),
                    key="top_mapa") if maximo > 1 else 1
    visibles = set(ranking["Candidato"].head(top))
    st.altair_chart(graficos.mapa_calor(detalle[detalle["Candidato"].isin(visibles)]))

col3, col4 = st.columns(2)
with col3.container(border=True, height="stretch"):
    st.markdown("**Brechas de habilidades**")
    st.caption("Requisitos que más faltan en el lote: indican qué capacitar o qué es difícil de encontrar.")
    st.altair_chart(graficos.brechas(detalle))
with col4.container(border=True, height="stretch"):
    st.markdown("**Habilidades adicionales más comunes**")
    st.caption("Lo que los candidatos traen y la oferta no pide: talento no buscado.")
    excedentes = [h for a in lote() for h in resultado(a)["excedentes"]]
    if excedentes:
        st.altair_chart(graficos.excedentes_comunes(excedentes))
    else:
        st.write("Ninguna.")
