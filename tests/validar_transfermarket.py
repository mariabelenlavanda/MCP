"""Valida las respuestas de referencia con los CSV originales de Transfermarkt.

Calcula las mismas cifras que tests/referencias.py, pero desde los CSV de
Kaggle y sin Power BI. Si una cifra coincide por los dos caminos, la referencia
es fiable. Si no coincide, o la consulta DAX está mal o el modelo de Power BI
transformó los datos al cargarlos.

Uso, desde la raíz de MCP:
    py tests/validar_csv.py "C:/ruta/a/la/carpeta/de/los/csv"
"""

import json
import sys
from pathlib import Path

import pandas as pd

REFERENCIAS = Path("tests/referencias_transfermarkt.json")


def leer(carpeta: Path, nombre: str, columnas: list[str]) -> pd.DataFrame:
    return pd.read_csv(carpeta / f"{nombre}.csv", usecols=columnas, low_memory=False)


def valor_powerbi(refs: dict, clave: str, columna: str):
    try:
        return refs["consultas"][clave]["rows"][0][columna]
    except (KeyError, IndexError):
        return None


def comparar(nombre: str, csv_valor, pbi_valor) -> None:
    if pbi_valor is None:
        estado = "sin referencia de Power BI"
    elif isinstance(csv_valor, float) or isinstance(pbi_valor, float):
        estado = "OK" if abs(float(csv_valor) - float(pbi_valor)) < 0.5 else "DISTINTO"
    else:
        estado = "OK" if csv_valor == pbi_valor else "DISTINTO"
    print(f"{nombre:<40} CSV={csv_valor!s:<22} PowerBI={pbi_valor!s:<22} {estado}")


def main() -> None:
    carpeta = Path(sys.argv[1])
    refs = json.loads(REFERENCIAS.read_text(encoding="utf-8"))

    apps = leer(carpeta, "appearances", ["game_id", "player_id", "player_club_id", "date", "goals"])
    games = leer(carpeta, "games", ["game_id", "competition_id", "season", "home_club_goals",
                                    "away_club_goals", "attendance", "stadium"])
    players = leer(carpeta, "players", ["player_id", "name", "position", "market_value_in_eur"])
    clubs = leer(carpeta, "clubs", ["club_id", "name"])
    valuations = leer(carpeta, "player_valuations", ["player_id", "date", "market_value_in_eur"])

    print("=== Cifras sueltas ===")
    comparar("3  goles totales", int(apps["goals"].sum()), valor_powerbi(refs, "3", "[v]"))
    comparar("4  partidos en games", len(games), valor_powerbi(refs, "4", "[n]"))
    comparar("4  partidos con apariciones", int(apps["game_id"].nunique()),
             valor_powerbi(refs, "4_games_played", "[v]"))

    messi_ids = players.loc[players["name"] == "Lionel Messi", "player_id"]
    comparar("5  goles de Lionel Messi", int(apps.loc[apps["player_id"].isin(messi_ids), "goals"].sum()),
             valor_powerbi(refs, "5", "[v]"))

    comparar("6  asistencia media LaLiga (ES1)",
             float(games.loc[games["competition_id"] == "ES1", "attendance"].mean()),
             valor_powerbi(refs, "6", "[v]"))
    comparar("7  goles en casa", int(games["home_club_goals"].sum()), valor_powerbi(refs, "7", "[casa]"))
    comparar("7  goles fuera", int(games["away_club_goals"].sum()), valor_powerbi(refs, "7", "[fuera]"))
    comparar("8  asistencia media temporada 2022",
             float(games.loc[games["season"] == 2022, "attendance"].mean()),
             valor_powerbi(refs, "8", "[t2022]"))
    comparar("8  asistencia media temporada 2023",
             float(games.loc[games["season"] == 2023, "attendance"].mean()),
             valor_powerbi(refs, "8", "[t2023]"))

    anio_apps = pd.to_datetime(apps["date"], errors="coerce").dt.year
    comparar("12 goles en 2023", int(apps.loc[anio_apps == 2023, "goals"].sum()),
             valor_powerbi(refs, "12_dim_date", "[v]"))

    huerfanas = int((~apps["player_club_id"].isin(clubs["club_id"])).sum())
    comparar("13 apariciones sin club", huerfanas,
             valor_powerbi(refs, "13_huerfanas", "[apariciones_sin_club]"))

    print("\n=== Rankings y listas (comparar a ojo con el banco) ===")

    print("\n9  Top 10 goleadores")
    goleadores = apps.merge(players[["player_id", "name"]], on="player_id").groupby("name")["goals"].sum()
    print(goleadores.sort_values(ascending=False).head(10).to_string())

    print("\n10 Top 5 estadios por asistencia media")
    estadios = games.groupby("stadium")["attendance"].agg(["mean", "count"])
    print(estadios.sort_values("mean", ascending=False).head(5).round(0).to_string())

    print("\n11 Valor de mercado medio por año (primeros y últimos)")
    anio_val = pd.to_datetime(valuations["date"], errors="coerce").dt.year
    serie = valuations.groupby(anio_val)["market_value_in_eur"].mean().round(0)
    print(serie.head(3).to_string())
    print("...")
    print(serie.tail(5).to_string())

    print("\n13 Club con más jugadores distintos")
    por_club = apps.merge(clubs, left_on="player_club_id", right_on="club_id").groupby("name")["player_id"].nunique()
    print(por_club.sort_values(ascending=False).head(3).to_string())

    print("\n14 Posiciones")
    print(sorted(players["position"].dropna().unique()))

    print("\n15 Mayor valor de mercado actual")
    maximo = players["market_value_in_eur"].max()
    print(players.loc[players["market_value_in_eur"] == maximo, ["name", "market_value_in_eur"]].to_string(index=False))


if __name__ == "__main__":
    main()