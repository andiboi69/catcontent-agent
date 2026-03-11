"""
Thumbnail Generator — Creates YouTube thumbnails from Pexels cat photos + text overlay.
Uses Pillow (no paid API needed).
"""

import os
import requests
import random
from PIL import Image, ImageDraw, ImageFont
from config import PEXELS_API_KEY


PEXELS_PHOTO_URL = "https://api.pexels.com/v1/search"
HEADERS = {"Authorization": PEXELS_API_KEY}

# Eye-catching colors for thumbnail text
COLORS = [
    "#FFFF00",  # Yellow
    "#FF0000",  # Red
    "#00FF00",  # Green
    "#FFFFFF",  # White
    "#FF6600",  # Orange
]


def find_thumbnail_photo(keywords):
    """Find a cute/dramatic cat photo for thumbnail.

    Args:
        keywords: list of search terms

    Returns:
        URL of the photo
    """
    query = " ".join(keywords) if isinstance(keywords, list) else keywords
    params = {
        "query": f"cat {query}",
        "per_page": 10,
        "orientation": "landscape",
    }
    resp = requests.get(PEXELS_PHOTO_URL, headers=HEADERS, params=params)
    resp.raise_for_status()
    photos = resp.json().get("photos", [])

    if photos:
        photo = random.choice(photos[:5])  # Pick from top 5
        return photo["src"]["large2x"]

    return None


def download_photo(url, output_path):
    """Download a photo from URL."""
    resp = requests.get(url, stream=True)
    resp.raise_for_status()
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(8192):
            f.write(chunk)
    return output_path


def create_thumbnail(photo_path, text, output_path):
    """Create a YouTube thumbnail with text overlay.

    Args:
        photo_path: path to background cat photo
        text: text to overlay (2-4 words max)
        output_path: where to save the thumbnail

    Returns:
        path to thumbnail
    """
    # YouTube thumbnail size
    thumb_w, thumb_h = 1280, 720

    # Open and resize photo
    img = Image.open(photo_path)
    img = img.resize((thumb_w, thumb_h), Image.LANCZOS)

    draw = ImageDraw.Draw(img)

    # Add dark gradient overlay at bottom for text readability
    for y in range(thumb_h // 2, thumb_h):
        alpha = int(180 * (y - thumb_h // 2) / (thumb_h // 2))
        draw.line([(0, y), (thumb_w, y)], fill=(0, 0, 0, alpha))

    # Add text
    color = random.choice(COLORS)

    # Try to use a bold font, fall back to default
    font_size = 72
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except OSError:
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()

    # Center text at bottom third
    text_upper = text.upper()
    bbox = draw.textbbox((0, 0), text_upper, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    x = (thumb_w - text_w) // 2
    y = thumb_h - text_h - 80

    # Draw text outline (stroke)
    outline_color = "#000000"
    for dx in [-3, -2, 0, 2, 3]:
        for dy in [-3, -2, 0, 2, 3]:
            draw.text((x + dx, y + dy), text_upper, font=font, fill=outline_color)

    # Draw main text
    draw.text((x, y), text_upper, font=font, fill=color)

    img.save(output_path, "JPEG", quality=95)
    return output_path


def generate_thumbnail(script, output_dir):
    """Generate a thumbnail for a script.

    Args:
        script: script dict with thumbnail_text and search keywords
        output_dir: where to save files

    Returns:
        path to thumbnail image
    """
    os.makedirs(output_dir, exist_ok=True)

    # Get keywords from first scene for photo search
    keywords = []
    if script.get("scenes"):
        keywords = script["scenes"][0].get("search_keywords", ["cute cat"])

    thumb_text = script.get("thumbnail_text", "OMG CATS")

    print(f"  Finding thumbnail photo...")
    photo_url = find_thumbnail_photo(keywords)

    if not photo_url:
        print("  -> No photo found for thumbnail")
        return None

    photo_path = os.path.join(output_dir, "thumb_bg.jpg")
    download_photo(photo_url, photo_path)

    thumb_path = os.path.join(output_dir, "thumbnail.jpg")
    create_thumbnail(photo_path, thumb_text, thumb_path)
    print(f"  -> Thumbnail saved: {thumb_path}")

    return thumb_path
