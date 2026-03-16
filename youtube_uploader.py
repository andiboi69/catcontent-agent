"""
YouTube Uploader — Uploads videos to YouTube via the Data API v3.
Handles OAuth2 authentication, video upload, thumbnail setting, and Shorts tagging.
"""

import os
import json
import time
import httplib2
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


PROJECT_DIR = os.path.dirname(__file__)
CLIENT_SECRET_FILE = os.path.join(PROJECT_DIR, "client_secret.json")
TOKEN_FILE = os.path.join(PROJECT_DIR, "youtube_token.json")
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


def get_authenticated_service():
    """Authenticate and return a YouTube API service object.

    First run opens a browser for Google login. Token is saved for future use.
    """
    credentials = None

    # Load saved token
    if os.path.exists(TOKEN_FILE):
        credentials = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # Refresh or get new token
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            print("  Refreshing YouTube token...")
            credentials.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRET_FILE):
                print(f"  ERROR: {CLIENT_SECRET_FILE} not found!")
                print("  Download it from Google Cloud Console -> Credentials -> OAuth 2.0 Client IDs")
                return None

            print("  Opening browser for YouTube authorization...")
            print("  (Sign in with the Google account that owns your YouTube channel)")
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            credentials = flow.run_local_server(port=8090, prompt="consent")

        # Save token for next time
        with open(TOKEN_FILE, "w") as f:
            f.write(credentials.to_json())
        print("  Token saved — won't need to login again.")

    return build("youtube", "v3", credentials=credentials)


def get_credentials():
    """Return authenticated credentials (for use by other APIs like Analytics)."""
    credentials = None
    if os.path.exists(TOKEN_FILE):
        credentials = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            credentials = flow.run_local_server(port=8090, prompt="consent")
        with open(TOKEN_FILE, "w") as f:
            f.write(credentials.to_json())
    return credentials


def upload_video(video_path, title, description, tags, category_id="22", privacy="public", made_for_kids=False):
    """Upload a video to YouTube.

    Args:
        video_path: Path to the video file
        title: Video title
        description: Video description
        tags: List of tags
        category_id: YouTube category (22 = People & Blogs, 15 = Pets & Animals)
        privacy: "public", "unlisted", or "private"
        made_for_kids: Whether the video is made for kids

    Returns:
        dict with video ID and URL, or None on failure
    """
    youtube = get_authenticated_service()
    if not youtube:
        return None

    # Ensure key hashtags are in description for YouTube discovery
    required_hashtags = ["#shorts", "#cats", "#catfacts", "#catlover", "#cutecat"]
    desc_lower = description.lower()
    missing = [h for h in required_hashtags if h not in desc_lower]
    if missing:
        description = description.rstrip() + "\n\n" + " ".join(missing)

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category_id,  # 15 = Pets & Animals
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": made_for_kids,
        },
    }

    print(f"  Uploading: {os.path.basename(video_path)}")
    print(f"  Title: {title}")
    print(f"  Privacy: {privacy}")

    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=1024 * 1024,  # 1MB chunks
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    # Upload with progress
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
    video_url = f"https://youtube.com/shorts/{video_id}"
    print(f"  Upload complete!")
    print(f"  URL: {video_url}")

    return {"video_id": video_id, "url": video_url}


def set_thumbnail(video_id, thumbnail_path):
    """Set a custom thumbnail for a video."""
    youtube = get_authenticated_service()
    if not youtube:
        return False

    if not thumbnail_path or not os.path.exists(thumbnail_path):
        print("  No thumbnail to set")
        return False

    try:
        media = MediaFileUpload(thumbnail_path, mimetype="image/jpeg")
        youtube.thumbnails().set(videoId=video_id, media_body=media).execute()
        print(f"  Thumbnail set!")
        return True
    except Exception as e:
        # Custom thumbnails require channel verification — not a blocker
        print(f"  Thumbnail skip (needs verified channel): {e}")
        return False


def upload_from_metadata(metadata_path, privacy="public"):
    """Upload a video using its metadata.json file.

    This is the main function called from agent.py.
    """
    with open(metadata_path, "r") as f:
        meta = json.load(f)

    video_path = meta.get("video_path")
    if not video_path or not os.path.exists(video_path):
        print(f"  ERROR: Video file not found: {video_path}")
        return None

    result = upload_video(
        video_path=video_path,
        title=meta["title"],
        description=meta["description"],
        tags=meta.get("tags", []),
        category_id="15",  # Pets & Animals
        privacy=privacy,
    )

    if result:
        # Try setting thumbnail
        thumb_path = meta.get("thumbnail_path")
        if thumb_path and os.path.exists(thumb_path):
            set_thumbnail(result["video_id"], thumb_path)

        # Save upload info back to metadata
        meta["youtube_video_id"] = result["video_id"]
        meta["youtube_url"] = result["url"]
        meta["uploaded_at"] = time.strftime("%Y%m%d_%H%M%S")
        with open(metadata_path, "w") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

    return result


def upload_from_folder(folder_path, privacy="public"):
    """Upload a video from an output folder (finds metadata.json automatically)."""
    meta_path = os.path.join(folder_path, "metadata.json")
    if not os.path.exists(meta_path):
        print(f"  ERROR: No metadata.json in {folder_path}")
        return None
    return upload_from_metadata(meta_path, privacy=privacy)
