"""Calcula las respuestas de referencia del banco del S&P 500, sin el agente.

Igual que tests/referencias.py, con las consultas del S&P 500.

Uso, desde la raíz de MCP (con el .env apuntando al S&P 500):
    py -m tests.referencias_sp500
"""

import json

from src import powerbi_client as pc

SALIDA = "tests/referencias_sp500.json"

CONSULTAS = {
    "rangos_fechas": 'EVALUATE ROW("idx_min", MIN(sp500_index[Date]), "idx_max", MAX(sp500_index[Date]), "stk_min", MIN(sp500_stocks[Date]), "stk_max", MAX(sp500_stocks[Date]), "cal_min", MIN(dim_date[Date]), "cal_max", MAX(dim_date[Date]))',
    "3": 'EVALUATE ROW("v", [total_market_cap])',
    "4": 'EVALUATE ROW("filas_companies", COUNTROWS(sp500_companies), "medida", [companies_count], "simbolos_en_stocks", DISTINCTCOUNT(sp500_stocks[Symbol]))',
    "5": 'EVALUATE ROW("v", CALCULATE([total_market_cap], sp500_companies[Symbol] = "AAPL"))',
    "5_comprobar_nombre": 'EVALUATE FILTER(SELECTCOLUMNS(sp500_companies, "symbol", sp500_companies[Symbol], "short", sp500_companies[Shortname]), CONTAINSSTRING([short], "Apple"))',
    "6": 'EVALUATE ROW("v", CALCULATE([avg_close], sp500_companies[Sector] = "Technology"))',
    "7": 'EVALUATE ROW("tecnologia", CALCULATE([total_market_cap], sp500_companies[Sector] = "Technology"), "salud", CALCULATE([total_market_cap], sp500_companies[Sector] = "Healthcare"))',
    "8": 'EVALUATE ROW("y2023", CALCULATE([index_value], dim_date[Year] = 2023), "y2024", CALCULATE([index_value], dim_date[Year] = 2024))',
    "9": 'EVALUATE TOPN(10, SUMMARIZECOLUMNS(sp500_companies[Shortname], "m", [total_market_cap]), [m], DESC)',
    "10": 'EVALUATE TOPN(5, SUMMARIZECOLUMNS(sp500_companies[Sector], "n", [companies_count]), [n], DESC)',
    "11": 'EVALUATE SUMMARIZECOLUMNS(dim_date[Year], "media", [index_value], "dias", COUNTROWS(sp500_index))',
    "12_dim_date": 'EVALUATE ROW("v", CALCULATE([total_volume], dim_date[Year] = 2023))',
    "12_stocks": 'EVALUATE ROW("v", CALCULATE([total_volume], FILTER(sp500_stocks, YEAR(sp500_stocks[Date]) = 2023)))',
    "13": 'EVALUATE TOPN(3, SUMMARIZECOLUMNS(sp500_companies[Sector], "v", [total_volume]), [v], DESC)',
    "13_huerfanos": 'EVALUATE ROW("simbolos_sin_empresa", COUNTROWS(EXCEPT(VALUES(sp500_stocks[Symbol]), VALUES(sp500_companies[Symbol]))))',
    "14": 'EVALUATE DISTINCT(sp500_companies[Sector])',
    "15": 'EVALUATE ROW("ultima_fecha", MAX(sp500_index[Date]), "ultimo_valor", LASTNONBLANKVALUE(sp500_index[Date], SUM(sp500_index[S&P500])), "media_index_value", [index_value])',
    "contexto_retornos": 'EVALUATE ROW("first_close", [first_close], "last_close", [last_close], "price_return", [price_return], "avg_company_return", [avg_company_return])',
}


def main() -> None:
    resultados = {"consultas": {}}
    for pregunta, dax in CONSULTAS.items():
        try:
            r = pc.execute_query(dax)
            resultados["consultas"][pregunta] = {"dax": dax, "ok": True, **r}
            print(f"{pregunta}: ok ({r['row_count']} filas)")
        except Exception as exc:
            resultados["consultas"][pregunta] = {"dax": dax, "ok": False, "error": str(exc)[:500]}
            print(f"{pregunta}: ERROR")

    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=1, default=str)
    print(f"\nGuardado en {SALIDA}")


if __name__ == "__main__":
    main()