import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

# Edge TTS voice options (rotate for variety)
VOICES = [
    "en-US-AriaNeural",       # Female, warm
    "en-US-GuyNeural",        # Male, casual
    "en-GB-SoniaNeural",      # British female
    "en-AU-NatashaNeural",    # Australian female
    "en-US-JennyNeural",      # Female, friendly
    "en-GB-RyanNeural",       # British male
]

# Funny content gets its own voice
FUNNY_VOICES = [
    "en-US-AnaNeural",        # Young/childlike, perfect for comedy
]

# Content formats — weighted by analytics (2026-06-12): "7 ways your cat
# shows love" listicles hit 8-13% like rates; roast comedy ("scammer/liar/
# vampire") dominates the bottom 50 videos. Duplicates = higher pick chance.
CONTENT_FORMATS = [
    "signs_cat_loves_you",  # Best engagement — body language decoded (3x)
    "signs_cat_loves_you",
    "signs_cat_loves_you",
    "cat_psychology",       # Strong views — what cats are thinking (2x)
    "cat_psychology",
    "cat_facts",            # Solid baseline — punchy facts (2x)
    "cat_facts",
    "funny_cat_facts",      # Comedy — high views but weak likes, keep 1x
]

# Video settings
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920  # Vertical for Shorts
SHORTS_MAX_DURATION = 59  # seconds
LONGFORM_TARGET_DURATION = 480  # 8 minutes

# Output directory
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
