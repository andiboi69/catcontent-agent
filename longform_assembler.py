"""
Long-Form Video Assembler — Landscape 1920x1080 with Ken Burns effect.
Slow zoom/pan on every clip for documentary feel. Fade transitions,
lower background music, voiceover-driven, chapter title cards, fact counter.
"""

import os
import sys
import json
import random
import subprocess

from video_assembler import FFMPEG, get_media_duration, escape_text, _find_font
from longform_config import (
    TARGET_WIDTH, TARGET_HEIGHT, TARGET_FPS,
    CLIP_DURATION, CLIP_MIN_DURATION, CLIP_PADDING,
    FADE_DURATION, AUDIO_RATE, AUDIO_CHANNELS,
    MUSIC_VOL_WITH_VOICE, VOICE_VOL,
    CHAPTER_CARD_DURATION, INTRO_DURATION, OUTRO_DURATION,
)

FONT_PATH = _find_font()

# Ken Burns — overscan amount for zoom/pan headroom
KB_SCALE = 1.15  # scale up 15% so we have room to zoom/pan


def generate_title_card(output_path, text, duration=CHAPTER_CARD_DURATION, subtitle=None):
    """Generate a title card clip (dark background + centered text + silent audio)."""
    safe_text = escape_text(text)

    filters = [
        f"color=c=0x1a1a2e:s={TARGET_WIDTH}x{TARGET_HEIGHT}:d={duration}:r={TARGET_FPS}",
    ]
    vf_parts = []

    # Main title
    vf_parts.append(
        f"drawtext=text='{safe_text}'"
        f"{':fontfile=' + FONT_PATH if FONT_PATH else ''}"
        f":fontsize=64:fontcolor=white:borderw=2:bordercolor=0x333333"
        f":x=(w-text_w)/2:y=(h-text_h)/2{'-30' if subtitle else ''}"
    )

    # Subtitle if provided
    if subtitle:
        safe_sub = escape_text(subtitle)
        vf_parts.append(
            f"drawtext=text='{safe_sub}'"
            f"{':fontfile=' + FONT_PATH if FONT_PATH else ''}"
            f":fontsize=32:fontcolor=0xaaaaaa"
            f":x=(w-text_w)/2:y=(h/2)+30"
        )

    # Fade in/out
    vf_parts.append(f"fade=t=in:d={FADE_DURATION}")
    vf_parts.append(f"fade=t=out:st={duration - FADE_DURATION}:d={FADE_DURATION}")

    vf = ",".join(vf_parts)

    cmd = [
        FFMPEG, "-y",
        "-f", "lavfi", "-i", ",".join(filters),
        "-f", "lavfi", "-i", f"anullsrc=r={AUDIO_RATE}:cl=mono:d={duration}",
        "-vf", vf,
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
        "-r", str(TARGET_FPS),
        "-c:a", "aac", "-ar", str(AUDIO_RATE), "-ac", str(AUDIO_CHANNELS),
        "-shortest",
        "-movflags", "+faststart",
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"    Title card error: {result.stderr[-200:]}")
        return None
    return output_path


def _ken_burns_filter(duration):
    """Generate a random Ken Burns zoom/pan filter for documentary feel.

    Returns an FFmpeg filter string that slowly zooms and/or pans across the frame.
    Input must be pre-scaled to KB_SCALE (1.15x) larger than target.
    """
    # Overscan dimensions (the larger input we crop from)
    ow = int(TARGET_WIDTH * KB_SCALE)
    oh = int(TARGET_HEIGHT * KB_SCALE)
    # Maximum pan distance in pixels
    max_pan = ow - TARGET_WIDTH  # ~288px at 1.15x

    # Pick a random Ken Burns style
    style = random.choice(["zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "pan_down"])

    total_frames = int(duration * TARGET_FPS)
    if total_frames <= 0:
        total_frames = 1

    if style == "zoom_in":
        # Start wide, end tight (zoom into center)
        return (
            f"zoompan=z='1+0.15*on/{total_frames}'"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={total_frames}:s={TARGET_WIDTH}x{TARGET_HEIGHT}:fps={TARGET_FPS}"
        )
    elif style == "zoom_out":
        # Start tight, end wide
        return (
            f"zoompan=z='1.15-0.15*on/{total_frames}'"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={total_frames}:s={TARGET_WIDTH}x{TARGET_HEIGHT}:fps={TARGET_FPS}"
        )
    elif style == "pan_left":
        return (
            f"zoompan=z='1.08'"
            f":x='{max_pan}*(1-on/{total_frames})':y='(ih-ih/zoom)/2'"
            f":d={total_frames}:s={TARGET_WIDTH}x{TARGET_HEIGHT}:fps={TARGET_FPS}"
        )
    elif style == "pan_right":
        return (
            f"zoompan=z='1.08'"
            f":x='{max_pan}*on/{total_frames}':y='(ih-ih/zoom)/2'"
            f":d={total_frames}:s={TARGET_WIDTH}x{TARGET_HEIGHT}:fps={TARGET_FPS}"
        )
    elif style == "pan_up":
        max_pan_v = oh - TARGET_HEIGHT
        return (
            f"zoompan=z='1.08'"
            f":x='(iw-iw/zoom)/2':y='{max_pan_v}*(1-on/{total_frames})'"
            f":d={total_frames}:s={TARGET_WIDTH}x{TARGET_HEIGHT}:fps={TARGET_FPS}"
        )
    else:  # pan_down
        max_pan_v = oh - TARGET_HEIGHT
        return (
            f"zoompan=z='1.08'"
            f":x='(iw-iw/zoom)/2':y='{max_pan_v}*on/{total_frames}'"
            f":d={total_frames}:s={TARGET_WIDTH}x{TARGET_HEIGHT}:fps={TARGET_FPS}"
        )


def normalize_clip_landscape(input_path, output_path, duration=CLIP_DURATION,
                              caption=None, voiceover_path=None,
                              scene_num=None, total_scenes=None):
    """Normalize a clip to 1920x1080 landscape with Ken Burns effect, caption,
    fact counter, and optional voiceover.

    Ken Burns: slow zoom/pan on every clip for cinematic documentary feel.
    Fact counter: "3/25" badge in top-right corner.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Sync duration to voiceover if available
    if voiceover_path and os.path.exists(voiceover_path):
        voice_dur = get_media_duration(voiceover_path)
        if voice_dur > 0:
            duration = max(voice_dur + CLIP_PADDING, CLIP_MIN_DURATION)

    actual_dur = get_media_duration(input_path)
    if actual_dur <= 0:
        actual_dur = duration

    # Build input args
    input_args = []
    if actual_dur < duration:
        input_args = ["-stream_loop", "-1", "-i", input_path, "-t", str(duration)]
    elif actual_dur > duration + 2:
        skip = random.uniform(0.5, min(actual_dur - duration - 0.5, 5.0))
        input_args = ["-ss", str(round(skip, 1)), "-i", input_path, "-t", str(duration)]
    else:
        input_args = ["-i", input_path, "-t", str(duration)]

    # Add voiceover as second input
    has_voice = voiceover_path and os.path.exists(voiceover_path)
    if has_voice:
        input_args += ["-i", voiceover_path]

    # Video filter chain — landscape with Ken Burns
    # Step 1: Scale up slightly larger than target (gives zoompan room to move)
    ow = int(TARGET_WIDTH * KB_SCALE)
    oh = int(TARGET_HEIGHT * KB_SCALE)
    filters = [
        f"scale={ow}:{oh}:force_original_aspect_ratio=increase",
        f"crop={ow}:{oh}",
        f"fps={TARGET_FPS}",
    ]

    # Step 2: Ken Burns zoom/pan effect — outputs at TARGET_WIDTH x TARGET_HEIGHT
    kb_filter = _ken_burns_filter(duration)
    filters.append(kb_filter)

    # Step 3: Caption overlay — bottom-center with rounded-look bar
    if caption:
        safe_text = escape_text(caption)
        text_len = len(caption)
        if text_len <= 15:
            fontsize = 56
        elif text_len <= 25:
            fontsize = 48
        else:
            fontsize = 38

        bar_h = fontsize + 60
        bar_y = TARGET_HEIGHT - bar_h - 60
        text_y = bar_y + (bar_h - fontsize) // 2

        # Semi-transparent dark bar
        filters.append(f"drawbox=x=0:y={bar_y}:w=iw:h={bar_h}:color=black@0.55:t=fill")
        # Caption text
        filters.append(
            f"drawtext=text='{safe_text}'"
            f"{':fontfile=' + FONT_PATH if FONT_PATH else ''}"
            f":fontsize={fontsize}:fontcolor=white:borderw=3:bordercolor=black"
            f":x=(w-text_w)/2:y={text_y}"
        )

    # Step 4: Fact counter badge — top-right corner (e.g., "3/25")
    if scene_num is not None and total_scenes is not None:
        counter_text = escape_text(f"{scene_num}/{total_scenes}")
        # Background pill
        filters.append(
            f"drawbox=x=iw-130:y=20:w=110:h=50:color=black@0.6:t=fill"
        )
        # Counter text — drawtext expressions use 'w' for frame width ('iw' is
        # not defined there and access-violates this FFmpeg build, exit 0xC0000005)
        filters.append(
            f"drawtext=text='{counter_text}'"
            f"{':fontfile=' + FONT_PATH if FONT_PATH else ''}"
            f":fontsize=28:fontcolor=white:borderw=2:bordercolor=black"
            f":x=w-125+((110-text_w)/2):y=28"
        )

    # Step 5: Fade in/out
    filters.append(f"fade=t=in:d={FADE_DURATION}")
    filters.append(f"fade=t=out:st={duration - FADE_DURATION}:d={FADE_DURATION}")

    vf = ",".join(filters)

    # Audio mapping
    if has_voice:
        audio_args = [
            "-map", "0:v", "-map", "1:a",
            "-c:a", "aac", "-ar", str(AUDIO_RATE), "-ac", str(AUDIO_CHANNELS),
            "-b:a", "128k", "-shortest",
        ]
    else:
        audio_args = ["-an"]

    cmd = [
        FFMPEG, "-y",
        *input_args,
        "-vf", vf,
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
        "-r", str(TARGET_FPS),
        *audio_args,
        "-movflags", "+faststart",
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        # Only log actual errors (not FFmpeg's normal stderr noise)
        err_lines = [l for l in result.stderr.strip().split("\n")
                     if "error" in l.lower() or "invalid" in l.lower() or "failed" in l.lower()]
        if err_lines:
            print(f"    FFmpeg error: {err_lines[-1][:120]}")
        else:
            print(f"    FFmpeg failed (exit code {result.returncode}), using fallback")
        # Fallback: drop Ken Burns and counter, but KEEP caption, voiceover and
        # fades — the voiceover IS the content; a silent clip is worse than a
        # static one.
        filters_simple = [
            f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase",
            f"crop={TARGET_WIDTH}:{TARGET_HEIGHT}",
            f"fps={TARGET_FPS}",
        ]
        if caption:
            safe_text = escape_text(caption)
            fb_fontsize = 48 if len(caption) <= 25 else 38
            fb_bar_h = fb_fontsize + 60
            fb_bar_y = TARGET_HEIGHT - fb_bar_h - 60
            fb_text_y = fb_bar_y + (fb_bar_h - fb_fontsize) // 2
            filters_simple.append(f"drawbox=x=0:y={fb_bar_y}:w=iw:h={fb_bar_h}:color=black@0.55:t=fill")
            filters_simple.append(
                f"drawtext=text='{safe_text}'"
                f"{':fontfile=' + FONT_PATH if FONT_PATH else ''}"
                f":fontsize={fb_fontsize}:fontcolor=white:borderw=3:bordercolor=black"
                f":x=(w-text_w)/2:y={fb_text_y}"
            )
        filters_simple.append(f"fade=t=in:d={FADE_DURATION}")
        filters_simple.append(f"fade=t=out:st={duration - FADE_DURATION}:d={FADE_DURATION}")
        cmd_fallback = [
            FFMPEG, "-y",
            *input_args,
            "-vf", ",".join(filters_simple),
            "-t", str(duration),
            "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
            "-r", str(TARGET_FPS),
            *audio_args,
            "-movflags", "+faststart",
            output_path
        ]
        subprocess.run(cmd_fallback, capture_output=True, text=True)

    # Ensure audio track exists (silent if no voiceover) — required for concat
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


def concat_clips_longform(clip_paths, output_path):
    """Concatenate clips using concat demuxer. Clips already have fade in/out."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    temp_dir = os.path.dirname(output_path)

    concat_list_path = os.path.join(temp_dir, "concat_list.txt")
    with open(concat_list_path, "w") as f:
        for clip in clip_paths:
            safe_path = clip.replace("\\", "/")
            f.write(f"file '{safe_path}'\n")

    cmd = [
        FFMPEG, "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_list_path,
        "-c:v", "libx264",
        "-c:a", "aac", "-ar", str(AUDIO_RATE), "-ac", str(AUDIO_CHANNELS),
        "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if os.path.exists(concat_list_path):
        os.remove(concat_list_path)

    if result.returncode != 0:
        print(f"    Concat error: {result.stderr[-300:]}")
        return None

    return output_path


def add_background_music_longform(video_path, music_path, output_path):
    """Mix background music at low volume behind voiceover for long-form."""
    tempo = round(random.uniform(0.95, 1.05), 2)
    norm_filter = "loudnorm=I=-14:TP=-1:LRA=11"
    tempo_filter = f",atempo={tempo}" if tempo != 1.0 else ""

    # Long-form: music must loop for ~10 min, very low volume
    audio_chain = (
        f"[1:a]{norm_filter}{tempo_filter},aloop=loop=-1:size=2e+09[music];"
        f"[music]atrim=duration=700,volume={MUSIC_VOL_WITH_VOICE}[bg];"
        f"[0:a]volume={VOICE_VOL}[voice];"
        f"[voice][bg]amix=inputs=2:duration=first:dropout_transition=2[mixed]"
    )

    cmd = [
        FFMPEG, "-y",
        "-i", video_path,
        "-i", music_path,
        "-filter_complex", audio_chain,
        "-map", "0:v",
        "-map", "[mixed]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        "-movflags", "+faststart",
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        # Fallback: simpler mix without loudnorm
        fallback_chain = (
            f"[1:a]volume=1.5,aloop=loop=-1:size=2e+09[music];"
            f"[music]atrim=duration=700[bg];"
            f"[0:a]volume=1.8[voice];"
            f"[voice][bg]amix=inputs=2:duration=first[mixed]"
        )
        cmd_simple = [
            FFMPEG, "-y",
            "-i", video_path, "-i", music_path,
            "-filter_complex", fallback_chain,
            "-map", "0:v", "-map", "[mixed]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
            "-shortest", "-movflags", "+faststart",
            output_path
        ]
        result2 = subprocess.run(cmd_simple, capture_output=True, text=True)
        if result2.returncode != 0:
            print(f"    Music mixing failed, using video without music")
            if os.path.exists(video_path) and video_path != output_path:
                import shutil
                shutil.copy2(video_path, output_path)

    return output_path


def assemble_longform_video(footage_data, script, output_dir, voiceover_paths=None):
    """Assemble a complete long-form video:
    1. Generate intro title card
    2. For each chapter: chapter card + scene clips with voiceover
    3. Generate outro card
    4. Concatenate with fade transitions
    5. Add background music at low volume
    """
    clips_dir = os.path.join(output_dir, "clips")
    os.makedirs(clips_dir, exist_ok=True)

    prepared_clips = []
    chapters = script.get("chapters", [])
    scenes = script.get("scenes", [])

    # Intro title card
    print(f"  Generating intro card...")
    intro_path = os.path.join(clips_dir, "intro.mp4")
    intro_result = generate_title_card(
        intro_path, script["title"],
        duration=INTRO_DURATION,
        subtitle="Purrfect Facts"
    )
    if intro_result and os.path.exists(intro_path):
        prepared_clips.append(intro_path)

    # Group scenes by chapter
    chapter_scenes = {}
    for i, scene in enumerate(scenes):
        ch = scene.get("chapter", "Main")
        if ch not in chapter_scenes:
            chapter_scenes[ch] = []
        chapter_scenes[ch].append((i, scene))

    # Count total content scenes (exclude intro/outro) for the fact counter
    total_content_scenes = sum(
        len(sl) for ch, sl in chapter_scenes.items()
        if ch.lower() not in ("intro", "outro")
    )
    fact_num = 0

    # Process each chapter
    chapter_idx = 0
    for chapter_name, scene_list in chapter_scenes.items():
        is_bookend = chapter_name.lower() in ("intro", "outro")

        if not is_bookend:
            # Chapter title card
            chapter_idx += 1
            card_path = os.path.join(clips_dir, f"chapter_{chapter_idx:02d}.mp4")
            print(f"  Chapter {chapter_idx}: {chapter_name}")
            card_result = generate_title_card(card_path, chapter_name, duration=CHAPTER_CARD_DURATION)
            if card_result and os.path.exists(card_path):
                prepared_clips.append(card_path)

        # Process scenes in this chapter
        for i, scene in scene_list:
            caption = scene.get("caption", "")
            footage_item = footage_data[i] if i < len(footage_data) else None
            footage_path = footage_item["footage_path"] if footage_item else None

            voice_path = None
            if voiceover_paths and i < len(voiceover_paths):
                voice_path = voiceover_paths[i]

            clip_path = os.path.join(clips_dir, f"scene_{i + 1:02d}.mp4")

            # Fact counter for content scenes (not intro/outro)
            s_num = None
            s_total = None
            if not is_bookend:
                fact_num += 1
                s_num = fact_num
                s_total = total_content_scenes

            if footage_path and os.path.exists(footage_path):
                print(f"  Scene {i + 1}/{len(scenes)}: \"{caption}\"")
                normalize_clip_landscape(
                    footage_path, clip_path, CLIP_DURATION, caption, voice_path,
                    scene_num=s_num, total_scenes=s_total,
                )
                if os.path.exists(clip_path) and os.path.getsize(clip_path) > 1000:
                    prepared_clips.append(clip_path)
                else:
                    print(f"    -> Failed, skipping")
            else:
                print(f"  Skipping scene {i + 1} (no footage)")

    # Outro card
    print(f"  Generating outro card...")
    outro_path = os.path.join(clips_dir, "outro.mp4")
    outro_result = generate_title_card(
        outro_path, "Thanks for Watching!",
        duration=OUTRO_DURATION,
        subtitle="Subscribe for more cat facts"
    )
    if outro_result and os.path.exists(outro_path):
        prepared_clips.append(outro_path)

    # Check we have enough
    content_clips = [c for c in prepared_clips if "chapter_" not in os.path.basename(c)
                     and "intro" not in os.path.basename(c)
                     and "outro" not in os.path.basename(c)]
    if len(content_clips) < 10:
        print(f"  ERROR: Only {len(content_clips)} scene clips — not enough for long-form!")
        return None

    # Concatenate all clips
    title_slug = script["title"][:40].replace(" ", "_")
    for ch in "?!'\",:;()[]{}#@&*":
        title_slug = title_slug.replace(ch, "")

    has_voiceover = voiceover_paths is not None and any(
        v and os.path.exists(v) for v in voiceover_paths
    ) if voiceover_paths else False

    no_music_path = os.path.join(output_dir, "no_music.mp4")
    print(f"  Stitching {len(prepared_clips)} clips with fade transitions...")
    concat_result = concat_clips_longform(prepared_clips, no_music_path)

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

    if music_files and has_voiceover:
        # Pick a chill track for long-form (chill tracks work better for longer videos)
        chill = [f for f in music_files if any(k in os.path.basename(f).lower()
                 for k in ["chill", "calm", "soft", "dreamy", "ambient", "warm"])]
        music = random.choice(chill) if chill else random.choice(music_files)
        print(f"  Adding music: {os.path.basename(music)} (low volume + voiceover)")
        add_background_music_longform(no_music_path, music, final_path)
    elif music_files:
        music = random.choice(music_files)
        print(f"  Adding music: {os.path.basename(music)}")
        add_background_music_longform(no_music_path, music, final_path)
    else:
        os.replace(no_music_path, final_path)

    # Cleanup
    if os.path.exists(no_music_path):
        try:
            os.remove(no_music_path)
        except OSError:
            pass

    return final_path
