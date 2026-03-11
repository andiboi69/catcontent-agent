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

# Content formats — educational, cute, satisfying (works with stock footage)
CONTENT_FORMATS = [
    "cat_facts",            # "Cat facts you didn't know" — mind-blowing facts
    "cat_breeds",           # "Most beautiful cat breeds" — breed showcase
    "reasons_to_get_cat",   # "Reasons to get a cat" — persuasive/heartwarming
    "signs_cat_loves_you",  # "Signs your cat loves you" — cat body language
    "cat_psychology",       # "What your cat is ACTUALLY thinking" — behavior explained
    "cat_vs_dog",           # "Cat vs Dog — who wins?" — fun comparison
    "cat_myths",            # "Cat myths DEBUNKED" — surprising truths
    "cat_tips",             # "Things I wish I knew before getting a cat"
]

# Video settings
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920  # Vertical for Shorts
SHORTS_MAX_DURATION = 59  # seconds
LONGFORM_TARGET_DURATION = 480  # 8 minutes

# Output directory
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
