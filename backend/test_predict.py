import asyncio
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.getcwd())
load_dotenv()

from app.engines.deepseek_analyst import DeepSeekAnalyst

async def main():
    print("Testing DeepSeekAnalyst Pipeline...")
    
    # Check Env
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        print("Error: DEEPSEEK_API_KEY not found.")
        return

    print(f"DeepSeek Key found: {key[:4]}***")
    
    analyst = DeepSeekAnalyst(timeout=60.0) # Short timeout for test
    
    # Mock Context
    context = {
        "kline_summary": "ETH price is 3000 USDT. Trend is bullish. RSI is 60.",
        "current_price": 3000.0,
        "funding_rate": 0.0001,
        "news_headlines": ["ETH Upgrade coming"]
    }
    
    try:
        print("Sending request to DeepSeek (may utilize R1 or V3)...")
        # Force a model if needed, or let it use default
        # If env DEEPSEEK_MODEL is set.
        
        result = await analyst.analyze_market("ETHUSDT", context)
        print("\n>>> Analysis Success! <<<")
        print(f"Model Used: {result.ai_model}")
        print(f"Prediction: {result.prediction}")
        print(f"Confidence: {result.confidence}")
        
    except Exception as e:
        print(f"\n>>> Analyze Failed: {e} <<<")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
