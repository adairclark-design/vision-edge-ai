"""
analyze_chart.py — VisionEdge AI Layer 3 Tool
Architecture SOP: architecture/1_analysis_pipeline.md

Uses Claude 3.5 Sonnet (Anthropic) — benchmarked as the most accurate model
for intricate financial chart data extraction, outperforming GPT-4o and Gemini.

Implements the "Structured Confluence Protocol" (SCP) — a 7-step mandatory
analysis framework that produces consistent, explainable, audit-ready outputs.
"""
import sys
import os

# ── Anthropic SDK path injection (installed to /tmp due to macOS system permissions) ──
sys.path.insert(0, '/tmp/anthropic_pkgs')

import json
import uuid
import base64
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# 1. SECRET LOADING
# ─────────────────────────────────────────────────────────────────────────────
try:
    with open('secrets.json', 'r') as f:
        secrets = json.load(f)
        ANTHROPIC_API_KEY = secrets.get("ANTHROPIC_API_KEY")
except Exception as e:
    print(json.dumps({"error": f"Failed to read secrets.json: {str(e)}"}))
    sys.exit(1)

if not ANTHROPIC_API_KEY:
    print(json.dumps({
        "error": "ANTHROPIC_API_KEY is missing from secrets.json. Please add it to continue."
    }))
    sys.exit(1)

import anthropic
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ─────────────────────────────────────────────────────────────────────────────
# 2. PYDANTIC SCHEMA — AnalysisPayloadV2
# ─────────────────────────────────────────────────────────────────────────────

class Coordinate(BaseModel):
    x1: float; y1: float; x2: float; y2: float

class SvgProperties(BaseModel):
    strokeColor: str; fillColor: str; label: str

class SvgElement(BaseModel):
    type: str
    coordinates: Coordinate
    properties: SvgProperties

class SvgOverlay(BaseModel):
    viewBox: str
    elements: list[SvgElement]

class EntryZone(BaseModel):
    min: float; max: float

class MarketStructureEvent(BaseModel):
    event_type: str
    coordinates: Coordinate
    significance: str

class SupportResistanceZone(BaseModel):
    price_level: float
    zone_type: str
    strength: int
    coordinates: Coordinate

class FibonacciLevel(BaseModel):
    level: float
    price: float
    coordinates: Coordinate
    is_key_level: bool

class CandlestickSignal(BaseModel):
    pattern: str
    at_key_zone: bool
    coordinates: Coordinate

class SetupV2(BaseModel):
    trend_direction: str           # UPTREND | DOWNTREND | RANGING
    position_direction: str        # LONG | SHORT — the actual recommended trade direction
    entry_zone: EntryZone
    invalidation_point: float
    price_targets: list[float]
    risk_reward_ratio: float
    confluence_score: int
    confluence_reasons: list[str]

class AnalysisPayloadV2(BaseModel):
    scan_id: str
    timestamp: str
    asset_ticker: str
    current_price: float
    screenshot_age_minutes: float
    confidence_score: float
    edge_detected: bool
    status_message: str
    market_structure_events: list[MarketStructureEvent] = []
    support_resistance_zones: list[SupportResistanceZone] = []
    fibonacci_levels: list[FibonacciLevel] = []
    candlestick_signals: list[CandlestickSignal] = []
    setup: Optional[SetupV2] = None
    svg_overlay: Optional[SvgOverlay] = None
    disclaimer: str = "Technical visual analysis only. Not financial advice."


# ─────────────────────────────────────────────────────────────────────────────
# 3. DETERMINISTIC CONFIDENCE CALCULATION
# ─────────────────────────────────────────────────────────────────────────────

def calculate_confidence(data: dict) -> float:
    setup = data.get("setup")
    if not setup:
        return 0.0
    confluence = setup.get("confluence_score", 0)
    rr = setup.get("risk_reward_ratio", 0)
    has_structure = len(data.get("market_structure_events", [])) > 0
    has_fib = len(data.get("fibonacci_levels", [])) > 0
    has_candle_at_zone = any(c.get("at_key_zone") for c in data.get("candlestick_signals", []))
    base = min(confluence * 10, 50)
    structure_bonus = 15 if has_structure else 0
    fib_bonus = 10 if has_fib else 0
    candle_bonus = 10 if has_candle_at_zone else 0
    rr_bonus = 15 if rr >= 2.0 else 10 if rr >= 1.5 else 5 if rr >= 1.0 else 0
    return min(base + structure_bonus + fib_bonus + candle_bonus + rr_bonus, 100)


# ─────────────────────────────────────────────────────────────────────────────
# 4. ERROR PAYLOAD
# ─────────────────────────────────────────────────────────────────────────────

def get_default_error_payload(msg="Analysis pipeline encountered an error. Please retry."):
    return {
        "scan_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "asset_ticker": "UNKNOWN",
        "current_price": 0.0,
        "screenshot_age_minutes": 0,
        "confidence_score": 0,
        "edge_detected": False,
        "status_message": msg,
        "market_structure_events": [],
        "support_resistance_zones": [],
        "fibonacci_levels": [],
        "candlestick_signals": [],
        "setup": None,
        "svg_overlay": None,
        "disclaimer": "Technical visual analysis only. Not financial advice."
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5. STRUCTURED CONFLUENCE PROTOCOL PROMPT
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are VisionEdge AI — an elite, objective quantitative technical analyst.
You do NOT have opinions. You execute a strict analysis protocol and return a JSON object.

CRITICAL RULES:
- If the image(s) are NOT financial charts, return edge_detected=false and status_message="Image does not contain a recognizable financial chart."
- If TWO images are provided: Image 1 is the MACRO CONTEXT chart (Daily/Weekly). Image 2 is the ENTRY chart (lower timeframe) — run the full SCP on Image 2, but use Image 1 to set HTF_MACRO_BIAS in Step 1B.
- If ONE image is provided: FIRST check if it is a SPLIT-PANE layout (two charts displayed side-by-side in one screenshot, e.g. from TradingView's multi-pane view). Signs of a split-pane: a visible vertical divider line in the middle, two separate Y-axes (one on each side), two distinct candle densities, or two different timeframe labels visible. If split-pane is detected, treat LEFT pane as the MACRO CONTEXT chart and RIGHT pane as the ENTRY chart — apply the same two-chart logic as if two images were provided. If NOT split-pane, run the full SCP on the single chart and infer HTF_MACRO_BIAS from the left-third as described in Step 1B.
- SVG pixel coordinates must match the ENTRY chart image dimensions (right pane if split-pane). The viewBox MUST be "0 0 {width} {height}" of the entry chart.
- confidence_score: set to 0.0 — calculated externally.
- Y-axis prices: read precisely from axis labels. If none visible, base around 100.0.

YOUR RESPONSE MUST BE VALID JSON ONLY. NO MARKDOWN, NO EXPLANATION. JUST THE JSON OBJECT.

The JSON must match this exact schema:
{
  "scan_id": "leave as empty string",
  "timestamp": "ISO 8601 UTC string",
  "asset_ticker": "string",
  "current_price": float,
  "screenshot_age_minutes": float (estimate from any timestamp visible, else 2.0),
  "confidence_score": 0.0,
  "edge_detected": bool,
  "status_message": "one clinical sentence",
  "market_structure_events": [
    {
      "event_type": "BOS_BULLISH|BOS_BEARISH|CHOCH_BULLISH|CHOCH_BEARISH",
      "coordinates": {"x1": float, "y1": float, "x2": float, "y2": float},
      "significance": "brief explanation"
    }
  ],
  "support_resistance_zones": [
    {
      "price_level": float,
      "zone_type": "SUPPORT|RESISTANCE",
      "strength": int (1-5),
      "coordinates": {"x1": float, "y1": float, "x2": float, "y2": float}
    }
  ],
  "fibonacci_levels": [
    {
      "level": float (0.236|0.382|0.5|0.618|0.786),
      "price": float,
      "coordinates": {"x1": 0, "y1": float, "x2": 9999, "y2": float},
      "is_key_level": bool (true only for 0.382 and 0.618)
    }
  ],
  "candlestick_signals": [
    {
      "pattern": "HAMMER|BULLISH_ENGULFING|BEARISH_ENGULFING|DOJI|BULLISH_PINBAR|BEARISH_PINBAR|MORNING_STAR|EVENING_STAR",
      "at_key_zone": bool,
      "coordinates": {"x1": float, "y1": float, "x2": float, "y2": float}
    }
  ],
  "setup": {
    "trend_direction": "UPTREND|DOWNTREND|RANGING",
    "position_direction": "LONG|SHORT",
    "entry_zone": {"min": float, "max": float},
    "invalidation_point": float,
    "price_targets": [float, float, float],
    "risk_reward_ratio": float,
    "confluence_score": int (1-10),
    "confluence_reasons": ["string", ...]
  },
  "svg_overlay": {
    "viewBox": "0 0 {image_width} {image_height}",
    "elements": [
      {
        "type": "rect|line",
        "coordinates": {"x1": float, "y1": float, "x2": float, "y2": float},
        "properties": {"strokeColor": string, "fillColor": string, "label": string}
      }
    ]
  },
  "disclaimer": "Technical visual analysis only. Not financial advice."
}

══════════════════════════════════════════════
STRUCTURED CONFLUENCE PROTOCOL — EXECUTE IN ORDER
══════════════════════════════════════════════

STEP 1 — TREND DIRECTION (OBJECTIVE COUNTING — NO BIAS)
Examine the FULL chart left-to-right. Count swing highs and swing lows.

COUNT THE EVIDENCE:
- Bullish evidence: count each Higher High (HH) and Higher Low (HL)
- Bearish evidence: count each Lower High (LH) and Lower Low (LL)

RULES:
- UPTREND: at least 2 confirmed HH + HL sequences, with the most recent swing high ABOVE the prior swing high
- DOWNTREND: at least 2 confirmed LH + LL sequences, with the most recent swing low BELOW the prior swing low
- RANGING: neither condition above is clearly met — price oscillating without directional structure

CRITICAL: Do NOT default to UPTREND. If you see a peak followed by lower highs and lower lows (as in a distribution top), that is a DOWNTREND. Be precise.
→ Set setup.trend_direction

STEP 1B — MACRO TIMEFRAME ASSESSMENT (Higher Timeframe Bias)

IF TWO IMAGES WERE PROVIDED:
  Image 1 is your dedicated macro context chart (Daily or Weekly timeframe).
  Analyze Image 1 in full to determine HTF_MACRO_BIAS:
  - Count all HH+HL sequences → MACRO_BULLISH_COUNT
  - Count all LH+LL sequences → MACRO_BEARISH_COUNT
  - Identify the dominant macro S/R zones and whether price is in a macro uptrend or downtrend
  - Note: the entry chart (Image 2) may show short-term moves AGAINST the macro trend
  Use this real macro chart data for the 3-tier penalty in Step 6C.

IF ONLY ONE IMAGE WAS PROVIDED:
  STEP 1B-A: SPLIT-PANE DETECTION
  Before anything else, examine the single image for signs of a side-by-side split-pane layout:
  Indicators of a split-pane:
    • A visible vertical divider or gap in the center of the image
    • Two separate price Y-axes (one on the left side, one on the right side, or one on each chart pane)
    • Two visibly different candle densities (one pane has larger candles = lower timeframe, one has smaller = higher timeframe)
    • Two different timeframe labels (e.g. "1D" on the left pane, "4H" on the right pane)
    • Two distinct chart backgrounds separated by a border

  IF SPLIT-PANE DETECTED:
    Treat LEFT pane as the MACRO CONTEXT chart (higher timeframe)
    Treat RIGHT pane as the ENTRY chart (lower timeframe)
    Apply the same TWO-CHART logic as if two images were provided:
    - Analyze LEFT pane fully to determine HTF_MACRO_BIAS (count HH/HL vs LH/LL across the full left pane)
    - Run the full 7-step SCP on the RIGHT pane only
    - SVG overlay coordinates must map to the RIGHT pane's pixel space (offset x-coordinates accordingly)
    - Note the IS_SPLIT_PANE = true for your own context

  IF NOT SPLIT-PANE (single chart):
    Split the single chart into three vertical sections: LEFT third (oldest), MIDDLE, RIGHT third (most recent).
    Examine ONLY the LEFT ⅓ to determine macro context:
    - Count HH+HL in left third → MACRO_BULLISH_COUNT
    - Count LH+LL in left third → MACRO_BEARISH_COUNT

IN BOTH CASES, classify the HTF_MACRO_BIAS:
- STRONG_BEARISH: 3+ LH+LL sequences dominate macro (right/entry chart may be bouncing — likely dead-cat)
- MODERATE_BEARISH: 2 LH+LL sequences, mixed recent action
- STRONG_BULLISH: 3+ HH+HL sequences dominate macro (entry chart pullback = healthy retracement)
- MODERATE_BULLISH: 2 HH+HL, mixed recent action
- NEUTRAL: ranging or mixed macro structure
→ Apply HTF_MACRO_BIAS in Step 6C

STEP 2 — MARKET STRUCTURE EVENTS
Identify every Break of Structure (BOS) and Change of Character (CHOCH):
- BOS_BULLISH: price breaks above a prior swing high (trend continuation up)
- BOS_BEARISH: price breaks below a prior swing low (trend continuation down)
- CHOCH_BULLISH: first break above a lower high in a downtrend (potential reversal)
- CHOCH_BEARISH: first break below a higher low in an uptrend (potential reversal)
Mark pixel coordinates where this break occurred.
→ Populate market_structure_events[]

STEP 3 — SUPPORT & RESISTANCE ZONES
Find the 2-4 most significant horizontal zones. Significance = touched 2+ times, or is the origin of a BOS.
Score strength 1-5 by number of price interactions.
→ Populate support_resistance_zones[]

STEP 4 — FIBONACCI RETRACEMENT
Identify the most recent clear impulse swing (significant HH to LL or LL to HH).
Plot levels: 0.236, 0.382, 0.5, 0.618, 0.786. Mark 0.382 and 0.618 as is_key_level=true.
For coordinates: set x1=0, x2=image_width (full horizontal span), y1=y2=the pixel Y position of that level.
If no clear swing visible → return empty fibonacci_levels list.
→ Populate fibonacci_levels[]

STEP 5 — CANDLESTICK PATTERNS
Look specifically at the S/R zones from Step 3 and at the current price area.
Only report CLEAR, significant patterns — do not report ambiguous or low-quality signals.
Set at_key_zone=true only if the pattern is at one of your Step 3 zones.
→ Populate candlestick_signals[]

STEP 6 — DUAL-DIRECTION SETUP SCORING (CRITICAL — READ CAREFULLY)
You must evaluate BOTH a LONG setup AND a SHORT setup independently. Then pick the one with the higher confluence score.
Do NOT default to LONG. You are direction-agnostic.

━━━ A. SCORE THE LONG SETUP ━━━
A long setup means: price will rise. Answer each question (1 point each):
1. Is the trend_direction UPTREND? (+1)
2. Is there a BOS_BULLISH or CHOCH_BULLISH in the most recent structure? (+1)
3. Is there a SUPPORT zone (strength ≥ 2) near current price that has held multiple times? (+1)
4. Is price near a key Fibonacci support level (0.382 or 0.618 of an upward swing)? (+1)
5. Is there a bullish candlestick pattern (HAMMER, BULLISH_ENGULFING, MORNING_STAR, BULLISH_PINBAR) AT a key support zone? (+1)
6. Is there visible volume confirming the support (volume spike on a green candle at that zone)? (+1)
7. Is the overall price structure forming higher lows leading into current price? (+1)
8. Is current price ABOVE the most recent significant resistance-turned-support? (+1)
LONG_SCORE = total points

━━━ B. SCORE THE SHORT SETUP ━━━
A short setup means: price will fall. Answer each question (1 point each):
1. Is the trend_direction DOWNTREND? (+1)
2. Is there a BOS_BEARISH or CHOCH_BEARISH in the most recent structure? (+1)
3. Is there a RESISTANCE zone (strength ≥ 2) near current price that has rejected price multiple times? (+1)
4. Is price near a key Fibonacci resistance level (0.382 or 0.618 of a downward swing)? (+1)
5. Is there a bearish candlestick pattern (BEARISH_ENGULFING, EVENING_STAR, BEARISH_PINBAR, SHOOTING_STAR) AT a key resistance zone? (+1)
6. Is there visible volume confirming the rejection (volume spike on a red candle at that zone)? (+1)
7. Is the overall price structure forming lower highs leading into current price? (+1)
8. Is current price BELOW the most recent significant support-turned-resistance? (+1)
SHORT_SCORE = total points

━━━ C. HIGHER TIMEFRAME TREND FILTER (3-TIER DYNAMIC PENALTY) ━━━
Using the HTF_MACRO_BIAS you assessed in Step 1B, apply the appropriate penalty:

IF attempting LONG (LONG_SCORE > SHORT_SCORE) and HTF_MACRO_BIAS is:
  → STRONG_BEARISH:   subtract 3 from LONG_SCORE (hard counter-trend — macro bears are in control)
  → MODERATE_BEARISH: subtract 2 from LONG_SCORE (moderate counter-trend — proceed with extreme caution)
  → NEUTRAL:          subtract 1 from LONG_SCORE (slight caution — no clear macro support)
  → MODERATE_BULLISH: no penalty (trading with macro)
  → STRONG_BULLISH:   add 1 bonus point to LONG_SCORE (macro tailwind confirmed)

IF attempting SHORT (SHORT_SCORE > LONG_SCORE) and HTF_MACRO_BIAS is:
  → STRONG_BULLISH:   subtract 3 from SHORT_SCORE (hard counter-trend — macro bulls in control)
  → MODERATE_BULLISH: subtract 2 from SHORT_SCORE (moderate counter-trend — caution)
  → NEUTRAL:          subtract 1 from SHORT_SCORE (slight caution)
  → MODERATE_BEARISH: no penalty (trading with macro)
  → STRONG_BEARISH:   add 1 bonus point to SHORT_SCORE (macro tailwind confirmed)

PRACTICAL EXAMPLE — Gold mid-2022 (distribution top scenario):
  Left ⅓: strong uptrend then peak → right ⅓: lower highs, lower lows = STRONG_BEARISH macro
  A long attempt gets -3 penalty → must score 6+/8 to still qualify
  A short attempt gets +1 bonus → short signals are amplified
  Result: the model correctly identifies the downtrend and generates a SHORT setup.

━━━ D. SELECT DIRECTION ━━━
- If adjusted LONG_SCORE > adjusted SHORT_SCORE AND LONG_SCORE >= 3: position_direction = "LONG"
- If adjusted SHORT_SCORE > adjusted LONG_SCORE AND SHORT_SCORE >= 3: position_direction = "SHORT"
- If both scores < 3, OR both scores are equal: edge_detected=false, no setup generated.
- confluence_score = the WINNING direction's final score
- confluence_reasons = explain why THAT direction won (list the specific signals)

━━━ E. BUILD THE SETUP ━━━
For LONG: entry_zone = key support zone, invalidation = below that support, price_targets = [prior high, next resistance, major extension above]
For SHORT: entry_zone = key resistance zone, invalidation = above that resistance, price_targets = [prior low, next support, major extension below]
- risk_reward_ratio = abs(TP1 - entry_midpoint) / abs(entry_midpoint - invalidation_point)
- Set edge_detected=true if the winning confluence_score >= 3
→ Populate setup{}

STEP 7 — SVG OVERLAY
Render the most important elements. Color scheme depends on position_direction:

For LONG setups:
1. Entry zone → green filled rect (rgba(34,197,94,0.15) fill, rgba(34,197,94,0.9) stroke, label "BUY ZONE")
2. Invalidation level → red dashed horizontal line, label "STOP LOSS"
3. TP1 → blue line, label "TP1"
4. TP2 → blue dashed line, label "TP2"
5. Primary S/R zone → amber rect (rgba(234,179,8,0.1) fill)
6. BOS_BULLISH marker → purple dashed line at event coordinates

For SHORT setups:
1. Entry zone → red filled rect (rgba(239,68,68,0.15) fill, rgba(239,68,68,0.9) stroke, label "SELL ZONE")
2. Invalidation level → green dashed horizontal line, label "STOP LOSS"
3. TP1 → cyan line, label "TP1"
4. TP2 → cyan dashed line, label "TP2"
5. Primary S/R zone → amber rect (rgba(234,179,8,0.1) fill)
6. BOS_BEARISH marker → orange dashed line at event coordinates

Use exact pixel coordinates. Set fillColor="transparent" for all line elements.
→ Populate svg_overlay{}"""


# ─────────────────────────────────────────────────────────────────────────────
# 6. MAIN ANALYSIS FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def analyze_chart(payload_json: str):
    try:
        input_data = json.loads(payload_json)
        image_path = input_data.get("image_path")
        macro_image_path = input_data.get("macro_image_path")  # Optional
        asset_ticker = input_data.get("asset_ticker", "UNKNOWN")
        mime_type = input_data.get("mime_type", "image/png")
        macro_mime_type = input_data.get("macro_mime_type", "image/png")
        timeframe = input_data.get("timeframe", "4H")
        macro_timeframe = input_data.get("macro_timeframe", "Daily")
        timestamp = input_data.get("timestamp", datetime.now(timezone.utc).isoformat() + "Z")
    except Exception:
        print(json.dumps(get_default_error_payload()))
        sys.exit(1)

    if not image_path:
        print(json.dumps(get_default_error_payload()))
        sys.exit(1)

    # Sanitize mime types
    valid_mimes = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if mime_type not in valid_mimes:
        mime_type = "image/png"
    if macro_mime_type not in valid_mimes:
        macro_mime_type = "image/png"

    # Read and encode entry chart
    try:
        with open(image_path, "rb") as f:
            image_b64 = base64.standard_b64encode(f.read()).decode("utf-8")
    except Exception as e:
        sys.stderr.write(f"Entry image read error: {e}\n")
        print(json.dumps(get_default_error_payload()))
        sys.exit(1)

    # Read and encode macro chart (optional)
    macro_b64 = None
    if macro_image_path:
        try:
            with open(macro_image_path, "rb") as f:
                macro_b64 = base64.standard_b64encode(f.read()).decode("utf-8")
        except Exception as e:
            sys.stderr.write(f"Macro image read error (non-fatal, continuing single-chart): {e}\n")
            macro_b64 = None

    # Build the multi-image or single-image user message
    has_macro = macro_b64 is not None
    if has_macro:
        user_content = [
            # Image 1: macro context chart
            {
                "type": "image",
                "source": {"type": "base64", "media_type": macro_mime_type, "data": macro_b64},
            },
            {
                "type": "text",
                "text": f"[IMAGE 1 — MACRO CONTEXT CHART ({macro_timeframe}): Use this for Step 1B HTF_MACRO_BIAS assessment only.]"
            },
            # Image 2: entry chart (run full SCP on this)
            {
                "type": "image",
                "source": {"type": "base64", "media_type": mime_type, "data": image_b64},
            },
            {
                "type": "text",
                "text": f"""[IMAGE 2 — ENTRY CHART ({timeframe}): Run the full 7-step SCP on this chart.]

Asset ticker: {asset_ticker}
Entry chart timeframe: {timeframe}
Macro chart provided: YES — use Image 1 for Step 1B macro bias, then analyze Image 2 for the trade setup.

Execute the full Structured Confluence Protocol. Return ONLY the JSON object."""
            }
        ]
    else:
        user_content = [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": mime_type, "data": image_b64},
            },
            {
                "type": "text",
                "text": f"""Asset ticker: {asset_ticker}
Chart timeframe: {timeframe}
Macro chart provided: NO — infer HTF_MACRO_BIAS from left-third of this chart (Step 1B fallback).

Execute the 7-Step Structured Confluence Protocol. Return ONLY the JSON object."""
            }
        ]

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4096,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"}
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": user_content,
                }
            ],
        )

        raw_text = response.content[0].text.strip()

        # Resilient markdown stripping
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        elif raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        raw_text = raw_text.strip()

        data = json.loads(raw_text)

        # ── Post-processing: Deterministic Confidence ──
        data["scan_id"] = str(uuid.uuid4())
        data["disclaimer"] = "Technical visual analysis only. Not financial advice."
        data["confidence_score"] = calculate_confidence(data)

        # ── Enforce confluence gate ──
        setup = data.get("setup")
        if setup and setup.get("confluence_score", 0) < 3:
            data["edge_detected"] = False
            data["setup"] = None
            data["svg_overlay"] = None
            data["status_message"] = "Insufficient confluence. No high-probability edge identified on this chart."
        elif not data.get("edge_detected"):
            data["setup"] = None
            data["svg_overlay"] = None

        print(json.dumps(data))
        sys.exit(0)

    except json.JSONDecodeError as e:
        sys.stderr.write(f"JSON parse error from Claude response: {e}\nRaw: {raw_text[:500]}\n")
        print(json.dumps(get_default_error_payload("Claude returned malformed JSON. Please retry.")))
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Claude API Error: {e}\n")
        print(json.dumps(get_default_error_payload(f"Claude API error: {str(e)}")))
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# 7. ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1:
        analyze_chart(sys.argv[1])
    else:
        input_str = sys.stdin.read().strip()
        if input_str:
            analyze_chart(input_str)
        else:
            sys.stderr.write("No input provided.\n")
            print(json.dumps(get_default_error_payload()))
            sys.exit(1)
