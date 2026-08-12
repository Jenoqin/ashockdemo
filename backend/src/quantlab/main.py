from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings
from .api import instruments, market, backtests
from .providers.base import ProviderError
from .errors import DataUnavailableError
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

    @app.exception_handler(DataUnavailableError)
    async def data_unavailable_handler(request: Request, exc: DataUnavailableError):
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "DATA_UNAVAILABLE",
                    "message": f"暂时无法获取 {exc.code} 的数据",
                    "action": "请稍后重试，或配置 TUSHARE_TOKEN 启用备用数据源"
                }
            }
        )

    app.include_router(instruments.router)
    app.include_router(market.router)
    app.include_router(backtests.router)

    return app

app = create_app()
