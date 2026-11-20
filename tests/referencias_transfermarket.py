"""Calcula las respuestas de referencia del banco de preguntas, sin el agente.

Lanza cada consulta DAX directamente contra Power BI y guarda el resultado en
un JSON. También guarda la fórmula de las medidas, para revisar qué calcula cada
una antes de dar una referencia por buena.

Uso, desde la raíz de MCP (con el .env apuntando al dataset):
    py -m tests.referencias
"""

import json

from src import powerbi_client as pc

SALIDA = "tests/referencias_transfermarkt.json"

CONSULTAS = {
    "3": 'EVALUATE ROW("v", [goals])',
    "4": 'EVALUATE ROW("n", COUNTROWS(games))',
    "5": 'EVALUATE ROW("v", CALCULATE([goals], players[name] = "Lionel Messi"))',
    "6": 'EVALUATE ROW("v", CALCULATE([average_attendance], competitions[competition_id] = "ES1"))',
    "6_comprobar_ligas": 'EVALUATE SELECTCOLUMNS(FILTER(competitions, competitions[country_name] = "Spain"), "id", competitions[competition_id], "name", competitions[name])',
    "7": 'EVALUATE ROW("casa", SUM(games[home_club_goals]), "fuera", SUM(games[away_club_goals]))',
    "8": 'EVALUATE ROW("t2022", CALCULATE([average_attendance], games[season] = 2022), "t2023", CALCULATE([average_attendance], games[season] = 2023))',
    "9": 'EVALUATE TOPN(10, SUMMARIZECOLUMNS(players[name], "g", [goals]), [g], DESC)',
    "10": 'EVALUATE TOPN(5, SUMMARIZECOLUMNS(games[stadium], "a", [average_attendance]), [a], DESC)',
    "11": 'EVALUATE SUMMARIZECOLUMNS(dim_date[Año], "v", [average_market_value])',
    "12_dim_date": 'EVALUATE ROW("v", CALCULATE([goals], dim_date[Año] = 2023))',
    "12_appearances": 'EVALUATE ROW("v", CALCULATE([goals], FILTER(appearances, YEAR(appearances[Date]) = 2023)))',
    "13": 'EVALUATE TOPN(1, SUMMARIZECOLUMNS(clubs[name], "n", DISTINCTCOUNT(appearances[player_id])), [n], DESC)',
    "14": 'EVALUATE DISTINCT(players[position])',
    "15": 'EVALUATE TOPN(1, SELECTCOLUMNS(players, "name", players[name], "v", players[market_value_in_eur]), [v], DESC)',
    "4_games_played": 'EVALUATE ROW("v", [games_played])',
    "13_sin_vacios": 'EVALUATE TOPN(1, FILTER(SUMMARIZECOLUMNS(clubs[name], "n", DISTINCTCOUNT(appearances[player_id])), NOT ISBLANK(clubs[name])), [n], DESC)',
    "13_huerfanas": 'EVALUATE ROW("apariciones_sin_club", COUNTROWS(FILTER(appearances, ISBLANK(RELATED(clubs[name])))), "total", COUNTROWS(appearances))',
    "10_partidos": 'EVALUATE TOPN(5, SUMMARIZECOLUMNS(games[stadium], "a", [average_attendance], "partidos", COUNTROWS(games)), [a], DESC)',
}

MEDIDAS = [
    "goals",
    "assists",
    "minutes_played",
    "games_played",
    "goals_per_game",
    "average_market_value",
    "average_attendance",
]


def main() -> None:
    resultados = {"consultas": {}, "medidas": {}}

    for pregunta, dax in CONSULTAS.items():
        try:
            r = pc.execute_query(dax)
            resultados["consultas"][pregunta] = {"dax": dax, "ok": True, **r}
            print(f"{pregunta}: ok ({r['row_count']} filas)")
        except Exception as exc:
            resultados["consultas"][pregunta] = {"dax": dax, "ok": False, "error": str(exc)[:500]}
            print(f"{pregunta}: ERROR")

    for nombre in MEDIDAS:
        try:
            resultados["medidas"][nombre] = pc.get_measure_dax(nombre)["expression"]
            print(f"medida {nombre}: ok")
        except Exception as exc:
            resultados["medidas"][nombre] = f"ERROR: {str(exc)[:300]}"
            print(f"medida {nombre}: ERROR")

    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=1, default=str)
    print(f"\nGuardado en {SALIDA}")


if __name__ == "__main__":
    main()