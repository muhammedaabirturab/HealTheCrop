# Crop Images

Add real crop photos here (and to `frontend/public/crop-images/`, which is what the app
actually serves) named to match `ml/data/crop_metadata.json`'s `"image"` field for each
crop, e.g. `rice.jpg`, `maize.jpg`, `banana.jpg`.

No photos are bundled by default — recruiters/graders can drop in licensed or
self-photographed images without any code changes. Until then, `CropCard.tsx` gracefully
falls back to a branded gradient + leaf icon placeholder (see
`frontend/src/components/CropCard.tsx`), so the UI never shows a broken image.
