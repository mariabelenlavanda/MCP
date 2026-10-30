#este es el archivo que va a hablar con PowerBI

import time
import httpx
import msal

from src import config
from src.powerbi_definition import  measure_expressions

##################################### PRIMERO VAMOS A COGER EL TOKEN DE CADA PERSONA #############################################
# Esta función hay que adoptarla para que funcione con lo que tenemos nosotros en el config

POWERBI_APP_SCOPES = ["https://analysis.windows.net/powerbi/api/.default"]
POWERBI_API_ROOT = "https://api.powerbi.com/v1.0/myorg"

#conexion API
FABRIC_API_ROOT = "https://api.fabric.microsoft.com/v1"
FABRIC_APP_SCOPES = ["https://api.fabric.microsoft.com/.default"]

_app = msal.ConfidentialClientApplication(
    client_id=config.CLIENT_ID,
    client_credential=config.CLIENT_SECRET,
    authority=f"https://login.microsoftonline.com/{config.TENANT_ID}",
)
_http = httpx.Client(timeout=config.HTTP_TIMEOUT_SECONDS)


def _token_or_raise(result: dict) -> str:
    token = result.get("access_token")
    if token:
        return token
    code = result.get("error", "token_error")
    description = result.get("error_description", "No error description returned.")
    raise RuntimeError(f"Falló la autenticación ({code}): {description}")


def get_access_token() -> str:
    result = _app.acquire_token_for_client(scopes=POWERBI_APP_SCOPES)
    return _token_or_raise(result)

def get_fabric_access_token() -> str:
    result = _app.acquire_token_for_client(scopes=FABRIC_APP_SCOPES)
    return _token_or_raise(result)


def get_model_definition_raw(format: str = "TMSL") -> httpx.Response:
    token = get_fabric_access_token()
    url = (
        f"{FABRIC_API_ROOT}/workspaces/{config.WORKSPACE_ID}"
        f"/semanticModels/{config.DATASET_ID}/getDefinition"
    )
    return _http.post(
        url,
        headers={"Authorization": f"Bearer {token}"},
        params={"format": format},
    )

def get_measure_dax(measure_name: str) -> dict:
    for m in measure_expressions(get_model_definition()):
        if m["name"] == measure_name:
            return m
    raise RuntimeError(
        f"La medida '{measure_name}' no existe. "
        "Usa describe_table_schema con la tabla que contiene las medidas."
    )

_LRO_SLEEP_CAP_SECONDS = 5


def _retry_after_seconds(response: httpx.Response) -> float:
    raw = response.headers.get("Retry-After")
    try:
        seconds = float(raw) if raw is not None else 0.0
    except ValueError:
        seconds = 1.0
    if seconds <= 0:
        return 0.0
    return min(seconds, _LRO_SLEEP_CAP_SECONDS)


def _fabric_get(url: str) -> httpx.Response:
    token = get_fabric_access_token()
    return _http.get(url, headers={"Authorization": f"Bearer {token}"})


def get_model_definition(format: str = "TMSL") -> dict:
    response = get_model_definition_raw(format)
    if response.status_code == 200:
        return response.json()
    if response.status_code != 202:
        raise RuntimeError(
            f"Fabric devolvió HTTP {response.status_code}: {response.text[:500]}"
        )

    operation_id = response.headers.get("x-ms-operation-id", "").strip()
    retry_after = _retry_after_seconds(response)
    deadline = time.monotonic() + config.HTTP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if retry_after:
            time.sleep(retry_after)
        state_response = _fabric_get(f"{FABRIC_API_ROOT}/operations/{operation_id}")
        if state_response.is_error:
            raise RuntimeError(
                f"Fabric devolvió HTTP {state_response.status_code}: {state_response.text[:500]}"
            )
        status = state_response.json().get("status")
        if status == "Succeeded":                    
            result = _fabric_get(f"{FABRIC_API_ROOT}/operations/{operation_id}/result")
            if result.is_error:
                raise RuntimeError(
                    f"Fabric devolvió HTTP {result.status_code}: {result.text[:500]}"
                )
            return result.json()
        if status in {"Failed", "Cancelled"}:
            raise RuntimeError(f"Fabric: la operación terminó como {status}: {state_response.text[:500]}")
        retry_after = _retry_after_seconds(state_response) or 1
    raise RuntimeError("Tiempo agotado esperando a Fabric.")

###################################### SEGUNDO PASO PARA PODER VER LAS CONSULTAS ################################################

## Ahora vamos a limpiar la respuesta que nos da
def _normalize_result(payload: dict) -> dict:
    results = payload.get("results")
    if not isinstance(results, list) or not results:
        raise RuntimeError("Power BI no devolvió resultados.")

    first_result = results[0]
    if first_result.get("error"):
        raise RuntimeError(f"La consulta DAX falló: {first_result['error']}")

    tables = first_result.get("tables") or []
    if not tables:
        return {"rows": [], "row_count": 0, "truncated": False}

    rows = tables[0].get("rows") or []
    truncated = len(rows) > config.RESULT_MAX_ROWS        
    return {
        "rows": rows[:config.RESULT_MAX_ROWS],             
        "row_count": min(len(rows), config.RESULT_MAX_ROWS),               
        "truncated": truncated,
    }


def execute_query(dax_query: str) -> dict:
    dax_query = dax_query.strip() #comprobación de si es un query correctamente formado
    if not dax_query:
        raise RuntimeError("dax_query es obligatorio.")
    if "EVALUATE" not in dax_query.upper():
        raise RuntimeError("dax_query debe contener una sentencia EVALUATE.")

    token = get_access_token()
    url = (
        f"{POWERBI_API_ROOT}/groups/{config.WORKSPACE_ID}"
        f"/datasets/{config.DATASET_ID}/executeQueries"
    )
    response = _http.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "queries": [{"query": dax_query}],
            "serializerSettings": {"includeNulls": True},
        },
    )
    if response.is_error:
        raise RuntimeError(
            f"Power BI devolvió HTTP {response.status_code}: {response.text[:500]}"
        )
    return _normalize_result(response.json())

############ VER LA LISTA DE LAS TABLAS #######################


def list_tables() -> list[dict]:
    result = execute_query("EVALUATE INFO.VIEW.TABLES()")
    tables = []
    for row in result["rows"]:
        if row["[IsHidden]"]:
            continue
        tables.append({
            "name": row["[Name]"],
            "description": row.get("[Description]"),
        })
    return tables


def describe_table(table_name: str) -> dict:
    columns_result = execute_query("EVALUATE INFO.VIEW.COLUMNS()")
    measures_result = execute_query("EVALUATE INFO.VIEW.MEASURES()")

    columns = []
    for row in columns_result["rows"]:
        if row["[Table]"] != table_name or row["[IsHidden]"]:
            continue
        columns.append({
            "name": row["[Name]"],
            "data_type": row["[DataType]"],
            "description": row.get("[Description]"),
        })

    measures = []
    for row in measures_result["rows"]:
        if row["[Table]"] != table_name or row["[IsHidden]"]:
            continue
        measures.append({
            "name": row["[Name]"],
            "data_type": row["[DataType]"],
            "description": row.get("[Description]"),
        })

    relationships_result = execute_query("EVALUATE INFO.VIEW.RELATIONSHIPS()")
    relationships = []
    for row in relationships_result["rows"]:
        if not row["[IsActive]"]:
            continue
        if row["[FromTable]"] != table_name and row["[ToTable]"] != table_name:
            continue
        relationships.append({
            "from": f"{row['[FromTable]']}[{row['[FromColumn]']}]",
            "to": f"{row['[ToTable]']}[{row['[ToColumn]']}]",
            "from_cardinality": row["[FromCardinality]"],
            "to_cardinality": row["[ToCardinality]"],
        })

    if not columns and not measures:
        raise RuntimeError(
            f"La tabla '{table_name}' no existe o no tiene columnas ni medidas visibles. "
            "Usa list_available_tables."
        )

    return {
        "table": table_name,
        "columns": columns,
        "measures": measures,
        "relationships": relationships,
    }
