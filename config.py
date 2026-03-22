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

# Content formats — funny only (best performing style)
CONTENT_FORMATS = [
    "funny_cat_facts",      # "Hilarious cat facts" — funny, meme-like tone
]

# Video settings
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920  # Vertical for Shorts
SHORTS_MAX_DURATION = 59  # seconds
LONGFORM_TARGET_DURATION = 480  # 8 minutes

# Output directory
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
