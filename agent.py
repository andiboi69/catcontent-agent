"""
Cat Content AI Agent — Main entry point.

Generates complete YouTube cat videos from a single command:
script -> footage -> voiceover -> assembly -> thumbnail -> metadata

Usage:
    python agent.py generate                  # 1 Short video
    python agent.py generate --count 7        # 7 Short videos
    python agent.py generate --type long      # 1 Long-form video
    python agent.py batch --count 7           # 7-day content batch
    python agent.py titles "cat rescue"       # 10 title ideas
    python agent.py script                    # Script only (no video)
"""

import os
import sys
import json
import argparse
from datetime import datetime

from config import OUTPUT_DIR
from script_generator import generate_script, generate_batch, generate_title_variations
from footage_finder import find_and_download_all
from voice_generator import generate_full_voiceover, get_random_voice
from video_assembler import assemble_full_video
from thumbnail_generator import generate_thumbnail
from youtube_uploader import upload_from_metadata, upload_from_folder
from youtube_analytics import fetch_analytics
from notifier import notify_upload_success, notify_upload_failed, notify_generation_failed


def check_ffmpeg():
    """Check if FFmpeg is installed."""
    try:
        import imageio_ffmpeg
        imageio_ffmpeg.get_ffmpeg_exe()
        return True
    except Exception:
        return False


def create_video(video_type="short", content_format=None, upload=False, privacy="public"):
    """Full pipeline: generate one complete video.

    Returns:
        dict with all output paths and metadata
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_dir = os.path.join(OUTPUT_DIR, f"{video_type}_{timestamp}")
    os.makedirs(video_dir, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  CAT CONTENT AGENT - Generating {video_type} video")
    print(f"{'='*60}")

    # Step 1: Generate script
    print(f"\n[1/5] Generating script...")
    script = generate_script(content_format=content_format, video_type=video_type)
    print(f"  Title: \"{script['title']}\"")
    print(f"  Format: {script['content_format']}")
    print(f"  Scenes: {len(script['scenes'])}")

    # Save script
    script_path = os.path.join(video_dir, "script.json")
    with open(script_path, "w", encoding="utf-8") as f:
        json.dump(script, f, indent=2, ensure_ascii=False)

    # Step 2: Find and download footage
    print(f"\n[2/5] Finding footage...")
    footage_data = find_and_download_all(script["scenes"], video_dir)
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
                from voice_generator import generate_voiceover
                generate_voiceover(narration, audio_path_i, voice=voice)
                voiceover_paths.append(audio_path_i)
                caption = scene.get("caption", "")
                print(f"  Scene {i+1}: \"{caption}\" -> \"{narration}\"")
            except Exception as e:
                print(f"  Scene {i+1}: voiceover failed ({e})")
                voiceover_paths.append(None)
        else:
            voiceover_paths.append(None)

    # Step 4: Assemble video (text-on-screen + voiceover)
    has_ffmpeg = check_ffmpeg()
    final_video = None
    audio_path = None

    if has_ffmpeg:
        print(f"\n[4/5] Assembling video (text + voiceover)...")
        final_video = assemble_full_video(footage_data, audio_path, script, video_dir, voiceover_paths=voiceover_paths)
        if final_video:
            size_mb = os.path.getsize(final_video) / (1024 * 1024)
            duration_s = "~" + str(int(len(script["scenes"]) * 2)) + "s"
            print(f"  Video saved: {os.path.basename(final_video)} ({size_mb:.1f}MB, {duration_s})")
        else:
            print(f"  Video assembly failed — raw assets saved in {video_dir}")
    else:
        print(f"\n[3/4] FFmpeg not found — skipping video assembly")

    # Step 5: Generate thumbnail
    print(f"\n[5/5] Generating thumbnail...")
    thumb_path = generate_thumbnail(script, video_dir)

    # Add engagement CTA to description
    description = script["description"].rstrip()
    if "subscribe" not in description.lower():
        description += "\n\nFollow for daily cat content! 🐱"

    # Save metadata for YouTube upload
    metadata = {
        "title": script["title"],
        "description": description,
        "tags": script["tags"],
        "video_type": video_type,
        "content_format": script["content_format"],
        "created_at": timestamp,
        "voice_used": voice,
        "video_path": final_video,
        "thumbnail_path": thumb_path,
        "output_dir": video_dir,
    }
    meta_path = os.path.join(video_dir, "metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    # Summary
    print(f"\n{'='*60}")
    print(f"  DONE!")
    print(f"{'='*60}")
    print(f"  Title:     {script['title']}")
    print(f"  Output:    {video_dir}")
    if final_video:
        print(f"  Video:     {os.path.basename(final_video)}")
    if thumb_path:
        print(f"  Thumbnail: thumbnail.jpg")
    print(f"  Script:    script.json")
    print(f"  Metadata:  metadata.json")
    print(f"{'='*60}\n")

    # Step 6: Upload to YouTube (if requested)
    if upload and final_video:
        print(f"[6/6] Uploading to YouTube...")
        try:
            result = upload_from_metadata(meta_path, privacy=privacy)
            if result:
                metadata["youtube_video_id"] = result["video_id"]
                metadata["youtube_url"] = result["url"]
                print(f"\n  YouTube: {result['url']}")
                notify_upload_success(script["title"], result["url"])
            else:
                notify_upload_failed(script["title"], "Upload returned no result")
        except Exception as e:
            print(f"  Upload error: {e}")
            notify_upload_failed(script["title"], str(e))

    return metadata


def create_batch(count=7, video_type="short", upload=False, privacy="public"):
    """Generate a batch of videos (e.g., 7-day content plan)."""
    print(f"\n{'='*60}")
    print(f"  BATCH MODE — Generating {count} {video_type} videos")
    if upload:
        print(f"  Auto-upload: ON ({privacy})")
    print(f"{'='*60}")

    results = []
    for i in range(count):
        print(f"\n--- Video {i+1}/{count} ---")
        try:
            result = create_video(video_type=video_type, upload=upload, privacy=privacy)
            results.append(result)
        except Exception as e:
            print(f"  ERROR on video {i+1}: {e}")
            results.append({"error": str(e)})
            notify_generation_failed(str(e))

    # Print batch summary
    print(f"\n{'='*60}")
    print(f"  BATCH COMPLETE — {len([r for r in results if 'error' not in r])}/{count} videos generated")
    print(f"{'='*60}")
    for i, r in enumerate(results):
        if "error" in r:
            print(f"  {i+1}. ERROR: {r['error']}")
        else:
            print(f"  {i+1}. {r['title']}")
    print(f"  Output folder: {OUTPUT_DIR}")
    print(f"{'='*60}\n")

    return results


def script_only(content_format=None, video_type="short"):
    """Generate just the script (no video production)."""
    print(f"\nGenerating {video_type} script...")
    script = generate_script(content_format=content_format, video_type=video_type)

    print(f"\n{'='*60}")
    print(f"  TITLE: {script['title']}")
    print(f"  FORMAT: {script['content_format']}")
    print(f"{'='*60}")
    print(f"\n  DESCRIPTION:\n  {script['description']}")
    print(f"\n  TAGS: {', '.join(script['tags'])}")
    print(f"\n  THUMBNAIL TEXT: {script.get('thumbnail_text', 'N/A')}")
    print(f"\n  SCENES:")
    for s in script["scenes"]:
        num = s.get('scene_number', '?')
        caption = s.get('caption', s.get('narration', ''))
        query = s.get('search_query', s.get('search_keywords', ''))
        print(f"    Scene {num}: \"{caption}\" -> [{query}]")
    print()

    return script


def main():
    parser = argparse.ArgumentParser(description="Cat Content AI Agent")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # generate command
    gen_parser = subparsers.add_parser("generate", help="Generate complete video(s)")
    gen_parser.add_argument("--count", type=int, default=1, help="Number of videos")
    gen_parser.add_argument("--type", choices=["short", "long"], default="short", help="Video type")
    gen_parser.add_argument("--format", choices=[
        "cat_facts", "cat_breeds", "reasons_to_get_cat", "signs_cat_loves_you",
        "cat_psychology", "cat_vs_dog", "cat_myths", "cat_tips"
    ], default=None, help="Content format")
    gen_parser.add_argument("--upload", action="store_true", help="Upload to YouTube after generating")
    gen_parser.add_argument("--privacy", choices=["public", "unlisted", "private"], default="public", help="YouTube privacy")

    # batch command
    batch_parser = subparsers.add_parser("batch", help="Generate a week of content")
    batch_parser.add_argument("--count", type=int, default=7, help="Number of videos")
    batch_parser.add_argument("--type", choices=["short", "long"], default="short", help="Video type")
    batch_parser.add_argument("--upload", action="store_true", help="Upload all to YouTube")
    batch_parser.add_argument("--privacy", choices=["public", "unlisted", "private"], default="public", help="YouTube privacy")

    # upload command (upload an existing video)
    upload_parser = subparsers.add_parser("upload", help="Upload an existing video to YouTube")
    upload_parser.add_argument("folder", help="Output folder path (e.g., output/short_20260311_163508)")
    upload_parser.add_argument("--privacy", choices=["public", "unlisted", "private"], default="public", help="YouTube privacy")

    # titles command
    titles_parser = subparsers.add_parser("titles", help="Generate title ideas")
    titles_parser.add_argument("topic", help="Topic for titles")
    titles_parser.add_argument("--count", type=int, default=10, help="Number of titles")

    # stats command
    stats_parser = subparsers.add_parser("stats", help="Fetch YouTube channel analytics")

    # script command
    script_parser = subparsers.add_parser("script", help="Generate script only (no video)")
    script_parser.add_argument("--type", choices=["short", "long"], default="short", help="Video type")
    script_parser.add_argument("--format", choices=[
        "emotional_story", "cat_facts", "day_in_the_life",
        "ranking", "funny_moments", "mystery"
    ], default=None, help="Content format")

    args = parser.parse_args()

    if args.command == "generate":
        if args.count > 1:
            create_batch(count=args.count, video_type=args.type, upload=args.upload, privacy=args.privacy)
        else:
            create_video(video_type=args.type, content_format=args.format, upload=args.upload, privacy=args.privacy)

    elif args.command == "batch":
        create_batch(count=args.count, video_type=args.type, upload=args.upload, privacy=args.privacy)

    elif args.command == "upload":
        print(f"\nUploading from: {args.folder}")
        upload_from_folder(args.folder, privacy=args.privacy)

    elif args.command == "titles":
        titles = generate_title_variations(args.topic, args.count)
        print(f"\nTitle ideas for \"{args.topic}\":")
        for i, title in enumerate(titles):
            print(f"  {i+1}. {title}")

    elif args.command == "stats":
        fetch_analytics()

    elif args.command == "script":
        script_only(content_format=args.format, video_type=args.type)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
