"""
Downloads one representative photo per crop from Wikipedia's REST summary API
(https://en.wikipedia.org/api/rest_v1/page/summary/<title>), which surfaces each
article's lead image from Wikimedia Commons. Commons images are almost always
CC-BY-SA, CC0, or public domain — freely reusable with attribution, unlike an
arbitrary scraped image whose license and provenance are unknown. Attribution
for every downloaded image is recorded in assets/crop_images/CREDITS.md.

Usage:
    pip install pillow requests
    python ml/scripts/fetch_crop_images.py
"""
import json
import sys
import time
import urllib.request
from io import BytesIO
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
TARGET_DIRS = [
    ROOT / "frontend" / "public" / "crop-images",
    ROOT / "assets" / "crop_images",
]
MAX_WIDTH = 900
JPEG_QUALITY = 82

# crop key (matches ml/data/crop_metadata.json "image" filenames) -> candidate
# Wikipedia article titles, tried in order until one resolves with an image.
CROPS: dict[str, list[str]] = {
    "rice": ["Rice"],
    "maize": ["Maize"],
    "chickpea": ["Chickpea"],
    "kidneybeans": ["Kidney bean", "Common bean"],
    "pigeonpeas": ["Pigeon pea"],
    "mothbeans": ["Vigna aconitifolia", "Moth bean"],
    "mungbean": ["Mung bean"],
    "blackgram": ["Vigna mungo", "Black gram"],
    "lentil": ["Lentil"],
    "pomegranate": ["Pomegranate"],
    "banana": ["Banana"],
    "mango": ["Mango"],
    "grapes": ["Grape"],
    "watermelon": ["Watermelon"],
    "muskmelon": ["Muskmelon", "Cantaloupe"],
    "apple": ["Apple"],
    "orange": ["Orange (fruit)"],
    "papaya": ["Papaya"],
    "coconut": ["Coconut"],
    "cotton": ["Cotton"],
    "jute": ["Jute"],
    "coffee": ["Coffee"],
    "wheat": ["Wheat"],
    "sugarcane": ["Sugarcane"],
    "tea": ["Tea plant", "Camellia sinensis"],
    "groundnut": ["Peanut"],
    "soybean": ["Soybean"],
    "mustard": ["Mustard plant", "Brassica juncea"],
    "sunflower": ["Common sunflower", "Helianthus annuus"],
    "tomato": ["Tomato"],
    "onion": ["Onion"],
    "potato": ["Potato"],
    "garlic": ["Garlic"],
    "brinjal": ["Eggplant"],
    "cabbage": ["Cabbage"],
    "cauliflower": ["Cauliflower"],
    "okra": ["Okra"],
    "spinach": ["Spinach"],
    "cucumber": ["Cucumber"],
    "guava": ["Guava"],
    "turmeric": ["Turmeric"],
    "ginger": ["Ginger"],
    "blackpepper": ["Black pepper"],
    "cardamom": ["Cardamom"],
    "coriander": ["Coriander"],
    "fenugreek": ["Fenugreek"],
    "sorghum": ["Sorghum"],
    "pearlmillet": ["Pearl millet"],
    "fingermillet": ["Finger millet", "Eleusine coracana"],
    "carrot": ["Carrot"],
    "peas": ["Pea"],
    "sesame": ["Sesame"],
}

HEADERS = {"User-Agent": "HealTheCrop-Student-Project/1.0 (educational use; contact via GitHub repo)"}


def fetch_json(url: str) -> dict | None:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"  ! failed to fetch {url}: {exc}")
        return None


def fetch_bytes(url: str, retries: int = 4) -> bytes | None:
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.read()
        except Exception as exc:  # noqa: BLE001
            wait = 2 ** attempt * 2
            print(f"  ! download failed ({exc}); retrying in {wait}s...")
            time.sleep(wait)
    print(f"  ! giving up on {url}")
    return None


def resolve_image(titles: list[str]) -> tuple[str, str, str] | None:
    """Returns (image_url, page_title, page_url) for the first title with an image."""
    for title in titles:
        api_title = title.replace(" ", "_")
        summary = fetch_json(f"https://en.wikipedia.org/api/rest_v1/page/summary/{api_title}")
        if not summary:
            continue
        # Prefer the pre-sized thumbnail over "originalimage": Wikimedia's robot
        # policy throttles/blocks repeated full-resolution original fetches, but
        # thumbnails are served from a cache designed for exactly this kind of use.
        image = summary.get("thumbnail") or summary.get("originalimage")
        if image and image.get("source"):
            page_url = summary.get("content_urls", {}).get("desktop", {}).get("page", f"https://en.wikipedia.org/wiki/{api_title}")
            return image["source"], summary.get("title", title), page_url
    return None


def save_optimized(image_bytes: bytes, dest_paths: list[Path]) -> None:
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    if img.width > MAX_WIDTH:
        ratio = MAX_WIDTH / img.width
        img = img.resize((MAX_WIDTH, int(img.height * ratio)), Image.LANCZOS)
    for path in dest_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        img.save(path, "JPEG", quality=JPEG_QUALITY, optimize=True)


def main():
    for d in TARGET_DIRS:
        d.mkdir(parents=True, exist_ok=True)

    credits_path = TARGET_DIRS[1] / "CREDITS.md"
    existing_credit_lines: dict[str, str] = {}
    if credits_path.exists():
        for line in credits_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("- **"):
                crop_key = line.split("**")[1].removesuffix(".jpg")
                existing_credit_lines[crop_key] = line + "\n"

    credits = ["# Crop Image Credits\n", "\nAll images sourced from Wikipedia article lead images (Wikimedia Commons).\n\n"]
    failures = []

    for crop, titles in CROPS.items():
        dest_paths = [d / f"{crop}.jpg" for d in TARGET_DIRS]
        if all(p.exists() for p in dest_paths):
            print(f"[{crop}] already downloaded, skipping")
            if crop in existing_credit_lines:
                credits.append(existing_credit_lines[crop])
            continue

        print(f"[{crop}] resolving image via: {titles}")
        result = resolve_image(titles)
        if not result:
            print(f"  ! no image found for {crop}")
            failures.append(crop)
            continue
        image_url, page_title, page_url = result
        image_bytes = fetch_bytes(image_url)
        if not image_bytes:
            failures.append(crop)
            continue

        save_optimized(image_bytes, dest_paths)
        print(f"  -> saved {crop}.jpg (from '{page_title}')")
        credits.append(f"- **{crop}.jpg** — [{page_title}]({page_url}), via Wikipedia/Wikimedia Commons\n")
        time.sleep(1.5)  # be polite to the API and avoid rate limiting

    credits_path.write_text("".join(credits), encoding="utf-8")
    print(f"\nWrote credits to {credits_path}")

    if failures:
        print(f"\nFAILED for: {failures}")
        sys.exit(1)
    print(f"\nAll {len(CROPS)} crop images downloaded successfully.")


if __name__ == "__main__":
    main()
