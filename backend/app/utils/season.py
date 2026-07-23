"""
Determines the current agricultural season for India's crop calendar from the
current date, with an optional manual override for testing/demo purposes.

    Kharif : Jun - Oct  (monsoon-sown)
    Rabi   : Nov - Mar  (winter-sown)
    Zaid   : Apr - May  (summer, irrigated)
"""
from datetime import date


def detect_season(reference_date: date | None = None) -> str:
    d = reference_date or date.today()
    month = d.month
    if month in (6, 7, 8, 9, 10):
        return "Kharif"
    if month in (11, 12, 1, 2, 3):
        return "Rabi"
    return "Zaid"


def resolve_season(manual_override: str | None) -> str:
    if manual_override:
        return manual_override
    return detect_season()
