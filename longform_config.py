"""
Long-form video configuration — constants specific to 8-10 min landscape videos.
Imports shared config from config.py.
"""

from config import GROQ_API_KEY, PEXELS_API_KEY, CONTENT_FORMATS, OUTPUT_DIR

# Video dimensions — landscape for regular YouTube
TARGET_WIDTH = 1920
TARGET_HEIGHT = 1080
TARGET_FPS = 30

# Clip timing
CLIP_DURATION = 7.0       # default clip length (seconds)
CLIP_MIN_DURATION = 5.0   # minimum even with short voiceover
CLIP_PADDING = 1.0        # breathing room after voiceover
FADE_DURATION = 0.5       # fade in/out per clip

# Audio
AUDIO_RATE = 24000
AUDIO_CHANNELS = 1
MUSIC_VOL_WITH_VOICE = "0.12"   # much lower than Shorts (0.25)
MUSIC_VOL_NO_VOICE = "0.35"
VOICE_VOL = "2.0"

# Script
LONGFORM_SCENE_COUNT = "25-30"
LONGFORM_TARGET_DURATION = 540  # ~9 minutes

# Chapter card
CHAPTER_CARD_DURATION = 3.0
INTRO_DURATION = 5.0
OUTRO_DURATION = 5.0

# Content formats — expanded for long-form (deeper topics work better)
LONGFORM_CONTENT_FORMATS = CONTENT_FORMATS + [
    "cat_history",          # "The Ancient History of Cats" — deep dive
    "cat_science",          # "The Science Behind Cat Behavior"
    "cat_breeds_deep",      # "Complete Guide to Cat Breeds"
    "cat_communication",    # "How Cats Actually Talk to You"
]
