#!/usr/bin/env python3
"""
video_factory.py — VisionEdge Marketing Agent | Layer 3: Video
Renders a TikTok-ready 1080x1920 MP4 using the Creatomate v2 API.

Template structure (from API Integration page):
  - Video.source  → chart image (real HTTP URL required — data URIs rejected by render workers)
  - Text-1.text   → primary caption (hook line)
  - Text-2.text   → secondary text (brand line)

Asset hosting: catbox.moe (free, anonymous, permanent URLs, fast).
Confirmed working: render 08cb412f succeeded in ~5 seconds.

PIPELINE:
  chart PNG → catbox.moe → real URL → Creatomate modifications.Video.source
  TTS  MP3  → catbox.moe → real URL → Creatomate template_data.audio
  → Creatomate renders 1080x1920 MP4 → returns CDN URL in ~5-30s
"""
import os
import sys
import json
import time
import logging
import requests
import random
from pathlib import Path

log = logging.getLogger(__name__)

SECRETS_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'secrets.json')


def _load_secrets() -> dict:
    try:
        with open(SECRETS_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        log.error(f"Cannot load secrets.json: {e}")
        return {}


SECRETS        = _load_secrets()

# MUSIC_VAULT: Royalty-free Lofi/Ambient tracks hosted on stable, permanent CDNs.
# Each URL is verified accessible. Kling kinetic background audio is muted,
# so this BGM plays freely without conflict.
MUSIC_VAULT = [
    # ccMixter / Free Music Archive — highly stable infrastructure
    "https://files.freemusicarchive.org/storage-freemusicarchive-org/music/no_curator/Kai_Engel/Satin/Kai_Engel_-_07_-_Sentinel.mp3",
    "https://files.freemusicarchive.org/storage-freemusicarchive-org/music/WFMU/Broke_For_Free/Directionless_EP/Broke_For_Free_-_01_-_Night_Owl.mp3",
    "https://files.freemusicarchive.org/storage-freemusicarchive-org/music/ccCommunity/Kai_Engel/Idea/Kai_Engel_-_08_-_Comfort.mp3",
    # Archive.org verified working tracks
    "https://archive.org/download/3x13_-_a_summer_spent_inside/3x.13_-_a_summer_spent_inside_-_cd1_01_-_previous_episode.mp3",
    "https://archive.org/download/3x13_-_a_summer_spent_inside/3x.13_-_a_summer_spent_inside_-_cd1_02_-_gusto.mp3",
]

CREATOMATE_KEY = SECRETS.get("CREATOMATE_API_KEY", os.getenv("CREATOMATE_API_KEY", ""))
TEMPLATE_ID    = SECRETS.get("CREATOMATE_TEMPLATE_ID", os.getenv("CREATOMATE_TEMPLATE_ID", ""))
BASE_URL       = "https://api.creatomate.com/v1"
CATBOX_API     = "https://catbox.moe/user/api.php"

# ── Cloudflare R2 Config (loaded lazily so catbox fallback still works) ────────
# To activate R2: add these 5 keys to secrets.json and they are auto-detected.
R2_ACCOUNT_ID       = SECRETS.get("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID    = SECRETS.get("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = SECRETS.get("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET_NAME      = SECRETS.get("R2_BUCKET_NAME", "polyvision-assets")
R2_PUBLIC_URL       = SECRETS.get("R2_PUBLIC_URL", "")   # e.g. https://pub-xxxx.r2.dev
_R2_ENABLED         = bool(R2_ACCOUNT_ID and R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY and R2_PUBLIC_URL)


def _auth_headers() -> dict:
    return {
        "Authorization": f"Bearer {CREATOMATE_KEY}",
        "Content-Type":  "application/json",
    }


# ── Asset Hosting: R2-first with catbox.moe fallback ─────────────────────────
def _upload_asset(file_path: str, retries: int = 2) -> str | None:
    """
    Upload a local file to the best available CDN and return a public URL.

    Priority:
      1. Cloudflare R2 (if R2_* keys present in secrets.json) — 99.99% SLA, zero egress fees.
      2. catbox.moe (anonymous fallback) — free but no SLA, for dev/emergency use only.

    Retry logic: attempts upload `retries` extra times on transient errors.
    """
    filename = Path(file_path).name

    # ── 1. Try Cloudflare R2 ──────────────────────────────────────────────────
    if _R2_ENABLED:
        for attempt in range(1 + retries):
            try:
                import boto3
                from botocore.config import Config as BotoConfig
                endpoint = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
                s3 = boto3.client(
                    "s3",
                    endpoint_url=endpoint,
                    aws_access_key_id=R2_ACCESS_KEY_ID,
                    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
                    config=BotoConfig(signature_version="s3v4"),
                    region_name="auto",
                )
                s3.upload_file(
                    file_path,
                    R2_BUCKET_NAME,
                    filename,
                    ExtraArgs={"ContentType": _guess_content_type(filename)},
                )
                public_url = f"{R2_PUBLIC_URL.rstrip('/')}/{filename}"
                log.info(f"[R2] Uploaded {filename} → {public_url}")
                return public_url
            except Exception as e:
                log.warning(f"[R2] Upload attempt {attempt + 1} failed: {e}")
        log.error(f"[R2] All {1 + retries} attempts failed for {filename} — falling back to catbox.")

    # ── 2. Catbox.moe fallback ────────────────────────────────────────────────
    log.warning(f"[CDN] Using catbox.moe fallback for {filename} (configure R2 keys for production).")
    for attempt in range(1 + retries):
        try:
            with open(file_path, "rb") as f:
                resp = requests.post(
                    CATBOX_API,
                    data={"reqtype": "fileupload"},
                    files={"fileToUpload": (filename, f)},
                    timeout=60,
                )
            resp.raise_for_status()
            url = resp.text.strip()
            if url.startswith("https://"):
                log.info(f"[catbox] Uploaded {filename} → {url}")
                return url
            log.error(f"[catbox] Unexpected response: {url[:100]}")
        except Exception as e:
            log.warning(f"[catbox] Upload attempt {attempt + 1} failed: {e}")
    log.error(f"[CDN] All upload attempts exhausted for {filename}.")
    return None


def _guess_content_type(filename: str) -> str:
    """Lightweight content-type mapper for R2 uploads."""
    ext = Path(filename).suffix.lower()
    return {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "mp3": "audio/mpeg", "mp4": "video/mp4", "gif": "image/gif"}.get(ext.lstrip("."), "application/octet-stream")


# Legacy alias — all existing call sites keep working without changes.
_upload_to_catbox = _upload_asset


# ── Render Submission ─────────────────────────────────────────────────────────
def _submit_render(chart_url: str, audio_url: str | None, caption: str, bg_image_url: str, logo_url: str | None = None) -> str | None:
    """
    Submit a render job to Creatomate with the exact template field names.
    Returns render ID or None on failure.
    """
    if not CREATOMATE_KEY or "PASTE" in CREATOMATE_KEY:
        log.error("CREATOMATE_API_KEY not configured.")
        return None
    # ── Blank Canvas Architecture ──
    # We no longer rely on a stock template because template mapping via modifications
    # was causing irreversible layer overrides and masking bugs when combining with template_data.
    # Instead, we define a pristine, clean canvas entirely from scratch.
    
    elements = []

    # ── 1. Build the background element (Kling MP4 vs DALL-E PNG) ──────────────
    _bg_is_video = bg_image_url.lower().endswith(".mp4")
    if _bg_is_video:
        log.info("[Creatomate] Using Kling kinetic video background (MP4 loop).")
        _bg_element = {
            "type": "video",
            "source": bg_image_url,
            "time": 0,
            "duration": 12,
            "width": "100%",
            "height": "100%",
            "x": "50%",
            "y": "50%",
            "fill_mode": "cover",
            "loop": True,         # Seamlessly loop the 5s Kling clip across 12s
            "volume": "0%",       # Mute Kling audio — our separate BGM track handles audio
            "track": 1,
            "transition": False,
        }
    else:
        log.info("[Creatomate] Using DALL-E static image background (Ken Burns pan).")
        _bg_element = {
            "type": "image",
            "source": bg_image_url,
            "time": 0,
            "duration": 12,
            "width": "120%",     # Overscale to allow smooth pan without black bars
            "height": "120%",
            "transition": False,
            "track": 1,
            "animations": [
                {
                    "time": 0,
                    "duration": 12,
                    "type": "pan",
                    "start_x": "0%",
                    "end_x": "20%",
                    "easing": "linear"
                }
            ]
        }

    # ── 2. The Master Visual Composition (Data Segment) ──
    elements.append({
        "type": "composition",
        "time": 0,
        "duration": 12,
        "elements": [
            _bg_element,
            {
                "type": "image",
                "source": chart_url,
                "time": 0,
                "duration": 12,
                "width": "100%",
                "height": "100%",
                "x": "50%",
                "y": "50%",
                "transition": False,
                "track": 2
                # NO ANIMATIONS BLOCK = MATHEMATICALLY STATIC = ZERO FADE INJECTED
            }
        ]
    })
    
    # ── 2. The PolyVision Branded Outro (Python Managed) ──
    if logo_url:
        elements.append({
            "type": "composition",
            "time": 12,
            "duration": 3,
            "elements": [
                {
                    "type": "image",
                    "source": logo_url,
                    "x": "50%",
                    "y": "50%",
                    "width": "100%",
                    "height": "100%",
                    "transition": False
                }
            ]
        })
    
    # The generated TTS voiceover
    if audio_url:
        elements.append({
            "type":   "audio",
            "source": audio_url,
            "time":   0,
            "volume": "100%",    # Full volume for main narration
            "audio_fade_in": 0.5
        })
        
    # Background Ambient Audio Matrix
    # Pick a track and verify it responds 200 before injecting.
    # If the chosen URL is dead, try the next one. Skip BGM entirely rather than crashing.
    _bgm_url = None
    _candidates = MUSIC_VAULT.copy()
    random.shuffle(_candidates)
    for _candidate in _candidates:
        try:
            _probe = requests.head(_candidate, timeout=5, allow_redirects=True)
            if _probe.status_code == 200:
                _bgm_url = _candidate
                break
            log.warning(f"[BGM] Track unavailable ({_probe.status_code}): {_candidate}")
        except Exception as _e:
            log.warning(f"[BGM] Track probe failed: {_candidate} — {_e}")

    if _bgm_url:
        elements.append({
            "type": "audio",
            "source": _bgm_url,
            "time": 0,
            "volume": "12%",
            "audio_fade_in": 1.0,
            "audio_fade_out": 2.0
        })
        log.info(f"[BGM] Injecting ambient track: {_bgm_url.split('/')[-1]}")
    else:
        log.warning("[BGM] All tracks unavailable — rendering without background music.")
        
    # Natively instruct Creatomate to build a fresh 9:16 vertical video
    payload = {
        "output_format": "mp4",   # Essential root-level declaration
        "source": {
            "output_format": "mp4",
            "frame_rate": 60,
            "width": 1080,
            "height": 1920,
            "duration": 15,
            "elements": elements
        }
    }

    try:
        resp = requests.post(
            f"{BASE_URL}/renders",
            headers=_auth_headers(),
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        renders   = resp.json()
        render    = renders[0] if isinstance(renders, list) else renders
        render_id = render.get("id", "")
        log.info(f"Render submitted — ID: {render_id} | Status: {render.get('status')}")
        return render_id
    except Exception as e:
        log.error(f"Render submission failed: {e}")
        return None


# ── Render Poll ───────────────────────────────────────────────────────────────
def _poll_render(render_id: str, max_wait: int = 300) -> str | None:
    """Poll until render complete. Returns video URL or None."""
    interval = 5
    attempts = max_wait // interval

    for i in range(attempts):
        time.sleep(interval)
        try:
            resp   = requests.get(
                f"{BASE_URL}/renders/{render_id}",
                headers=_auth_headers(),
                timeout=15,
            )
            resp.raise_for_status()
            data   = resp.json()
            status = data.get("status", "")
            log.info(f"Render [{i+1}/{attempts}] status: {status}")

            if status == "succeeded":
                url = data.get("url", "")
                log.info(f"✅ Video ready → {url}")
                return url
            elif status in ("failed", "deleted"):
                log.error(f"Render {status}: {data.get('error_message', 'unknown error')}")
                return None
        except Exception as e:
            log.warning(f"Poll {i+1} failed: {e}")

    log.error(f"Render timed out after {max_wait}s.")
    return None


# ── Public Interface ──────────────────────────────────────────────────────────
def create_video(
    chart_image_path: str,
    audio_path: str | None,
    caption: str,
    bg_image_url: str,
    logo_path: str | None = None,
) -> str | None:
    """
    Full pipeline:
      1. Upload chart PNG to catbox.moe → public URL
      2. Upload voiceover MP3 to catbox.moe → public URL (if provided)
      3. Submit Creatomate render job
      4. Poll until MP4 is ready
      5. Return public Creatomate CDN video URL

    Args:
        chart_image_path: Local path to chart PNG (from chart_generator).
        audio_path:       Local path to TTS MP3 (from tts_generator). None = silent.
        caption:          Hook text to overlay on the video.

    Returns:
        Public URL for the finished MP4, or None on failure.
    """
    if not CREATOMATE_KEY or "PASTE" in CREATOMATE_KEY:
        log.error("CREATOMATE_API_KEY not ready.")
        return None

    log.info(f"Uploading chart to catbox.moe: {Path(chart_image_path).name}")
    chart_url = _upload_to_catbox(chart_image_path)
    if not chart_url:
        return None

    audio_url = None
    if audio_path and os.path.exists(audio_path):
        log.info(f"Uploading voiceover to catbox.moe: {Path(audio_path).name}")
        audio_url = _upload_to_catbox(audio_path)
        if not audio_url:
            log.warning("Audio upload failed — rendering silent video.")
            
    logo_url = None
    if logo_path and os.path.exists(logo_path):
        log.info(f"Uploading logo to catbox.moe: {Path(logo_path).name}")
        logo_url = _upload_to_catbox(logo_path)

    log.info("Submitting Creatomate render job...")
    render_id = _submit_render(chart_url, audio_url, caption, bg_image_url, logo_url=logo_url)
    if not render_id:
        return None

    log.info("Polling for render completion (~5-30s)...")
    return _poll_render(render_id)


# ── Standalone Test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [video_factory] %(levelname)s: %(message)s",
    )

    tmp_dir = os.path.join(os.path.dirname(__file__), '..', '..', '.tmp', 'marketing')
    charts  = sorted(Path(tmp_dir).glob("chart_*.png"), reverse=True)
    audios  = sorted(Path(tmp_dir).glob("voiceover_*.mp3"), reverse=True)

    chart_path   = str(charts[0]) if charts else None
    audio_path   = str(audios[0]) if audios else None
    test_caption = "AI just spotted a major setup forming. Most traders will miss this."

    if not chart_path:
        print("No chart PNG in .tmp/marketing/. Run chart_generator.py first.")
        sys.exit(1)

    log.info(f"Chart:   {chart_path}")
    log.info(f"Audio:   {audio_path or 'None (silent)'}")
    log.info(f"Caption: {test_caption}")

    url = create_video(chart_path, audio_path, test_caption)
    if url:
        print(f"\n✅ VIDEO URL: {url}")
    else:
        print("\n❌ Video render failed.")
        sys.exit(1)
