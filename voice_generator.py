"""
Voice Generator — Uses Edge TTS (free) to generate voiceover narration.
Rotates between different voices for variety.
"""

import os
import asyncio
import random
import edge_tts
from config import VOICES, FUNNY_VOICES


def get_random_voice(content_format=None):
    """Pick a random voice. Funny formats get a funny voice."""
    if content_format == "funny_cat_facts":
        return random.choice(FUNNY_VOICES)
    return random.choice(VOICES)


def _get_rate(voice):
    """Get speech rate based on voice. Funny voices are faster."""
    if voice in FUNNY_VOICES:
        return "+15%"
    return "-5%"


async def _generate_speech(text, output_path, voice=None):
    """Internal async function to generate speech."""
    if voice is None:
        voice = get_random_voice()

    rate = _get_rate(voice)
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_path)
    return output_path


def generate_voiceover(text, output_path, voice=None):
    """Generate voiceover audio from text.

    Args:
        text: The narration text
        output_path: Where to save the .mp3 file
        voice: Specific voice to use, or random if None

    Returns:
        path to the generated audio file
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    asyncio.run(_generate_speech(text, output_path, voice))
    return output_path


def generate_scene_voiceovers(scenes, output_dir, voice=None):
    """Generate voiceover for each scene in a script.

    Uses the same voice for all scenes in one video (consistency).

    Args:
        scenes: list of scene dicts with 'narration' field
        output_dir: directory to save audio files
        voice: voice to use for all scenes, or random if None

    Returns:
        list of audio file paths
    """
    if voice is None:
        voice = get_random_voice()

    audio_dir = os.path.join(output_dir, "audio")
    os.makedirs(audio_dir, exist_ok=True)

    paths = []
    for i, scene in enumerate(scenes):
        narration = scene.get("narration", "")
        if not narration:
            paths.append(None)
            continue

        audio_path = os.path.join(audio_dir, f"scene_{i+1:02d}.mp3")
        print(f"  Generating voiceover for scene {i+1}...")
        generate_voiceover(narration, audio_path, voice=voice)
        paths.append(audio_path)

    return paths


def generate_full_voiceover(script, output_dir, voice=None):
    """Generate a single voiceover file for the entire script.

    Args:
        script: script dict with 'scenes' list
        output_dir: directory to save audio file
        voice: voice to use, or random if None

    Returns:
        path to the combined audio file
    """
    if voice is None:
        voice = get_random_voice()

    # Combine all narration with pauses
    full_text = ""
    for scene in script["scenes"]:
        narration = scene.get("narration", "")
        if narration:
            full_text += narration + " ... "

    audio_dir = os.path.join(output_dir, "audio")
    audio_path = os.path.join(audio_dir, "full_voiceover.mp3")
    generate_voiceover(full_text.strip(), audio_path, voice=voice)
    return audio_path
