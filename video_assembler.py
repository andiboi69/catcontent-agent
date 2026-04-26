"""
Video Assembler v5 — Rapid-fire compilation style.
Ultra-fast cuts (1.5s), flash transitions, sound effects between clips.
No boring hook frames — start with action immediately.
"""

import os
import sys
import json
import shutil
import subprocess
import random

# Find FFmpeg — prefer system install, fall back to imageio_ffmpeg
def _find_ffmpeg():
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"

FFMPEG = _find_ffmpeg()


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
            path = font.replace("\\", "/")
            # FFmpeg drawtext uses colon as separator — escape on Windows only
            if sys.platform == "win32":
                path = path.replace(":", "\\\\:")
            return path
    return None


FONT_PATH = _find_font()

# Clip settings
TARGET_FPS = 30
TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920
CLIP_DURATION = 2.5  # fallback if no voiceover
CLIP_MIN_DURATION = 1.8  # minimum clip length even with short voiceover
CLIP_PADDING = 0.15  # extra time after voiceover ends
HOOK_DURATION = 1.5  # hook clip at the start
AUDIO_RATE = 24000   # must match Edge TTS output (24kHz)
AUDIO_CHANNELS = 1   # mono

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
    """Generate a quick white flash frame for transitions (with silent audio for concat compat)."""
    cmd = [
        FFMPEG, "-y",
        "-f", "lavfi",
        "-i", f"color=c=white:s={TARGET_WIDTH}x{TARGET_HEIGHT}:d={duration}:r={TARGET_FPS}",
        "-f", "lavfi",
        "-i", f"anullsrc=r={AUDIO_RATE}:cl=mono:d={duration}",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-r", str(TARGET_FPS),
        "-c:a", "aac", "-ar", str(AUDIO_RATE), "-ac", str(AUDIO_CHANNELS),
        "-shortest",
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

    # Simple approach: generate video-only hook, then add silent audio track
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
        output_path + ".tmp.mp4"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None

    # Add silent audio for concat compatibility
    cmd2 = [
        FFMPEG, "-y",
        "-i", output_path + ".tmp.mp4",
        "-f", "lavfi", "-i", f"anullsrc=r={AUDIO_RATE}:cl=mono",
        "-c:v", "copy", "-c:a", "aac",
        "-ar", str(AUDIO_RATE), "-ac", str(AUDIO_CHANNELS),
        "-map", "0:v", "-map", "1:a",
        "-shortest",
        "-movflags", "+faststart",
        output_path
    ]
    result2 = subprocess.run(cmd2, capture_output=True, text=True)
    if os.path.exists(output_path + ".tmp.mp4"):
        os.remove(output_path + ".tmp.mp4")
    if result2.returncode != 0:
        return None
    return output_path


def normalize_clip(input_path, output_path, duration=CLIP_DURATION, caption=None, voiceover_path=None):
    """Normalize a clip: scale to vertical, add caption, optionally add voiceover.

    If voiceover_path is provided, clip duration syncs to voiceover length.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # If voiceover exists, sync clip duration to voice length
    if voiceover_path and os.path.exists(voiceover_path):
        voice_dur = get_media_duration(voiceover_path)
        if voice_dur > 0:
            duration = max(voice_dur + CLIP_PADDING, CLIP_MIN_DURATION)

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

    # Add voiceover as second input if available
    if voiceover_path and os.path.exists(voiceover_path):
        input_args += ["-i", voiceover_path]

    # Video filter chain — simple and reliable
    filters = [
        f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase",
        f"crop={TARGET_WIDTH}:{TARGET_HEIGHT}",
        f"fps={TARGET_FPS}",
    ]

    # Caption overlay — clean centered text, auto-sized to fit
    if caption:
        safe_text = escape_text(caption)
        # Scale font based on text length to prevent overflow
        text_len = len(caption)
        if text_len <= 15:
            fontsize = 78
        elif text_len <= 20:
            fontsize = 69
        elif text_len <= 25:
            fontsize = 60
        else:
            fontsize = 51
        bar_h = fontsize + 120
        text_y = 60 + (bar_h - fontsize) // 2
        # Semi-transparent dark bar
        filters.append(f"drawbox=x=0:y=60:w=iw:h={bar_h}:color=black@0.6:t=fill")
        # Main text — large, white, clean
        filters.append(
            f"drawtext=text='{safe_text}'"
            f"{':fontfile=' + FONT_PATH if FONT_PATH else ''}"
            f":fontsize={fontsize}:fontcolor=white:borderw=5:bordercolor=black"
            f":x=(w-text_w)/2:y={text_y}"
        )

    vf = ",".join(filters)

    # Build output args — include audio mapping if voiceover present
    has_voice = voiceover_path and os.path.exists(voiceover_path)
    if has_voice:
        audio_args = ["-map", "0:v", "-map", "1:a", "-c:a", "aac", "-ar", str(AUDIO_RATE), "-ac", str(AUDIO_CHANNELS), "-b:a", "128k", "-shortest"]
    else:
        audio_args = ["-an"]

    cmd = [
        FFMPEG, "-y",
        *input_args,
        "-vf", vf,
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "fast",
        "-pix_fmt", "yuv420p",
        "-r", str(TARGET_FPS),
        *audio_args,
        "-movflags", "+faststart",
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        # Print last few lines of FFmpeg error for debugging
        err_lines = result.stderr.strip().split("\n")
        print(f"    FFmpeg error: {err_lines[-1][:120] if err_lines else 'unknown'}")
        # Fallback: simplest possible (no voiceover)
        filters_simple = [
            f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase",
            f"crop={TARGET_WIDTH}:{TARGET_HEIGHT}",
            f"fps={TARGET_FPS}",
        ]
        if caption:
            safe_text = escape_text(caption)
            fb_fontsize = 60 if len(caption) > 20 else 72
            filters_simple.append(f"drawbox=x=0:y=75:w=iw:h=210:color=black@0.7:t=fill")
            filters_simple.append(
                f"drawtext=text='{safe_text}'"
                f"{':fontfile=' + FONT_PATH if FONT_PATH else ''}"
                f":fontsize={fb_fontsize}:fontcolor=white:borderw=5:bordercolor=black"
                f":x=(w-text_w)/2:y=120"
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

    # Ensure clip has audio track (silent if no voiceover) — required for concat
    if not has_voice and os.path.exists(output_path):
        tmp_path = output_path + ".tmp.mp4"
        os.replace(output_path, tmp_path)
        cmd_audio = [
            FFMPEG, "-y",
            "-i", tmp_path,
            "-f", "lavfi", "-i", f"anullsrc=r={AUDIO_RATE}:cl=mono",
            "-c:v", "copy", "-c:a", "aac",
            "-ar", str(AUDIO_RATE), "-ac", str(AUDIO_CHANNELS),
            "-map", "0:v", "-map", "1:a",
            "-shortest", "-movflags", "+faststart",
            output_path
        ]
        subprocess.run(cmd_audio, capture_output=True, text=True)
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    return output_path


def concat_clips(clip_paths, output_path):
    """Concatenate normalized clips using TS intermediate format."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    temp_dir = os.path.dirname(output_path)

    # Use concat demuxer (file list) instead of TS — preserves audio streams
    concat_list_path = os.path.join(temp_dir, "concat_list.txt")
    with open(concat_list_path, "w") as f:
        for clip in clip_paths:
            safe_path = clip.replace("\\", "/")
            f.write(f"file '{safe_path}'\n")

    concat_output = os.path.join(temp_dir, "concat_with_voice.mp4")

    cmd = [
        FFMPEG, "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_list_path,
        "-c:v", "libx264",
        "-c:a", "aac", "-ar", str(AUDIO_RATE), "-ac", str(AUDIO_CHANNELS),
        "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        concat_output
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if os.path.exists(concat_list_path):
        os.remove(concat_list_path)

    if result.returncode != 0:
        print(f"    Concat error: {result.stderr[-300:]}")
        # Fallback to old TS method (no audio)
        ts_files = []
        for i, clip in enumerate(clip_paths):
            ts_path = os.path.join(temp_dir, f"temp_{i:02d}.ts")
            cmd2 = [
                FFMPEG, "-y", "-i", clip,
                "-c:v", "copy", "-bsf:v", "h264_mp4toannexb",
                "-an", "-f", "mpegts", ts_path
            ]
            subprocess.run(cmd2, capture_output=True, text=True)
            if os.path.exists(ts_path) and os.path.getsize(ts_path) > 0:
                ts_files.append(ts_path)
        if not ts_files:
            return None
        ts_list = "|".join(f.replace("\\", "/") for f in ts_files)
        cmd3 = [
            FFMPEG, "-y", "-i", f"concat:{ts_list}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", concat_output
        ]
        subprocess.run(cmd3, capture_output=True, text=True)
        for ts in ts_files:
            if os.path.exists(ts):
                os.remove(ts)
        if not os.path.exists(concat_output):
            return None

    os.replace(concat_output, output_path)
    return output_path


def add_background_music(video_path, music_path, output_path, has_voiceover=False):
    """Mix background music behind the video with random tempo variation.

    If has_voiceover is True, keeps existing audio (voiceover) and mixes music underneath at lower volume.
    """
    # Random tempo shift so the same track sounds slightly different each time
    tempo = round(random.uniform(0.9, 1.12), 2)

    # Normalize music to -14dB first (loudnorm), then set as background level
    norm_filter = "loudnorm=I=-14:TP=-1:LRA=11"
    tempo_filter = f",atempo={tempo}" if tempo != 1.0 else ""

    # Lower music volume when voiceover is present so voice stays clear
    music_vol = "0.25" if has_voiceover else "0.5"

    if has_voiceover:
        # Mix voiceover (from video) + background music
        audio_chain = (
            f"[1:a]{norm_filter}{tempo_filter},aloop=loop=-1:size=2e+09[music];"
            f"[music]atrim=duration=120,volume={music_vol}[bg];"
            f"[0:a]volume=1.8[voice];"
            f"[voice][bg]amix=inputs=2:duration=first:dropout_transition=2[mixed]"
        )
        map_audio = "[mixed]"
    else:
        # No voiceover — just add music
        audio_chain = (
            f"[1:a]{norm_filter}{tempo_filter},aloop=loop=-1:size=2e+09[music];"
            f"[music]atrim=duration=120,volume={music_vol}[mixed]"
        )
        map_audio = "[mixed]"

    cmd = [
        FFMPEG, "-y",
        "-i", video_path,
        "-i", music_path,
        "-filter_complex", audio_chain,
        "-map", "0:v",
        "-map", map_audio,
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        "-movflags", "+faststart",
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        # Fallback: simple mix without loudnorm
        if has_voiceover:
            fallback_chain = (
                f"[1:a]volume=1.5,aloop=loop=-1:size=2e+09[music];"
                f"[music]atrim=duration=120[bg];"
                f"[0:a]volume=1.8[voice];"
                f"[voice][bg]amix=inputs=2:duration=first[mixed]"
            )
        else:
            fallback_chain = "[1:a]volume=5,aloop=loop=-1:size=2e+09[music];[music]atrim=duration=120[mixed]"

        cmd_simple = [
            FFMPEG, "-y",
            "-i", video_path,
            "-i", music_path,
            "-filter_complex", fallback_chain,
            "-map", "0:v",
            "-map", "[mixed]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest",
            "-movflags", "+faststart",
            output_path
        ]
        result2 = subprocess.run(cmd_simple, capture_output=True, text=True)
        if result2.returncode != 0:
            print(f"    Music mixing failed, using video without music")
            if os.path.exists(video_path) and video_path != output_path:
                import shutil
                shutil.copy2(video_path, output_path)

    return output_path


def assemble_full_video(footage_data, audio_path, script, output_dir, voiceover_paths=None):
    """Rapid-fire compilation assembly:
    1. Normalize each clip (duration synced to voiceover if available)
    2. Insert flash frames between clips
    3. Concatenate everything
    4. Add background music (mixed with voiceover)

    Args:
        voiceover_paths: list of per-scene audio paths (same length as footage_data), or None
    """
    clips_dir = os.path.join(output_dir, "clips")
    os.makedirs(clips_dir, exist_ok=True)

    num_scenes = len(footage_data)

    # Generate flash transition frame once
    flash_path = os.path.join(clips_dir, "flash.mp4")
    generate_flash_frame(flash_path, duration=0.08)
    has_flash = os.path.exists(flash_path) and os.path.getsize(flash_path) > 100

    prepared_clips = []

    for i, item in enumerate(footage_data):
        scene = item["scene"]
        footage_path = item["footage_path"]
        caption = scene.get("caption", "")

        # Get per-scene voiceover if available
        voice_path = None
        if voiceover_paths and i < len(voiceover_paths):
            voice_path = voiceover_paths[i]

        clip_path = os.path.join(clips_dir, f"clip_{i + 1:02d}.mp4")

        if footage_path and os.path.exists(footage_path):
            print(f"  Clip {i + 1}/{num_scenes}: \"{caption}\"")
            normalize_clip(
                footage_path, clip_path, CLIP_DURATION, caption, voice_path
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

    # Count actual content clips (exclude flash frames)
    content_clips = [c for c in prepared_clips if "flash" not in os.path.basename(c)]
    if len(content_clips) < 2:
        print("  ERROR: Not enough clips to assemble!")
        return None
    if len(content_clips) < 4:
        print(f"  WARNING: Only {len(content_clips)} clips — video will be short ({len(content_clips) * 2.5:.0f}s)")

    # Concatenate
    title_slug = script["title"][:40].replace(" ", "_")
    for ch in "?!'\",:;()[]{}#@&*":
        title_slug = title_slug.replace(ch, "")

    has_voiceover = voiceover_paths is not None and any(
        v and os.path.exists(v) for v in voiceover_paths
    ) if voiceover_paths else False

    no_music_path = os.path.join(output_dir, "no_music.mp4")
    print(f"  Stitching {len([c for c in prepared_clips if 'flash' not in c])} clips with flash transitions...")
    concat_result = concat_clips(prepared_clips, no_music_path)

    if not concat_result:
        return None

    # Add background music — pick based on content mood
    music_dir = os.path.join(os.path.dirname(__file__), "music")
    music_files = []
    if os.path.exists(music_dir):
        music_files = [
            os.path.join(music_dir, f) for f in os.listdir(music_dir)
            if f.endswith((".mp3", ".wav", ".m4a")) and os.path.basename(f).lower().startswith("fun-")
        ]

    # Music history tracking — avoid repeating the same track
    history_path = os.path.join(os.path.dirname(__file__), "used_music.json")
    used_music = []
    if os.path.exists(history_path):
        try:
            with open(history_path, "r") as f:
                used_music = json.load(f)
        except (json.JSONDecodeError, IOError):
            used_music = []

    def pick_music(files):
        """Pick a random fun- track, avoiding recently used ones."""
        if not files:
            return None

        # Filter out recently used tracks (reset when all have been used)
        unused = [f for f in files if os.path.basename(f) not in used_music]
        if not unused:
            used_music.clear()
            unused = files

        pick = random.choice(unused)

        # Save to history
        used_music.append(os.path.basename(pick))
        try:
            with open(history_path, "w") as f:
                json.dump(used_music, f)
        except IOError:
            pass

        return pick

    final_path = os.path.join(output_dir, f"{title_slug}.mp4")

    if music_files:
        music = pick_music(music_files)
        vo_label = " + voiceover" if has_voiceover else ""
        print(f"  Adding music: {os.path.basename(music)}{vo_label}")
        add_background_music(no_music_path, music, final_path, has_voiceover=has_voiceover)
    else:
        os.replace(no_music_path, final_path)

    # Cleanup
    if os.path.exists(no_music_path):
        try:
            os.remove(no_music_path)
        except OSError:
            pass

    return final_path
