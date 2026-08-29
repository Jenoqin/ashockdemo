from functools import lru_cache
import json
from pathlib import Path
from quantlab.config import get_settings
from quantlab.cache import MarketCache
from quantlab.providers.tushare_provider import TushareProvider
from quantlab.services.market_data import MarketDataService
from quantlab.services.assets import AssetService
from quantlab.services.backtest import BacktestService
import tushare as ts


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

@lru_cache
def get_market_cache() -> MarketCache:
    settings = get_settings()
    return MarketCache(settings.database_path)

@lru_cache
def get_tushare_provider():
    settings = get_settings()
    # Prefer a secret file so the token does not need to be duplicated in
    # project configuration. Keep the direct environment variable as the
    # alternative token source.
    token = _load_secret_file(settings.tushare_token_file) if settings.tushare_token_file else None
    if not token and settings.tushare_token:
        token = settings.tushare_token.strip()
    if token:
        client = ts.pro_api(token=token)
        client._DataApi__http_url = settings.tushare_api_url
        return TushareProvider(client, get_market_cache())
    # Keep a provider object with the stable Tushare dataset name so fully
    # covered SQLite ranges remain usable without a token. Any cache miss will
    # call the adapter and surface a normal Tushare configuration error.
    return TushareProvider(None, get_market_cache())

def get_market_data_service() -> MarketDataService:
    return MarketDataService(get_market_cache(), get_tushare_provider())

@lru_cache
def get_asset_service() -> AssetService:
    return AssetService(get_tushare_provider(), get_market_cache())

def get_backtest_service() -> BacktestService:
    return BacktestService()
