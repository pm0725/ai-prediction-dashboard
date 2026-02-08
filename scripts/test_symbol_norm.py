import sys
import os

# 将 backend 目录添加到 sys.path
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), 'backend')))

from app.services.data_aggregator import normalize_symbol

def test_normalization():
    test_cases = [
        ("btcusdt", "BTCUSDT"),
        ("ETH-USDT", "ETHUSDT"),
        ("sol/usdt", "SOLUSDT"),
        ("bnb_usdt", "BNBUSDT"),
        ("pepe", "1000PEPEUSDT"),
        ("1000pepe", "1000PEPEUSDT"),
        ("SHIB", "1000SHIBUSDT"),
        ("doge", "DOGEUSDT"),
        ("LUNCUSDT", "1000LUNCUSDT"),
        ("rats-usdt", "1000RATSUSDT")
    ]
    
    print(f"{'Input':<15} | {'Expected':<15} | {'Result':<15} | {'Status'}")
    print("-" * 65)
    
    passed = 0
    for inp, expected in test_cases:
        result = normalize_symbol(inp)
        status = "✅" if result == expected else "❌"
        if result == expected:
            passed += 1
        print(f"{inp:<15} | {expected:<15} | {result:<15} | {status}")
    
    print("-" * 65)
    print(f"Passed: {passed}/{len(test_cases)}")
    
    if passed == len(test_cases):
        print("\nAll normalization tests passed!")
    else:
        print("\nSome tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    test_normalization()
