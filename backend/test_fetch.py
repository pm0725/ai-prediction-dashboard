import sys
import os
import asyncio
sys.path.append(os.getcwd())

from app.services.data_fetcher import DataFetcher

async def main():
    print("Testing DataFetcher...")
    try:
        fetcher = DataFetcher()
        # Mock exchange initialization if needed (DataFetcher does it lazily)
        klines = await fetcher.get_klines("ETHUSDT", "1d", limit=10)
        print(f"Success! Retrieved {len(klines)} klines.")
        if klines:
            print(f"First kline: {klines[0]}")
    except Exception as e:
        print(f"CRITICAL FAILURE: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
