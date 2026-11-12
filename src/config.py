#vamos a crear una configuración que esté centrada en un solo archivo

import os
from dotenv import load_dotenv
load_dotenv()

def _required(name: str) -> str: #basada en la funcion de powerbi.py llamada required_env
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Variable missinsg {name}") #preguntar la diferencia entre 
    return value

TENANT_ID = _required("POWERBI_TENANT_ID")
CLIENT_ID =  _required("POWERBI_CLIENT_ID")
CLIENT_SECRET = _required("POWERBI_CLIENT_SECRET")
WORKSPACE_ID = _required("POWERBI_WORKSPACE_ID")
DATASET_ID = _required("POWERBI_DATASET_ID")
#REPORT_ID = _required("POWERBI_TEST_REPORT_ID") #preguntar si sobra ya que sirve solo para leer la definición del informe con la API


HOST = os.environ.get("HOST", "127.0.0.1")       
PORT = int(os.environ.get("PORT", "8001"))   #preguntar si hace falta poner lo de entero para que lea un numero y no sea un texto             
HTTP_TIMEOUT_SECONDS = float(os.environ.get("POWERBI_HTTP_TIMEOUT_SECONDS", "60"))
RESULT_MAX_ROWS = int(os.environ.get("POWERBI_RESULT_MAX_ROWS", "1000"))

#PREGUNTAR SI LO DE HOST, PORT,ETC SE PUEDE COGER COMO LOS DE TENANT ID CON LA FUNCION REQUIRED YA QUE ESTÁ EN .env O SI TENGO QUE COGERLO ASÍ