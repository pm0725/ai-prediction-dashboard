
import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.engines.deepseek_analyst import DeepSeekAnalyst
from app.services.data_aggregator import prepare_context_for_ai

async def main():
    # Mock API Key if missing (we don't need to make actual call for this test)
    if not os.getenv("DEEPSEEK_API_KEY"):
        os.environ["DEEPSEEK_API_KEY"] = "mock_key"
        
    print("Fetching context for ETHUSDT...")
    context = await prepare_context_for_ai("ETHUSDT", timeframe="4h")
    
    print("Constructing prompt...")
    analyst = DeepSeekAnalyst(api_key="mock_key")
    
    # Context to dict
    context_dict = context.to_dict()
    # Inject mock preferences
    context_dict["user_preferences"] = {"depth": 3, "risk": "moderate"}
    
    prompt = analyst._build_user_prompt("ETHUSDT", context_dict)
    
    print("\n" + "="*50)
    print("GENERATED PROMPT")
    print("="*50)
    print(prompt)
    print("="*50)
    
    # Validation
    has_trend = "趋势周期背景" in prompt
    has_vpvr = "筹码分布 (VPVR)" in prompt or "POC" in prompt
    
    print(f"\nValidation Results:")
    print(f"- Has Trend Context: {'✅' if has_trend else '❌'}")
    print(f"- Has VPVR Data: {'✅' if has_vpvr else '❌'}")
    
    if has_trend and has_vpvr:
        print("\nSUCCESS: Prompt integration verified.")
    else:
        print("\nFAILURE: Missing required prompt sections.")

if __name__ == "__main__":
    asyncio.run(main())
