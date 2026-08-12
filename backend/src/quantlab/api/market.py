from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import date
from quantlab.api.dependencies import get_market_data_service, get_asset_service
from quantlab.services.market_data import MarketDataService
from quantlab.services.assets import AssetService
from quantlab.services.analytics import analyze_market

router = APIRouter()

@router.get("/api/market/{code}/daily")
def get_daily(
    code: str, 
    start: date = Query(...), 
    end: date = Query(...), 
    market_service: MarketDataService = Depends(get_market_data_service)
):
    if start > end:
        raise HTTPException(status_code=400, detail={"code": "INVALID_DATE_RANGE", "message": "Start date must be before end date"})
    
    try:
        result = market_service.get_daily(code, start, end)
        return {
            "data": [b.model_dump() for b in result.bars], 
            "meta": result.meta.model_dump()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/analysis/{code}")
def get_analysis(
    code: str, 
    start: date = Query(...), 
    end: date = Query(...),
    market_service: MarketDataService = Depends(get_market_data_service),
    asset_service: AssetService = Depends(get_asset_service)
):
    if start > end:
        raise HTTPException(status_code=400, detail={"code": "INVALID_DATE_RANGE", "message": "Start date must be before end date"})
    
    # Needs to get market bars, benchmark bars if any
    market_res = market_service.get_daily(code, start, end)
    profile = asset_service.get_profile(code)
    
    bench_bars = None
    if profile.asset_type == "etf" and profile.etf.tracking_index_code:
        try:
            bench_res = market_service.get_daily(profile.etf.tracking_index_code, start, end)
            bench_bars = bench_res.bars
        except Exception:
            pass

    analysis = analyze_market(market_res.bars, benchmark_bars=bench_bars)
    
    return {
        "data": analysis.model_dump(),
        "meta": market_res.meta.model_dump()
    }

@router.post("/api/data/{code}/refresh")
def refresh_data(
    code: str,
    market_service: MarketDataService = Depends(get_market_data_service)
):
    # Just do a typical refresh on recent history
    from datetime import timedelta
    today = date.today()
    try:
        market_service.get_daily(code, today - timedelta(days=60), today, refresh=True)
        return {"data": {"refreshed": True}, "meta": {}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
