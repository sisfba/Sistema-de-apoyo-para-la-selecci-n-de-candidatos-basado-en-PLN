# Sistema de apoyo a la selección de candidatos (PLN) — v2

Cambios respecto a la primera versión (ver conversación con Claude para el
detalle completo del proceso):

## Novedades en esta versión

1. **extraction.py — extracción consciente de columnas.** Se detectó que
   varios CVs (incluidos los 80 generados con IA) usan un diseño de dos
   columnas en la sección de Educación/Habilidades Técnicas, y que
   `pdfplumber.extract_text()` por defecto mezclaba el texto de ambas
   columnas en la misma línea, rompiendo términos reales. La nueva versión
   de `extract_text_from_pdf` agrupa palabras por fila visual, detecta
   huecos horizontales grandes (indicio de columnas) fila por fila, y
   reordena el texto respetando cada columna por separado.

2. **gazetteer.py — ampliado con términos reales encontrados en CVs de
   salud, tecnología y administración** (ej. Ecocardiografía, DSM-5,
   Cirugía Laparoscópica, ACLS, Farmacovigilancia, PyTorch, LangChain,
   SIEM, NIIF, SAP S/4HANA). Antes de esta ampliación, el gazetteer
   solo detectaba en promedio 3.8 habilidades por CV de salud; después,
   6.2 (casi el doble), y con términos semánticamente relevantes en vez
   de solo palabras genéricas de perfil profesional.

3. **ofertas.py — 6 ofertas de ejemplo**, 2 por cada uno de los 3
   sectores usados en la evaluación (tecnología, administración/gestión,
   salud).

4. **run_lote.py** — script nuevo para procesar una carpeta completa de
   CVs contra una oferta de una sola vez (en vez de un CV a la vez).

## Alcance de la evaluación

De los 80 CVs disponibles (con perfiles de docenas de profesiones muy
distintas: desde ingeniero de minas hasta sommelier), se decidió acotar
la evaluación formal a 15-20 CVs de 3 sectores relacionados (tecnología,
administración/gestión y salud), porque construir un gazetteer que cubra
con calidad decenas de dominios profesionales no es viable en el plazo
del proyecto. Esto se documenta como decisión metodológica explícita en
el capítulo 4 (alcance) y como línea de trabajo futuro en el capítulo 5
(ampliar cobertura a otros dominios).

## Instalación

```bash
pip install -r requirements.txt
python -m spacy download es_core_news_md
```

## Uso rápido (un CV contra una oferta)

```python
from extraction import extract_text_from_pdf, extract_skills
from ofertas import OFERTAS
from compatibilidad_produccion import calcular_compatibilidad

texto_cv = extract_text_from_pdf("ruta/a/tu_cv.pdf")
skills_cv = sorted(extract_skills(texto_cv).keys())

oferta = OFERTAS["oferta_salud_clinica"]  # ver ofertas.py para las 6 disponibles
skills_oferta = sorted(extract_skills(oferta["texto"]).keys())

resultado = calcular_compatibilidad(skills_cv, skills_oferta)
print(resultado)
```

## Uso en lote (una carpeta completa de CVs)

1. Coloca los PDFs en una carpeta (por ejemplo `cvs/`).
2. Edita `run_lote.py`: ajusta `CARPETA_CVS` y `OFERTA_KEY`.
3. Corre `python run_lote.py`.

## Ofertas disponibles (ofertas.py)

- `oferta_logistica` — Jefe de Planificación y Abastecimiento
- `oferta_ti_funcional` — Especialista Funcional / Analista de Requerimientos
- `oferta_ti_desarrollo` — Desarrollador de Software Java
- `oferta_salud_clinica` — Médico Internista / Especialista Clínico
- `oferta_salud_enfermeria` — Enfermero(a) de Cuidados Críticos
- `oferta_salud_farmacovigilancia` — Especialista en Farmacovigilancia

## Siguiente paso pendiente

- Correr `run_lote.py` sobre los 18 CVs seleccionados (6 tech, 6 admin,
  6 salud) contra su oferta correspondiente, y guardar los resultados
  para el capítulo 4.3 (Evaluación).
- Conseguir el criterio de un evaluador humano sobre esos mismos 18 pares,
  para poder calcular el coeficiente Kappa de Cohen.
- Calibrar `UMBRAL_COINCIDENCIA` en `compatibilidad_produccion.py`
  (actualmente 0.60) según esos resultados.
- Construir la interfaz en Streamlit.

## Aplicación web (Streamlit)

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

La barra lateral define la oferta (puestos de ejemplo o agregados por el usuario,
que se guardan en `ofertas_personalizadas.json`), los requisitos obligatorios
(pesan el doble) y los umbrales de similitud. Secciones:

- **Individual / Masiva**: evaluación de uno o muchos CVs (PDF o Word, subidos o desde la
  carpeta `cvs_80`), ranking con filtros, informe PDF por candidato y Excel con formato.
- **Tablero**: distribución de puntajes, mapa de calor candidatos × requisitos,
  brechas de habilidades y habilidades adicionales más comunes.
- **Comparar**: radar de perfil por área y comparación requisito por requisito.
- **Laboratorio PLN**: mapa semántico (PCA de los embeddings), detalle de
  similitudes, sensibilidad al umbral y texto con habilidades resaltadas.
- **Validación**: Kappa de Cohen contra `Evaluacion_Kappa_PLN.xlsx` y curva de
  concordancia según el umbral.

Código de la interfaz: `app.py` (encabezado, barra lateral, navegación),
`app_pages/` (una página por sección), `motor.py` (extracción y embeddings con
caché; misma regla de decisión que `compatibilidad_produccion.py`),
`ui_comun.py`, `graficos.py`, `reportes.py` y `metricas.py`.
