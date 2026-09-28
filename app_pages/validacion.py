from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

import graficos
import metricas
from motor import analizar_cv, habilidades_oferta, matriz_similitud, umbral_efectivo
from ofertas import OFERTAS

o = st.session_state.ctx
RAIZ = Path(__file__).resolve().parents[2]
PLANTILLA_PROYECTO = RAIZ / "Evaluacion_Kappa_PLN.xlsx"
CARPETA_CVS = RAIZ / "cvs_80"

st.subheader(":material/fact_check: Validación del sistema")
st.caption(
    "Concordancia entre el sistema y un evaluador humano con la Kappa de Cohen (capítulo 4.3), "
    "y búsqueda del umbral de similitud que mejor reproduce el criterio humano."
)

origen = st.segmented_control(
    "Plantilla de evaluación",
    ["Plantilla del proyecto", "Subir otra plantilla"],
    default="Plantilla del proyecto" if PLANTILLA_PROYECTO.exists() else "Subir otra plantilla",
    key="origen_plantilla",
) or "Plantilla del proyecto"

if origen == "Plantilla del proyecto":
    if not PLANTILLA_PROYECTO.exists():
        st.warning(f"No se encontró {PLANTILLA_PROYECTO.name} en la carpeta del proyecto.", icon=":material/warning:")
        st.stop()
    fuente = PLANTILLA_PROYECTO
    st.caption(f"Usando {PLANTILLA_PROYECTO.name}.")
else:
    fuente = st.file_uploader(
        "Plantilla en Excel (columnas «Resultado del sistema» y «Criterio del evaluador humano»)",
        type=["xlsx"], key="plantilla_kappa",
    )
    if fuente is None:
        st.stop()

try:
    datos = metricas.leer_plantilla(fuente)
except Exception as e:
    st.error(f"No se pudo leer la plantilla: {e}", icon=":material/error:")
    st.stop()

sin_criterio = int(datos["humano"].isna().sum())
m = metricas.calcular(datos["sistema"], datos["humano"])

# ------------------------- Resultado registrado -------------------------
st.markdown("#### Resultado registrado en la plantilla")
if sin_criterio:
    st.caption(f"{m['n']} observaciones con criterio humano; {sin_criterio} sin completar quedan fuera del cálculo.")
with st.container(horizontal=True):
    st.metric("Kappa de Cohen", f"{m['kappa']:.3f}", m["interpretacion"], delta_color="off", border=True)
    st.metric("Concordancia observada", f"{m['po']:.1%}", border=True)
    st.metric("Concordancia por azar", f"{m['pe']:.1%}", border=True)
    st.metric("Precisión", f"{m['precision']:.1%}", border=True)
    st.metric("Exhaustividad", f"{m['recall']:.1%}", border=True)
    st.metric("F1", f"{m['f1']:.3f}", border=True)

col1, col2 = st.columns([1, 1])
with col1.container(border=True, height="stretch"):
    st.markdown("**Matriz de confusión**")
    st.altair_chart(graficos.matriz_confusion(m["vp"], m["fp"], m["fn"], m["vn"]))
with col2.container(border=True, height="stretch"):
    st.markdown("**Interpretación (Landis y Koch, 1977)**")
    escala = pd.DataFrame({
        "Kappa": ["< 0.00", "0.00 – 0.20", "0.21 – 0.40", "0.41 – 0.60", "0.61 – 0.80", "0.81 – 1.00"],
        "Acuerdo": ["Sin acuerdo", "Leve", "Aceptable", "Moderado", "Considerable", "Casi perfecto"],
    })
    escala["Este estudio"] = escala["Acuerdo"].map(lambda a: "◀" if a == m["interpretacion"] else "")
    st.dataframe(escala, hide_index=True)
    st.caption(
        f"Sistema y evaluador coinciden en {m['vp'] + m['vn']} de {m['n']} casos: {m['vp']} donde ambos "
        f"dicen que el requisito se cumple y {m['vn']} donde ambos dicen que no. Discrepan en "
        f"{m['fp']} falsos positivos y {m['fn']} falsos negativos."
    )

desacuerdos = datos[(datos["sistema"] != datos["humano"]) & datos["humano"].notna()]
if not desacuerdos.empty:
    with st.expander(f"Ver los {len(desacuerdos)} casos de desacuerdo"):
        st.dataframe(desacuerdos[[metricas.COL_CV, metricas.COL_OFERTA, metricas.COL_REQUISITO,
                                  metricas.COL_SISTEMA, metricas.COL_HUMANO]], hide_index=True)

# ------------------------- Curva Kappa vs umbral -------------------------
st.markdown("#### ¿Qué umbral concuerda mejor con el evaluador humano?")
st.caption(
    "Recalcula la decisión del sistema para cada fila de la plantilla con distintos umbrales, usando "
    "los PDF originales, y mide la concordancia con el criterio humano en cada caso."
)
carpeta = Path(st.text_input("Carpeta con los CVs de la evaluación", str(CARPETA_CVS), key="carpeta_validacion"))


@st.cache_data(show_spinner=False)
def mejores_similitudes(filas: tuple, carpeta: str):
    """Para cada (cv, oferta, requisito): similitud máxima con el CV. None si no se encuentra el CV/oferta."""
    pdfs = sorted(Path(carpeta).glob("*.pdf"))
    ofertas_por_titulo = {v["titulo"]: v["texto"] for v in OFERTAS.values()}
    resultado = []
    for cv, oferta, requisito in filas:
        prefijo = Path(str(cv)).stem
        pdf = next((p for p in pdfs if p.stem.startswith(prefijo)), None)
        texto_oferta = ofertas_por_titulo.get(oferta)
        if pdf is None or texto_oferta is None:
            resultado.append(None)
            continue
        _, skills_cv, _ = analizar_cv(pdf.read_bytes(), pdf.name)
        skills_oferta, _ = habilidades_oferta(texto_oferta)
        if requisito not in skills_oferta or not skills_cv:
            resultado.append(0.0 if skills_oferta else None)
            continue
        sim = matriz_similitud(skills_cv, skills_oferta)
        resultado.append(float(sim[skills_oferta.index(requisito)].max()))
    return resultado


if st.button("Calcular curva de concordancia", type="primary", icon=":material/show_chart:",
             disabled=not carpeta.is_dir(), key="btn_curva"):
    filas = tuple(zip(datos[metricas.COL_CV], datos[metricas.COL_OFERTA], datos[metricas.COL_REQUISITO]))
    with st.spinner("Analizando los CVs de la plantilla..."):
        st.session_state.sims_validacion = mejores_similitudes(filas, str(carpeta))

sims = st.session_state.get("sims_validacion")
if sims is not None and len(sims) == len(datos):
    base = datos.assign(sim=sims)
    base = base[base["sim"].notna() & base["humano"].notna()]
    reqs = base[metricas.COL_REQUISITO].astype(str)

    def decisiones(umbral):
        return [s >= umbral_efectivo(r, umbral, o["umbral_siglas"]) for s, r in zip(base["sim"], reqs)]

    umbrales = np.round(np.arange(0.40, 0.951, 0.025), 3)
    curva = []
    for u in umbrales:
        mu = metricas.calcular(decisiones(u), base["humano"])
        curva += [{"Umbral": u, "Métrica": "Kappa", "Valor": mu["kappa"]},
                  {"Umbral": u, "Métrica": "Precisión", "Valor": mu["precision"]},
                  {"Umbral": u, "Métrica": "Exhaustividad", "Valor": mu["recall"]}]
    curva = pd.DataFrame(curva)
    kappas = curva[curva["Métrica"] == "Kappa"]
    mejor = kappas.loc[kappas["Valor"].idxmax()]
    actual = metricas.calcular(decisiones(o["umbral"]), base["humano"])
    coincide_registro = np.mean(np.array(decisiones(0.60)) == base["sistema"].astype(bool).to_numpy())

    with st.container(horizontal=True):
        st.metric("Observaciones recalculadas", len(base), border=True)
        st.metric("Kappa con el umbral actual", f"{actual['kappa']:.3f}", f"umbral {o['umbral']:.2f}",
                  delta_color="off", border=True)
        st.metric("Mejor Kappa", f"{mejor['Valor']:.3f}", f"umbral {mejor['Umbral']:.3f}",
                  delta_color="off", border=True)
        st.metric("Reproduce la plantilla (umbral 0.60)", f"{coincide_registro:.1%}", border=True,
                  help="Porcentaje de filas donde la decisión recalculada coincide con «Resultado del sistema».")
    with st.container(border=True):
        st.altair_chart(graficos.curva_umbral(curva, o["umbral"], "Valor de la métrica", dominio=(0, 1)))
    st.caption(
        "Si la Kappa se mantiene alta en un rango amplio de umbrales, el resultado es robusto y no "
        "depende de haber elegido un valor exacto. Mueva el umbral en **Ajustes del modelo** "
        "(barra lateral) para ver su posición en la curva."
    )
