"""Prueba el servidor MCP como lo haría un cliente MCP.

    tools/list
      -> list_available_tables
      -> describe_table_schema(<tabla>)
      -> query_powerbi_dax(DAX)

Uso:
    py tests/test_mcp.py http://127.0.0.1:8001/mcp
"""

import argparse
import asyncio
import json
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

DEFAULT_DAX = 'EVALUATE ROW("ok", 1)'


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prueba el servidor MCP.")
    parser.add_argument("url", help="Endpoint MCP, incluida la ruta /mcp.")
    parser.add_argument("--table", default="Medidas", help="Tabla a describir.")
    parser.add_argument("--dax", default=DEFAULT_DAX, help="Consulta DAX a ejecutar.")
    parser.add_argument("--measure", default="1. OTP 15", help="Medida a consultar.")
    return parser.parse_args()


def _print_result(title: str, result) -> None:
    print(f"\n=== {title} ===")
    if getattr(result, "isError", False):
        print("TOOL RETURNED AN ERROR:")
    for block in getattr(result, "content", []) or []:
        text = getattr(block, "text", None)
        try:
            text = json.dumps(json.loads(text), indent=2, ensure_ascii=False)
        except (TypeError, ValueError):
            pass
        print(text if text is not None else block)


async def _run(args: argparse.Namespace) -> int:
    async with streamablehttp_client(args.url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("=== tools/list ===")
            for tool in tools.tools:
                print(f"- {tool.name}: {tool.title}")

            _print_result(
                "list_available_tables",
                await session.call_tool("list_available_tables", {}),
            )
            _print_result(
                f"describe_table_schema({args.table})",
                await session.call_tool(
                    "describe_table_schema", {"table_name": args.table}
                ),
            )
            _print_result(
                "query_powerbi_dax",
                await session.call_tool("query_powerbi_dax", {"dax_query": args.dax}),
            )
            _print_result(
                "dax_measure",
                await session.call_tool("dax_measure", {"measure_name": args.measure}),
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_run(_arguments())))

#py tests/test_mcp.py http://127.0.0.1:8001/mcp --dax "EVALUATE ROW(\"otp\", [1. OTP 15])"