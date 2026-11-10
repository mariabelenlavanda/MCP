# EST EES EL TRADUCTIR ENTRE EL CLIENTE MCP Y POWERBI_CLIENT.PY
#Cliente  →  mcp_server.py (3 herramientas)  →  powerbi_client.py  →  Power BI
# las herramientas son las que hay en el powerbi_client y son: lis_tables(), describe_table(),execute_query()
#en el mcp_server se llamaran: list_avalilable_tables, describe_table_schema(table_name), query_powerbi_dax(dax_query)
# FUNCOINES QUE TIENE EL MCP:
#mcp = FastMCP("Power BI MCP")-->Esto crea el servidor	Lo he adaptado de create_app() 
# _READ_ONLY (ToolAnnotations)-->Aquí avisa al cliente de que las herramientas solo leen/ viene de  _READ_ONLY_QUERY_ANNOTATIONS 
# _dumps(value)-->Convierte el resultado a JSON/ esta adaptado de dumps_json
# list_available_tables()--> Llama a list_tables()/ esta adaptado de list_available_pbi_dashboards
# describe_table_schema(table_name)-->Llama a describe_table(...)/ esta adaptado dedescribe_pbi_dashboard
# query_powerbi_dax(dax_query)	Llama a execute_query(...)/ esta adaptado dequery_pbi_dashboard
# Ruta /health y arranque con uvicorn--> Para ejecutarlo como servidor/ esta adaptado de _health_handler y main.py
# CADA HERRAMIENTA HACE TRES COSAS, RECIBE EL ARGUMENTO, LLAMA AL CLIENTE Y DEVUELVE _DUMPS(RESULTADO)
# Cada @mcp.tool también necesita una descripción, que dice cuándo usar la herramienta, y un Field(description=...) por argumento. 
# Los consejos que el original incluye para el DAX (agregar los resultados, usar TOPN, usar solo nombres que existan en el esquema) 
# salen de _dashboard_query_usage en catalog.py.
import json
from typing import Annotated, Any
import logging

logging.getLogger("httpx").setLevel(logging.WARNING)

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field
from starlette.requests import Request 
from starlette.responses import JSONResponse, Response
from starlette.routing import Route



from src import powerbi_client

_READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)

mcp = FastMCP("Power BI MCP")


def _dumps(value: Any) -> str:
    return json.dumps(value, default=str, ensure_ascii=False)


@mcp.tool(title="Query Power BI with DAX", annotations=_READ_ONLY)
def query_powerbi_dax(
    dax_query: Annotated[
        str,
        Field(description="One read-only DAX query with a single EVALUATE statement."),
    ],
) -> str:
    """Run a read-only DAX query against the semantic model.

    Use the model's measures whenever one exists for what is asked, and do not
    recalculate their logic from columns. Measures are written in square
    brackets and can be grouped or filtered, for example:
    EVALUATE SUMMARIZECOLUMNS(Table[column], "name", [Measure]).
    Use only tables, columns and measures returned by describe_table_schema.
    Aggregate results, and use TOPN if you return detail rows.
    """
    result = powerbi_client.execute_query(dax_query)
    return _dumps(result)

#py -c "from src.mcp_server import query_powerbi_dax; print(query_powerbi_dax('EVALUATE ROW(\"ok\", 1)'))"

@mcp.tool(title="List available Power BI tables", annotations=_READ_ONLY)
def list_available_tables() -> str:
    """List the tables of the Power BI semantic model with their descriptions.

    This is the first step. If a table contains measures (indicators that are
    already calculated), also describe it with describe_table_schema before
    writing any query, so you can use those measures instead of recalculating
    their logic.
    """
    return _dumps(powerbi_client.list_tables())      
    

@mcp.tool(title="Describe Power BI table", annotations=_READ_ONLY)
def describe_table_schema(
    table_name: Annotated[
        str,
        Field(description="Name of a table returned by list_available_tables."),
    ],
) -> str:
    """Return the columns (name, type, description), the measures and the relationships of a table.

    Relationships show which other tables it joins to and their cardinality
    (One or Many). Use it to learn how tables connect before writing a DAX
    query that spans several of them. Use only the names returned here when
    writing DAX. Measures are written in square brackets, for example
    [Measure name].
    """
    return _dumps(powerbi_client.describe_table(table_name))

@mcp.tool(title="Get the DAX of a Power BI measure", annotations=_READ_ONLY)
def dax_measure(
    measure_name: Annotated[
        str,
        Field(description="Exact name of a measure returned by describe_table_schema."),
    ],
) -> str:
    """Return the DAX formula that defines a measure of the model.

    Use it when asked how an indicator is calculated, or to understand which
    filters a measure applies before writing another query.
    """
    return _dumps(powerbi_client.get_measure_dax(measure_name))   


############ VAMOS CON LA TERCERA CAPA: LAS HERRAMIENTAS YA LAS TENEMOS EN PYTHON Y AHORA FALTA QUE SE PUBLIQUEN
# POR HTTP PARA QUE EL CLIENTE MCP SE PUEDA CONECTAR ###################


async def _health_handler(request: Request) -> JSONResponse | Response:
    if request.method == "HEAD":
        return Response(status_code=200)
    return JSONResponse({"status": "ok"})


def create_app():
    app = mcp.streamable_http_app()
    app.routes.insert(0, Route("/health", _health_handler, methods=["GET", "HEAD"]))
    return app

