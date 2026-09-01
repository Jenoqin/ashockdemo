from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import date, timedelta
from quantlab.api.dependencies import get_market_data_service, get_asset_service
from quantlab.services.market_data import MarketDataService
from quantlab.services.assets import AssetService
from quantlab.services.analytics import analyze_market

router = APIRouter()

ANALYSIS_LOOKBACK_DAYS = 120


def _research_payload(
    code: str,
    start: date,
    end: date,
    market_service: MarketDataService,
    asset_service: AssetService,
):
    instrument, instrument_meta = asset_service.get_instrument_with_meta(code)

    # A single history read supplies both the selected chart range and the
    # lookback needed to warm rolling indicators.
    history_start = start - timedelta(days=ANALYSIS_LOOKBACK_DAYS)
    history_res = market_service.get_daily(code, history_start, end)
    market_bars = [
        bar for bar in history_res.bars if start <= bar.trade_date <= end
    ]

    benchmark_bars = None
    warnings = list(instrument_meta.get("warnings", []))
    warnings.extend(history_res.meta.warnings)
    if instrument.asset_type == "etf":
        try:
            benchmark_code = asset_service.get_tracking_index_code(code)
            if benchmark_code:
                benchmark_res = market_service.get_index_daily(
                    benchmark_code, start, end
                )
                benchmark_bars = benchmark_res.bars
                warnings.extend(benchmark_res.meta.warnings)
        except Exception:
            # The asset analysis remains usable, but the API makes the missing
            # benchmark explicit instead of silently returning partial output.
            warnings.append("BENCHMARK_UNAVAILABLE")

    analysis = analyze_market(
        market_bars,
        benchmark_bars=benchmark_bars,
        history_bars=history_res.bars,
    )
    meta = history_res.meta.model_copy(
        update={"warnings": list(dict.fromkeys(warnings))}
    )
    return {
        "data": {
            "instrument": instrument.model_dump(),
            "market": [bar.model_dump() for bar in market_bars],
            "analysis": analysis.model_dump(),
        },
        "meta": meta.model_dump(),
    }

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
    
    result = _research_payload(
        code, start, end, market_service, asset_service
    )
    return {"data": result["data"]["analysis"], "meta": result["meta"]}


@router.get("/api/research/{code}")
def get_research(
    code: str,
    start: date = Query(...),
    end: date = Query(...),
    market_service: MarketDataService = Depends(get_market_data_service),
    asset_service: AssetService = Depends(get_asset_service),
):
    if start > end:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_DATE_RANGE",
                "message": "Start date must be before end date",
            },
        )
    return _research_payload(code, start, end, market_service, asset_service)

@router.post("/api/data/{code}/refresh")
def refresh_data(
    code: str,
    market_service: MarketDataService = Depends(get_market_data_service)
):
    # Just do a typical refresh on recent history
    today = date.today()
    try:
        market_service.get_daily(code, today - timedelta(days=60), today, refresh=True)
        return {"data": {"refreshed": True}, "meta": {}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
