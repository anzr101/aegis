"""
AEGIS configuration.

Reads environment, decides whether we run in LIVE mode (real Claude calls)
or DEMO mode (realistic canned output). The app never crashes for a missing
key — it just degrades to DEMO and says so clearly in the UI.
"""
import os
from pathlib import Path

# Load .env if present (no hard dependency — works without python-dotenv too)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "aegis.db"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
MODEL = os.getenv("AEGIS_MODEL", "claude-sonnet-4-6").strip()

# LIVE only if a non-empty, plausibly real key is present.
LIVE_MODE = bool(ANTHROPIC_API_KEY) and ANTHROPIC_API_KEY.startswith("sk-")

APP_NAME = "AEGIS"
APP_TAGLINE = "Campaign Intelligence"
AGENCY = "Ezor Media"

# Streaming pacing for demo mode (seconds) so the relay reads as "thinking".
DEMO_CHUNK_DELAY = float(os.getenv("AEGIS_DEMO_DELAY", "0.012"))
DEMO_AGENT_PAUSE = float(os.getenv("AEGIS_AGENT_PAUSE", "0.35"))


def mode_label() -> str:
    return "LIVE" if LIVE_MODE else "DEMO"
