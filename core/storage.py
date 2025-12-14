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

def load_latest_profile() -> dict | None:
    if not os.path.exists(PROFILES_DIR):
        return None

    files = [
        f for f in os.listdir(PROFILES_DIR)
        if f.endswith(".json")
    ]

    if not files:
        return None

    def parse_timestamp(filename: str):
        """
        Extracts datetime from:
        YYYY-MM-DD_HH-MM_<anything>.json
        """
        try:
            ts = filename.split("_", 2)[:2]
            return datetime.strptime("_".join(ts), "%Y-%m-%d_%H-%M")
        except Exception:
            return None

    dated_files = []
    for f in files:
        dt = parse_timestamp(f)
        if dt:
            dated_files.append((dt, f))

    if not dated_files:
        return None

    dated_files.sort(key=lambda x: x[0], reverse=True)
    latest_file = dated_files[0][1]

    latest_path = os.path.join(PROFILES_DIR, latest_file)

    with open(latest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def merge_with_fallback(
    current: dict,
    fallback: dict
) -> tuple[dict, list[str]]:
    """
    Fills empty fields in `current` using `fallback`.
    Returns (merged_profile, list_of_filled_fields)
    """

    filled_fields = []

    def is_empty(v):
        return v is None or (isinstance(v, str) and not v.strip())

    merged = current.copy()

    for key, value in current.items():
        if isinstance(value, dict):
            merged[key] = value.copy()
            fb_sub = fallback.get(key, {}) if isinstance(fallback.get(key), dict) else {}

            for sub_key, sub_val in value.items():
                if is_empty(sub_val) and not is_empty(fb_sub.get(sub_key)):
                    merged[key][sub_key] = fb_sub[sub_key]
                    filled_fields.append(f"{key}.{sub_key}")

        else:
            if is_empty(value) and not is_empty(fallback.get(key)):
                merged[key] = fallback[key]
                filled_fields.append(key)

    return merged, filled_fields
