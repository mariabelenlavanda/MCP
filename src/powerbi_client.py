#este es el archivo que va a hablar con PowerBI
import msal
from src import config

###### PRIMERO VAMOS A COGER EL TOKEN DE CADA PERSONA
####ESta función hay que adoptarla para que funcione con lo que tenemos nosotros en el config

import msal
from src import config

POWERBI_APP_SCOPES = ["https://analysis.windows.net/powerbi/api/.default"]

_app = msal.ConfidentialClientApplication(
    client_id=config.CLIENT_ID,
    client_credential=config.CLIENT_SECRET,
    authority=f"https://login.microsoftonline.com/{config.TENANT_ID}",
)


def _token_or_raise(result: dict) -> str:
    token = result.get("access_token")
    if token:
        return token
    code = result.get("error", "token_error")        
    description = result.get("error_description", "No error description returned.")   
    raise RuntimeError(f"{operation} failed ({code}): {description}.{suffix}")       


def get_access_token() -> str:
    result = _app.acquire_token_for_client(scopes=POWERBI_APP_SCOPES)
    return _token_or_raise(result)
    

