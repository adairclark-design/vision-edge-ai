#!/usr/bin/env python3
"""
agent_scheduler.py — VisionEdge Marketing Agent | Layer 2: Cron Orchestrator
Zero-touch autonomous scheduler. Runs as a standalone process (or alongside
the Next.js app via a companion process).

Schedule:
  - 09:00 EST: Morning generation cycle (X post + TikTok video + Reddit draft)
  - 18:00 EST: Evening generation cycle (X post only — no video spam)
  - 00:05 EST: Nightly reflection cycle (analyze telemetry → update brain)

Run this process persistently:
  python tools/marketing/agent_scheduler.py

Or add it to your existing server startup script.
"""
import os
import sys
import time
import random
import logging
from datetime import datetime

# ── Path ──────────────────────────────────────────────────────────────────────
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, THIS_DIR)

# ── Logging ───────────────────────────────────────────────────────────────────
log_path = os.path.join(THIS_DIR, '..', '..', '.tmp', 'marketing', 'agent.log')
os.makedirs(os.path.dirname(log_path), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [scheduler] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_path, mode="a"),
    ],
)
log = logging.getLogger(__name__)

# ── APScheduler ───────────────────────────────────────────────────────────────
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron      import CronTrigger

from agent_generator import run_generation_cycle
from agent_reflector import run_reflection
from agent_db        import init_db


def morning_cycle():
    """09:00 EST ±30 min — Full cycle: X + TikTok + Reddit draft."""
    # Layer 2 jitter: human micro-delay (0.5–8 min) before any API call fires.
    # Layer 1 jitter is handled by APScheduler's jitter= parameter below.
    micro_delay = random.randint(30, 480)
    log.info(f"⏰ Morning cycle triggered. Human micro-delay: {micro_delay}s before execution.")
    time.sleep(micro_delay)
    log.info("🚀 Morning cycle executing now.")
    run_generation_cycle(dry_run=False)


def evening_cycle():
    """18:00 EST ±15 min — X post only (no TikTok — avoid double-posting same day)."""
    # Layer 2 jitter: human micro-delay before execution.
    micro_delay = random.randint(30, 300)
    log.info(f"⏰ Evening X-only cycle triggered. Human micro-delay: {micro_delay}s before execution.")
    time.sleep(micro_delay)
    log.info("🚀 Evening cycle executing now.")
    import json

    secrets_path = os.path.join(THIS_DIR, '..', '..', 'secrets.json')
    try:
        with open(secrets_path, 'r') as f:
            secrets = json.load(f)
    except Exception:
        secrets = {}

    from agent_generator import run_x_post, HIGH_CONVICTION_TICKERS
    ticker = random.choice(HIGH_CONVICTION_TICKERS)
    run_x_post(ticker, secrets, dry_run=False)


def nightly_reflection():
    """00:05 EST — Fetch telemetry + run Claude reflection + update brain."""
    log.info("🧠 Nightly reflection triggered.")
    run_reflection()


def main():
    log.info("=" * 60)
    log.info("VisionEdge Autonomous Marketing Agent — STARTING")
    log.info(f"Started at: {datetime.now().isoformat()}")
    log.info("=" * 60)

    # Ensure DB tables exist
    init_db()

    scheduler = BlockingScheduler(timezone="America/New_York")

    # Morning full cycle — 09:00 EST ±30 min daily
    # jitter=1800 = ±30 min engine-level variance → fires anywhere 08:30–09:30 EST
    scheduler.add_job(
        morning_cycle,
        trigger=CronTrigger(hour=9, minute=0, timezone="America/New_York"),
        id="morning_cycle",
        name="Morning Generation Cycle",
        replace_existing=True,
        jitter=1800,   # ±30 minutes engine-level scatter
    )

    # Evening X-only cycle — 18:00 EST ±15 min daily
    # jitter=900 = ±15 min engine-level variance → fires anywhere 17:45–18:15 EST
    scheduler.add_job(
        evening_cycle,
        trigger=CronTrigger(hour=18, minute=0, timezone="America/New_York"),
        id="evening_cycle",
        name="Evening X Post",
        replace_existing=True,
        jitter=900,    # ±15 minutes engine-level scatter
    )

    # Nightly reflection — 00:05 EST ±10 min daily
    # jitter=600 = ±10 min scatter (lower impact needed for analytics job)
    scheduler.add_job(
        nightly_reflection,
        trigger=CronTrigger(hour=0, minute=5, timezone="America/New_York"),
        id="nightly_reflection",
        name="Nightly Brain Reflection",
        replace_existing=True,
        jitter=600,    # ±10 minutes engine-level scatter
    )

    log.info("Scheduled jobs (with anti-shadowban jitter):")
    log.info("  ✅  ~08:30–09:30 EST — Full generation cycle (X + TikTok + Reddit draft)")
    log.info("  ✅  ~17:45–18:15 EST — Evening X post")
    log.info("  ✅  ~00:00–00:15 EST — Nightly reflection + brain update")
    log.info("  🎲  Every job has dual-layer jitter: engine-level (APScheduler) + micro-delay (sleep)")
    log.info("Agent is running. Press Ctrl+C to stop.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Agent scheduler stopped.")


if __name__ == "__main__":
    main()
