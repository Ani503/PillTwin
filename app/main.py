# Proxy app entrypoint to support `uvicorn app.main:app`
from api.main import app

__all__ = ["app"]
