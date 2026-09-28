"""
Utilidades compartidas por las páginas de la interfaz.

Estado de sesión que usan las páginas:
  ctx          -> oferta seleccionada y ajustes del modelo (lo arma app.py en cada ejecución)
  candidatos   -> {archivo: {"texto", "skills", "cats"}} de todos los CVs analizados
  lote         -> lista de archivos de la última evaluación masiva
  individual   -> archivo de la última evaluación individual
"""
import re
from pathlib import Path

import pandas as pd
import streamlit as st

import graficos
from motor import evaluar

VERDE, NARANJA = "#1A7F4B", "#B86E00"


def ctx() -> dict:
    return st.session_state.ctx


def candidatos() -> dict:
    return st.session_state.setdefault("candidatos", {})


def lote() -> list:
    return st.session_state.get("lote", [])


def pool() -> list:
    """Candidatos disponibles para comparar/analizar: el lote y el CV individual."""
    nombres = list(lote())
    ind = st.session_state.get("individual")
    if ind and ind not in nombres:
        nombres.append(ind)
    return [n for n in nombres if n in candidatos()]


def registrar_cv(nombre: str, texto: str, skills: tuple, cats: dict):
    candidatos()[nombre] = {"texto": texto, "skills": skills, "cats": cats}


def resultado(archivo: str) -> dict:
    """Evalúa un CV contra la oferta y los ajustes actuales (reacciona al umbral)."""
    c, o = candidatos()[archivo], ctx()
    return evaluar(c["skills"], o["requisitos"], o["umbral"], o["umbral_siglas"], o["obligatorios"])


def nombre_legible(archivo: str) -> str:
    """'CV_17_Roberto_Roldán_Contador___Auditor.pdf' -> 'Roberto Roldán Contador Auditor'."""
    nombre = re.sub(r"^(curriculos_pdf_)?CV_\d+_", "", Path(archivo).stem)
    return re.sub(r"_+", " ", nombre).strip() or Path(archivo).stem


def nivel(puntaje: float):
    if puntaje >= 70:
        return "Alta", "green"
    if puntaje >= 40:
        return "Media", "orange"
    return "Baja", "red"


def tabla_ranking(archivos: list) -> pd.DataFrame:
    filas = []
    for a in archivos:
        r = resultado(a)
        total = len(r["coincidentes"]) + len(r["faltantes"])
        filas.append({
            "Candidato": nombre_legible(a),
            "Compatibilidad": r["puntaje"],
            "Nivel": nivel(r["puntaje"])[0],
            "Cumplidos": f"{len(r['coincidentes'])} de {total}",
            "Obligatorios": "Cumple" if not r["faltan_obligatorios"] else f"Faltan {len(r['faltan_obligatorios'])}",
            "Coincidentes": ", ".join(c[0] for c in r["coincidentes"]),
            "Faltantes": ", ".join(r["faltantes"]),
            "Archivo": a,
        })
    df = pd.DataFrame(filas)
    if df.empty:
        return df
    df = df.sort_values("Compatibilidad", ascending=False, ignore_index=True)
    df.insert(0, "Puesto", range(1, len(df) + 1))
    return df


def tabla_detalle_lote(archivos: list) -> pd.DataFrame:
    """Formato largo: una fila por candidato y requisito (para mapa de calor y Excel)."""
    filas = []
    for a in archivos:
        r = resultado(a)
        for d in r["detalle"]:
            filas.append({"Candidato": nombre_legible(a), "Archivo": a, "Compatibilidad": r["puntaje"], **d})
    return pd.DataFrame(filas)


def requiere_lote():
    if not lote():
        st.info(
            "Todavía no hay una evaluación masiva. Cargue varios CVs en **Evaluación masiva** "
            "para ver esta sección.",
            icon=":material/info:",
        )
        st.page_link("app_pages/masiva.py", label="Ir a evaluación masiva", icon=":material/groups:")
        st.stop()


def requiere_pool():
    if not pool():
        st.info(
            "Primero evalúe al menos un CV (individual o masivo) para usar esta sección.",
            icon=":material/info:",
        )
        with st.container(horizontal=True):
            st.page_link("app_pages/individual.py", label="Evaluación individual", icon=":material/person_search:")
            st.page_link("app_pages/masiva.py", label="Evaluación masiva", icon=":material/groups:")
        st.stop()


def selector_candidato(label: str, key: str) -> str:
    opciones = pool()
    ranking = {a: i for i, a in enumerate(tabla_ranking(opciones)["Archivo"])} if opciones else {}
    opciones = sorted(opciones, key=lambda a: ranking.get(a, 0))
    return st.selectbox(label, opciones, format_func=nombre_legible, key=key)


def encabezado(titulo: str, descripcion: str, icono: str):
    st.subheader(f"{icono} {titulo}")
    st.caption(descripcion)


def mostrar_detalle(res: dict, clave: str):
    """Velocímetro + métricas + las tres listas explicativas de un resultado."""
    n_coinc = len(res["coincidentes"])
    total = n_coinc + len(res["faltantes"])
    etiqueta, color = nivel(res["puntaje"])

    col_gauge, col_metricas = st.columns([1, 2], vertical_alignment="center")
    with col_gauge:
        st.echarts_chart(graficos.velocimetro(res["puntaje"]), height=220, key=f"gauge_{clave}")
    with col_metricas:
        with st.container(horizontal=True):
            st.metric("Requisitos cumplidos", f"{n_coinc} de {total}", border=True)
            st.metric("Habilidades adicionales", len(res["excedentes"]), border=True)
            if ctx()["obligatorios"]:
                faltan = len(res["faltan_obligatorios"])
                st.metric("Obligatorios", "Cumple" if not faltan else f"Faltan {faltan}", border=True)
        st.badge(f"Compatibilidad {etiqueta.lower()}", color=color, icon=":material/insights:")
        if res["faltan_obligatorios"]:
            st.warning(
                "No cumple requisitos obligatorios: " + ", ".join(res["faltan_obligatorios"]),
                icon=":material/report:",
            )

    col1, col2, col3 = st.columns(3)
    with col1.container(border=True, height="stretch"):
        st.markdown(":green[:material/check_circle:] **Coincidentes**")
        st.caption("Requisitos de la oferta presentes en el CV.")
        for hab_oferta, hab_cv, sim in res["coincidentes"] or []:
            marca = " :red-badge[obligatorio]" if hab_oferta in ctx()["obligatorios"] else ""
            if hab_oferta == hab_cv:
                st.markdown(f"- {hab_oferta}{marca}")
            else:
                st.markdown(f"- {hab_oferta}{marca} *(vía «{hab_cv}», similitud {sim})*")
        if not res["coincidentes"]:
            st.write("Ninguna.")
    with col2.container(border=True, height="stretch"):
        st.markdown(":red[:material/cancel:] **Faltantes**")
        st.caption("La oferta las pide; no se encontraron en el CV.")
        for hab in res["faltantes"]:
            marca = " :red-badge[obligatorio]" if hab in ctx()["obligatorios"] else ""
            st.markdown(f"- {hab}{marca}")
        if not res["faltantes"]:
            st.write("Ninguna: el CV cubre todo lo solicitado.")
    with col3.container(border=True, height="stretch"):
        st.markdown(":blue[:material/add_circle:] **Excedentes**")
        st.caption("El CV las tiene; la oferta no las pide.")
        for hab in res["excedentes"]:
            st.markdown(f"- {hab}")
        if not res["excedentes"]:
            st.write("Ninguna.")
