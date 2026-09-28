"""
Informes descargables: Excel con formato (lote) y PDF por candidato.
Requiere xlsxwriter y reportlab (ver requirements.txt).
"""
import io
from datetime import datetime
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

AZUL, ROJO, VERDE, NARANJA = "#1D2A57", "#E3051B", "#1A7F4B", "#B86E00"


# ------------------------------- Excel -------------------------------
def excel_lote(oferta: str, ranking: pd.DataFrame, detalle: pd.DataFrame, ajustes: str) -> bytes:
    """Libro con hojas Ranking, Matriz, Brechas y Detalle, con formato condicional."""
    salida = io.BytesIO()
    matriz = detalle.pivot_table(index="Candidato", columns="Requisito", values="Similitud", aggfunc="first")
    matriz = matriz.reindex(ranking["Candidato"])
    brechas = (
        detalle.groupby("Requisito")
        .agg(**{"Candidatos que no lo cumplen": ("Cumple", lambda s: int((~s).sum())),
                "Total de candidatos": ("Cumple", "size")})
        .reset_index()
    )
    brechas["% sin el requisito"] = (
        100 * brechas["Candidatos que no lo cumplen"] / brechas["Total de candidatos"]
    ).round(1)
    brechas = brechas.sort_values("% sin el requisito", ascending=False)
    detalle_xl = detalle.drop(columns=["Archivo", "Compatibilidad"]).assign(
        Cumple=lambda d: d["Cumple"].map({True: "Sí", False: "No"}),
        Obligatorio=lambda d: d["Obligatorio"].map({True: "Sí", False: "No"}),
    )

    with pd.ExcelWriter(salida, engine="xlsxwriter") as writer:
        libro = writer.book
        titulo = libro.add_format({"bold": True, "font_size": 14, "font_color": AZUL})
        sub = libro.add_format({"italic": True, "font_color": "#57606A"})
        cabecera = libro.add_format({"bold": True, "font_color": "#FFFFFF", "bg_color": AZUL,
                                     "border": 1, "text_wrap": True, "valign": "vcenter"})

        def hoja(df, nombre, anchos, index=False):
            df.to_excel(writer, sheet_name=nombre, startrow=3, index=index)
            ws = writer.sheets[nombre]
            ws.write(0, 0, f"{nombre} · {oferta}", titulo)
            ws.write(1, 0, f"Generado el {datetime.now():%d/%m/%Y %H:%M} · {ajustes}", sub)
            columnas = ([df.index.name or ""] if index else []) + list(df.columns)
            for c, nombre_col in enumerate(columnas):
                ws.write(3, c, nombre_col, cabecera)
                ws.set_column(c, c, anchos(c, nombre_col))
            ws.freeze_panes(4, 1 if index else 0)
            return ws

        ws = hoja(ranking.drop(columns=["Archivo"]), "Ranking",
                  lambda c, n: 50 if n in ("Coincidentes", "Faltantes") else (34 if n == "Candidato" else 14))
        col = list(ranking.drop(columns=["Archivo"]).columns).index("Compatibilidad")
        ws.conditional_format(4, col, 3 + len(ranking), col,
                              {"type": "data_bar", "bar_color": "#7F95C9", "min_type": "num", "min_value": 0,
                               "max_type": "num", "max_value": 100, "bar_solid": True})

        ws = hoja(matriz, "Matriz", lambda c, n: 34 if c == 0 else 14, index=True)
        ws.set_row(3, 60)
        ws.conditional_format(4, 1, 3 + len(matriz), len(matriz.columns),
                              {"type": "3_color_scale", "min_type": "num", "min_value": 0, "min_color": "#F4F6FA",
                               "mid_type": "num", "mid_value": 0.6, "mid_color": "#AFC0E0",
                               "max_type": "num", "max_value": 1, "max_color": "#1D2A57"})

        ws = hoja(brechas, "Brechas", lambda c, n: 34 if c == 0 else 18)
        ws.conditional_format(4, 3, 3 + len(brechas), 3,
                              {"type": "data_bar", "bar_color": "#F08A96", "min_type": "num", "min_value": 0,
                               "max_type": "num", "max_value": 100, "bar_solid": True})

        hoja(detalle_xl, "Detalle", lambda c, n: 34 if n in ("Candidato", "Habilidad más cercana del CV") else 16)
    return salida.getvalue()


# -------------------------------- PDF --------------------------------
def _barra(puntaje: float, ancho=16 * cm, alto=0.55 * cm) -> Drawing:
    color = VERDE if puntaje >= 70 else NARANJA if puntaje >= 40 else ROJO
    d = Drawing(ancho, alto + 4)
    d.add(Rect(0, 2, ancho, alto, fillColor=colors.HexColor("#E8EDF5"), strokeColor=None, rx=4, ry=4))
    d.add(Rect(0, 2, ancho * min(puntaje, 100) / 100, alto, fillColor=colors.HexColor(color),
               strokeColor=None, rx=4, ry=4))
    return d


def pdf_candidato(candidato: str, archivo: str, oferta: str, res: dict, ajustes: str,
                  logo: Path | None = None) -> bytes:
    salida = io.BytesIO()
    doc = SimpleDocTemplate(salida, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=1.6 * cm, bottomMargin=1.6 * cm,
                            title=f"Informe de compatibilidad - {candidato}")
    estilos = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=estilos["Title"], textColor=colors.HexColor(AZUL), fontSize=17,
                        alignment=0, spaceAfter=2)
    h2 = ParagraphStyle("h2", parent=estilos["Heading2"], textColor=colors.HexColor(AZUL), fontSize=12,
                        spaceBefore=12, spaceAfter=6)
    normal = ParagraphStyle("n", parent=estilos["Normal"], fontSize=9.5, leading=13)
    pequeno = ParagraphStyle("p", parent=normal, fontSize=8, textColor=colors.HexColor("#57606A"))
    grande = ParagraphStyle("g", parent=normal, fontSize=30, leading=34, alignment=TA_CENTER,
                            textColor=colors.HexColor(AZUL), fontName="Helvetica-Bold")

    cabecera_txt = [
        Paragraph("Informe de compatibilidad CV–oferta", h1),
        Paragraph("Maestría en Inteligencia Artificial · Universidad César Vallejo · "
                  "Proyecto integrador de PLN · Grupo 10", pequeno),
    ]
    if logo and logo.exists():
        cab = Table([[Image(str(logo), 1.8 * cm, 1.8 * cm), cabecera_txt]], colWidths=[2.3 * cm, 14.7 * cm])
    else:
        cab = Table([[cabecera_txt]], colWidths=[17 * cm])
    cab.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                             ("LINEBELOW", (0, 0), (-1, 0), 2.5, colors.HexColor(ROJO)),
                             ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))

    n_coinc = len(res["coincidentes"])
    total = n_coinc + len(res["faltantes"])
    datos = Table([
        [Paragraph("<b>Candidato</b>", normal), Paragraph(candidato, normal)],
        [Paragraph("<b>Archivo</b>", normal), Paragraph(archivo, normal)],
        [Paragraph("<b>Oferta</b>", normal), Paragraph(oferta, normal)],
        [Paragraph("<b>Requisitos cumplidos</b>", normal), Paragraph(f"{n_coinc} de {total}", normal)],
        [Paragraph("<b>Fecha</b>", normal), Paragraph(f"{datetime.now():%d/%m/%Y %H:%M}", normal)],
    ], colWidths=[4 * cm, 8 * cm])
    datos.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#D5DCE8"))]))
    puntaje = Table([[Paragraph(f"{res['puntaje']}%", grande)],
                     [Paragraph("Compatibilidad", ParagraphStyle("c", parent=pequeno, alignment=TA_CENTER))]],
                    colWidths=[5 * cm])
    puntaje.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F4F6FA")),
                                 ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D5DCE8")),
                                 ("TOPPADDING", (0, 0), (-1, 0), 12), ("BOTTOMPADDING", (0, -1), (-1, -1), 10)]))
    resumen = Table([[datos, puntaje]], colWidths=[12 * cm, 5 * cm])
    resumen.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))

    filas = [["Requisito de la oferta", "Habilidad más cercana del CV", "Similitud", "Resultado"]]
    estilo_det = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(AZUL)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D5DCE8")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (2, 0), (3, -1), "CENTER"),
    ]
    for i, d in enumerate(res["detalle"], start=1):
        req = d["Requisito"] + (" (obligatorio)" if d["Obligatorio"] else "")
        filas.append([Paragraph(req, normal), Paragraph(d["Habilidad más cercana del CV"], normal),
                      f"{d['Similitud']:.3f}", "Cumple" if d["Cumple"] else "No cumple"])
        estilo_det.append(("TEXTCOLOR", (3, i), (3, i), colors.HexColor(VERDE if d["Cumple"] else ROJO)))
        if i % 2 == 0:
            estilo_det.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F4F6FA")))
    detalle = Table(filas, colWidths=[5.2 * cm, 5.8 * cm, 2.6 * cm, 3.4 * cm], repeatRows=1)
    detalle.setStyle(TableStyle(estilo_det))

    elementos = [cab, Spacer(1, 12), resumen, Spacer(1, 10), _barra(res["puntaje"])]
    if res["faltan_obligatorios"]:
        elementos += [Spacer(1, 8), Paragraph(
            f"<font color='{ROJO}'><b>Atención:</b> no cumple los requisitos obligatorios: "
            f"{', '.join(res['faltan_obligatorios'])}.</font>", normal)]
    elementos += [
        Paragraph("Detalle por requisito", h2), detalle,
        Paragraph("Habilidades adicionales del candidato", h2),
        Paragraph(", ".join(res["excedentes"]) or "Ninguna.", normal),
        Spacer(1, 16),
        Paragraph(f"Ajustes del modelo: {ajustes}. Modelo de embeddings: paraphrase-multilingual-"
                  "MiniLM-L12-v2 (Sentence-BERT). Extracción: spaCy (es_core_news_md) + gazetteer propio. "
                  "Herramienta de apoyo: no reemplaza el criterio de un reclutador humano.", pequeno),
    ]
    doc.build(elementos)
    return salida.getvalue()
