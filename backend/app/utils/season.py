"""
Farmer-facing seasons are the four ordinary calendar seasons — deliberately NOT
India's Kharif/Rabi/Zaid agricultural terms, which many first-time, demo, or
international users won't recognize. This module maps a UI season into the
season category the trained Random Forest model was actually fit on, so the
model's accuracy is unaffected while the Manual Input form stays approachable.

    Spring (Mar-May) -> Zaid    short, irrigated pre-monsoon growing window
    Summer (Jun-Aug) -> Kharif  monsoon sowing season
    Autumn (Sep-Nov) -> Kharif  Kharif's late-growing/harvest months
    Winter (Dec-Feb) -> Rabi    winter cropping season
"""
from datetime import date

UI_SEASONS = ("spring", "summer", "autumn", "winter")

UI_TO_MODEL_SEASON = {
    "spring": "Zaid",
    "summer": "Kharif",
    "autumn": "Kharif",
    "winter": "Rabi",
}


def detect_ui_season(reference_date: date | None = None) -> str:
    d = reference_date or date.today()
    month = d.month
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    if month in (9, 10, 11):
        return "autumn"
    return "winter"


def resolve_season(ui_season: str | None) -> tuple[str, str]:
    """Returns (model_season, ui_season_used) for the given farmer-facing season
    (or today's date if none/unrecognized was provided)."""
    resolved_ui = ui_season.lower() if ui_season and ui_season.lower() in UI_TO_MODEL_SEASON else detect_ui_season()
    return UI_TO_MODEL_SEASON[resolved_ui], resolved_ui
