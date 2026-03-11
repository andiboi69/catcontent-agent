"""
Footage Finder — Searches Pexels for cat footage.
Tracks ALL previously used clips in a history file so videos never repeat across generations.
"""

import os
import json
import requests
import random
from config import PEXELS_API_KEY, OUTPUT_DIR


PEXELS_VIDEO_URL = "https://api.pexels.com/videos/search"
PEXELS_HEADERS = {"Authorization": PEXELS_API_KEY}

# History file — persists across all video generations
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "used_footage.json")


def _load_history():
    """Load set of previously used video IDs."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
            pass
    return set()


def _save_history(used_ids):
    """Save used video IDs to disk."""
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(list(used_ids), f)
    except Exception:
        pass


def search_pexels_videos(query, per_page=15, orientation="portrait", page=1):
    """Search Pexels for cat videos."""
    params = {
        "query": query,
        "per_page": per_page,
        "orientation": orientation,
        "size": "medium",
        "page": page,
    }
    try:
        resp = requests.get(PEXELS_VIDEO_URL, headers=PEXELS_HEADERS, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    results = []
    for video in data.get("videos", []):
        duration = video.get("duration", 0)
        if duration > 30:
            continue

        video_files = sorted(
            video.get("video_files", []),
            key=lambda f: f.get("height", 0),
            reverse=True,
        )
        chosen = None
        for vf in video_files:
            h = vf.get("height", 0)
            if 720 <= h <= 1080:
                chosen = vf
                break
        if not chosen and video_files:
            chosen = video_files[0]

        if chosen:
            results.append({
                "id": video["id"],
                "duration": duration,
                "width": chosen.get("width"),
                "height": chosen.get("height"),
                "url": chosen["link"],
                "type": "video",
                "source": "pexels",
            })

    return results


def find_footage_for_scene(scene, used_ids):
    """Find footage for a scene, avoiding already-used clips.

    Searches multiple pages and keyword variations to find fresh clips.
    """
    keywords = scene.get("search_keywords", [])
    if not keywords:
        q = scene.get("search_query", "funny cat")
        keywords = [q] if isinstance(q, str) else q

    # Try each keyword across multiple pages
    for kw in keywords:
        for page in range(1, 4):  # Search pages 1-3 for more variety
            videos = search_pexels_videos(kw, per_page=15, page=page)
            # Filter out already-used clips
            fresh = [v for v in videos if v["id"] not in used_ids]
            if fresh:
                return random.choice(fresh)

    # Try simplified keywords
    for kw in keywords:
        simple = kw.split()[-1] if len(kw.split()) > 1 else kw
        for page in range(1, 3):
            videos = search_pexels_videos(f"cat {simple}", per_page=15, page=page)
            fresh = [v for v in videos if v["id"] not in used_ids]
            if fresh:
                return random.choice(fresh)

    # Fallback: generic queries across pages
    fallback_queries = [
        "funny cat", "playful cat", "cat playing", "kitten playing",
        "cat jumping", "cute kitten", "cat behavior", "cat reaction",
        "cat and dog", "cat funny moment",
    ]
    random.shuffle(fallback_queries)
    for q in fallback_queries:
        page = random.randint(1, 5)
        videos = search_pexels_videos(q, per_page=15, page=page)
        fresh = [v for v in videos if v["id"] not in used_ids]
        if fresh:
            return random.choice(fresh)

    # Last resort: allow any clip (even if used before)
    for q in ["funny cat", "cat playing"]:
        videos = search_pexels_videos(q, per_page=15)
        if videos:
            return random.choice(videos)

    return None


def download_footage(footage, output_dir):
    """Download a footage item to disk."""
    os.makedirs(output_dir, exist_ok=True)

    ext = "mp4" if footage["type"] == "video" else "jpg"
    filename = f"footage_{footage['source']}_{footage['id']}.{ext}"
    filepath = os.path.join(output_dir, filename)

    if os.path.exists(filepath):
        return filepath

    try:
        resp = requests.get(footage["url"], stream=True, timeout=30)
        resp.raise_for_status()

        with open(filepath, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
    except Exception as e:
        print(f"    Download error: {e}")
        return None

    return filepath


def find_and_download_all(scenes, output_dir):
    """Find and download footage for all scenes.

    Tracks used clips globally (across all videos ever generated).
    """
    results = []
    footage_dir = os.path.join(output_dir, "footage")

    # Load global history + track this session
    global_used = _load_history()
    session_used = set()

    for i, scene in enumerate(scenes):
        query = scene.get("search_query", scene.get("search_keywords", ["funny cat"]))
        print(f"  Finding footage for scene {i+1}: {query}")

        # Combine global + session used IDs
        all_used = global_used | session_used

        footage = find_footage_for_scene(scene, all_used)

        if footage:
            session_used.add(footage["id"])
            path = download_footage(footage, footage_dir)
            if path:
                is_fresh = footage["id"] not in global_used
                status = "NEW" if is_fresh else "reused"
                print(f"    -> {status}: {os.path.basename(path)} ({footage['duration']}s)")
                results.append({"scene": scene, "footage_path": path, "footage_type": footage["type"]})
            else:
                print(f"    -> Download failed")
                results.append({"scene": scene, "footage_path": None, "footage_type": None})
        else:
            print(f"    -> No footage found")
            results.append({"scene": scene, "footage_path": None, "footage_type": None})

    # Save all used IDs to history
    global_used.update(session_used)
    _save_history(global_used)
    print(f"  Footage library: {len(global_used)} unique clips used total")

    return results
