# Real dataset source

`crop_recommendation_public_22crops.csv` is the widely-used public "Crop
Recommendation Dataset" (2200 rows, 22 crops, columns: N, P, K, temperature,
humidity, ph, rainfall, label). It originates from precision-agriculture
research combining rainfall/climate data, fertilizer data, and Indian soil
survey data, and has been mirrored on Kaggle and numerous public GitHub repos
since (e.g. https://github.com/gireesh777/Crop_Recommendation_System_using_ML,
https://www.kaggle.com/datasets/atharvaingle/crop-recommendation-dataset).
This copy was fetched directly from a public GitHub mirror.

## How it's used

`ml/scripts/generate_dataset.py` uses these 2200 real rows as ground truth for
the 22 crops they cover. The public dataset does not include `season`,
`location`, or `moisture` columns (HealTheCrop's model uses all three), so
those are added on top of the real N/P/K/temperature/humidity/ph/rainfall
values:

- `season`: assigned from each crop's known cultivation season (e.g. rice is
  grown in Kharif) — a fixed agronomic fact, not sampled.
- `location`: assigned via the same regional-affinity weighted sampling used
  for the fully-synthetic crops (see `CROP_REGIONAL_AFFINITY` in
  `generate_dataset.py`), so the real rows carry the same location signal.
- `moisture`: soil moisture isn't part of the original dataset. It's derived
  from each crop's own humidity and rainfall requirements (crops needing more
  atmospheric humidity/rainfall are grown in wetter soil) plus per-row noise —
  a standard agronomic proxy, not a fabricated number, and documented as
  derived rather than measured.

The remaining 30 crops beyond this dataset's 22 are generated synthetically
from FAO/ICAR agronomic reference ranges (see `CROP_PROFILES` in
`generate_dataset.py`) exactly as before — HealTheCrop is transparent that
this portion is synthetic-but-realistic, not scraped or measured data.
