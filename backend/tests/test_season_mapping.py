from datetime import date

from app.ml.crop_predictor import build_explanation
from app.utils.season import UI_TO_MODEL_SEASON, detect_ui_season, resolve_season


def test_all_four_ui_seasons_map_to_a_valid_model_season():
    valid_model_seasons = {"Kharif", "Rabi", "Zaid"}
    for ui_season, model_season in UI_TO_MODEL_SEASON.items():
        assert model_season in valid_model_seasons, f"{ui_season} maps to unknown model season {model_season}"


def test_resolve_season_returns_both_model_and_ui_values():
    model_season, ui_season = resolve_season("winter")
    assert ui_season == "winter"
    assert model_season == "Rabi"


def test_resolve_season_is_case_insensitive():
    model_season, ui_season = resolve_season("WINTER")
    assert ui_season == "winter"
    assert model_season == "Rabi"


def test_resolve_season_falls_back_to_auto_detect_for_unknown_input():
    model_season, ui_season = resolve_season("Kharif")  # old-style value, no longer recognized as UI input
    assert ui_season in ("spring", "summer", "autumn", "winter")
    assert model_season in ("Kharif", "Rabi", "Zaid")


def test_resolve_season_falls_back_to_auto_detect_for_none():
    model_season, ui_season = resolve_season(None)
    assert ui_season == detect_ui_season()


def test_detect_ui_season_boundaries():
    assert detect_ui_season(date(2026, 3, 1)) == "spring"
    assert detect_ui_season(date(2026, 5, 31)) == "spring"
    assert detect_ui_season(date(2026, 6, 1)) == "summer"
    assert detect_ui_season(date(2026, 8, 31)) == "summer"
    assert detect_ui_season(date(2026, 9, 1)) == "autumn"
    assert detect_ui_season(date(2026, 11, 30)) == "autumn"
    assert detect_ui_season(date(2026, 12, 1)) == "winter"
    assert detect_ui_season(date(2026, 2, 28)) == "winter"


def test_build_explanation_returns_structured_factors():
    """Explanation is structured data, not a hardcoded English sentence, so the
    frontend can compose it in whichever of the 6 supported languages is active."""
    features = {
        "nitrogen": 95, "phosphorus": 45, "potassium": 42,
        "temperature": 26, "humidity": 85, "ph": 6.0, "rainfall": 230,
    }
    feature_importance = {
        "N": 0.14, "P": 0.10, "K": 0.12, "temperature": 0.06,
        "humidity": 0.19, "ph": 0.05, "rainfall": 0.16, "season": 0.17, "location": 0.01,
    }
    explanation = build_explanation(features, feature_importance, "rice", "summer")
    assert explanation["crop"] == "rice"
    assert explanation["season"] == "summer"
    assert 1 <= len(explanation["factors"]) <= 2
    assert all(f["level"] in ("ideal", "low", "high") for f in explanation["factors"])
    # humidity (85, within 40-90) and rainfall (230, within 50-250) are the two
    # highest-importance numeric features here and both sit inside the comfort range
    assert {f["feature"] for f in explanation["factors"]} == {"humidity", "rainfall"}
    assert all(f["level"] == "ideal" for f in explanation["factors"])


def test_build_explanation_handles_unfavorable_values_without_crashing():
    features = {
        "nitrogen": 2, "phosphorus": 1, "potassium": 1,
        "temperature": 45, "humidity": 5, "ph": 3.5, "rainfall": 5,
    }
    feature_importance = {"N": 0.14, "P": 0.10, "K": 0.12, "humidity": 0.19, "rainfall": 0.16}
    explanation = build_explanation(features, feature_importance, "mothbeans", "spring")
    assert explanation["crop"] == "mothbeans"
    # every value here is far outside its comfort range, so no factors qualify —
    # the frontend falls back to a generic "closest match" message in that case
    assert explanation["factors"] == []
