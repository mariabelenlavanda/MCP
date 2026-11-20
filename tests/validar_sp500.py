"""Valida las respuestas de referencia del S&P 500 con los CSV originales de Kaggle.

Calcula las mismas cifras que tests/referencias_sp500.py, pero desde los CSV y
sin Power BI. Igual que en el modelo, de sp500_stocks solo se usan las filas con
precio de cierre (Close), porque Power Query quita las que lo tienen vacío.

Uso, desde la raíz de MCP:
    py tests/validar_sp500.py "C:/ruta/a/la/carpeta/SP500"
"""

import json
import sys
from pathlib import Path

import pandas as pd

REFERENCIAS = Path("tests/referencias_sp500.json")


def valor_powerbi(refs: dict, clave: str, columna: str):
    try:
        return refs["consultas"][clave]["rows"][0][columna]
    except (KeyError, IndexError):
        return None


def comparar(nombre: str, csv_valor, pbi_valor) -> None:
    if pbi_valor is None:
        estado = "sin referencia de Power BI"
    else:
        estado = "OK" if abs(float(csv_valor) - float(pbi_valor)) < 0.01 else "DISTINTO"
    print(f"{nombre:<42} CSV={csv_valor!s:<22} PowerBI={pbi_valor!s:<22} {estado}")


def main() -> None:
    carpeta = Path(sys.argv[1])
    refs = json.loads(REFERENCIAS.read_text(encoding="utf-8"))

    empresas = pd.read_csv(carpeta / "sp500_companies.csv",
                           usecols=["Symbol", "Shortname", "Sector", "Marketcap"])
    precios = pd.read_csv(carpeta / "sp500_stocks.csv",
                          usecols=["Date", "Symbol", "Close", "Volume"], low_memory=False)
    precios = precios[precios["Close"].notna()]
    precios["Year"] = pd.to_datetime(precios["Date"]).dt.year
    precios = precios.merge(empresas[["Symbol", "Sector"]], on="Symbol", how="left")
    indice = pd.read_csv(carpeta / "sp500_index.csv")
    indice["Date"] = pd.to_datetime(indice["Date"])
    indice["Year"] = indice["Date"].dt.year

    print("=== Cifras sueltas ===")
    comparar("3  capitalización total", empresas["Marketcap"].sum(), valor_powerbi(refs, "3", "[v]"))
    comparar("4  empresas", len(empresas), valor_powerbi(refs, "4", "[filas_companies]"))
    comparar("4  empresas con precios", precios["Symbol"].nunique(),
             valor_powerbi(refs, "4", "[simbolos_en_stocks]"))
    comparar("5  capitalización de Apple (AAPL)",
             empresas.loc[empresas["Symbol"] == "AAPL", "Marketcap"].sum(), valor_powerbi(refs, "5", "[v]"))
    comparar("6  cierre medio Technology",
             precios.loc[precios["Sector"] == "Technology", "Close"].mean(), valor_powerbi(refs, "6", "[v]"))
    por_sector = empresas.groupby("Sector")["Marketcap"].sum()
    comparar("7  capitalización Technology", por_sector["Technology"], valor_powerbi(refs, "7", "[tecnologia]"))
    comparar("7  capitalización Healthcare", por_sector["Healthcare"], valor_powerbi(refs, "7", "[salud]"))
    comparar("8  índice medio 2023", indice.loc[indice["Year"] == 2023, "S&P500"].mean(),
             valor_powerbi(refs, "8", "[y2023]"))
    comparar("8  índice medio 2024", indice.loc[indice["Year"] == 2024, "S&P500"].mean(),
             valor_powerbi(refs, "8", "[y2024]"))
    comparar("12 volumen 2023", precios.loc[precios["Year"] == 2023, "Volume"].sum(),
             valor_powerbi(refs, "12_dim_date", "[v]"))
    ultimo = indice.sort_values("Date").iloc[-1]
    comparar("15 último valor del índice", ultimo["S&P500"], valor_powerbi(refs, "15", "[ultimo_valor]"))
    print(f"   fecha del último valor: {ultimo['Date'].date()}")

    print("\n=== Rankings y listas (comparar a ojo con el banco) ===")
    print("\n9  Top 10 por capitalización (agrupado por nombre)")
    print(empresas.groupby("Shortname")["Marketcap"].sum().sort_values(ascending=False).head(10).to_string())
    print("\n10 Sectores con más empresas")
    print(empresas["Sector"].value_counts().head(5).to_string())
    print("\n11 Índice medio por año")
    print(indice.groupby("Year")["S&P500"].agg(["mean", "count"]).round(2).to_string())
    print("\n13 Sectores con más volumen")
    print(precios.groupby("Sector")["Volume"].sum().sort_values(ascending=False).head(3).to_string())
    print("\n14 Sectores")
    print(sorted(empresas["Sector"].dropna().unique()))


if __name__ == "__main__":
    main()