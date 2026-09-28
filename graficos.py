"""
Gráficos de la interfaz (Altair y opciones de ECharts), con la paleta institucional.
"""
import altair as alt
import numpy as np
import pandas as pd

AZUL, ROJO, VERDE, NARANJA, GRIS = "#1D2A57", "#E3051B", "#1A7F4B", "#B86E00", "#8A94A6"
NIVELES = alt.Scale(domain=["Alta", "Media", "Baja"], range=[VERDE, NARANJA, ROJO])


def velocimetro(puntaje: float) -> dict:
    return {
        "series": [{
            "type": "gauge",
            "startAngle": 200,
            "endAngle": -20,
            "min": 0,
            "max": 100,
            "radius": "100%",
            "center": ["50%", "62%"],
            "progress": {"show": True, "width": 16, "itemStyle": {"color": AZUL}},
            "axisLine": {"lineStyle": {"width": 16, "color": [[0.4, "#F8D4D8"], [0.7, "#F6E3C4"], [1, "#CFE9DA"]]}},
            "pointer": {"show": False},
            "axisTick": {"show": False},
            "splitLine": {"show": False},
            "axisLabel": {"show": False},
            "anchor": {"show": False},
            "title": {"show": True, "offsetCenter": [0, "32%"], "fontSize": 13, "color": GRIS},
            "detail": {
                "valueAnimation": True,
                "offsetCenter": [0, "-2%"],
                "fontSize": 34,
                "fontWeight": "bold",
                "formatter": "{value}%",
                "color": AZUL,
            },
            "data": [{"value": puntaje, "name": "Compatibilidad"}],
        }]
    }


def ranking_barras(df: pd.DataFrame, top: int = 15) -> alt.Chart:
    datos = df.head(top)
    return (
        alt.Chart(datos)
        .mark_bar(cornerRadiusEnd=4)
        .encode(
            x=alt.X("Compatibilidad:Q", title="Compatibilidad (%)", scale=alt.Scale(domain=[0, 100])),
            y=alt.Y("Candidato:N", sort="-x", title=None),
            color=alt.Color("Nivel:N", scale=NIVELES, legend=alt.Legend(title="Nivel", orient="bottom")),
            tooltip=["Candidato", alt.Tooltip("Compatibilidad:Q", format=".1f"), "Cumplidos"],
        )
        .properties(height=max(160, 28 * len(datos)))
    )


def distribucion(df: pd.DataFrame) -> alt.Chart:
    return (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("Compatibilidad:Q", bin=alt.Bin(extent=[0, 100], step=10), title="Compatibilidad (%)"),
            y=alt.Y("count():Q", title="Candidatos"),
            color=alt.Color("Nivel:N", scale=NIVELES, legend=alt.Legend(title="Nivel", orient="bottom")),
            tooltip=[alt.Tooltip("count():Q", title="Candidatos"), "Nivel"],
        )
        .properties(height=260)
    )


def dona_niveles(df: pd.DataFrame) -> alt.Chart:
    conteo = df["Nivel"].value_counts().reindex(["Alta", "Media", "Baja"], fill_value=0).reset_index()
    conteo.columns = ["Nivel", "Candidatos"]
    base = alt.Chart(conteo).encode(
        theta=alt.Theta("Candidatos:Q", stack=True),
        color=alt.Color("Nivel:N", scale=NIVELES, legend=alt.Legend(title="Nivel", orient="bottom")),
        tooltip=["Nivel", "Candidatos"],
    )
    return (base.mark_arc(innerRadius=60, outerRadius=100) + base.mark_text(radius=120, fontSize=13).encode(
        text=alt.Text("Candidatos:Q"))).properties(height=260)


def mapa_calor(detalle: pd.DataFrame) -> alt.Chart:
    """Candidatos (filas) x requisitos (columnas), coloreado por similitud."""
    orden_cand = (
        detalle.drop_duplicates("Candidato").sort_values("Compatibilidad", ascending=False)["Candidato"].tolist()
    )
    orden_req = (
        detalle.groupby("Requisito")["Cumple"].mean().sort_values(ascending=False).index.tolist()
    )
    base = alt.Chart(detalle).encode(
        x=alt.X("Requisito:N", sort=orden_req, title=None, axis=alt.Axis(labelAngle=-40, labelLimit=240)),
        y=alt.Y("Candidato:N", sort=orden_cand, title=None, axis=alt.Axis(labelLimit=220)),
    )
    celdas = base.mark_rect(stroke="#FFFFFF", strokeWidth=1.5).encode(
        color=alt.Color(
            "Similitud:Q",
            scale=alt.Scale(domain=[0, 1], range=["#F4F6FA", "#AFC0E0", AZUL]),
            legend=alt.Legend(title="Similitud", orient="bottom", gradientLength=220),
        ),
        tooltip=[
            "Candidato", "Requisito", "Habilidad más cercana del CV",
            alt.Tooltip("Similitud:Q", format=".3f"), "Tipo de coincidencia",
        ],
    )
    marcas = base.transform_filter(alt.datum.Cumple).mark_text(
        text="✓", fontSize=13, fontWeight="bold", color="#FFFFFF")
    return (celdas + marcas).properties(height=max(200, 26 * len(orden_cand)))


def brechas(detalle: pd.DataFrame) -> alt.Chart:
    """Porcentaje de candidatos a los que les falta cada requisito."""
    datos = (
        detalle.groupby("Requisito")
        .agg(faltan=("Cumple", lambda s: int((~s).sum())), total=("Cumple", "size"))
        .reset_index()
    )
    datos["Porcentaje"] = 100 * datos["faltan"] / datos["total"]
    datos["Etiqueta"] = datos.apply(lambda r: f"{r.faltan} de {r.total}", axis=1)
    base = alt.Chart(datos).encode(
        y=alt.Y("Requisito:N", sort="-x", title=None, axis=alt.Axis(labelLimit=200)),
        x=alt.X("Porcentaje:Q", title="Candidatos que no lo cumplen (%)", scale=alt.Scale(domain=[0, 115])),
    )
    barras = base.mark_bar(cornerRadiusEnd=4).encode(
        color=alt.Color("Porcentaje:Q", scale=alt.Scale(domain=[0, 100], range=["#F6C9CE", ROJO]), legend=None),
        tooltip=["Requisito", "Etiqueta", alt.Tooltip("Porcentaje:Q", format=".0f")],
    )
    texto = base.mark_text(align="left", dx=4, color=GRIS, fontSize=11).encode(text="Etiqueta:N")
    return (barras + texto).properties(height=max(180, 24 * len(datos)))


def excedentes_comunes(excedentes: list, top: int = 15) -> alt.Chart:
    datos = pd.Series(excedentes).value_counts().head(top).reset_index()
    datos.columns = ["Habilidad", "Candidatos"]
    return (
        alt.Chart(datos)
        .mark_bar(cornerRadiusEnd=4, color=AZUL)
        .encode(
            y=alt.Y("Habilidad:N", sort="-x", title=None, axis=alt.Axis(labelLimit=200)),
            x=alt.X("Candidatos:Q", title="Candidatos que la tienen", axis=alt.Axis(tickMinStep=1)),
            tooltip=["Habilidad", "Candidatos"],
        )
        .properties(height=max(180, 24 * len(datos)))
    )


def radar(perfiles: dict, ejes: dict) -> dict:
    """perfiles: {nombre: {categoria: valor}}; ejes: {categoria: etiqueta}."""
    maximo = max([1] + [v for p in perfiles.values() for v in p.values()])
    colores = [AZUL, ROJO, VERDE, NARANJA]
    return {
        "color": colores,
        "legend": {"bottom": 0, "data": list(perfiles)},
        "tooltip": {"trigger": "item"},
        "radar": {
            "indicator": [{"name": etiqueta, "max": maximo} for etiqueta in ejes.values()],
            "radius": "65%",
            "center": ["50%", "48%"],
            "splitArea": {"areaStyle": {"color": ["#FFFFFF", "#F4F6FA"]}},
            "axisName": {"color": AZUL, "fontSize": 12},
        },
        "series": [{
            "type": "radar",
            "areaStyle": {"opacity": 0.12},
            "lineStyle": {"width": 2},
            "data": [
                {"name": nombre, "value": [perfil.get(c, 0) for c in ejes]}
                for nombre, perfil in perfiles.items()
            ],
        }],
    }


def proyeccion_2d(vectores: np.ndarray) -> np.ndarray:
    """PCA a 2 dimensiones (centrado + SVD)."""
    centrados = vectores - vectores.mean(axis=0)
    _, _, vt = np.linalg.svd(centrados, full_matrices=False)
    return centrados @ vt[:2].T


def mapa_semantico(puntos: pd.DataFrame, enlaces: pd.DataFrame) -> alt.Chart:
    """puntos: Habilidad, Origen, x, y. enlaces: x, y, x2, y2, Similitud."""
    colores = alt.Scale(
        domain=["Requisito de la oferta", "Habilidad del CV", "En ambos"], range=[ROJO, AZUL, VERDE]
    )
    ejes = dict(axis=alt.Axis(labels=False, ticks=False, grid=True, title=None, domain=False))
    lineas = alt.Chart(enlaces).mark_rule(strokeDash=[4, 3], color=VERDE, opacity=0.8).encode(
        x=alt.X("x:Q", **ejes), y=alt.Y("y:Q", **ejes), x2="x2:Q", y2="y2:Q",
        tooltip=["Requisito", "Habilidad", alt.Tooltip("Similitud:Q", format=".3f")],
    )
    puntos_ch = alt.Chart(puntos).mark_circle(size=140, opacity=0.9, stroke="#FFFFFF", strokeWidth=1).encode(
        x=alt.X("x:Q", **ejes), y=alt.Y("y:Q", **ejes),
        color=alt.Color("Origen:N", scale=colores, legend=alt.Legend(title=None, orient="bottom")),
        tooltip=["Habilidad", "Origen"],
    )
    # los requisitos se rotulan arriba a la derecha y las habilidades del CV abajo a la izquierda,
    # para que un requisito y la habilidad que lo cubre no se tapen entre sí
    etiquetas_req = alt.Chart(puntos).transform_filter(alt.datum.Origen != "Habilidad del CV").mark_text(
        align="left", dx=8, dy=-7, fontSize=11, color="#1B2433").encode(x="x:Q", y="y:Q", text="Habilidad:N")
    etiquetas_cv = alt.Chart(puntos).transform_filter(alt.datum.Origen == "Habilidad del CV").mark_text(
        align="right", dx=-8, dy=12, fontSize=11, color=AZUL, fontWeight="bold").encode(
        x="x:Q", y="y:Q", text="Habilidad:N")
    return (lineas + puntos_ch + etiquetas_req + etiquetas_cv).properties(height=520)


def curva_umbral(datos: pd.DataFrame, umbral_actual: float, y_titulo: str, dominio=(0, 100)) -> alt.Chart:
    """datos: Umbral, Métrica, Valor (formato largo)."""
    colores = {"Kappa": AZUL, "Compatibilidad (%)": AZUL, "Precisión": VERDE, "Exhaustividad": NARANJA}
    metricas = [m for m in colores if m in set(datos["Métrica"])]
    lineas = alt.Chart(datos).mark_line(point=True, strokeWidth=2).encode(
        x=alt.X("Umbral:Q", title="Umbral de similitud", scale=alt.Scale(zero=False)),
        y=alt.Y("Valor:Q", title=y_titulo, scale=alt.Scale(domain=list(dominio))),
        color=alt.Color("Métrica:N", legend=alt.Legend(title=None, orient="bottom"),
                        scale=alt.Scale(domain=metricas, range=[colores[m] for m in metricas])),
        tooltip=[alt.Tooltip("Umbral:Q", format=".3f"), "Métrica", alt.Tooltip("Valor:Q", format=".3f")],
    )
    regla = alt.Chart(pd.DataFrame({"Umbral": [umbral_actual]})).mark_rule(
        color=ROJO, strokeDash=[6, 4], strokeWidth=2).encode(x="Umbral:Q")
    return (lineas + regla).properties(height=320)


def matriz_confusion(vp: int, fp: int, fn: int, vn: int) -> alt.Chart:
    datos = pd.DataFrame([
        {"Sistema": "Coincide", "Evaluador humano": "Sí", "Casos": vp, "Tipo": "Acuerdo"},
        {"Sistema": "Coincide", "Evaluador humano": "No", "Casos": fp, "Tipo": "Desacuerdo"},
        {"Sistema": "No coincide", "Evaluador humano": "Sí", "Casos": fn, "Tipo": "Desacuerdo"},
        {"Sistema": "No coincide", "Evaluador humano": "No", "Casos": vn, "Tipo": "Acuerdo"},
    ])
    base = alt.Chart(datos).encode(
        x=alt.X("Evaluador humano:N", sort=["Sí", "No"], axis=alt.Axis(orient="top", labelAngle=0)),
        y=alt.Y("Sistema:N", sort=["Coincide", "No coincide"]),
    )
    celdas = base.mark_rect(cornerRadius=6, stroke="#FFFFFF", strokeWidth=3).encode(
        color=alt.Color("Tipo:N", scale=alt.Scale(domain=["Acuerdo", "Desacuerdo"], range=[AZUL, "#F6C9CE"]),
                        legend=None),
        tooltip=["Sistema", "Evaluador humano", "Casos"],
    )
    texto = base.mark_text(fontSize=26, fontWeight="bold").encode(
        text="Casos:Q",
        color=alt.condition(alt.datum.Tipo == "Acuerdo", alt.value("#FFFFFF"), alt.value(ROJO)),
    )
    return (celdas + texto).properties(height=240)
