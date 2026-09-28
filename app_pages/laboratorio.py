import html
import re

import numpy as np
import pandas as pd
import streamlit as st

import graficos
from motor import embeddings, evaluar
from ui_comun import candidatos, ctx, encabezado, requiere_pool, resultado, selector_candidato

o = ctx()
encabezado(
    "Laboratorio PLN",
    "Lo que ocurre dentro del sistema: extracción, espacio semántico y efecto del umbral.",
    ":material/hub:",
)
requiere_pool()

archivo = selector_candidato("Candidato a analizar", key="lab_candidato")
cv = candidatos()[archivo]
res = resultado(archivo)

tab_mapa, tab_sim, tab_umbral, tab_texto = st.tabs([
    ":material/scatter_plot: Mapa semántico",
    ":material/table_chart: Detalle de similitud",
    ":material/tune: Sensibilidad al umbral",
    ":material/text_snippet: Texto resaltado",
])

# ------------------------- Mapa semántico 2D -------------------------
with tab_mapa:
    st.caption(
        "Cada punto es una habilidad convertida en vector por Sentence-BERT y proyectada a 2 "
        "dimensiones con PCA. Habilidades con significado parecido quedan cerca aunque se escriban "
        "distinto; las líneas punteadas unen cada requisito con la habilidad del CV que lo cubrió."
    )
    requisitos, habilidades = list(o["requisitos"]), list(cv["skills"])
    etiquetas = list(dict.fromkeys(requisitos + habilidades))
    if len(etiquetas) < 3:
        st.info("Se necesitan al menos 3 habilidades para dibujar el mapa.", icon=":material/info:")
    else:
        coords = graficos.proyeccion_2d(embeddings(tuple(etiquetas)))
        pos = {e: coords[i] for i, e in enumerate(etiquetas)}
        origen = {
            e: "En ambos" if e in requisitos and e in habilidades
            else "Requisito de la oferta" if e in requisitos else "Habilidad del CV"
            for e in etiquetas
        }
        solo_relevantes = st.toggle("Mostrar solo requisitos y habilidades emparejadas", key="lab_solo")
        emparejadas = {c[1] for c in res["coincidentes"]}
        visibles = [e for e in etiquetas if not solo_relevantes or e in requisitos or e in emparejadas]
        puntos = pd.DataFrame([{"Habilidad": e, "Origen": origen[e], "x": pos[e][0], "y": pos[e][1]}
                               for e in visibles])
        enlaces = pd.DataFrame([
            {"Requisito": r, "Habilidad": h, "Similitud": s,
             "x": pos[r][0], "y": pos[r][1], "x2": pos[h][0], "y2": pos[h][1]}
            for r, h, s in res["coincidentes"] if r != h
        ], columns=["Requisito", "Habilidad", "Similitud", "x", "y", "x2", "y2"])
        st.altair_chart(graficos.mapa_semantico(puntos, enlaces))

# ------------------------- Detalle de similitud -------------------------
with tab_sim:
    st.caption(
        "Para cada requisito, la habilidad más cercana del CV y su similitud coseno. "
        "«Semántica» indica coincidencias que el sistema aceptó sin que el texto fuera idéntico."
    )
    detalle = pd.DataFrame(res["detalle"])
    if detalle.empty:
        st.write("La oferta no tiene requisitos detectados.")
    else:
        conteo = detalle["Tipo de coincidencia"].value_counts()
        with st.container(horizontal=True):
            st.metric("Coincidencias exactas", int(conteo.get("Exacta", 0)), border=True)
            st.metric("Coincidencias semánticas", int(conteo.get("Semántica", 0)), border=True)
            st.metric("No encontradas", int(conteo.get("No encontrada", 0)), border=True)
        st.dataframe(
            detalle.sort_values("Similitud", ascending=False),
            hide_index=True,
            column_order=["Requisito", "Habilidad más cercana del CV", "Similitud", "Umbral aplicado",
                          "Tipo de coincidencia", "Cumple"] + (["Obligatorio"] if o["obligatorios"] else []),
            column_config={
                "Similitud": st.column_config.ProgressColumn(min_value=0, max_value=1, format="%.3f"),
                "Umbral aplicado": st.column_config.NumberColumn(format="%.2f", width="small"),
                "Cumple": st.column_config.CheckboxColumn(width="small"),
                "Obligatorio": st.column_config.CheckboxColumn(width="small"),
            },
        )

# ------------------------- Sensibilidad al umbral -------------------------
with tab_umbral:
    st.caption(
        "Cómo cambia el puntaje de este candidato al variar el umbral de similitud general "
        "(el de siglas se mantiene en su valor actual). La línea roja marca el umbral en uso."
    )
    umbrales = np.round(np.arange(0.40, 0.951, 0.025), 3)
    curva = pd.DataFrame([
        {"Umbral": u, "Métrica": "Compatibilidad (%)",
         "Valor": evaluar(cv["skills"], o["requisitos"], u, o["umbral_siglas"], o["obligatorios"])["puntaje"]}
        for u in umbrales
    ])
    st.altair_chart(graficos.curva_umbral(curva, o["umbral"], "Compatibilidad (%)"))
    st.caption(
        "Un umbral bajo acepta coincidencias poco parecidas (más falsos positivos); uno alto solo "
        "acepta habilidades casi idénticas (más falsos negativos). La página **Validación** muestra "
        "qué umbral concuerda mejor con el evaluador humano."
    )

# ------------------------- Texto resaltado -------------------------
with tab_texto:
    st.caption(
        "Texto extraído del PDF con las habilidades que detectaron spaCy y el gazetteer. "
        "Verde: cubren un requisito de la oferta. Azul: otras habilidades del CV."
    )
    cubren = {c[1] for c in res["coincidentes"]}
    terminos = sorted(cv["skills"], key=len, reverse=True)
    texto = cv["texto"]
    if terminos:
        patron = re.compile(r"(?<!\w)(" + "|".join(re.escape(t) for t in terminos) + r")(?!\w)", re.IGNORECASE)
        partes, ultimo = [], 0
        for m in patron.finditer(texto):
            clase = "req" if m.group(0).lower() in cubren else "cv"
            partes += [html.escape(texto[ultimo:m.start()]), f'<mark class="{clase}">{html.escape(m.group(0))}</mark>']
            ultimo = m.end()
        partes.append(html.escape(texto[ultimo:]))
        resaltado = "".join(partes)
    else:
        resaltado = html.escape(texto)
    with st.container(border=True, height=520):
        st.html(f'<div style="white-space: pre-wrap; line-height: 1.7; font-size: 0.9rem;">{resaltado}</div>')
