#este es el archivo que va a hablar con PowerBI

import httpx
import msal

from src import config

##################################### PRIMERO VAMOS A COGER EL TOKEN DE CADA PERSONA #############################################
# Esta función hay que adoptarla para que funcione con lo que tenemos nosotros en el config

POWERBI_APP_SCOPES = ["https://analysis.windows.net/powerbi/api/.default"]
POWERBI_API_ROOT = "https://api.powerbi.com/v1.0/myorg"

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