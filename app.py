"""
Interfaz del sistema de apoyo a la selección de candidatos basado en PLN.

Para correrla:
    streamlit run app.py

Estructura:
    app.py          encabezado, barra lateral (oferta y ajustes) y navegación
    app_pages/      una página por sección (individual, masiva, tablero, ...)
    motor.py        extracción + embeddings con caché y regla de decisión
    ui_comun.py     utilidades compartidas entre páginas
    graficos.py     gráficos (Altair / ECharts)
    reportes.py     Excel y PDF descargables
    metricas.py     Kappa de Cohen y métricas de validación

El logo institucional se lee desde assets/logo_ucv.png y la paleta de
colores está en .streamlit/config.toml. La primera versión de esta
interfaz quedó en app_v1_respaldo.py.
"""
import base64
import json
import time
from pathlib import Path
from urllib.parse import quote

import streamlit as st

from motor import CATEGORIAS, UMBRAL_DEFECTO, UMBRAL_SIGLAS_DEFECTO, habilidades_oferta
from ofertas import OFERTAS

st.set_page_config(
    page_title="Selección de candidatos · PLN UCV",
    page_icon=":material/work:",
    layout="wide",
)

BASE = Path(__file__).parent
LOGO = BASE / "assets" / "logo_ucv.png"
# puestos agregados desde la interfaz; se suman a los de ofertas.py
RUTA_PERSONALIZADAS = BASE / "ofertas_personalizadas.json"

AZUL_UCV = "#1D2A57"
ROJO_UCV = "#E3051B"


# ------------------------- Puestos personalizados -------------------------
def cargar_personalizadas() -> dict:
    try:
        return json.loads(RUTA_PERSONALIZADAS.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def guardar_personalizadas(puestos: dict):
    RUTA_PERSONALIZADAS.write_text(json.dumps(puestos, ensure_ascii=False, indent=2), encoding="utf-8")


def agregar_puesto():
    """Callback del formulario: valida, guarda y deja seleccionado el puesto nuevo."""
    titulo = st.session_state.nuevo_titulo.strip()
    area = st.session_state.nuevo_area.strip()
    obligatorios = st.session_state.nuevo_obligatorios.strip()
    deseables = st.session_state.nuevo_deseables.strip()
    if not titulo or not (obligatorios or deseables):
        st.toast("Complete el nombre del puesto y al menos un requerimiento.", icon=":material/error:")
        return
    existentes = {o["titulo"].lower() for o in {**OFERTAS, **cargar_personalizadas()}.values()}
    if titulo.lower() in existentes:
        st.toast(f"Ya existe un puesto llamado «{titulo}».", icon=":material/error:")
        return

    texto = f"{titulo}\n" + (f"Área: {area}\n" if area else "")
    if obligatorios:
        texto += f"Requisitos obligatorios:\n{obligatorios}\n"
    if deseables:
        texto += f"Requisitos deseables:\n{deseables}\n"
    skills_oblig, _ = habilidades_oferta(obligatorios) if obligatorios else ((), {})

    puestos = cargar_personalizadas()
    clave = f"personalizada_{int(time.time() * 1000)}"
    puestos[clave] = {"titulo": titulo, "area": area, "texto": texto, "obligatorios": list(skills_oblig)}
    guardar_personalizadas(puestos)

    st.session_state.puesto = clave
    for k in ("nuevo_titulo", "nuevo_area", "nuevo_obligatorios", "nuevo_deseables"):
        st.session_state[k] = ""
    st.toast(f"Puesto «{titulo}» agregado.", icon=":material/check_circle:")


def eliminar_puesto(clave: str):
    puestos = cargar_personalizadas()
    titulo = puestos.pop(clave, {}).get("titulo", "")
    guardar_personalizadas(puestos)
    st.session_state.pop("puesto", None)
    st.toast(f"Puesto «{titulo}» eliminado.", icon=":material/delete:")


def restablecer_ajustes():
    st.session_state.umbral = UMBRAL_DEFECTO
    st.session_state.umbral_siglas = UMBRAL_SIGLAS_DEFECTO


# ------------------------- Estilo institucional -------------------------
def fondo_red_neuronal() -> str:
    """SVG de una red neuronal estilizada, como data URI para el fondo de la barra lateral."""
    ancho, alto = 320, 440
    capas = [4, 6, 6, 5, 2]
    xs = [30 + i * (ancho - 60) / (len(capas) - 1) for i in range(len(capas))]
    nodos = [
        [(x, 40 + (j + 0.5) * (alto - 80) / n) for j in range(n)]
        for x, n in zip(xs, capas)
    ]
    lineas = "".join(
        f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}"/>'
        for a, b in zip(nodos, nodos[1:])
        for x1, y1 in a
        for x2, y2 in b
    )
    circulos = "".join(
        f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{9 if i in (0, len(nodos) - 1) else 7}" '
        f'fill="{ROJO_UCV if (i + j) % 5 == 0 else AZUL_UCV}"/>'
        for i, capa in enumerate(nodos)
        for j, (x, y) in enumerate(capa)
    )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ancho} {alto}">'
        f'<g stroke="{AZUL_UCV}" stroke-width="1" opacity="0.10">{lineas}</g>'
        f'<g opacity="0.20">{circulos}</g></svg>'
    )
    return "data:image/svg+xml;utf8," + quote(svg)


logo_html = ""
if LOGO.exists():
    st.logo(str(LOGO), size="large")
    logo_b64 = base64.b64encode(LOGO.read_bytes()).decode()
    logo_html = f'<img class="logo" src="data:image/png;base64,{logo_b64}" alt="Logo UCV">'

st.html(
    f"""
    <style>
      .ucv-banner {{
        background: linear-gradient(115deg, {AZUL_UCV} 0%, #2C3F7C 100%);
        border-bottom: 5px solid {ROJO_UCV};
        border-radius: 14px;
        padding: 18px 28px 16px;
        color: #FFFFFF;
        display: flex;
        align-items: center;
        gap: 22px;
      }}
      .ucv-banner .logo {{
        width: 72px;
        height: 72px;
        border-radius: 12px;
        flex-shrink: 0;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
      }}
      .ucv-banner .etiqueta {{
        display: inline-block;
        background: rgba(255, 255, 255, 0.14);
        border-radius: 999px;
        padding: 3px 12px;
        font-size: 0.72rem;
        letter-spacing: 0.06em;
        text-transform: uppercase;
      }}
      .ucv-banner .titulo {{
        margin: 8px 0 3px;
        font-size: 1.65rem;
        font-weight: 700;
        line-height: 1.2;
      }}
      .ucv-banner .subtitulo {{ opacity: 0.85; font-size: 0.92rem; }}
      [data-testid="stSidebar"] {{
        background-image:
          url("{fondo_red_neuronal()}"),
          radial-gradient(rgba(29, 42, 87, 0.07) 1px, transparent 1px),
          linear-gradient(180deg, #FFFFFF 0%, #EEF2F9 100%);
        background-size: 100% auto, 18px 18px, 100% 100%;
        background-position: bottom center, 0 0, 0 0;
        background-repeat: no-repeat, repeat, no-repeat;
      }}
      [data-testid="stSidebarContent"] {{ background: transparent; }}
      [data-testid="stSidebar"] [data-testid="stExpander"] details {{ background: #FFFFFF; }}
      mark.req {{ background: #CFE9DA; color: #0F5132; padding: 1px 4px; border-radius: 4px; }}
      mark.cv {{ background: #DCE4F5; color: {AZUL_UCV}; padding: 1px 4px; border-radius: 4px; }}
    </style>
    <div class="ucv-banner">
      {logo_html}
      <div>
        <span class="etiqueta">Proyecto integrador · Procesamiento de Lenguaje Natural</span>
        <div class="titulo">Sistema de apoyo a la selección de candidatos</div>
        <div class="subtitulo">Maestría en Inteligencia Artificial · Universidad César Vallejo · Grupo 10</div>
      </div>
    </div>
    """
)

# ------------------------- Barra lateral: oferta y ajustes -------------------------
personalizadas = cargar_personalizadas()
todas_ofertas = {**OFERTAS, **personalizadas}
if st.session_state.get("puesto") not in todas_ofertas:
    st.session_state.pop("puesto", None)
st.session_state.setdefault("umbral", UMBRAL_DEFECTO)
st.session_state.setdefault("umbral_siglas", UMBRAL_SIGLAS_DEFECTO)

with st.sidebar:
    st.subheader(":material/work: Oferta laboral")
    clave = st.selectbox(
        "Puesto",
        options=list(todas_ofertas.keys()),
        format_func=lambda k: todas_ofertas[k]["titulo"]
        + ("  · agregado" if k in personalizadas else ""),
        key="puesto",
    )
    oferta = todas_ofertas[clave]
    requisitos, cats_oferta = habilidades_oferta(oferta["texto"])

    with st.expander("Ver texto de la oferta"):
        st.text(oferta["texto"])

    st.markdown(f"**Requisitos detectados** ({len(requisitos)})")
    if requisitos:
        st.markdown(" ".join(f":blue-badge[{r}]" for r in requisitos))
    else:
        st.warning(
            "No se reconoció ninguna habilidad en esta oferta. Use términos más "
            "específicos (herramientas, técnicas, certificaciones).",
            icon=":material/warning:",
        )
    obligatorios = st.multiselect(
        "Requisitos obligatorios",
        options=list(requisitos),
        default=[r for r in oferta.get("obligatorios", []) if r in requisitos],
        key=f"oblig_{clave}",
        help="Pesan el doble en el puntaje, y se señala a los candidatos que no los cumplen.",
        placeholder="Ninguno (todos pesan igual)",
    )

    if clave in personalizadas:
        st.button(
            "Eliminar este puesto",
            icon=":material/delete:",
            on_click=eliminar_puesto,
            args=(clave,),
            key="btn_eliminar_puesto",
        )

    with st.expander("Agregar nuevo puesto", icon=":material/add_circle:"):
        with st.form("form_nuevo_puesto", border=False):
            st.text_input("Nombre del puesto", key="nuevo_titulo", placeholder="Ej.: Analista de Datos")
            st.text_input("Área o sector (opcional)", key="nuevo_area", placeholder="Ej.: Tecnología")
            st.text_area(
                "Requisitos obligatorios",
                key="nuevo_obligatorios",
                height=120,
                placeholder="Uno por línea, por ejemplo:\n- Python\n- SQL",
            )
            st.text_area(
                "Requisitos deseables",
                key="nuevo_deseables",
                height=120,
                placeholder="Uno por línea, por ejemplo:\n- Power BI\n- Machine learning",
            )
            st.form_submit_button(
                "Guardar puesto",
                type="primary",
                icon=":material/save:",
                on_click=agregar_puesto,
                width="stretch",
            )
        st.caption(
            "El sistema reconoce las habilidades incluidas en su gazetteer; al guardar, "
            "revise en «Requisitos detectados» cuáles identificó."
        )

    with st.expander("Ajustes del modelo", icon=":material/tune:"):
        st.slider(
            "Umbral de similitud",
            min_value=0.40, max_value=0.90, step=0.01, key="umbral",
            help="Similitud coseno mínima para aceptar que una habilidad del CV cubre un requisito.",
        )
        st.slider(
            "Umbral para siglas",
            min_value=0.70, max_value=1.00, step=0.01, key="umbral_siglas",
            help="Umbral más estricto para términos de una sola palabra corta (ITIL, SIEM, UML...).",
        )
        st.button("Restablecer valores del estudio", icon=":material/restart_alt:",
                  on_click=restablecer_ajustes, width="stretch")

    st.caption("La oferta y los ajustes elegidos aquí se aplican en todas las secciones.")

st.session_state.ctx = {
    "clave": clave,
    "titulo": oferta["titulo"],
    "texto": oferta["texto"],
    "requisitos": requisitos,
    "cats_oferta": cats_oferta,
    "obligatorios": tuple(obligatorios),
    "umbral": st.session_state.umbral,
    "umbral_siglas": st.session_state.umbral_siglas,
    "ajustes": f"umbral {st.session_state.umbral:.2f}, siglas {st.session_state.umbral_siglas:.2f}"
               + (f", {len(obligatorios)} obligatorios" if obligatorios else ""),
    "logo": LOGO if LOGO.exists() else None,
    "categorias": CATEGORIAS,
}

# ------------------------- Navegación -------------------------
paginas = st.navigation(
    [
        st.Page("app_pages/individual.py", title="Individual", icon=":material/person_search:", default=True),
        st.Page("app_pages/masiva.py", title="Masiva", icon=":material/groups:"),
        st.Page("app_pages/tablero.py", title="Tablero", icon=":material/dashboard:"),
        st.Page("app_pages/comparar.py", title="Comparar", icon=":material/compare_arrows:"),
        st.Page("app_pages/laboratorio.py", title="Laboratorio PLN", icon=":material/hub:"),
        st.Page("app_pages/validacion.py", title="Validación", icon=":material/fact_check:"),
        st.Page("app_pages/acerca.py", title="Acerca de", icon=":material/info:"),
    ],
    position="top",
)
paginas.run()
