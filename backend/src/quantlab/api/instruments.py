from fastapi import APIRouter, Depends, HTTPException
from typing import Any
from quantlab.api.dependencies import get_asset_service
from quantlab.services.assets import AssetService

from quantlab.providers.base import normalize_code
from fastapi.responses import JSONResponse

router = APIRouter()

@router.get("/api/instruments/search")
def search_instruments(q: str, asset_service: AssetService = Depends(get_asset_service)):
    try:
        results = asset_service.provider.search(q)
        return {"data": [r.model_dump() for r in results], "meta": {}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/instruments/{code}")
def get_instrument(code: str, asset_service: AssetService = Depends(get_asset_service)):
    try:
        norm_code = normalize_code(code)
        instrument = asset_service.provider.get_instrument(norm_code)
        return {"data": instrument.model_dump(), "meta": {}}
    except ValueError as e:
        return JSONResponse(status_code=422, content={"error": {"code": "INVALID_INSTRUMENT_CODE", "message": str(e)}})
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/api/etf/{code}")
def get_etf_profile(code: str, asset_service: AssetService = Depends(get_asset_service)):
    profile = asset_service.get_profile(code)
    if profile.asset_type != "etf":
        raise HTTPException(status_code=400, detail={"code": "INVALID_ASSET_TYPE", "message": "Not an ETF"})
    return {"data": profile.model_dump(), "meta": {}}

@router.get("/api/equity/{code}")
def get_equity_profile(code: str, asset_service: AssetService = Depends(get_asset_service)):
    profile = asset_service.get_profile(code)
    if profile.asset_type != "equity":
        raise HTTPException(status_code=400, detail={"code": "INVALID_ASSET_TYPE", "message": "Not an equity"})
    return {"data": profile.model_dump(), "meta": {}}
