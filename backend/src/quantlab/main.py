from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings
from .api import instruments, market, backtests
from .providers.base import ProviderError
from .errors import DataUnavailableError, InstrumentNotFoundError
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
            "provider": "Tushare Pro",
        }

    @app.exception_handler(DataUnavailableError)
    async def data_unavailable_handler(request: Request, exc: DataUnavailableError):
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "DATA_UNAVAILABLE",
                    "message": f"暂时无法获取 {exc.code} 的数据",
                    "action": "请检查 Tushare Pro 配置后重试"
                }
            }
        )

    @app.exception_handler(InstrumentNotFoundError)
    async def instrument_not_found_handler(request: Request, exc: InstrumentNotFoundError):
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "INSTRUMENT_NOT_FOUND",
                    "message": str(exc),
                    "action": "请从搜索结果中选择有效的 A 股或 ETF",
                }
            },
        )

    @app.exception_handler(ProviderError)
    async def provider_error_handler(request: Request, exc: ProviderError):
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "PROVIDER_UNAVAILABLE",
                    "message": "证券数据源暂时不可用",
                    "action": "请稍后重试",
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(
        request: Request,
        exc: RequestValidationError,
    ):
        if request.url.path == "/api/backtests/ma-cross":
            return JSONResponse(
                status_code=422,
                content={
                    "error": {
                        "code": "INVALID_BACKTEST_PARAMETERS",
                        "message": "回测参数无效",
                    }
                },
            )
        return await request_validation_exception_handler(request, exc)

    app.include_router(instruments.router)
    app.include_router(market.router)
    app.include_router(backtests.router)

    return app

app = create_app()
