from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings

def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="QuantLab API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.get("/api/health")
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "service": "quantlab-api",
            "primary_provider": "akshare",
            "fallback_enabled": bool(settings.tushare_token),
        }

    return app

app = create_app()
