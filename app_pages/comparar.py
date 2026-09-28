import pandas as pd
import streamlit as st

import graficos
from motor import perfil_por_categoria
from ui_comun import candidatos, ctx, encabezado, nombre_legible, pool, requiere_pool, resultado, tabla_ranking

o = ctx()
encabezado(
    "Comparar candidatos",
    "Ponga de 2 a 4 candidatos lado a lado: perfil por área y requisito por requisito.",
    ":material/compare_arrows:",
)
requiere_pool()

opciones = tabla_ranking(pool())["Archivo"].tolist()
if len(opciones) < 2:
    st.info("Se necesitan al menos 2 CVs evaluados para comparar.", icon=":material/info:")
    st.stop()

elegidos = st.multiselect(
    "Candidatos",
    opciones,
    default=opciones[:3],
    max_selections=4,
    format_func=nombre_legible,
    key="comparar_candidatos",
)
if len(elegidos) < 2:
    st.caption("Seleccione al menos 2 candidatos.")
    st.stop()

resultados = {a: resultado(a) for a in elegidos}

with st.container(horizontal=True):
    for a in elegidos:
        r = resultados[a]
        total = len(r["coincidentes"]) + len(r["faltantes"])
        st.metric(nombre_legible(a), f"{r['puntaje']}%", f"{len(r['coincidentes'])} de {total} requisitos",
                  delta_color="off", delta_arrow="off", border=True)

col1, col2 = st.columns(2)
with col1.container(border=True, height="stretch"):
    st.markdown("**Perfil de habilidades por área**")
    st.caption("Cantidad de habilidades de cada CV en cada área del gazetteer.")
    perfiles = {nombre_legible(a): perfil_por_categoria(candidatos()[a]["cats"]) for a in elegidos}
    st.echarts_chart(graficos.radar(perfiles, o["categorias"]), height=420, key="radar_comparar")

with col2.container(border=True, height="stretch"):
    st.markdown("**Cumplimiento por área de la oferta**")
    st.caption("Porcentaje de los requisitos de cada área que cumple cada candidato.")
    filas = []
    for a in elegidos:
        cumplidos = {c[0] for c in resultados[a]["coincidentes"]}
        for req, cats in o["cats_oferta"].items():
            for cat in cats:
                filas.append({"Candidato": nombre_legible(a), "Área": o["categorias"].get(cat, cat),
                              "Cumple": req in cumplidos})
    if filas:
        datos = pd.DataFrame(filas).groupby(["Área", "Candidato"])["Cumple"].mean().mul(100).reset_index()
        st.bar_chart(datos, x="Área", y="Cumple", color="Candidato", stack=False, horizontal=True,
                     y_label="Requisitos cumplidos (%)", x_label="", height=380)

st.subheader("Cara a cara, requisito por requisito")
tabla = pd.DataFrame({"Requisito": list(o["requisitos"])})
for a in elegidos:
    sims = {d["Requisito"]: d for d in resultados[a]["detalle"]}
    tabla[nombre_legible(a)] = tabla["Requisito"].map(
        lambda r: ("✅ " if sims[r]["Cumple"] else "❌ ") + f"{sims[r]['Similitud']:.2f}"
    )
cumplen = pd.DataFrame({nombre_legible(a): tabla["Requisito"].map(
    lambda r, a=a: r in {c[0] for c in resultados[a]["coincidentes"]}) for a in elegidos})
tabla["Lo cumplen"] = cumplen.sum(axis=1).astype(str) + f" de {len(elegidos)}"
if o["obligatorios"]:
    tabla.insert(1, "Obligatorio", tabla["Requisito"].isin(o["obligatorios"]).map({True: "Sí", False: ""}))
st.dataframe(tabla, hide_index=True)

nombres = [nombre_legible(a) for a in elegidos]
ambos = cumplen.all(axis=1)
with st.container(horizontal=True):
    st.metric("Todos lo cumplen", int(ambos.sum()), border=True)
    st.metric("Ninguno lo cumple", int((~cumplen.any(axis=1)).sum()), border=True)
    for n in nombres:
        exclusivos = cumplen[n] & (cumplen.sum(axis=1) == 1)
        st.metric(f"Solo {n.split()[0]}", int(exclusivos.sum()), border=True,
                  help=", ".join(tabla.loc[exclusivos, "Requisito"]) or "Ninguno")
