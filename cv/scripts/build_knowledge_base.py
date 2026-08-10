"""
Builds cv/data/disease_knowledge_base.json from the raw government-source
extractions in cv/data/sources/*.json (each one produced by downloading an
official NIPHM — National Institute of Plant Health Management, Govt of
India — crop IPM Package PDF and mining its pest/disease/chemical-control
tables; see cv/data/sources/README.md).

This script only reshapes and lightly classifies already-sourced content —
it does not invent pesticide names, dosages, or biological control agents.
The few fields that are genuinely NOT present in any government IPM package
(severity_level, expected_recovery_days, recovery_recommendations — these
documents describe pest biology and control, not "days to heal") are filled
with clearly-labeled general estimates, documented in cv/data/sources/README.md,
rather than left blank or misrepresented as sourced.

Run after adding/updating a file in cv/data/sources/:

    python cv/scripts/build_knowledge_base.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES_DIR = ROOT / "cv" / "data" / "sources"
TRANSLATIONS_DIR = ROOT / "cv" / "data" / "translations"
OUTPUT_PATH = ROOT / "cv" / "data" / "disease_knowledge_base.json"
SUPPLEMENTARY_PATH = SOURCES_DIR / "supplementary_entries.json"
SUPPORTED_LANGUAGES = ["hi", "kn", "ta", "te", "ml"]

def classify_category(raw_category: str) -> tuple[str, str]:
    """Extraction agents wrote free-text category descriptions (e.g. 'fungal
    disease (oomycete)', 'bacterial disease (phytoplasma/MLO)', 'mite pest'),
    not a fixed enum — this matches by keyword rather than exact string so
    variants aren't silently dropped into the wrong (or default) bucket."""
    text = raw_category.strip().lower()
    if "physiological" in text:
        return "deficiency", "deficiency"
    if "nematode" in text:
        return "pest", "nematode"
    if "mite" in text:
        return "pest", "mite"
    if "viral" in text or "viroid" in text:
        return "disease", "viral"
    if "bacter" in text or "phytoplasma" in text:
        return "disease", "bacterial"
    if "fung" in text or "algal" in text:
        return "disease", "fungal"
    return "pest", "insect"

RECOVERY_DAYS_BY_CATEGORY = {
    "fungal": 14, "bacterial": 14, "viral": 0,
    "insect": 10, "mite": 10, "nematode": 21,
}

RECOVERY_NOTE_BY_TYPE = {
    "disease": "Follow the chemical/biological control schedule above; already-affected tissue will not repair itself, but new growth should be unaffected once the pathogen is controlled.",
    "pest": "Monitor the field after treatment to confirm the pest population has dropped below the economic threshold; already-damaged plant parts will not recover, but the plant can resume normal growth once feeding pressure stops.",
    "deficiency": "This is a physiological/non-biotic disorder rather than a pest or pathogen — correcting the underlying cultural or storage condition it stems from is the primary remedy; already-affected tissue will not reverse.",
}

SEVERITY_HIGH_KEYWORDS = [
    "national-significance", "national significance", "epidemic", "devastat",
    "major economic", "yield loss", "critical",
]


def infer_severity(symptoms: str) -> str:
    text = symptoms.lower()
    if any(kw in text for kw in SEVERITY_HIGH_KEYWORDS):
        return "High"
    if "regional-significance" in text or "regional significance" in text:
        return "Moderate"
    return "Moderate"


def slugify(name: str) -> str:
    cleaned = re.sub(r"[^\w\s/-]", "", name)
    cleaned = cleaned.replace("/", "_").replace("-", "_")
    cleaned = re.sub(r"\s+", "_", cleaned.strip())
    return cleaned


def build_entry(crop: str, item: dict, raw_category: str, source: dict) -> tuple[str, dict]:
    entry_type, category = classify_category(raw_category)
    key = f"{slugify(crop)}___{slugify(item['name'])}"

    chemical_control = item.get("chemical_control", "") or "Not applicable — see cultural/biological control."
    dosage = item.get("dosage", "") or "Not stated in the source document — follow the product's CIBRC-approved label."
    cultural = item.get("cultural_control", "") or ""
    biological = item.get("biological_control", "") or "Not specifically detailed in the source document."

    prevention_tips = [tip.strip().rstrip(".") for tip in re.split(r";\s*", cultural) if tip.strip()] or [
        "Follow general good agricultural practice for this crop."
    ]
    recommended_pesticides = [p.strip() for p in re.split(r";\s*", chemical_control) if p.strip()]

    entry = {
        "display_name": f"{item['name']} ({crop})",
        "type": entry_type,
        "category": category,
        "scientific_name": item.get("scientific_name"),
        "applicable_crops": [crop],
        "description": item.get("symptoms", ""),
        "severity_level": infer_severity(item.get("symptoms", "")),
        "organic_treatment": cultural or "Refer to biological control measures below; no separate organic-only chemistry is specified in the source document.",
        "biological_control": biological,
        "chemical_treatment": chemical_control,
        "recommended_pesticides": recommended_pesticides,
        "recommended_insecticide": chemical_control if entry_type == "pest" else None,
        "recommended_fungicide": chemical_control if category == "fungal" else None,
        "dosage_guidance": dosage,
        "safety_precautions": source.get("general_safety_precautions"),
        "waiting_period_before_harvest": source.get("waiting_period_notes"),
        "prevention_tips": prevention_tips,
        "recovery_recommendations": RECOVERY_NOTE_BY_TYPE[entry_type],
        "expected_recovery_days": RECOVERY_DAYS_BY_CATEGORY.get(category, 14),
        "sources": [{
            "title": source.get("source_title", f"NIPHM IPM Package for {crop}"),
            "publisher": "National Institute of Plant Health Management (NIPHM), Directorate of Plant Protection Quarantine & Storage, Ministry of Agriculture & Farmers Welfare, Government of India",
            "url": source.get("source_url"),
        }],
    }
    return key, entry


def main():
    knowledge_base: dict[str, dict] = {}
    skipped = []

    source_files = sorted(SOURCES_DIR.glob("niphm_*.json"))
    for path in source_files:
        data = json.loads(path.read_text(encoding="utf-8"))
        for crop, source in data.items():
            if "error" in source:
                skipped.append((crop, source["error"]))
                continue
            for pest in source.get("pests", []):
                key, entry = build_entry(crop, pest, pest.get("category", "insect pest"), source)
                knowledge_base[key] = entry
            for disease in source.get("diseases", []):
                key, entry = build_entry(crop, disease, disease.get("category", "fungal disease"), source)
                knowledge_base[key] = entry

    if SUPPLEMENTARY_PATH.exists():
        supplementary = json.loads(SUPPLEMENTARY_PATH.read_text(encoding="utf-8"))
        knowledge_base.update({k: v for k, v in supplementary.items() if not k.startswith("_")})

    translation_counts = {}
    for lang in SUPPORTED_LANGUAGES:
        merged: dict[str, dict] = {}
        for chunk_path in sorted(TRANSLATIONS_DIR.glob(f"{lang}_chunk*.json")):
            try:
                merged.update(json.loads(chunk_path.read_text(encoding="utf-8")))
            except json.JSONDecodeError as exc:
                # A translation agent may still be mid-write when this runs —
                # skip an unparseable chunk rather than aborting the whole build.
                print(f"Skipping {chunk_path.name} (invalid JSON, likely still being written): {exc}")
        applied = 0
        for key, localized_fields in merged.items():
            if key in knowledge_base:
                knowledge_base[key].setdefault("translations", {})[lang] = localized_fields
                applied += 1
        translation_counts[lang] = applied

    OUTPUT_PATH.write_text(json.dumps(knowledge_base, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(knowledge_base)} entries to {OUTPUT_PATH}")
    if skipped:
        print("Skipped (extraction errors, not included):")
        for crop, err in skipped:
            print(f"  - {crop}: {err}")
    for lang, count in translation_counts.items():
        print(f"Translations applied for '{lang}': {count}/{len(knowledge_base)}")


if __name__ == "__main__":
    main()
