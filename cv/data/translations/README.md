# Knowledge base translations

Every pest/disease/deficiency entry in `cv/data/disease_knowledge_base.json`
can carry a `translations` object, keyed by language code (`hi`, `kn`, `ta`,
`te`, `ml`), holding a localized copy of the fields a farmer actually reads:

```json
"Rice___Rice_blast": {
  "display_name": "Rice Blast (Rice)",
  "description": "Diamond-shaped lesions ...",
  "scientific_name": "Pyricularia oryzae Cavara",
  "...": "...",
  "translations": {
    "hi": {
      "display_name": "चावल का ब्लास्ट रोग (चावल)",
      "description": "पत्तियों पर हीरे के आकार के धब्बे ...",
      "organic_treatment": "...",
      "biological_control": "...",
      "chemical_treatment": "...",
      "dosage_guidance": "...",
      "safety_precautions": "...",
      "waiting_period_before_harvest": "...",
      "prevention_tips": ["...", "..."],
      "recovery_recommendations": "..."
    },
    "kn": { "...": "..." }
  }
}
```

## What gets translated, and what doesn't

Translated per language: `display_name`, `description`, `organic_treatment`,
`biological_control`, `chemical_treatment` (connector prose only),
`dosage_guidance` (connector prose only), `safety_precautions`,
`waiting_period_before_harvest`, `prevention_tips`, `recovery_recommendations`.

Deliberately **not** translated, in any language:

- `scientific_name` — always the Latin binomial, unchanged.
- `recommended_pesticides` / `recommended_insecticide` / `recommended_fungicide`
  — exact registered product names and formulation codes (e.g. "Mancozeb 75%
  WP") stay in Roman script in every language. A farmer matches this string
  against the physical product label at the shop; transliterating or
  translating it would break that match and is not how real Indian
  agricultural extension material handles chemical names either.
- Embedded chemical names/numbers/units *inside* `chemical_treatment` and
  `dosage_guidance` — only the connecting sentence structure is translated;
  the product name, percentage, quantity, and unit (g/ml/L/kg/%/ha/acre) are
  copied verbatim so a mistranslation can never alter a dose.
- `sources` — citation titles and publisher names stay in English, per
  standard bibliographic practice (they're the actual titles of the cited
  English-language government documents).
- `severity_level`, `category`, `type`, `applicable_crops`,
  `expected_recovery_days` — these are enums/numbers the frontend translates
  itself via `frontend/src/i18n/locales/*.json` (`pestDetection.severityLow`
  etc.), not free text stored per-entry.

## How translations are produced

`cv/data/translations/<lang>_chunk<N>.json` are raw translation-agent output —
each one covers a subset of `disease_knowledge_base.json` entries (split by
crop group to keep each translation job a manageable, reliably-completable
size) for one language. `cv/scripts/build_knowledge_base.py` merges every
`<lang>_chunk*.json` it finds into the corresponding entries' `translations`
dict when it rebuilds `disease_knowledge_base.json` — run it again any time a
new translation chunk is added:

```bash
python cv/scripts/build_knowledge_base.py
```

## How the backend serves the right language

`GET/POST /api/v1/pest/scan?lang=hi` — `backend/app/cv/disease_service.py`'s
`_kb_entry(key, lang)` looks up `entry["translations"][lang]` and overlays
those fields on top of the English base entry. Every detection in the
response carries `content_language`: the language actually used for that
entry's text. If a farmer requests `hi` but a specific entry has no Hindi
translation yet, `content_language` comes back `"en"` and the frontend shows
"This information is currently available only in English" for that card —
never a silent mix of Hindi labels wrapped around English content, and never
a fabricated translation.

## Adding a new language or filling gaps

Translate the untranslated fields listed above for the missing entries
(the `disease_knowledge_base.json` values themselves are the English source
of truth), save as `cv/data/translations/<lang>_chunk<N>.json` in the same
per-entry shape shown above, and re-run `build_knowledge_base.py`. No backend
or frontend code changes are needed — `SUPPORTED_LANGUAGES` in
`disease_service.py` already lists all 5 target languages; add a new code
there (and to the frontend's `frontend/src/i18n/locales/`) only if introducing
a language beyond Hindi/Kannada/Tamil/Telugu/Malayalam.
