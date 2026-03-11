"""
Video Assembler v5 — Rapid-fire compilation style.
Ultra-fast cuts (1.5s), flash transitions, sound effects between clips.
No boring hook frames — start with action immediately.
"""

import os
import sys
import subprocess
import random
import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def _find_font():
    """Find a usable font path across Windows and Linux."""
    candidates = [
        # Windows
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/Impact.ttf",
        # Linux (Ubuntu/Debian)
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for font in candidates:
        if os.path.exists(font):
            # FFmpeg drawtext uses colon as separator — escape Windows paths
            path = font.replace("\\", "/").replace(":", "\\\\:")
            return path
    return None


FONT_PATH = _find_font()

# Clip settings
TARGET_FPS = 30
TARGET_WIDTH = 720
TARGET_HEIGHT = 1280
CLIP_DURATION = 2.5  # fast enough to keep attention, slow enough to read facts
HOOK_DURATION = 1.5  # hook clip at the start

# Hook templates — short, fits on screen (max 20 chars)
HOOK_TEMPLATES = [
    "Wait for #1...",
    "Watch till the end",
    "#1 will SHOCK you",
    "Stay for #1",
    "Did you know?",
    "Cat lovers ONLY",
    "Mind = Blown",
    "True or false?",
    "You had NO idea",
    "POV cat facts",
]


def get_media_duration(filepath):
    """Get duration of a media file in seconds."""
    cmd = [FFMPEG, "-i", filepath, "-f", "null", "-"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        for line in result.stderr.split("\n"):
            if "Duration:" in line:
                time_str = line.split("Duration:")[1].split(",")[0].strip()
                parts = time_str.split(":")
                return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    except Exception:
        pass
    return 0


def escape_text(text):
    """Escape text for FFmpeg drawtext filter."""
    return (text
        .replace("\\", "\\\\\\\\")
        .replace("'", "\u2019")
        .replace(":", " ")
        .replace("%", " percent")
        .replace(";", " ")
        .replace('"', "")
    )


def generate_flash_frame(output_path, duration=0.1):
    """Generate a quick white flash frame for transitions."""
    cmd = [
        FFMPEG, "-y",
        "-f", "lavfi",
        "-i", f"color=c=white:s={TARGET_WIDTH}x{TARGET_HEIGHT}:d={duration}:r={TARGET_FPS}",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-r", str(TARGET_FPS),
        "-an",
        output_path
    ]
    subprocess.run(cmd, capture_output=True, text=True)
    return output_path


def generate_boom_sound(output_path, freq=150, duration=0.15):
    """Generate a punchy bass boom sound effect."""
    cmd = [
        FFMPEG, "-y",
        "-f", "lavfi",
        "-i", f"sine=frequency={freq}:duration={duration}",
        "-af", f"afade=t=in:d=0.01,afade=t=out:d={duration*0.7},volume=0.6,bass=g=10",
        "-c:a", "aac",
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # Simpler fallback without bass filter
        cmd = [
            FFMPEG, "-y",
            "-f", "lavfi",
            "-i", f"sine=frequency={freq}:duration={duration}",
            "-af", f"afade=t=in:d=0.01,afade=t=out:d={duration*0.7},volume=0.6",
            "-c:a", "aac",
            output_path
        ]
        subprocess.run(cmd, capture_output=True, text=True)
    return output_path


def generate_hook_clip(footage_path, output_path, hook_text=None):
    """Generate a 1.5s hook clip with eye-catching text over the first scene's footage."""
    if hook_text is None:
        hook_text = random.choice(HOOK_TEMPLATES)

    safe_text = escape_text(hook_text)

    actual_dur = get_media_duration(footage_path)
    input_args = ["-i", footage_path, "-t", str(HOOK_DURATION)]

    filters = [
        f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase",
        f"crop={TARGET_WIDTH}:{TARGET_HEIGHT}",
        f"fps={TARGET_FPS}",
        # Darken the footage slightly for text contrast
        "eq=brightness=-0.1:saturation=1.2",
        # Large centered hook text
        f"drawtext=text='{safe_text}'"
        f"{':fontfile=' + FONT_PATH if FONT_PATH else ''}"
        f":fontsize=56:fontcolor=yellow:borderw=4:bordercolor=black"
        f":x=(w-text_w)/2:y=(h-text_h)/2",
    ]

    vf = ",".join(filters)

    cmd = [
        FFMPEG, "-y",
        *input_args,
        "-vf", vf,
        "-t", str(HOOK_DURATION),
        "-c:v", "libx264",
        "-preset", "fast",
        "-pix_fmt", "yuv420p",
        "-r", str(TARGET_FPS),
        "-an",
        "-movflags", "+faststart",
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    return output_path


def normalize_clip(input_path, output_path, duration=CLIP_DURATION, caption=None):
    """Normalize a clip: scale to vertical, add caption."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    actual_dur = get_media_duration(input_path)
    if actual_dur <= 0:
        actual_dur = duration

    source_duration = duration

    # Build input args — keep it simple to avoid seek issues
    input_args = []
    if actual_dur < source_duration:
        input_args = ["-stream_loop", "-1", "-i", input_path, "-t", str(source_duration)]
    elif actual_dur > source_duration + 2:
        # Skip into the clip a bit for variety, but keep it safe
        skip = random.uniform(0.5, min(actual_dur - source_duration - 0.5, 5.0))
        input_args = ["-ss", str(round(skip, 1)), "-i", input_path, "-t", str(source_duration)]
    else:
        input_args = ["-i", input_path, "-t", str(source_duration)]

    # Video filter chain — simple and reliable
    filters = [
        f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase",
        f"crop={TARGET_WIDTH}:{TARGET_HEIGHT}",
        f"fps={TARGET_FPS}",
    ]

    # Caption overlay — clean centered text
    if caption:
        safe_text = escape_text(caption)
        # Semi-transparent dark bar
        filters.append(f"drawbox=x=0:y=40:w=iw:h=180:color=black@0.6:t=fill")
        # Main text — large, white, clean
        filters.append(
            f"drawtext=text='{safe_text}'"
            f"{':fontfile=' + FONT_PATH if FONT_PATH else ''}"
            f":fontsize=52:fontcolor=white:borderw=3:bordercolor=black"
            f":x=(w-text_w)/2:y=85"
        )

    vf = ",".join(filters)

    cmd = [
        FFMPEG, "-y",
        *input_args,
        "-vf", vf,
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "fast",
        "-pix_fmt", "yuv420p",
        "-r", str(TARGET_FPS),
        "-an",
        "-movflags", "+faststart",
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        # Debug: check for malloc/memory errors
        if "malloc" in result.stderr:
            print(f"    Memory error — trying without text overlay")
        # Fallback: simplest possible
        filters_simple = [
            f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase",
            f"crop={TARGET_WIDTH}:{TARGET_HEIGHT}",
            f"fps={TARGET_FPS}",
        ]
        if caption:
            safe_text = escape_text(caption)
            filters_simple.append(f"drawbox=x=0:y=50:w=iw:h=160:color=black@0.7:t=fill")
            filters_simple.append(
                f"drawtext=text='{safe_text}'"
                f"{':fontfile=' + FONT_PATH if FONT_PATH else ''}"
                f":fontsize=58:fontcolor=white:borderw=4:bordercolor=black"
                f":x=(w-text_w)/2:y=80"
            )

        cmd_fallback = [
            FFMPEG, "-y",
            "-i", input_path,
            "-t", str(duration),
            "-vf", ",".join(filters_simple),
            "-c:v", "libx264",
            "-preset", "fast",
            "-pix_fmt", "yuv420p",
            "-r", str(TARGET_FPS),
            "-an",
            "-movflags", "+faststart",
            output_path
        ]
        subprocess.run(cmd_fallback, capture_output=True, text=True)

    return output_path


def concat_clips(clip_paths, output_path):
    """Concatenate normalized clips using TS intermediate format."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    temp_dir = os.path.dirname(output_path)

    ts_files = []
    for i, clip in enumerate(clip_paths):
        ts_path = os.path.join(temp_dir, f"temp_{i:02d}.ts")
        cmd = [
            FFMPEG, "-y", "-i", clip,
            "-c:v", "copy", "-bsf:v", "h264_mp4toannexb",
            "-f", "mpegts", ts_path
        ]
        subprocess.run(cmd, capture_output=True, text=True)
        if os.path.exists(ts_path) and os.path.getsize(ts_path) > 0:
            ts_files.append(ts_path)

    if not ts_files:
        return None

    ts_list = "|".join(f.replace("\\", "/") for f in ts_files)
    concat_output = os.path.join(temp_dir, "concat_no_audio.mp4")

    cmd = [
        FFMPEG, "-y",
        "-i", f"concat:{ts_list}",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        concat_output
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    for ts in ts_files:
        if os.path.exists(ts):
            os.remove(ts)

    if result.returncode != 0:
        print(f"    Concat error: {result.stderr[-300:]}")
        return None

    os.replace(concat_output, output_path)
    return output_path


def add_background_music(video_path, music_path, output_path):
    """Mix background music behind the video."""
    cmd = [
        FFMPEG, "-y",
        "-i", video_path,
        "-i", music_path,
        "-filter_complex",
        "[1:a]volume=0.35,aloop=loop=-1:size=2e+09[music];[music]atrim=duration=120[trimmed]",
        "-map", "0:v",
        "-map", "[trimmed]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        "-movflags", "+faststart",
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"    Music mixing failed, using video without music")
        if os.path.exists(video_path) and video_path != output_path:
            import shutil
            shutil.copy2(video_path, output_path)

    return output_path


def assemble_full_video(footage_data, audio_path, script, output_dir):
    """Rapid-fire compilation assembly:
    1. Normalize each clip (1.8s, sped up, caption)
    2. Insert flash frames between clips
    3. Concatenate everything
    4. Add background music (louder)
    """
    clips_dir = os.path.join(output_dir, "clips")
    os.makedirs(clips_dir, exist_ok=True)

    num_scenes = len(footage_data)

    # Generate flash transition frame once
    flash_path = os.path.join(clips_dir, "flash.mp4")
    generate_flash_frame(flash_path, duration=0.08)
    has_flash = os.path.exists(flash_path) and os.path.getsize(flash_path) > 100

    prepared_clips = []

    # Generate hook clip using first available footage
    first_footage = None
    for item in footage_data:
        if item["footage_path"] and os.path.exists(item["footage_path"]):
            first_footage = item["footage_path"]
            break

    if first_footage:
        hook_text = random.choice(HOOK_TEMPLATES)
        hook_path = os.path.join(clips_dir, "hook.mp4")
        print(f"  Hook: \"{hook_text}\"")
        hook_result = generate_hook_clip(first_footage, hook_path, hook_text)
        if hook_result and os.path.exists(hook_path) and os.path.getsize(hook_path) > 1000:
            prepared_clips.append(hook_path)
            if has_flash:
                prepared_clips.append(flash_path)

    for i, item in enumerate(footage_data):
        scene = item["scene"]
        footage_path = item["footage_path"]
        caption = scene.get("caption", "")

        clip_path = os.path.join(clips_dir, f"clip_{i + 1:02d}.mp4")

        if footage_path and os.path.exists(footage_path):
            print(f"  Clip {i + 1}/{num_scenes}: \"{caption}\"")
            normalize_clip(
                footage_path, clip_path, CLIP_DURATION, caption
            )

            if os.path.exists(clip_path) and os.path.getsize(clip_path) > 1000:
                # Add flash before each clip (except first after hook)
                if prepared_clips and has_flash and prepared_clips[-1] != flash_path:
                    prepared_clips.append(flash_path)
                prepared_clips.append(clip_path)
            else:
                print(f"    -> Failed, skipping")
        else:
            print(f"  Skipping scene {i + 1} (no footage)")

    if len(prepared_clips) < 2:
        print("  ERROR: Not enough clips to assemble!")
        return None

    # Concatenate
    title_slug = script["title"][:40].replace(" ", "_")
    for ch in "?!'\",:;()[]{}#@&*":
        title_slug = title_slug.replace(ch, "")

    no_music_path = os.path.join(output_dir, "no_music.mp4")
    print(f"  Stitching {len([c for c in prepared_clips if 'flash' not in c])} clips with flash transitions...")
    concat_result = concat_clips(prepared_clips, no_music_path)

    if not concat_result:
        return None

    # Add background music
    music_dir = os.path.join(os.path.dirname(__file__), "music")
    music_files = []
    if os.path.exists(music_dir):
        music_files = [
            os.path.join(music_dir, f) for f in os.listdir(music_dir)
            if f.endswith((".mp3", ".wav", ".m4a"))
        ]

    final_path = os.path.join(output_dir, f"{title_slug}.mp4")

    if music_files:
        music = random.choice(music_files)
        print(f"  Adding music: {os.path.basename(music)}")
        add_background_music(no_music_path, music, final_path)
    else:
        os.replace(no_music_path, final_path)

    # Cleanup
    if os.path.exists(no_music_path):
        try:
            os.remove(no_music_path)
        except OSError:
            pass

    return final_path
