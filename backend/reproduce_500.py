
import os
import sys

# Add current directory to path
cwd = os.getcwd()
sys.path.insert(0, cwd)
print(f"CWD: {cwd}")
print(f"Path: {sys.path}")
print(f"Dir content: {os.listdir(cwd)}")

try:
    from fastapi.testclient import TestClient
    from main import app
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

def reproduce():
    print("Initializing TestClient...")
    try:
        # raise_server_exceptions=True allows the exception to bubble up
        client = TestClient(app, raise_server_exceptions=True)
        
        print("Sending request to /api/analysis/context/BTCUSDT...")
        response = client.get("/api/analysis/context/BTCUSDT")
        print(f"Status Code: {response.status_code}")
        # print(f"Response: {response.text[:500]}") # Truncate if too long
    except Exception as e:
        print("Caught exception during request:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    reproduce()
