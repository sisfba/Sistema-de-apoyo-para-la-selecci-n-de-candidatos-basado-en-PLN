import spacy
from spacy.matcher import PhraseMatcher
import pdfplumber
from gazetteer import GAZETTEER, gazetteer_flat

nlp = spacy.load("es_core_news_md")

def build_matcher():
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    for categoria, terminos in GAZETTEER.items():
        patterns = [nlp.make_doc(t) for t in terminos]
        matcher.add(categoria, patterns)
    return matcher

MATCHER = build_matcher()

def extract_text_from_pdf(path):
    """
    Extrae y limpia el texto de un CV en PDF, con detección de columnas.

    Muchos CVs (incluidos los generados con IA para este proyecto) usan un
    diseño en dos columnas en alguna sección puntual (por ejemplo, Educación
    en una columna y Habilidades Técnicas en otra, lado a lado), aunque el
    resto del documento sea de una sola columna. pdfplumber.extract_text()
    por defecto no respeta el orden visual en esos casos: mezcla palabras
    de ambas columnas en la misma línea, lo que rompe frases y hace que
    términos reales (ej. "Ecocardiografía", "PyTorch") queden pegados a
    texto de la otra columna.

    Esta versión agrupa las palabras en filas por su posición vertical y,
    fila por fila, detecta si hay un hueco horizontal grande (indicio de
    dos columnas en ese punto del documento). Las filas con ese hueco se
    van acumulando en dos "columnas diferidas" (izquierda/derecha) hasta
    que aparece una fila normal de una sola columna; en ese momento se
    vuelca primero toda la columna izquierda acumulada y luego toda la
    derecha, antes de continuar con el resto del texto en su orden normal.
    """
    text_parts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
            if not words:
                continue
            page_text = _extract_page_text_column_aware(words, page.width)
            text_parts.append(page_text)
    text = "\n".join(text_parts)
    lines = [l.strip() for l in text.split("\n")]
    lines = [l for l in lines if l]
    return "\n".join(lines)


def _group_into_rows(words, top_tolerance=4.0):
    """Agrupa palabras en filas visuales según su posición vertical (top)."""
    ordered = sorted(words, key=lambda w: (w["top"], w["x0"]))
    rows = []
    current_row = []
    current_top = None
    for w in ordered:
        if current_top is None or abs(w["top"] - current_top) <= top_tolerance:
            current_row.append(w)
            current_top = w["top"] if current_top is None else current_top
        else:
            rows.append(current_row)
            current_row = [w]
            current_top = w["top"]
    if current_row:
        rows.append(current_row)
    return rows


def _extract_page_text_column_aware(words, page_width, min_gap_ratio=0.15):
    rows = _group_into_rows(words)
    min_gap = page_width * min_gap_ratio

    output = []
    left_buffer = []
    right_buffer = []

    def flush_buffers():
        if left_buffer:
            output.append("\n".join(left_buffer))
            left_buffer.clear()
        if right_buffer:
            output.append("\n".join(right_buffer))
            right_buffer.clear()

    for row in rows:
        row_sorted = sorted(row, key=lambda w: w["x0"])
        # buscar el hueco horizontal más grande dentro de esta fila
        max_gap, gap_idx = 0, None
        for i in range(len(row_sorted) - 1):
            gap = row_sorted[i + 1]["x0"] - row_sorted[i]["x1"]
            if gap > max_gap:
                max_gap, gap_idx = gap, i

        if max_gap >= min_gap and gap_idx is not None:
            left_words = row_sorted[: gap_idx + 1]
            right_words = row_sorted[gap_idx + 1 :]
            left_buffer.append(" ".join(w["text"] for w in left_words))
            right_buffer.append(" ".join(w["text"] for w in right_words))
        else:
            flush_buffers()
            output.append(" ".join(w["text"] for w in row_sorted))

    flush_buffers()
    return "\n".join(output)

def extract_skills(text):
    """
    Devuelve un set de habilidades encontradas en el texto, con su categoría.
    Usa coincidencia por frase (gazetteer) sobre el texto normalizado en minúsculas.
    """
    doc = nlp(text.lower())
    matches = MATCHER(doc)
    found = {}
    for match_id, start, end in matches:
        categoria = nlp.vocab.strings[match_id]
        span_text = doc[start:end].text
        found.setdefault(span_text, set()).add(categoria)
    return found

def summarize_extraction(path):
    text = extract_text_from_pdf(path)
    skills = extract_skills(text)
    return {
        "archivo": path,
        "longitud_texto": len(text),
        "habilidades_encontradas": sorted(skills.keys()),
        "total_habilidades": len(skills),
    }

if __name__ == "__main__":
    # Prueba con un texto de ejemplo mientras llegan los CVs reales
    ejemplo = """
    Ingeniero de sistemas con experiencia en desarrollo de software y
    administración de bases de datos. Manejo de Python, SQL y Power BI.
    Experiencia liderando equipos ágiles bajo metodología Scrum.
    Nivel de inglés intermedio. Fuerte capacidad de trabajo en equipo
    y resolución de problemas complejos.
    """
    resultado = extract_skills(ejemplo)
    print("Habilidades detectadas en el texto de ejemplo:")
    for skill, categorias in sorted(resultado.items()):
        print(f"  - {skill}  [{', '.join(categorias)}]")
