# Crop Images

Real representative photos for all 22 supported crops, fetched from Wikipedia article lead
images (Wikimedia Commons) via [`ml/scripts/fetch_crop_images.py`](../../ml/scripts/fetch_crop_images.py).
See [`CREDITS.md`](CREDITS.md) for source attribution per image.

These are duplicated into `frontend/public/crop-images/` (what the app actually serves) —
run the fetch script again after adding a new crop to `ml/data/crop_metadata.json`, or drop
in your own licensed/self-photographed replacement using the same filename.

If an image is ever missing, `CropCard.tsx` falls back to a branded gradient + leaf icon
placeholder rather than a broken image.
