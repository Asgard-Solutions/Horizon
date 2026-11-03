"""ASGI entry point (used by `uvicorn server:app`)."""
from mediacenter.app import create_app

app = create_app()
