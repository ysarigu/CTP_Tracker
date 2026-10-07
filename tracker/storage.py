import json
from datetime import datetime
from pathlib import Path

from django.conf import settings

from ctp_tracker import SECTIONS


def new_progress():
    now = datetime.now().isoformat()
    return {
        "created": now,
        "last_updated": now,
        "sections_tested": {
            section["name"]: {"status": "not_started", "entries": []}
            for section in SECTIONS.values()
        },
    }


def load_progress():
    progress_file = Path(settings.PROGRESS_FILE)
    if not progress_file.exists():
        return new_progress()

    with progress_file.open(encoding="utf-8") as file:
        progress = json.load(file)

    if not isinstance(progress, dict) or not isinstance(progress.get("sections_tested"), dict):
        raise ValueError(f"{progress_file} does not contain a valid CTP progress document.")
    return progress


def save_progress(progress):
    progress_file = Path(settings.PROGRESS_FILE)
    progress_file.parent.mkdir(parents=True, exist_ok=True)
    progress["last_updated"] = datetime.now().isoformat()
    with progress_file.open("w", encoding="utf-8") as file:
        json.dump(progress, file, indent=2)
