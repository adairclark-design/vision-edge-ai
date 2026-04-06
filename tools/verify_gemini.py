import os
import sys
import json
from google import genai

# Read from secrets.json instead of .env due to macOS permission lock
try:
    with open('secrets.json', 'r') as f:
        secrets = json.load(f)
        GOOGLE_API_KEY = secrets.get("GOOGLE_API_KEY")
except Exception as e:
    print(json.dumps({"error": f"Failed to read secrets.json: {str(e)}"}))
    sys.exit(1)

if not GOOGLE_API_KEY:
    print(json.dumps({"error": "GOOGLE_API_KEY is not set in .env"}))
    sys.exit(1)

client = genai.Client(api_key=GOOGLE_API_KEY)

def verify_gemini_connection():
    """Simple verification script to ensure we can reach Gemini 1.5 Pro and parse JSON using the new SDK."""
    try:
        # We ask for a simple JSON response to test structured output capabilities
        prompt = """
        Return a simple JSON object with a single key 'status' and value 'connected'.
        Do not include markdown formatting or backticks, just the raw JSON.
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-pro',
            contents=prompt,
        )
        text = response.text.strip()
        
        # Remove markdown if it occasionally sneaks through
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
            
        data = json.loads(text.strip())
        
        if data.get("status") == "connected":
           print(json.dumps({"status": "success", "message": "Gemini 1.5 Pro connection verified via google.genai"}))
           sys.exit(0)
        else:
           print(json.dumps({"status": "error", "message": f"Unexpected response format: {data}"}))
           sys.exit(1)
           
    except Exception as e:
        print(json.dumps({"status": "error", "message": f"Connection failed: {str(e)}"}))
        sys.exit(1)

if __name__ == "__main__":
    verify_gemini_connection()

