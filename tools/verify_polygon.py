import os
import sys
import json
import requests

try:
    with open('secrets.json', 'r') as f:
        secrets = json.load(f)
        POLYGON_API_KEY = secrets.get("POLYGON_API_KEY")
except Exception as e:
    print(json.dumps({"error": f"Failed to read secrets.json: {str(e)}"}))
    sys.exit(1)

if not POLYGON_API_KEY:
    print(json.dumps({"error": "POLYGON_API_KEY is not set in .env"}))
    sys.exit(1)

def verify_polygon_connection():
    """Simple verification script to ensure we can reach Polygon.io for real-time BTC/USD pricing."""
    ticker = "X:BTCUSD"
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev?adjusted=true&apiKey={POLYGON_API_KEY}"
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == "OK" and data.get("resultsCount", 0) > 0:
            price = data["results"][0]["c"] # close price
            print(json.dumps({
                "status": "success", 
                "message": f"Polygon API verified. BTC/USD previous close: ${price}"
            }))
            sys.exit(0)
        else:
            print(json.dumps({"status": "error", "message": f"Unexpected response form Polygon: {data}"}))
            sys.exit(1)
            
    except Exception as e:
        print(json.dumps({"status": "error", "message": f"Connection failed: {str(e)}"}))
        sys.exit(1)

if __name__ == "__main__":
    verify_polygon_connection()
