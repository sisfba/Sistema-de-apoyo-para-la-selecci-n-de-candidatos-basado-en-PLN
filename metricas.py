"""
Métricas de concordancia sistema vs. evaluador humano (capítulo 4.3):
Kappa de Cohen (Cohen, 1960), interpretación de Landis y Koch (1977),
precisión, exhaustividad y F1.
"""
import pandas as pd

COL_CV = "CV"
COL_OFERTA = "Oferta"
COL_REQUISITO = "Requisito"
COL_SISTEMA = "Resultado del sistema"
COL_HUMANO = "Criterio del evaluador humano (completar)"

_SI = {"sí", "si", "coincide", "1", "true", "verdadero", "x"}
_NO = {"no", "no coincide", "0", "false", "falso"}


def a_binario(valor):
    """'Sí'/'Coincide'/1 -> True, 'No'/'No coincide'/0 -> False, vacío -> None."""
    if pd.isna(valor):
        return None
    texto = str(valor).strip().lower()
    if texto in _SI:
        return True
    if texto in _NO:
        return False
    return None


def leer_plantilla(archivo) -> pd.DataFrame:
    """Lee la hoja de evaluación y normaliza las decisiones a booleanos."""
    hojas = pd.read_excel(archivo, sheet_name=None)
    hoja = next((df for df in hojas.values() if COL_HUMANO in df.columns), None)
    if hoja is None:
        raise ValueError(f"No se encontró una hoja con la columna «{COL_HUMANO}».")
    df = hoja.copy()
    df["sistema"] = df[COL_SISTEMA].map(a_binario)
    df["humano"] = df[COL_HUMANO].map(a_binario)
    return df


def interpretar_kappa(k: float) -> str:
    if k < 0:
        return "Sin acuerdo"
    for limite, texto in [(0.20, "Leve"), (0.40, "Aceptable"), (0.60, "Moderado"),
                          (0.80, "Considerable"), (1.00, "Casi perfecto")]:
        if k <= limite:
            return texto
    return "Casi perfecto"


def calcular(sistema, humano) -> dict:
    pares = [(bool(s), bool(h)) for s, h in zip(sistema, humano) if s is not None and h is not None]
    n = len(pares)
    vp = sum(s and h for s, h in pares)
    fp = sum(s and not h for s, h in pares)
    fn = sum(not s and h for s, h in pares)
    vn = sum(not s and not h for s, h in pares)
    if n == 0:
        return {"n": 0, "vp": 0, "fp": 0, "fn": 0, "vn": 0, "po": 0.0, "pe": 0.0, "kappa": 0.0,
                "precision": 0.0, "recall": 0.0, "f1": 0.0, "interpretacion": "Sin datos"}
    po = (vp + vn) / n
    pe = ((vp + fp) * (vp + fn) + (fn + vn) * (fp + vn)) / n ** 2
    kappa = (po - pe) / (1 - pe) if pe < 1 else 1.0
    precision = vp / (vp + fp) if vp + fp else 0.0
    recall = vp / (vp + fn) if vp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"n": n, "vp": vp, "fp": fp, "fn": fn, "vn": vn, "po": po, "pe": pe, "kappa": kappa,
            "precision": precision, "recall": recall, "f1": f1, "interpretacion": interpretar_kappa(kappa)}
