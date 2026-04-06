# Layer 1 Architecture: Analysis Pipeline

This SOP documents the expected structure, logic, and error handling for the `tools/analyze_chart.py` tool.

## 1. Goal

Take a raw financial chart screenshot (Base64 or URL), pass it to Gemini (genai client), and return a strictly typed `AnalysisPayload` JSON. The JSON will be consumed by the frontend to render the SVG HUD layer and summary.

## 2. Inputs

The tool MUST accept a single JSON string literal payload: `{"image_path": "string", "asset_ticker": "string", "timestamp": "string"}`

## 3. Tool Logic Sequence

1. **Pre-Flight Validation:** Verify the image file exists at `image_path` (either a `.tmp/` file or URL).
2. **Gemini Invocation:** Load the image using `genai.types.Part.from_bytes` and pass a highly explicit metaprompt asking specifically for spatial px coordinates mapping to price action.
3. **JSON Extraction:** Strip any formatting (````json`) from the Gemini response and strictly parse as JSON.
4. **Behavioral Rule Check:**
   - Verify `confidence_score` > 70.
   - If < 70, `edge_detected` must be `false` and `setup` should ideally be null or a disclaimer.
5. **Output Delivery:** Print ONLY the raw output JSON literal to `stdout`. Do not append text to `stdout`. Any non-fatal logging must go to `stderr`.

## 4. Edge Cases & Fallbacks

- **Non-JSON Response from Gemini:** If Gemini fails to return parseable JSON, return a highly constrained default error JSON:
  `{"status_message": "Failed to parse AI structure. Retrying...", "confidence_score": 0, "edge_detected": false}`
- **Rate Limit Hit (429):** Sleep for 5 seconds and retry (max 3 times).

## 5. Golden Rule (Maintenance)

If the prompt given to Gemini changes (e.g., to ask for a new indicator like RSI), you MUST update this SOP before changing `tools/analyze_chart.py`.
