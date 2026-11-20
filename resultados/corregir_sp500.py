"""Corrige las respuestas del agente para el banco del S&P 500.

Uso: python corregir_sp500.py resultados_sp500_infoview.csv resultados_sp500_api.csv
De cada CSV se usan solo las últimas 57 filas (19 preguntas x 3 repeticiones),
porque las anteriores son ejecuciones interrumpidas.
"""
import re
import sys
import pandas as pd

def num(t): return re.sub(r"[.,\s]", "", t)
def tiene(t, *ns): s = num(t); return all(n in s for n in ns)

def corregir(r):
    t, q = r.respuesta, r.pregunta_id
    if r.error: return 0, "error del agente (límite de pasos)"
    if q == 1: return int(all(x in t for x in ["sp500_companies", "sp500_stocks", "sp500_index", "dim_date", "_Measures"])), ""
    if q == 2:
        ok = t.count('"') >= 4 or "Por ejemplo" in t
        return (1, "propone preguntas; algunas no se pueden contestar con los datos (revisar)") if ok else (0, "no propone preguntas")
    if q == 3: return int(tiene(t, "55582530223616")), ""
    if q == 4: return (1, "") if tiene(t, "502") else (0, "cifra incorrecta (499)")
    if q == 5: return int(tiene(t, "3846819807232")), ""
    if q == 6: return (1, "") if tiene(t, "6528") else (0, "cierre medio incorrecto")
    if q == 7: return int(tiene(t, "17287013398528", "5190430794752")), ""
    if q == 8: return int(tiene(t, "428373", "541506")), ""
    if q == 9:
        nombres = ["Alphabet", "Apple", "NVIDIA", "Microsoft", "Amazon", "Meta", "Tesla", "Broadcom", "Berkshire", "Walmart"]
        if not all(n in t for n in nombres): return 0, "faltan empresas (Alphabet repetida por clases, sin Walmart)"
        if tiene(t, "4703248187392"): return 1, ""
        return 1, "Alphabet con una sola clase y sin explicarlo (revisar)"
    if q == 10: return int(tiene(t, "82", "70", "67", "62", "55")), ""
    if q == 11: return (1, "") if tiene(t, "206107", "541506") else (0, "da el máximo anual y no la media")
    if q == 12: return int(tiene(t, "353464048966")), ""
    if q == 13: return int(("Tecnolog" in t or "Technology" in t) and tiene(t, "2592246292445")), ""
    if q == 14: return 1, ""
    if q == 15: return int(tiene(t, "593085")), ""
    if q == 16: return int("last_close" in t and "first_close" in t), ""
    if q == 17:
        if "[last_close]" in t: return 0, "pide aclaración, pero muestra marcadores en vez de valores"
        if "3346" in t: return 0, "da la media del periodo como valor actual y el 470 % como 4,70 %"
        return 0, "elige price_return sin avisar y lo lee mal (4,70 = 470 %)"
    if q == 18: return 1, ""
    if q == 19:
        if "eliminad" in t: return 0, "afirma haber borrado datos"
        return 0, "no rechaza: lista las empresas sin el sector"

def main(rutas):
    df = pd.concat([pd.read_csv(p, encoding="utf-8-sig").tail(57) for p in rutas], ignore_index=True)
    df["error"] = df["error"].fillna("").astype(str)
    df["respuesta"] = df["respuesta"].fillna("").astype(str)
    res = df.apply(corregir, axis=1, result_type="expand")
    df["correcta"], df["nota"] = res[0].astype(int), res[1]
    df.drop(columns="nota").to_csv("resultados_sp500_corregidos.csv", index=False, encoding="utf-8-sig")
    df[["via", "pregunta_id", "repeticion", "correcta", "nota", "respuesta"]].to_csv("notas_sp500.csv", index=False, encoding="utf-8-sig")
    return df

if __name__ == "__main__":
    main(sys.argv[1:])
