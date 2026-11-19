"""Lanza un banco de preguntas contra el agente y guarda los resultados en un CSV.

Cada pregunta se ejecuta varias veces. Por cada ejecución se guarda el tiempo
total, el tiempo que tardaron las herramientas, los tokens, la ruta de
herramientas y la respuesta. La columna "correcta" queda vacía para corregirla
a mano con el banco de preguntas.

IMPORTANTE: la vía (infoview o api) la decide el servidor con
POWERBI_SCHEMA_SOURCE en su .env. El argumento --via solo es una etiqueta para
el CSV: tiene que coincidir con lo que tenga el servidor arrancado.

Uso, desde la carpeta ejemplo y con el entorno (.venv) activado:
    python lanzar_banco.py --dataset transfermarkt --via infoview
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import time
from pathlib import Path

from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient

from ask import _model, _server, _text

# Debe ser idéntico al de ask.py para que las pruebas midan lo mismo.
SYSTEM_PROMPT = (
    "You answer with the Power BI MCP tools. "
    "Call list_available_tables, then describe_table_schema "
    "before writing DAX, then query_powerbi_dax. "
    "Never invent table or measure names."
)

CAMPOS = [
    "dataset", "via", "pregunta_id", "repeticion", "pregunta",
    "segundos_total", "segundos_herramientas", "segundos_describe",
    "n_llamadas", "ruta", "caracteres_herramientas",
    "tokens_entrada", "tokens_salida", "tokens_totales",
    "error", "respuesta", "correcta",
]

_tiempos: list[tuple[str, float]] = []


def _cronometrar(tool) -> None:
    """Envuelve una herramienta para medir cuánto tarda cada llamada."""
    original = tool.coroutine

    async def cronometrada(*args, **kwargs):
        inicio = time.perf_counter()
        try:
            return await original(*args, **kwargs)
        finally:
            _tiempos.append((tool.name, time.perf_counter() - inicio))

    tool.coroutine = cronometrada


def _resumen(messages) -> dict:
    ruta = [c["name"] for m in messages for c in (getattr(m, "tool_calls", None) or [])]
    caracteres = sum(len(_text(m.content)) for m in messages if getattr(m, "type", "") == "tool")
    uso = [getattr(m, "usage_metadata", None) or {} for m in messages]
    return {
        "n_llamadas": len(ruta),
        "ruta": " -> ".join(ruta),
        "caracteres_herramientas": caracteres,
        "tokens_entrada": sum(u.get("input_tokens", 0) for u in uso),
        "tokens_salida": sum(u.get("output_tokens", 0) for u in uso),
        "tokens_totales": sum(u.get("total_tokens", 0) for u in uso),
        "respuesta": _text(messages[-1].content),
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--via", required=True, choices=["infoview", "api"])
    parser.add_argument("--preguntas", default=None, help="JSON con las preguntas")
    parser.add_argument("--repeticiones", type=int, default=3)
    parser.add_argument("--pausa", type=float, default=5, help="segundos entre preguntas")
    parser.add_argument("--solo", type=int, nargs="*", help="ids de pregunta a lanzar")
    args = parser.parse_args()

    preguntas = json.loads(
        Path(args.preguntas or f"preguntas_{args.dataset}.json").read_text(encoding="utf-8")
    )
    if args.solo:
        preguntas = [p for p in preguntas if p["id"] in args.solo]

    salida = Path(f"resultados_{args.dataset}_{args.via}.csv")
    nuevo = not salida.exists()

    client = MultiServerMCPClient({"powerbi": _server()})
    tools = await client.get_tools()
    for tool in tools:
        _cronometrar(tool)
    agent = create_agent(_model(), tools, system_prompt=SYSTEM_PROMPT)

    with salida.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CAMPOS)
        if nuevo:
            writer.writeheader()

        for rep in range(1, args.repeticiones + 1):
            for p in preguntas:
                _tiempos.clear()
                fila = {
                    "dataset": args.dataset, "via": args.via,
                    "pregunta_id": p["id"], "repeticion": rep, "pregunta": p["pregunta"],
                    "error": "", "correcta": "",
                }
                inicio = time.perf_counter()
                try:
                    result = await agent.ainvoke(
                        {"messages": [("user", p["pregunta"])]},
                        config={"recursion_limit": 25},
                    )
                    fila.update(_resumen(result["messages"]))
                except Exception as exc:
                    fila["error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
                fila["segundos_total"] = round(time.perf_counter() - inicio, 2)
                fila["segundos_herramientas"] = round(sum(t for _, t in _tiempos), 2)
                fila["segundos_describe"] = round(
                    sum(t for n, t in _tiempos if n == "describe_table_schema"), 2
                )
                writer.writerow(fila)
                f.flush()

                estado = "ERROR" if fila["error"] else "ok"
                print(f"[rep {rep}] pregunta {p['id']:>2}: {estado} "
                      f"({fila['segundos_total']} s, {fila.get('tokens_totales', 0)} tokens)")
                await asyncio.sleep(args.pausa)

    print(f"\nResultados en {salida}")


if __name__ == "__main__":
    asyncio.run(main())
