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
        Field(description="Una consulta DAX de solo lectura con una sentencia EVALUATE."),
    ],
) -> str:
    """Ejecuta una consulta DAX contra el modelo semántico configurado."""
    result = powerbi_client.execute_query(dax_query)     
    return _dumps(result)

#py -c "from src.mcp_server import query_powerbi_dax; print(query_powerbi_dax('EVALUATE ROW(\"ok\", 1)'))"

@mcp.tool(title="List available Power BI tables", annotations=_READ_ONLY)
def list_available_tables() -> str:
    """Lista las tablas del modelo semántico de Power BI con su descripción.

    Es el primer paso: llámala antes de escribir cualquier consulta DAX.
    Después usa describe_table_schema con la tabla que te interese.
    """
    return _dumps(powerbi_client.list_tables())      
    

@mcp.tool(title="Describe Power BI table", annotations=_READ_ONLY)
def describe_table_schema(
    table_name: Annotated[
        str,
        Field(description="Nombre de una tabla devuelto por list_available_tables."),
    ],
) -> str:
    """Devuelve las columnas (nombre, tipo, descripción) y las medidas de una tabla.

    Usa solo los nombres que aparecen aquí al escribir el DAX. Las medidas se
    escriben entre corchetes, por ejemplo [Nombre de la medida].
    """
    return _dumps(powerbi_client.describe_table(table_name))     

# py -c "from src.mcp_server import list_available_tables; print(list_available_tables())"
# py -c "from src.mcp_server import describe_table_schema; print(describe_table_schema('Medidas'))"