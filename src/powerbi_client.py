#este es el archivo que va a hablar con PowerBI

import time

import httpx



import msal

from src import config
from src.powerbi_definition import parse_semantic_model_definition

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
def _get_schema() -> dict:
    return parse_semantic_model_definition(get_model_definition())

def list_tables() -> list[dict]:
    schema = _get_schema()
    tables = []
    for t in schema["tables"]:               
        tables.append({
            "name": t["name"],
            "description": t.get("description"),
        })
    return tables

"""
“El repo original obtiene el esquema con la API de Fabric, que exige permisos de escritura sobre el modelo. 
Probé alternativas y INFO.VIEW.* funciona con permisos de solo lectura, así que lo sustituí por consultas DAX y 
mantuve el formato de salida del original.”
"""

def describe_table(table_name: str) -> dict:
    schema = _get_schema()

    table = None
    for t in schema["tables"]:
        if t["name"] == table_name:
            table = t
    if table is None:
        raise RuntimeError(
            f"La tabla '{table_name}' no existe. Usa list_available_tables."
        )

    measures = []
    for m in schema["measures"]:
        if m["table"] == table_name:       
            measures.append(m)

    relationships = []
    for r in schema["relationships"]:
        if r["from"].startswith(f"{table_name}[") or r["to"].startswith(f"{table_name}["):
            relationships.append(r)

    return {
        "table": table_name,
        "columns": table["columns"],
        "measures": measures,
        "relationships": relationships,
    }

