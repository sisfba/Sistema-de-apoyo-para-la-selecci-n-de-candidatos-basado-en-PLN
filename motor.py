"""
Motor de análisis para la interfaz: envuelve extraction.py y el modelo
Sentence-BERT con caché de Streamlit, y separa el cálculo de similitudes
(costoso, se cachea) de la aplicación del umbral (barato, se recalcula al
mover el deslizador).

La regla de decisión es la misma de compatibilidad_produccion.py: para cada
requisito de la oferta se toma la habilidad más cercana del CV y se exige
UMBRAL_COINCIDENCIA, o UMBRAL_SIGLAS si el requisito es una sigla corta.
Con los umbrales por defecto y sin requisitos obligatorios, el puntaje es
idéntico al del módulo original.
"""
import io

import numpy as np
import streamlit as st

from compatibilidad_produccion import UMBRAL_COINCIDENCIA, UMBRAL_SIGLAS, _es_sigla

CATEGORIAS = {
    "tecnologia": "Tecnología",
    "salud": "Salud",
    "administracion_gestion": "Administración y gestión",
    "ventas_marketing": "Ventas y marketing",
    "educacion": "Educación",
    "idiomas": "Idiomas",
    "habilidades_blandas": "Habilidades blandas",
}

UMBRAL_DEFECTO = UMBRAL_COINCIDENCIA
UMBRAL_SIGLAS_DEFECTO = UMBRAL_SIGLAS


@st.cache_resource(show_spinner="Cargando modelos de lenguaje (solo la primera vez)...")
def cargar_motor():
    """Carga spaCy + gazetteer y el modelo Sentence-BERT una sola vez por servidor."""
    from extraction import extract_text, extract_skills
    from compatibilidad_produccion import get_model

    return extract_text, extract_skills, get_model()


def _habilidades(texto: str):
    _, extract_skills, _ = cargar_motor()
    encontradas = extract_skills(texto)
    skills = tuple(sorted(encontradas))
    categorias = {s: sorted(encontradas[s]) for s in skills}
    return skills, categorias


FORMATOS_CV = ["pdf", "docx"]


@st.cache_data(show_spinner=False, max_entries=500)
def analizar_cv(contenido: bytes, nombre: str = "cv.pdf"):
    """PDF o Word -> (texto, habilidades, {habilidad: [categorías]}). Se cachea por contenido."""
    extract_text, _, _ = cargar_motor()
    texto = extract_text(io.BytesIO(contenido), nombre)
    skills, categorias = _habilidades(texto)
    return texto, skills, categorias


@st.cache_data(show_spinner=False, max_entries=200)
def habilidades_oferta(texto: str):
    """Texto de oferta -> (habilidades, {habilidad: [categorías]})."""
    return _habilidades(texto)


@st.cache_data(show_spinner=False, max_entries=2000)
def embeddings(skills: tuple) -> np.ndarray:
    """Vectores normalizados (el producto punto equivale a la similitud coseno)."""
    _, _, modelo = cargar_motor()
    if not skills:
        return np.zeros((0, modelo.get_sentence_embedding_dimension()), dtype=np.float32)
    return modelo.encode(list(skills), normalize_embeddings=True, convert_to_numpy=True)


def matriz_similitud(skills_cv: tuple, skills_oferta: tuple) -> np.ndarray:
    """Matriz (requisitos de la oferta x habilidades del CV) de similitud coseno."""
    return embeddings(skills_oferta) @ embeddings(skills_cv).T


def umbral_efectivo(requisito: str, umbral: float, umbral_siglas: float) -> float:
    return umbral_siglas if _es_sigla(requisito) else umbral


def evaluar(skills_cv: tuple, skills_oferta: tuple, umbral: float = UMBRAL_DEFECTO,
            umbral_siglas: float = UMBRAL_SIGLAS_DEFECTO, obligatorios=()) -> dict:
    """
    Aplica la regla de decisión y devuelve:
      puntaje, coincidentes [(req, hab_cv, sim)], faltantes, excedentes,
      faltan_obligatorios, detalle [dict por requisito].
    Los requisitos obligatorios pesan el doble en el puntaje.
    """
    obligatorios = set(obligatorios)
    sim = matriz_similitud(skills_cv, skills_oferta) if skills_cv and skills_oferta else None

    coincidentes, faltantes, detalle, usadas = [], [], [], set()
    peso_total = peso_cumplido = 0.0
    for i, req in enumerate(skills_oferta):
        peso = 2.0 if req in obligatorios else 1.0
        peso_total += peso
        corte = umbral_efectivo(req, umbral, umbral_siglas)
        if sim is None:
            mejor_hab, mejor_sim = None, 0.0
        else:
            j = int(sim[i].argmax())
            mejor_hab, mejor_sim = skills_cv[j], float(sim[i, j])
        cumple = mejor_hab is not None and mejor_sim >= corte
        if cumple:
            coincidentes.append((req, mejor_hab, round(mejor_sim, 3)))
            usadas.add(mejor_hab)
            peso_cumplido += peso
            tipo = "Exacta" if req == mejor_hab else "Semántica"
        else:
            faltantes.append(req)
            tipo = "No encontrada"
        detalle.append({
            "Requisito": req,
            "Habilidad más cercana del CV": mejor_hab or "—",
            "Similitud": round(mejor_sim, 3),
            "Umbral aplicado": corte,
            "Tipo de coincidencia": tipo,
            "Cumple": cumple,
            "Obligatorio": req in obligatorios,
        })

    return {
        "puntaje": round(100 * peso_cumplido / peso_total, 1) if peso_total else 0.0,
        "coincidentes": coincidentes,
        "faltantes": faltantes,
        "excedentes": [h for h in skills_cv if h not in usadas],
        "faltan_obligatorios": [r for r in faltantes if r in obligatorios],
        "detalle": detalle,
    }


def perfil_por_categoria(categorias: dict) -> dict:
    """Cantidad de habilidades del CV en cada área del gazetteer."""
    conteo = {c: 0 for c in CATEGORIAS}
    for cats in categorias.values():
        for c in cats:
            if c in conteo:
                conteo[c] += 1
    return conteo
