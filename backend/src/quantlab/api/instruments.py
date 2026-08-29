from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from quantlab.api.dependencies import get_asset_service
from quantlab.errors import InstrumentNotFoundError
from quantlab.services.assets import AssetService

from quantlab.providers.base import normalize_code
from fastapi.responses import JSONResponse

router = APIRouter()


def _meta(asset_service: AssetService, cache_meta: dict | None = None) -> dict:
    return cache_meta or {
        "sources": asset_service.provider_names,
        "fetched_at": datetime.now(timezone.utc),
        "cache_hit": False,
        "warnings": [],
    }

@router.get("/api/instruments/search")
def search_instruments(q: str, asset_service: AssetService = Depends(get_asset_service)):
    results = asset_service.search(q)
    return {
        "data": [r.model_dump() for r in results],
        "meta": _meta(asset_service, asset_service.catalog_meta()),
    }


@router.get("/api/instruments/{code}/profile")
def get_profile(code: str, asset_service: AssetService = Depends(get_asset_service)):
    profile = asset_service.get_profile(code)
    return {
        "data": profile.model_dump(),
        "meta": _meta(asset_service, asset_service.profile_meta(code)),
    }

@router.get("/api/instruments/{code}")
def get_instrument(code: str, asset_service: AssetService = Depends(get_asset_service)):
    try:
        norm_code = normalize_code(code)
        instrument = asset_service.get_instrument(norm_code)
        return {
            "data": instrument.model_dump(),
            "meta": _meta(asset_service, asset_service.catalog_meta()),
        }
    except ValueError as e:
        return JSONResponse(status_code=422, content={"error": {"code": "INVALID_INSTRUMENT_CODE", "message": str(e)}})
    except InstrumentNotFoundError:
        raise

@router.get("/api/etf/{code}")
def get_etf_profile(code: str, asset_service: AssetService = Depends(get_asset_service)):
    profile = asset_service.get_profile(code)
    if profile.asset_type != "etf":
        return JSONResponse(status_code=400, content={"error": {"code": "INVALID_ASSET_TYPE", "message": "该证券不是 ETF"}})
    return {
        "data": profile.model_dump(),
        "meta": _meta(asset_service, asset_service.profile_meta(code)),
    }

@router.get("/api/equity/{code}")
def get_equity_profile(code: str, asset_service: AssetService = Depends(get_asset_service)):
    profile = asset_service.get_profile(code)
    if profile.asset_type != "equity":
        return JSONResponse(status_code=400, content={"error": {"code": "INVALID_ASSET_TYPE", "message": "该证券不是股票"}})
    return {
        "data": profile.model_dump(),
        "meta": _meta(asset_service, asset_service.profile_meta(code)),
    }
