from functools import lru_cache
import json
from pathlib import Path
from quantlab.config import get_settings
from quantlab.cache import MarketCache
from quantlab.providers.akshare_provider import AkShareProvider
from quantlab.providers.tushare_provider import TushareProvider
from quantlab.services.market_data import MarketDataService
from quantlab.services.assets import AssetService
from quantlab.services.backtest import BacktestService
import akshare as ak
import tushare as ts

from quantlab.providers.demo_provider import DemoProvider


def _load_secret_file(path: str) -> str | None:
    """Read a token from a bare, dotenv-style, or JSON secret file."""
    try:
        text = Path(path).expanduser().read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not text:
        return None
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            for key in ("TUSHARE_TOKEN", "tushare_token", "token"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
    except json.JSONDecodeError:
        pass
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").strip()
        key, separator, value = line.partition("=")
        if not separator:
            key, separator, value = line.partition(":")
        if separator and key.strip().upper() in {"TUSHARE_TOKEN", "TOKEN"}:
            return value.strip().strip("\"'") or None
    if "\n" not in text and "=" not in text:
        return text.strip().strip("\"'") or None
    return None

def get_market_cache() -> MarketCache:
    settings = get_settings()
    database_path = settings.demo_database_path if settings.demo_mode else settings.database_path
    return MarketCache(database_path)

@lru_cache
def get_akshare_provider():
    settings = get_settings()
    if settings.demo_mode:
        return DemoProvider()
    return AkShareProvider(ak)

@lru_cache
def get_tushare_provider():
    settings = get_settings()
    if settings.demo_mode:
        return None
    # Prefer a secret file so the token does not need to be duplicated in
    # project configuration. Keep the direct environment variable as fallback.
    token = _load_secret_file(settings.tushare_token_file) if settings.tushare_token_file else None
    if not token and settings.tushare_token:
        token = settings.tushare_token.strip()
    if token:
        client = ts.pro_api(token=token)
        client._DataApi__http_url = settings.tushare_api_url
        return TushareProvider(client)
    return None

def get_market_data_service() -> MarketDataService:
    # Both adapters expose stable hfq prices before entering the shared cache.
    return MarketDataService(get_market_cache(), get_akshare_provider(), get_tushare_provider())

@lru_cache
def get_asset_service() -> AssetService:
    return AssetService(get_akshare_provider(), get_tushare_provider())

def get_backtest_service() -> BacktestService:
    return BacktestService()
