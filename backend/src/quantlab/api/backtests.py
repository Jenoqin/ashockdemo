from fastapi import APIRouter, Depends, HTTPException
from quantlab.models import BacktestRequest
from quantlab.api.dependencies import get_backtest_service, get_market_data_service
from quantlab.services.backtest import BacktestService, run_ma_cross
from quantlab.services.market_data import MarketDataService
from datetime import date

from fastapi.responses import JSONResponse

router = APIRouter()

@router.post("/api/backtests/ma-cross")
def api_run_ma_cross(
    request: BacktestRequest,
    market_service: MarketDataService = Depends(get_market_data_service)
):
    if request.fast_window >= request.slow_window:
        return JSONResponse(status_code=422, content={"error": {"code": "INVALID_BACKTEST_PARAMETERS", "message": "fast window must be less than slow window"}})
    
    start_date = request.start or date(2000, 1, 1)
    end_date = request.end or date.today()
    if start_date > end_date:
        return JSONResponse(status_code=422, content={"error": {"code": "INVALID_BACKTEST_PARAMETERS", "message": "start > end"}})

    try:
        market_res = market_service.get_daily(request.code, start_date, end_date)
        if len(market_res.bars) < request.slow_window:
            return JSONResponse(status_code=422, content={"error": {"code": "INVALID_BACKTEST_PARAMETERS", "message": "not enough bars"}})
            
        result = run_ma_cross(request, market_res.bars)
        return {"data": result.model_dump(), "meta": {}}
    except ValueError as e:
        return JSONResponse(status_code=422, content={"error": {"code": "INVALID_BACKTEST_PARAMETERS", "message": str(e)}})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
