"""
Long-Form Cat Content Agent — Separate entry point for 8-10 min videos.

Generates complete long-form YouTube videos from a single command:
script -> footage -> voiceover -> assembly -> thumbnail -> upload

Usage:
    python longform_agent.py generate                     # 1 long-form video
    python longform_agent.py generate --upload             # generate + upload
    python longform_agent.py generate --format cat_science # specific format
    python longform_agent.py upload output/longform_...    # upload existing
    python longform_agent.py script                        # script only
"""

import os
import sys
import json
import argparse
from datetime import datetime

from config import OUTPUT_DIR
from longform_config import LONGFORM_CONTENT_FORMATS
from longform_script_generator import generate_longform_script
from longform_footage_finder import find_and_download_all_landscape
from voice_generator import generate_voiceover, get_random_voice
from longform_assembler import assemble_longform_video
from thumbnail_generator import generate_thumbnail
from longform_uploader import upload_longform_from_metadata
from notifier import notify_upload_success, notify_upload_failed, notify_generation_failed


def check_ffmpeg():
    """Check if FFmpeg is available."""
    try:
        import imageio_ffmpeg
        imageio_ffmpeg.get_ffmpeg_exe()
        return True
    except Exception:
        return False


def create_longform_video(content_format=None, upload=False, privacy="public"):
    """Full pipeline: generate one complete long-form video."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_dir = os.path.join(OUTPUT_DIR, f"longform_{timestamp}")
    os.makedirs(video_dir, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  LONG-FORM CAT CONTENT AGENT")
    print(f"  Target: 8-10 minute landscape video")
    print(f"{'='*60}")

    # Step 1: Generate script
    print(f"\n[1/5] Generating long-form script...")
    script = generate_longform_script(content_format=content_format)
    print(f"  Title: \"{script['title']}\"")
    print(f"  Format: {script['content_format']}")
    print(f"  Scenes: {len(script['scenes'])}")
    print(f"  Chapters: {', '.join(script.get('chapters', []))}")

    script_path = os.path.join(video_dir, "script.json")
    with open(script_path, "w", encoding="utf-8") as f:
        json.dump(script, f, indent=2, ensure_ascii=False)

    # Step 2: Find and download landscape footage
    print(f"\n[2/5] Finding landscape footage...")
    footage_data = find_and_download_all_landscape(script["scenes"], video_dir)
    found = sum(1 for f in footage_data if f["footage_path"])
    print(f"  Found footage for {found}/{len(script['scenes'])} scenes")

    # Step 3: Generate voiceover for each scene
    print(f"\n[3/5] Generating voiceover...")
    voice = get_random_voice()
    print(f"  Voice: {voice}")
    voiceover_paths = []
    audio_dir = os.path.join(video_dir, "audio")
    os.makedirs(audio_dir, exist_ok=True)
    for i, scene in enumerate(script["scenes"]):
        narration = scene.get("narration", scene.get("caption", ""))
        if narration:
            audio_path_i = os.path.join(audio_dir, f"scene_{i+1:02d}.mp3")
            try:
                generate_voiceover(narration, audio_path_i, voice=voice)
                voiceover_paths.append(audio_path_i)
                caption = scene.get("caption", "")
                print(f"  Scene {i+1}: \"{caption}\"")
            except Exception as e:
                print(f"  Scene {i+1}: voiceover failed ({e})")
                voiceover_paths.append(None)
        else:
            voiceover_paths.append(None)

    # Step 4: Assemble video
    has_ffmpeg = check_ffmpeg()
    final_video = None

    if has_ffmpeg:
        print(f"\n[4/5] Assembling long-form video (landscape + voiceover + fades)...")
        final_video = assemble_longform_video(footage_data, script, video_dir, voiceover_paths=voiceover_paths)
        if final_video:
            size_mb = os.path.getsize(final_video) / (1024 * 1024)
            duration_est = len(script["scenes"]) * 16
            print(f"  Video saved: {os.path.basename(final_video)} ({size_mb:.1f}MB, ~{duration_est}s)")
        else:
            print(f"  Video assembly failed — raw assets saved in {video_dir}")
    else:
        print(f"\n[4/5] FFmpeg not found — skipping video assembly")

    # Step 5: Generate thumbnail
    print(f"\n[5/5] Generating thumbnail...")
    thumb_path = generate_thumbnail(script, video_dir)

    # Build description with chapter timestamps
    description = script.get("description", "").rstrip()
    if "subscribe" not in description.lower():
        description += "\n\nSubscribe for more cat facts!"
    # Ensure no #shorts leaked in
    description = description.replace("#shorts", "").replace("#Shorts", "")

    # Remove #shorts from tags too
    tags = [t for t in script.get("tags", []) if t.lower() != "shorts" and t.lower() != "#shorts"]

    # Save metadata
    metadata = {
        "title": script["title"],
        "description": description,
        "tags": tags,
        "video_type": "longform",
        "content_format": script["content_format"],
        "created_at": timestamp,
        "voice_used": voice,
        "video_path": final_video,
        "thumbnail_path": thumb_path,
        "output_dir": video_dir,
        "chapters": script.get("chapters", []),
    }
    meta_path = os.path.join(video_dir, "metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    # Summary
    print(f"\n{'='*60}")
    print(f"  DONE!")
    print(f"{'='*60}")
    print(f"  Title:     {script['title']}")
    print(f"  Type:      Long-form ({len(script['scenes'])} scenes)")
    print(f"  Output:    {video_dir}")
    if final_video:
        print(f"  Video:     {os.path.basename(final_video)}")
    if thumb_path:
        print(f"  Thumbnail: thumbnail.jpg")
    print(f"{'='*60}\n")

    # Upload if requested
    if upload and final_video:
        print(f"[6/6] Uploading to YouTube (long-form)...")
        try:
            result = upload_longform_from_metadata(meta_path, privacy=privacy)
            if result:
                metadata["youtube_video_id"] = result["video_id"]
                metadata["youtube_url"] = result["url"]
                print(f"\n  YouTube: {result['url']}")
                notify_upload_success(f"[LONG] {script['title']}", result["url"])
            else:
                notify_upload_failed(f"[LONG] {script['title']}", "Upload returned no result")
        except Exception as e:
            print(f"  Upload error: {e}")
            notify_upload_failed(f"[LONG] {script['title']}", str(e))

    return metadata


def script_only(content_format=None):
    """Generate just the long-form script."""
    print(f"\nGenerating long-form script...")
    script = generate_longform_script(content_format=content_format)

    print(f"\n{'='*60}")
    print(f"  TITLE: {script['title']}")
    print(f"  FORMAT: {script['content_format']}")
    print(f"  CHAPTERS: {', '.join(script.get('chapters', []))}")
    print(f"{'='*60}")
    print(f"\n  DESCRIPTION:\n  {script['description'][:200]}...")
    print(f"\n  SCENES ({len(script['scenes'])}):")
    current_chapter = None
    for s in script["scenes"]:
        ch = s.get("chapter", "")
        if ch != current_chapter:
            current_chapter = ch
            print(f"\n    --- {ch} ---")
        num = s.get("scene_number", "?")
        caption = s.get("caption", "")
        narration = s.get("narration", "")[:60]
        print(f"    {num}. \"{caption}\" -> {narration}...")
    print()

    return script


def main():
    parser = argparse.ArgumentParser(description="Long-Form Cat Content Agent")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # generate command
    gen_parser = subparsers.add_parser("generate", help="Generate a long-form video")
    gen_parser.add_argument("--format", choices=LONGFORM_CONTENT_FORMATS, default=None, help="Content format")
    gen_parser.add_argument("--upload", action="store_true", help="Upload to YouTube")
    gen_parser.add_argument("--privacy", choices=["public", "unlisted", "private"], default="public")

    # upload command
    upload_parser = subparsers.add_parser("upload", help="Upload an existing long-form video")
    upload_parser.add_argument("folder", help="Output folder path")
    upload_parser.add_argument("--privacy", choices=["public", "unlisted", "private"], default="public")

    # script command
    script_parser = subparsers.add_parser("script", help="Generate script only")
    script_parser.add_argument("--format", choices=LONGFORM_CONTENT_FORMATS, default=None)

    args = parser.parse_args()

    if args.command == "generate":
        create_longform_video(content_format=args.format, upload=args.upload, privacy=args.privacy)
    elif args.command == "upload":
        meta_path = os.path.join(args.folder, "metadata.json")
        if not os.path.exists(meta_path):
            print(f"  ERROR: No metadata.json in {args.folder}")
            return
        from longform_uploader import upload_longform_from_metadata
        upload_longform_from_metadata(meta_path, privacy=args.privacy)
    elif args.command == "script":
        script_only(content_format=args.format)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
