"""
Long-Form YouTube Uploader — Uploads as regular YouTube video (not Short).
No #shorts tags, uses youtube.com/watch?v= URLs, Pets & Animals category.
Reuses OAuth from youtube_uploader.py.
"""

import os
import json
import time
from googleapiclient.http import MediaFileUpload
from youtube_uploader import get_authenticated_service, set_thumbnail


def upload_longform_video(video_path, title, description, tags,
                          category_id="15", privacy="public", made_for_kids=False):
    """Upload a video as a regular YouTube video (not Short).

    Args:
        video_path: Path to the video file
        title: Video title
        description: Video description (no #shorts)
        tags: List of tags
        category_id: 15 = Pets & Animals
        privacy: "public", "unlisted", or "private"
        made_for_kids: Whether the video is made for kids

    Returns:
        dict with video_id and url, or None
    """
    youtube = get_authenticated_service()
    if not youtube:
        return None

    # Ensure NO #shorts in description (long-form must not be tagged as Short)
    description = description.replace("#shorts", "").replace("#Shorts", "")

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": made_for_kids,
        },
    }

    print(f"  Uploading long-form: {os.path.basename(video_path)}")
    print(f"  Title: {title}")
    print(f"  Privacy: {privacy}")

    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=1024 * 1024 * 5,  # 5MB chunks (larger for long-form)
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                print(f"  Uploading... {pct}%")
        except Exception as e:
            print(f"  Upload error: {e}")
            return None

    video_id = response["id"]
    video_url = f"https://youtube.com/watch?v={video_id}"
    print(f"  Upload complete!")
    print(f"  URL: {video_url}")

    return {"video_id": video_id, "url": video_url}


def upload_longform_from_metadata(metadata_path, privacy="public"):
    """Upload a long-form video using its metadata.json file."""
    with open(metadata_path, "r") as f:
        meta = json.load(f)

    video_path = meta.get("video_path")
    if not video_path or not os.path.exists(video_path):
        print(f"  ERROR: Video file not found: {video_path}")
        return None

    result = upload_longform_video(
        video_path=video_path,
        title=meta["title"],
        description=meta["description"],
        tags=meta.get("tags", []),
        category_id="15",
        privacy=privacy,
    )

    if result:
        thumb_path = meta.get("thumbnail_path")
        if thumb_path and os.path.exists(thumb_path):
            set_thumbnail(result["video_id"], thumb_path)

        meta["youtube_video_id"] = result["video_id"]
        meta["youtube_url"] = result["url"]
        meta["uploaded_at"] = time.strftime("%Y%m%d_%H%M%S")
        with open(metadata_path, "w") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

    return result
