"""
Regression tests for per-language content in DiseaseDetectionService._kb_entry.

The knowledge base stores translations under entry["translations"][lang] for
a fixed set of user-facing fields; everything else (scientific_name, product
names, sources) must stay in English regardless of the requested language.
When a requested language has no translation for a given entry, the service
must fall back to English and say so via content_language, rather than
silently mixing languages.
"""
from app.cv.disease_service import DiseaseDetectionService


def _service_with_fake_kb():
    service = DiseaseDetectionService.__new__(DiseaseDetectionService)
    service.knowledge_base = {
        "Healthy": {
            "display_name": "Healthy Plant", "description": "No issues detected.",
            "organic_treatment": "None", "chemical_treatment": "None",
            "recommended_pesticides": [], "prevention_tips": [], "expected_recovery_days": 0,
        },
        "Rice___Rice_blast": {
            "display_name": "Rice Blast (Rice)",
            "description": "Diamond-shaped lesions on leaves.",
            "scientific_name": "Pyricularia oryzae Cavara",
            "organic_treatment": "Use resistant varieties.",
            "chemical_treatment": "Carbendazim 50% WP",
            "recommended_pesticides": ["Carbendazim 50% WP"],
            "prevention_tips": ["Use resistant varieties"],
            "expected_recovery_days": 14,
            "translations": {
                "hi": {
                    "display_name": "चावल का ब्लास्ट रोग (चावल)",
                    "description": "पत्तियों पर हीरे के आकार के धब्बे।",
                    "organic_treatment": "प्रतिरोधी किस्मों का उपयोग करें।",
                    "chemical_treatment": "Carbendazim 50% WP",
                    "prevention_tips": ["प्रतिरोधी किस्मों का उपयोग करें"],
                }
            },
        },
    }
    service.cnn_model = None
    service.class_indices = None
    return service


def test_kb_entry_defaults_to_english():
    service = _service_with_fake_kb()
    entry = service._kb_entry("Rice___Rice_blast", "en")
    assert entry["content_language"] == "en"
    assert entry["display_name"] == "Rice Blast (Rice)"


def test_kb_entry_returns_translated_fields_when_available():
    service = _service_with_fake_kb()
    entry = service._kb_entry("Rice___Rice_blast", "hi")
    assert entry["content_language"] == "hi"
    assert entry["display_name"] == "चावल का ब्लास्ट रोग (चावल)"
    assert entry["description"] == "पत्तियों पर हीरे के आकार के धब्बे।"
    assert entry["prevention_tips"] == ["प्रतिरोधी किस्मों का उपयोग करें"]
    # Scientific name must never be translated.
    assert entry["scientific_name"] == "Pyricularia oryzae Cavara"


def test_kb_entry_falls_back_to_english_when_translation_missing():
    """An entry with no translations dict at all (e.g. 'Healthy') must not
    crash and must report content_language="en" honestly rather than
    claiming the requested language."""
    service = _service_with_fake_kb()
    entry = service._kb_entry("Healthy", "hi")
    assert entry["content_language"] == "en"
    assert entry["display_name"] == "Healthy Plant"


def test_kb_entry_falls_back_when_specific_language_not_translated():
    service = _service_with_fake_kb()
    entry = service._kb_entry("Rice___Rice_blast", "ta")
    assert entry["content_language"] == "en"
    assert entry["display_name"] == "Rice Blast (Rice)"
