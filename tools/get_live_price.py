import sys
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

# Read from secrets.json instead of .env due to macOS permission lock
try:
    with open('secrets.json', 'r') as f:
        secrets = json.load(f)
        POLYGON_API_KEY = secrets.get("POLYGON_API_KEY")
except Exception as e:
    print(json.dumps({"error": f"Failed to read secrets.json: {str(e)}"}))
    sys.exit(1)

if not POLYGON_API_KEY:
    print(json.dumps({"error": "POLYGON_API_KEY is not set in secrets.json"}))
    sys.exit(1)

def get_live_price(ticker: str):
    """
    Fetches the last known trade or previous close for the given ticker.
    Supports stocks (e.g. AAPL) and crypto (e.g. X:BTCUSD).
    """
    
    # Simple formatting for crypto
    if ticker.startswith("BTC") or ticker.startswith("ETH"):
        polygon_ticker = f"X:{ticker}USD"
    elif not ticker.startswith("X:"):
        polygon_ticker = ticker
    else:
        polygon_ticker = ticker

    # We use the /prev endpoint as a broad catch-all for the "current" price in Polygon basic tier
    url = f"https://api.polygon.io/v2/aggs/ticker/{polygon_ticker}/prev?adjusted=true&apiKey={POLYGON_API_KEY}"
    
    payload = {
        "ticker": polygon_ticker,
        "price": 0.0,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "error"
    }

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == "OK" and data.get("resultsCount", 0) > 0:
            payload["price"] = data["results"][0]["c"] # close price
            payload["status"] = "success"
            print(json.dumps(payload))
            sys.exit(0)
        else:
            payload["message"] = "Ticker not found or no data returned"
            print(json.dumps(payload))
            sys.exit(1)
            
    except Exception as e:
        payload["message"] = str(e)
        print(json.dumps(payload))
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        get_live_price(sys.argv[1].upper())
    else:
        # Expected from Next.js stdout pipe
        input_str = sys.stdin.read().strip()
        if input_str:
            try:
               input_data = json.loads(input_str)
               get_live_price(input_data.get("ticker", "AAPL").upper())
            except:
               get_live_price(input_str.upper())
        else:
            print(json.dumps({"error": "No ticker provided"}))
            sys.exit(1)
