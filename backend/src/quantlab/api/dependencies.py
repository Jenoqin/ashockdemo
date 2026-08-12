from quantlab.config import get_settings
from quantlab.cache import MarketCache
from quantlab.providers.akshare_provider import AkShareProvider
from quantlab.providers.tushare_provider import TushareProvider
from quantlab.services.market_data import MarketDataService
from quantlab.services.assets import AssetService
from quantlab.services.backtest import BacktestService
import akshare as ak
import tushare as ts

def get_market_cache() -> MarketCache:
    settings = get_settings()
    return MarketCache(settings.database_path)

def get_akshare_provider() -> AkShareProvider:
    return AkShareProvider(ak)

def get_tushare_provider() -> TushareProvider | None:
    settings = get_settings()
    if settings.tushare_token:
        ts.set_token(settings.tushare_token)
        return TushareProvider(ts.pro_api())
    return None

def get_market_data_service() -> MarketDataService:
    return MarketDataService(get_market_cache(), get_akshare_provider(), get_tushare_provider())

def get_asset_service() -> AssetService:
    return AssetService(get_akshare_provider())

def get_backtest_service() -> BacktestService:
    return BacktestService()
