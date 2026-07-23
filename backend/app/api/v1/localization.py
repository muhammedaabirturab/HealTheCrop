import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/localization", tags=["Localization"])

_LOCALIZATION_DIR = Path(__file__).resolve().parents[4] / "localization"
SUPPORTED_LANGUAGES = ["en", "hi", "kn", "ta", "te", "ml"]
LANGUAGE_NAMES = {"en": "English", "hi": "हिन्दी", "kn": "ಕನ್ನಡ", "ta": "தமிழ்", "te": "తెలుగు", "ml": "മലയാളം"}


@router.get("/languages")
def list_languages():
    return [{"code": code, "name": LANGUAGE_NAMES[code]} for code in SUPPORTED_LANGUAGES]


@router.get("/{lang_code}")
def get_translations(lang_code: str):
    if lang_code not in SUPPORTED_LANGUAGES:
        raise HTTPException(status_code=404, detail="Unsupported language code")
    path = _LOCALIZATION_DIR / f"{lang_code}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Translation file not found")
    return json.loads(path.read_text(encoding="utf-8"))
