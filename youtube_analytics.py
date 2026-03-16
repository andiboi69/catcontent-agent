"""
YouTube Analytics — Fetch video performance data from YouTube APIs.

Uses YouTube Data API v3 for video stats and YouTube Analytics API for traffic sources.
Requires scopes: youtube, youtube.upload, yt-analytics.readonly
"""

import os
import json
from datetime import datetime, timezone, timedelta
from googleapiclient.discovery import build
from youtube_uploader import get_authenticated_service, get_credentials


def get_channel_info(youtube):
    """Get the authenticated channel's ID and uploads playlist."""
    response = youtube.channels().list(
        part="snippet,statistics,contentDetails",
        mine=True,
    ).execute()

    if not response.get("items"):
        print("  ERROR: No channel found for this account")
        return None

    channel = response["items"][0]
    return {
        "channel_id": channel["id"],
        "title": channel["snippet"]["title"],
        "subscribers": int(channel["statistics"].get("subscriberCount", 0)),
        "total_views": int(channel["statistics"].get("viewCount", 0)),
        "total_videos": int(channel["statistics"].get("videoCount", 0)),
        "uploads_playlist": channel["contentDetails"]["relatedPlaylists"]["uploads"],
    }


def get_all_video_ids(youtube, playlist_id, max_results=200):
    """Get all video IDs from the uploads playlist."""
    video_ids = []
    next_page = None

    while True:
        response = youtube.playlistItems().list(
            part="contentDetails,snippet",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page,
        ).execute()

        for item in response.get("items", []):
            video_ids.append({
                "video_id": item["contentDetails"]["videoId"],
                "title": item["snippet"]["title"],
                "published_at": item["snippet"]["publishedAt"],
            })

        next_page = response.get("nextPageToken")
        if not next_page or len(video_ids) >= max_results:
            break

    return video_ids


def get_video_stats(youtube, video_ids):
    """Fetch statistics for a batch of video IDs (max 50 per request)."""
    all_stats = {}

    # Process in batches of 50
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        ids_str = ",".join(batch)

        response = youtube.videos().list(
            part="statistics,contentDetails",
            id=ids_str,
        ).execute()

        for item in response.get("items", []):
            stats = item["statistics"]
            all_stats[item["id"]] = {
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
                "duration": item["contentDetails"].get("duration", ""),
            }

    return all_stats


def parse_duration(iso_duration):
    """Parse ISO 8601 duration (PT30S, PT1M5S) to seconds."""
    import re
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_duration)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def days_ago(iso_date):
    """Calculate days since a date."""
    published = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    return (now - published).days


def get_traffic_sources(credentials, channel_id, start_date=None):
    """Fetch traffic source breakdown from YouTube Analytics API."""
    analytics = build("youtubeAnalytics", "v2", credentials=credentials)

    if not start_date:
        start_date = (datetime.now(timezone.utc) - timedelta(days=28)).strftime("%Y-%m-%d")
    end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    try:
        response = analytics.reports().query(
            ids=f"channel=={channel_id}",
            startDate=start_date,
            endDate=end_date,
            metrics="views,estimatedMinutesWatched",
            dimensions="insightTrafficSourceType",
            sort="-views",
        ).execute()

        sources = []
        for row in response.get("rows", []):
            sources.append({
                "source": row[0],
                "views": row[1],
                "watch_minutes": round(row[2], 1),
            })
        return sources
    except Exception as e:
        print(f"  Traffic sources error: {e}")
        return None


def get_per_video_traffic(credentials, channel_id, video_ids, start_date=None):
    """Fetch traffic sources per video."""
    analytics = build("youtubeAnalytics", "v2", credentials=credentials)

    if not start_date:
        start_date = (datetime.now(timezone.utc) - timedelta(days=28)).strftime("%Y-%m-%d")
    end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    try:
        response = analytics.reports().query(
            ids=f"channel=={channel_id}",
            startDate=start_date,
            endDate=end_date,
            metrics="views",
            dimensions="video,insightTrafficSourceType",
            filters=f"video=={','.join(video_ids[:50])}",
            sort="-views",
        ).execute()

        # Group by video
        video_traffic = {}
        for row in response.get("rows", []):
            vid = row[0]
            source = row[1]
            views = row[2]
            if vid not in video_traffic:
                video_traffic[vid] = {}
            video_traffic[vid][source] = views
        return video_traffic
    except Exception as e:
        print(f"  Per-video traffic error: {e}")
        return None


def fetch_analytics():
    """Main function: fetch and display all channel analytics."""
    youtube = get_authenticated_service()
    if not youtube:
        print("Failed to authenticate with YouTube")
        return None

    # Get channel info
    print("\nFetching channel data...")
    channel = get_channel_info(youtube)
    if not channel:
        return None

    # Get all uploaded videos
    videos = get_all_video_ids(youtube, channel["uploads_playlist"])
    if not videos:
        print("No videos found on channel")
        return None

    # Get stats for all videos
    video_ids = [v["video_id"] for v in videos]
    stats = get_video_stats(youtube, video_ids)

    # Merge data
    results = []
    for v in videos:
        vid = v["video_id"]
        s = stats.get(vid, {"views": 0, "likes": 0, "comments": 0, "duration": ""})
        duration_s = parse_duration(s["duration"])
        results.append({
            "video_id": vid,
            "title": v["title"],
            "published_at": v["published_at"],
            "days_ago": days_ago(v["published_at"]),
            "views": s["views"],
            "likes": s["likes"],
            "comments": s["comments"],
            "duration_s": duration_s,
            "url": f"https://youtube.com/shorts/{vid}",
        })

    # Sort by views (best first)
    results.sort(key=lambda x: x["views"], reverse=True)

    # Print channel summary
    print(f"\n{'='*70}")
    print(f"  CHANNEL: {channel['title']}")
    print(f"  Subscribers: {channel['subscribers']}")
    print(f"  Total Views: {channel['total_views']}")
    print(f"  Total Videos: {channel['total_videos']}")
    print(f"{'='*70}")

    # Print video table
    total_views = sum(r["views"] for r in results)
    total_likes = sum(r["likes"] for r in results)
    total_comments = sum(r["comments"] for r in results)
    avg_views = total_views / len(results) if results else 0

    print(f"\n  Total: {total_views} views, {total_likes} likes, {total_comments} comments")
    print(f"  Average: {avg_views:.0f} views/video")
    print(f"\n  {'#':<4} {'Views':<8} {'Likes':<7} {'Dur':<6} {'Age':<6} Title")
    print(f"  {'-'*4} {'-'*7} {'-'*6} {'-'*5} {'-'*5} {'-'*35}")

    for i, r in enumerate(results):
        dur = f"{r['duration_s']}s" if r['duration_s'] else "?"
        age = f"{r['days_ago']}d"
        title = r["title"][:38]
        print(f"  {i+1:<4} {r['views']:<8} {r['likes']:<7} {dur:<6} {age:<6} {title}")

    # Print top/bottom performers
    if len(results) >= 5:
        print(f"\n  TOP 3:")
        for r in results[:3]:
            print(f"    {r['views']} views — {r['title']}")
            print(f"      {r['url']}")

        print(f"\n  BOTTOM 3:")
        for r in results[-3:]:
            print(f"    {r['views']} views — {r['title']}")

    # Print insights
    print(f"\n  INSIGHTS:")
    shorts = [r for r in results if r["duration_s"] <= 60]
    if shorts:
        short_durations = [r["duration_s"] for r in shorts if r["duration_s"] > 0]
        if short_durations:
            avg_dur = sum(short_durations) / len(short_durations)
            print(f"    Avg video length: {avg_dur:.0f}s")

        # Best duration range
        under_25 = [r for r in shorts if 0 < r["duration_s"] < 25]
        over_25 = [r for r in shorts if r["duration_s"] >= 25]
        if under_25 and over_25:
            avg_under = sum(r["views"] for r in under_25) / len(under_25)
            avg_over = sum(r["views"] for r in over_25) / len(over_25)
            better = "under 25s" if avg_under > avg_over else "25s+"
            print(f"    Better duration: {better} ({avg_under:.0f} vs {avg_over:.0f} avg views)")

    if channel["subscribers"] > 0:
        views_per_sub = total_views / channel["subscribers"]
        print(f"    Views per subscriber: {views_per_sub:.1f}")

    # Fetch traffic sources
    print(f"\n  TRAFFIC SOURCES (last 28 days):")
    credentials = get_credentials()
    traffic = get_traffic_sources(credentials, channel["channel_id"])
    if traffic:
        total_traffic_views = sum(t["views"] for t in traffic)
        for t in traffic:
            pct = (t["views"] / total_traffic_views * 100) if total_traffic_views > 0 else 0
            source_name = t["source"].replace("_", " ").replace("YT ", "").title()
            print(f"    {source_name:<30} {t['views']:>7} views ({pct:>5.1f}%)  {t['watch_minutes']:>7} min watched")

        # Highlight Shorts feed specifically
        shorts_feed = next((t for t in traffic if "SHORTS" in t["source"].upper() or "SHORT" in t["source"].upper()), None)
        if shorts_feed:
            shorts_pct = (shorts_feed["views"] / total_traffic_views * 100) if total_traffic_views > 0 else 0
            print(f"\n    Shorts feed: {shorts_feed['views']} views ({shorts_pct:.1f}% of total)")
        else:
            print(f"\n    Shorts feed: 0 views (algorithm hasn't picked up yet)")
    else:
        print(f"    Could not fetch traffic data (may need re-authorization)")

    print(f"\n{'='*70}")

    # Save results to file
    output = {
        "fetched_at": datetime.now().isoformat(),
        "channel": channel,
        "videos": results,
        "traffic_sources": traffic,
        "summary": {
            "total_views": total_views,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "avg_views": avg_views,
            "video_count": len(results),
        }
    }

    output_path = os.path.join(os.path.dirname(__file__), "analytics.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n  Full data saved to: analytics.json")

    return output
