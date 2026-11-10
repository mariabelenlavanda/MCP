"""Ask one question to the local Power BI MCP through a LangGraph agent.

The MCP server must already be running. This script loads its tools and lets
the model call list, describe and query.

    uv run python ask.py "¿Qué tablas hay?"
"""

from __future__ import annotations

import asyncio
import os
import sys
import warnings

warnings.filterwarnings("ignore", message=".*create_react_agent.*")


from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent

load_dotenv()


def _server() -> dict:
    token = os.getenv("MCP_SHARED_TOKEN", "").strip()
    connection: dict = {
        "transport": "streamable_http",
        "url": os.getenv("MCP_URL", "http://127.0.0.1:8001/mcp"),
    }
    if token:
        connection["headers"] = {"Authorization": f"Bearer {token}"}
    return connection


def _model():
    provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()
    if provider == "gemini":
        if not (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")):
            raise SystemExit("Set GOOGLE_API_KEY in examples/langgraph_client/.env")
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            temperature=0,
        )
    if provider == "openai":
        if not os.getenv("OPENAI_API_KEY", "").strip():
            raise SystemExit("Set OPENAI_API_KEY in examples/langgraph_client/.env")
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            base_url=os.getenv("OPENAI_BASE_URL") or None,
            temperature=0,
        )
    raise SystemExit(f"LLM_PROVIDER must be openai or gemini, got {provider!r}")

TRACE_CHARS = 300  # caracteres que se enseñan de cada resultado


def _text(content) -> str:
    """Convierte el contenido de un mensaje en texto plano."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )
    return str(content)


def _print_trace(messages) -> None:
    steps: dict[str, int] = {}
    total_chars = 0
    for m in messages:
        for call in getattr(m, "tool_calls", None) or []:
            steps[call["id"]] = len(steps) + 1
            print(f"\n[{steps[call['id']]}] {call['name']}")
            print(f"    argumentos: {call['args']}")
        if getattr(m, "type", "") == "tool":
            text = _text(m.content)
            total_chars += len(text)
            shown = text[:TRACE_CHARS] + ("..." if len(text) > TRACE_CHARS else "")
            error = " ERROR" if getattr(m, "status", "") == "error" else ""
            print(f"    resultado [{steps.get(m.tool_call_id, '?')}]{error} ({len(text)} caracteres): {shown}")

    ruta = [c["name"] for m in messages for c in (getattr(m, "tool_calls", None) or [])]
    tokens = sum(
        (getattr(m, "usage_metadata", None) or {}).get("total_tokens", 0) for m in messages
    )
    print(f"\nRuta: {' -> '.join(ruta) or '(ninguna herramienta)'}")
    print(f"Caracteres devueltos por las herramientas: {total_chars}")
    print(f"Tokens totales del modelo: {tokens}")

async def main() -> int:
    question = " ".join(sys.argv[1:]).strip()
    if not question:
        print('Usage: uv run python ask.py "tu pregunta"', file=sys.stderr)
        return 2

    model = _model()
    client = MultiServerMCPClient({"powerbi": _server()})
    tools = await client.get_tools()
    agent = create_agent(
        model,
        tools,
        system_prompt=(
            "You answer with the Power BI MCP tools. "
            "Call list_available_tables, then describe_table_schema "
            "before writing DAX, then query_powerbi_dax. "
            "Never invent table or measure names."
        ),
    )
    result = await agent.ainvoke({"messages": [("user", question)]})
    _print_trace(result["messages"])
    print("\n=== RESPUESTA ===")
    print(_text(result["messages"][-1].content))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
