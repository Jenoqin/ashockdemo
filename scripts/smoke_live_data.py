import sys
import os

# Add backend/src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend/src")))

from quantlab.api.dependencies import get_market_data_service
from datetime import date, timedelta
import asyncio

async def run_smoke():
    try:
        service = get_market_data_service()
        end = date.today()
        start = end - timedelta(days=5)
        
        print(f"Fetching 510300.SH from {start} to {end}...")
        result = service.get_daily("510300.SH", start, end)
        bars = result.bars
        if not bars:
            print("❌ Failed to fetch data")
            sys.exit(1)
        
        print(f"✅ Found {len(bars)} bars. Last bar: {bars[-1].close}")
        
        print("Smoke test passed.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("❌ Smoke test failed:", e)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_smoke())
