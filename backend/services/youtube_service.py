"""YouTube service for uploading videos and managing channel integration."""
import os
import logging
import time
import json
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

TOKEN_FILE = Path("youtube_tokens.json")


class YouTubeService:
    """Handle YouTube video uploads and metadata."""

    def __init__(self):
        self.api_key = os.environ.get("YOUTUBE_API_KEY")
        self.client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
        self.client_id = os.environ.get("YOUTUBE_CLIENT_ID")
        self.enabled = bool(self.api_key or self.client_secret)
        self._youtube_client = None  # Cached YouTube API client

    def is_enabled(self) -> bool:
        """Check if YouTube integration is enabled."""
        return self.enabled and os.environ.get("ENABLE_YOUTUBE_UPLOAD") == "1"

    def _load_tokens(self) -> Optional[Dict[str, Any]]:
        """Load OAuth tokens from disk."""
        if not TOKEN_FILE.exists():
            return None
        try:
            return json.loads(TOKEN_FILE.read_text())
        except Exception as e:
            logger.warning(f"Failed to load YouTube tokens: {e}")
            return None

    def _save_tokens(self, tokens: Dict[str, Any]):
        """Persist OAuth tokens to disk."""
        try:
            TOKEN_FILE.write_text(json.dumps(tokens, indent=2))
        except Exception as e:
            logger.error(f"Failed to save YouTube tokens: {e}")

    def _refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        Refresh OAuth access token using refresh_token.
        
        Returns:
            Updated token dict with new access_token and expiry, or None if failed
        """
        if not self.client_id or not self.client_secret:
            logger.error("YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET required for token refresh")
            return None

        import requests

        token_url = "https://oauth2.googleapis.com/token"
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        max_retries = 3
        backoff_sec = 1

        for attempt in range(max_retries):
            try:
                resp = requests.post(token_url, data=payload, timeout=10)

                if resp.status_code == 200:
                    new_tokens = resp.json()
                    # Merge with existing tokens (preserve refresh_token)
                    return {
                        "access_token": new_tokens["access_token"],
                        "refresh_token": refresh_token,
                        "expires_in": new_tokens.get("expires_in", 3600),
                        "token_type": new_tokens.get("token_type", "Bearer"),
                    }
                elif resp.status_code == 401:
                    logger.error("YouTube OAuth refresh failed: Invalid credentials (401)")
                    return None
                elif resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", backoff_sec))
                    logger.warning(f"YouTube rate limit hit (429), retrying after {retry_after}s")
                    time.sleep(retry_after)
                    backoff_sec = min(retry_after * 2, 60)
                else:
                    logger.error(f"YouTube token refresh failed: {resp.status_code} {resp.text}")
                    return None

            except requests.RequestException as e:
                logger.warning(f"Token refresh attempt {attempt+1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(backoff_sec)
                    backoff_sec = min(backoff_sec * 2, 60)

        return None

    def _get_authenticated_client(self):
        """
        Get authenticated YouTube API client with automatic token refresh.
        
        Returns:
            YouTube API client, or None if authentication unavailable
        """
        if self._youtube_client:
            return self._youtube_client

        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
        except ImportError:
            logger.error("google-api-client not installed. Install: pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client")
            return None

        # Load tokens from disk
        tokens = self._load_tokens()
        if not tokens or "refresh_token" not in tokens:
            logger.error("No YouTube refresh token found. Run OAuth flow first.")
            return None

        # Refresh if needed (always refresh on startup for safety)
        refreshed = self._refresh_access_token(tokens["refresh_token"])
        if not refreshed:
            logger.error("Failed to refresh YouTube access token")
            return None

        # Save updated tokens
        self._save_tokens(refreshed)

        # Build credentials object
        creds = Credentials(
            token=refreshed["access_token"],
            refresh_token=refreshed["refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret,
        )

        # Build YouTube API client
        self._youtube_client = build("youtube", "v3", credentials=creds)
        return self._youtube_client

    def upload_video(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list = None,
        thumbnail_path: Optional[Path] = None,
        privacy_status: str = "public",
    ) -> Dict[str, Any]:
        """
        Upload a video to YouTube.
        
        Args:
            video_path: Local path to MP4 file
            title: Video title
            description: Video description
            tags: List of tags/keywords
            thumbnail_path: Optional custom thumbnail
            privacy_status: 'public', 'private', or 'unlisted'
            
        Returns:
            {
                'success': bool,
                'video_id': str,
                'url': str,
                'error': str (if failed)
            }
        """
        if not self.is_enabled():
            logger.warning("YouTube upload not enabled (no API key or ENABLE_YOUTUBE_UPLOAD != 1)")
            return {"success": False, "error": "YouTube integration not enabled"}

        if not Path(video_path).exists():
            return {"success": False, "error": f"Video file not found: {video_path}"}

        try:
            from googleapiclient.http import MediaFileUpload
            from googleapiclient.errors import HttpError

            logger.info(f"Uploading video to YouTube: {title}")

            # Get authenticated client (handles token refresh)
            youtube = self._get_authenticated_client()
            if not youtube:
                return {"success": False, "error": "Failed to authenticate with YouTube"}

            # Prepare request body
            request_body = {
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": tags or [],
                    "categoryId": "24",  # Spirituality category
                },
                "status": {
                    "privacyStatus": privacy_status,
                    "madeForKids": False,
                },
            }

            # Upload media with retry on 401/429
            media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype="video/mp4")
            request = youtube.videos().insert(
                part="snippet,status",
                body=request_body,
                media_body=media,
            )

            max_retries = 3
            backoff_sec = 2

            for attempt in range(max_retries):
                try:
                    response = request.execute()
                    video_id = response.get("id")
                    video_url = f"https://youtube.com/watch?v={video_id}"

                    logger.info(f"Video uploaded successfully: {video_url}")

                    # Upload thumbnail if provided
                    if thumbnail_path and Path(thumbnail_path).exists():
                        try:
                            self._upload_thumbnail(youtube, video_id, thumbnail_path)
                        except Exception as e:
                            logger.warning(f"Failed to upload thumbnail: {e}")

                    return {
                        "success": True,
                        "video_id": video_id,
                        "url": video_url,
                    }

                except HttpError as he:
                    status = he.resp.status
                    if status == 401:
                        logger.warning(f"YouTube upload 401 (Unauthorized), refreshing token (attempt {attempt+1})")
                        # Force token refresh
                        self._youtube_client = None
                        youtube = self._get_authenticated_client()
                        if not youtube:
                            return {"success": False, "error": "Failed to refresh YouTube token after 401"}
                        # Rebuild request with new client
                        request = youtube.videos().insert(
                            part="snippet,status",
                            body=request_body,
                            media_body=media,
                        )
                        time.sleep(backoff_sec)
                        backoff_sec = min(backoff_sec * 2, 60)
                    elif status == 429:
                        retry_after = int(he.resp.get("Retry-After", backoff_sec))
                        logger.warning(f"YouTube rate limit (429), retrying after {retry_after}s")
                        time.sleep(retry_after)
                        backoff_sec = min(retry_after * 2, 120)
                    elif status == 403:
                        # Quota exceeded or forbidden
                        error_msg = f"YouTube API quota exceeded or forbidden (403): {he}"
                        logger.error(error_msg)
                        return {"success": False, "error": error_msg}
                    else:
                        logger.error(f"YouTube upload failed with HTTP {status}: {he}")
                        return {"success": False, "error": f"YouTube API error ({status}): {he}"}

            return {"success": False, "error": "YouTube upload failed after retries"}

        except ImportError:
            logger.warning("google-api-client not installed; skipping YouTube upload")
            return {
                "success": False,
                "error": "google-api-client not installed. Install with: pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client",
            }
        except Exception as e:
            logger.exception(f"YouTube upload failed: {e}")
            return {"success": False, "error": str(e)}

    def _upload_thumbnail(self, youtube, video_id: str, thumbnail_path: Path):
        """Upload custom thumbnail for video."""
        from googleapiclient.http import MediaFileUpload

        media = MediaFileUpload(str(thumbnail_path), mimetype="image/jpeg")
        youtube.thumbnails().set(videoId=video_id, media_body=media).execute()
        logger.info(f"Thumbnail uploaded for video {video_id}")

    @staticmethod
    def generate_description(job_plan: Dict[str, Any], job_id: str) -> str:
        """Generate YouTube video description from job plan."""
        topic = job_plan.get("topic", "Devotional Video")
        language = job_plan.get("language", "en")

        if language == "hi":
            description = f"संतान धर्म: {topic}\n\n"
            description += "यह वीडियो कृत्रिम बुद्धिमत्ता द्वारा उत्पन्न किया गया है।\n\n"
            description += "#संतानधर्म #devotional #sanatan\n\n"
        else:
            description = f"Sanatan Dharma: {topic}\n\n"
            description += "This video was generated using AI.\n\n"
            description += "#SanatanDharma #Devotional #Sanatan\n\n"

        description += f"Generated: {datetime.now().strftime('%Y-%m-%d')}\n"
        description += f"Job ID: {job_id}"

        return description

    @staticmethod
    def generate_title(job_plan: Dict[str, Any]) -> str:
        """Generate YouTube video title from job plan."""
        topic = job_plan.get("topic", "Devotional Video")
        return f"🕉️ {topic} - Sanatan Dharma"


def should_upload_to_youtube(job_plan: Dict[str, Any]) -> bool:
    """Check if job should upload to YouTube based on plan and env."""
    if not os.environ.get("ENABLE_YOUTUBE_UPLOAD"):
        return False
    return job_plan.get("enable_youtube_upload", False)
