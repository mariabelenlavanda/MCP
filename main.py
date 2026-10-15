import uvicorn

from src import config
from src.mcp_server import create_app

app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,                # ¿qué constante de config?
        log_level="warning",
    )