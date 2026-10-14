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

def execute_query(dax_query: str) -> dict:
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
    return response.json()







