"""
Long-Form Footage Finder — Searches Pexels for LANDSCAPE cat footage.
Prefers longer clips (5-15s) for the 8-10 min video format.
Shares footage history with Shorts pipeline (no clip reuse across either).
"""

import os
import random
import requests
from config import PEXELS_API_KEY
from footage_finder import (
    _load_history, _save_history, download_footage,
    PEXELS_VIDEO_URL, PEXELS_HEADERS,
)


def search_pexels_landscape(query, per_page=15, page=1):
    """Search Pexels for LANDSCAPE cat videos. Prefers longer clips."""
    q_lower = query.lower()
    if "cat" not in q_lower and "kitten" not in q_lower and "feline" not in q_lower:
        query = f"cat {query}"

    params = {
        "query": query,
        "per_page": per_page,
        "orientation": "landscape",
        "size": "medium",
        "page": page,
    }
    try:
        resp = requests.get(PEXELS_VIDEO_URL, headers=PEXELS_HEADERS, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    BAD_SLUG_WORDS = {
        "woman", "man", "girl", "boy", "person", "people", "child", "children",
        "baby", "owner", "holding", "kissing", "hugging", "selfie", "portrait",
        "couple", "family", "friend", "hand", "hands", "face", "model",
        "dog", "puppy", "bird", "parrot", "fish", "hamster", "rabbit",
        "horse", "snake", "turtle", "lizard", "frog",
        "car", "house", "building", "room", "kitchen", "bedroom", "bathroom",
        "food", "plant", "flower", "tree", "landscape", "city", "street",
        "ear", "earring", "jewelry", "tattoo", "piercing",
    }

    CAT_SLUG_WORDS = {
        "cat", "cats", "kitten", "kittens", "feline", "kitty", "tabby",
        "calico", "persian", "siamese", "bengal", "ragdoll", "sphynx", "maine",
    }

    results = []
    for video in data.get("videos", []):
        duration = video.get("duration", 0)
        # Accept longer clips for long-form (up to 60s)
        if duration > 60:
            continue

        video_url = video.get("url", "")
        slug = video_url.split("/")[-2] if "/" in video_url else ""
        slug_lower = slug.lower().replace("-", " ")
        slug_words = set(slug_lower.split())

        if not (slug_words & CAT_SLUG_WORDS):
            continue
        if slug_words & BAD_SLUG_WORDS:
            continue

        video_files = sorted(
            video.get("video_files", []),
            key=lambda f: f.get("height", 0),
            reverse=True,
        )
        chosen = None
        for vf in video_files:
            h = vf.get("height", 0)
            w = vf.get("width", 0)
            # Prefer 1080p landscape
            if 720 <= h <= 1080 and w >= h:
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

    # Sort by duration — prefer clips in the 5-15s sweet spot
    results.sort(key=lambda v: abs(v["duration"] - 10))
    return results


def find_footage_for_scene_landscape(scene, used_ids):
    """Find landscape footage for a scene, avoiding used clips."""
    keywords = scene.get("search_keywords", [])
    if not keywords:
        q = scene.get("search_query", "funny cat")
        keywords = [q] if isinstance(q, str) else q

    for kw in keywords:
        for page in range(1, 4):
            videos = search_pexels_landscape(kw, per_page=15, page=page)
            fresh = [v for v in videos if v["id"] not in used_ids]
            if fresh:
                return random.choice(fresh[:5])

    # Simplified keyword fallback
    for kw in keywords:
        simple = kw.split()[-1] if len(kw.split()) > 1 else kw
        for page in range(1, 3):
            videos = search_pexels_landscape(f"cat {simple}", per_page=15, page=page)
            fresh = [v for v in videos if v["id"] not in used_ids]
            if fresh:
                return random.choice(fresh[:5])

    # Generic fallback
    fallback_queries = [
        "funny cat", "playful cat", "cat playing", "kitten playing",
        "cute kitten", "cat sleeping", "cat stretching", "orange tabby cat",
        "fluffy cat", "cat grooming", "cat in sunlight", "persian cat",
    ]
    random.shuffle(fallback_queries)
    for q in fallback_queries:
        page = random.randint(1, 5)
        videos = search_pexels_landscape(q, per_page=15, page=page)
        fresh = [v for v in videos if v["id"] not in used_ids]
        if fresh:
            return random.choice(fresh[:5])

    # Last resort: allow reuse
    for q in ["funny cat", "cat playing"]:
        videos = search_pexels_landscape(q, per_page=15)
        if videos:
            return random.choice(videos)

    return None


def find_and_download_all_landscape(scenes, output_dir):
    """Find and download landscape footage for all scenes.

    Shares history with Shorts pipeline — no clip reuse across either.
    """
    results = []
    footage_dir = os.path.join(output_dir, "footage")

    global_used = _load_history()
    session_used = set()

    for i, scene in enumerate(scenes):
        query = scene.get("search_query", scene.get("search_keywords", ["funny cat"]))
        print(f"  Finding landscape footage for scene {i+1}/{len(scenes)}: {query}")

        all_used = global_used | session_used
        footage = find_footage_for_scene_landscape(scene, all_used)

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

    global_used.update(session_used)
    _save_history(global_used)
    print(f"  Footage library: {len(global_used)} unique clips used total")

    return results
