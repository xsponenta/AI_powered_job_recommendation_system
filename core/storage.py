import json
import os
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

BASE_DIR = PROJECT_ROOT / ".cv_app"
PROFILES_DIR = BASE_DIR / "profiles"
HISTORY_DIR = BASE_DIR / "cv_history"

PROFILES_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_DIR.mkdir(parents=True, exist_ok=True)


# ---------- PROFILES ----------

def save_profile(name: str, profile: dict):
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    path = PROFILES_DIR / f"{ts}_{name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)


def load_profile(name: str) -> dict:
    path = PROFILES_DIR / f"{name}.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_profiles():
    return [p.stem for p in PROFILES_DIR.glob("*.json")]


# ---------- CV HISTORY ----------

def save_cv_history(profile_name: str, raw_text: str):
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    fname = f"{ts}-{profile_name}.json"
    path = HISTORY_DIR / fname

    data = {
        "timestamp": ts,
        "profile_name": profile_name,
        "raw_text": raw_text
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def list_cv_history():
    return sorted(HISTORY_DIR.glob("*.json"), reverse=True)


def load_cv_history(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
