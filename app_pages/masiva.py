from pathlib import Path

import streamlit as st

import graficos
import reportes
from motor import FORMATOS_CV, analizar_cv
from ui_comun import (
    ctx, encabezado, lote, mostrar_detalle, nombre_legible, registrar_cv, resultado,
    tabla_detalle_lote, tabla_ranking,
)

CARPETA_DEFECTO = Path(__file__).resolve().parents[2] / "cvs_80"

o = ctx()
encabezado(
    "Evaluación masiva",
    "Evalúe muchos CVs a la vez y obtenga un ranking frente a la oferta seleccionada.",
    ":material/groups:",
)
st.markdown(f"**Oferta seleccionada:** {o['titulo']}")


def procesar(documentos):
    """documentos: lista de (nombre, bytes). Extrae y registra cada CV, con barra de progreso."""
    nombres, errores = [], []
    barra = st.progress(0.0, text="Preparando la evaluación...")
    for i, (nombre, contenido) in enumerate(documentos, start=1):
        barra.progress(i / len(documentos), text=f"Procesando {i} de {len(documentos)}: {nombre}")
        try:
            registrar_cv(nombre, *analizar_cv(contenido, nombre))
            nombres.append(nombre)
        except Exception as e:  # un PDF dañado no debe detener todo el lote
            errores.append(f"{nombre}: {e}")
    barra.empty()
    st.session_state.lote = nombres
    st.session_state.errores_lote = errores


fuente = st.segmented_control(
    "Origen de los CVs",
    ["Subir archivos", "Carpeta del equipo"],
    default="Subir archivos",
    key="fuente_lote",
) or "Subir archivos"

if fuente == "Subir archivos":
    archivos = st.file_uploader(
        "Currículums en PDF o Word (puede seleccionar varios a la vez)",
        type=FORMATOS_CV,
        accept_multiple_files=True,
        key="cv_masivo",
    )
    if st.button(
        f"Evaluar {len(archivos)} CV" + ("s" if len(archivos) != 1 else ""),
        type="primary",
        icon=":material/play_arrow:",
        disabled=not archivos or not o["requisitos"],
        key="btn_masivo",
    ):
        procesar([(f.name, f.getvalue()) for f in archivos])
else:
    carpeta = Path(st.text_input("Carpeta con los CVs", str(CARPETA_DEFECTO), key="carpeta_lote"))
    pdfs = sorted(p for ext in FORMATOS_CV for p in carpeta.glob(f"*.{ext}")) if carpeta.is_dir() else []
    st.caption(f"{len(pdfs)} CVs (PDF o Word) encontrados en la carpeta." if carpeta.is_dir()
               else "La carpeta no existe en este equipo.")
    if st.button(
        f"Evaluar {len(pdfs)} CVs de la carpeta",
        type="primary",
        icon=":material/play_arrow:",
        disabled=not pdfs or not o["requisitos"],
        key="btn_carpeta",
    ):
        procesar([(p.name, p.read_bytes()) for p in pdfs])

if not lote():
    st.caption(
        "Cargue varios CVs y pulse **Evaluar** para obtener un ranking. Los resultados se "
        "recalculan solos si cambia la oferta, los requisitos obligatorios o el umbral."
    )
    st.stop()

for err in st.session_state.get("errores_lote", []):
    st.error(f"No se pudo procesar {err}", icon=":material/error:")

ranking = tabla_ranking(lote())

st.subheader("Resumen del lote")
with st.container(horizontal=True):
    st.metric("CVs evaluados", len(ranking), border=True)
    st.metric("Compatibilidad promedio", f"{ranking['Compatibilidad'].mean():.1f}%", border=True)
    st.metric("Mejor puntaje", f"{ranking['Compatibilidad'].max():.1f}%", border=True)
    st.metric("Compatibilidad alta (≥ 70%)", int((ranking["Compatibilidad"] >= 70).sum()), border=True)
    if o["obligatorios"]:
        st.metric("Cumplen obligatorios", int((ranking["Obligatorios"] == "Cumple").sum()), border=True)

st.subheader("Ranking de candidatos")
with st.container(border=True):
    c1, c2, c3 = st.columns([1.2, 2, 1.2])
    niveles = c1.pills("Nivel", ["Alta", "Media", "Baja"], selection_mode="multi",
                       default=["Alta", "Media", "Baja"], key="filtro_nivel")
    deben_tener = c2.multiselect("Deben tener", list(o["requisitos"]), key="filtro_requisitos",
                                 placeholder="Cualquier requisito")
    minimo = c3.slider("Puntaje mínimo", 0, 100, 0, step=5, key="filtro_minimo")

filtrado = ranking[ranking["Nivel"].isin(niveles or []) & (ranking["Compatibilidad"] >= minimo)]
for req in deben_tener:
    filtrado = filtrado[filtrado["Archivo"].map(lambda a: req in [c[0] for c in resultado(a)["coincidentes"]])]
st.caption(f"Mostrando {len(filtrado)} de {len(ranking)} candidatos.")

st.dataframe(
    filtrado,
    hide_index=True,
    column_order=[c for c in filtrado.columns if c != "Archivo" and (o["obligatorios"] or c != "Obligatorios")],
    column_config={
        "Puesto": st.column_config.NumberColumn(width="small"),
        "Compatibilidad": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%",
                                                          width="medium"),
        "Nivel": st.column_config.TextColumn(width="small"),
        "Cumplidos": st.column_config.TextColumn(width="small"),
        "Coincidentes": st.column_config.TextColumn(width="large"),
        "Faltantes": st.column_config.TextColumn(width="large"),
    },
)

if not filtrado.empty:
    st.markdown(f"**Top {min(15, len(filtrado))} candidatos**")
    st.altair_chart(graficos.ranking_barras(filtrado))

with st.container(horizontal=True):
    st.download_button(
        "Excel con formato",
        data=reportes.excel_lote(o["titulo"], ranking, tabla_detalle_lote(lote()), o["ajustes"]),
        file_name="ranking_candidatos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        icon=":material/table_view:",
        type="primary",
    )
    st.download_button(
        "CSV",
        data=ranking.drop(columns=["Archivo"]).to_csv(sep=";", index=False).encode("utf-8-sig"),
        file_name="ranking_candidatos.csv",
        mime="text/csv",
        icon=":material/download:",
    )

st.subheader("Detalle por candidato")
elegido = st.selectbox(
    "Candidato",
    options=ranking["Archivo"].tolist(),
    format_func=lambda a: f"{int(ranking.loc[ranking['Archivo'] == a, 'Puesto'].iloc[0])}. {nombre_legible(a)}",
    key="detalle_lote",
)
res = resultado(elegido)
st.download_button(
    "Informe PDF del candidato",
    data=reportes.pdf_candidato(nombre_legible(elegido), elegido, o["titulo"], res, o["ajustes"], o["logo"]),
    file_name=f"informe_{nombre_legible(elegido).replace(' ', '_')}.pdf",
    mime="application/pdf",
    icon=":material/picture_as_pdf:",
    key="pdf_lote",
)
mostrar_detalle(res, "lote")
