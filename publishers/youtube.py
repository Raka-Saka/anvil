"""
YouTube Publisher - Upload audio articles as videos to YouTube.

Combines cover image + audio into a video, then uploads via YouTube Data API.

API Docs: https://developers.google.com/youtube/v3
Cost: FREE (quota limits apply - 10,000 units/day, upload = 1600 units)

Setup:
1. Go to https://console.cloud.google.com/
2. Create a project and enable YouTube Data API v3
3. Create OAuth2 credentials (Desktop app)
4. Download client_secrets.json to config/
5. Run OAuth flow to get refresh token
"""

import logging
import subprocess
import json
from pathlib import Path
from typing import Optional
from datetime import datetime
from .base import BasePublisher, ArticleData, PublishResult

logger = logging.getLogger(__name__)

# Try imports
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    HAS_GOOGLE_API = True
except ImportError:
    HAS_GOOGLE_API = False


class YouTubePublisher(BasePublisher):
    """Publish audio articles as videos to YouTube."""

    platform_name = "youtube"
    SCOPES = [
        'https://www.googleapis.com/auth/youtube.upload',
        'https://www.googleapis.com/auth/youtube.force-ssl'  # Required for captions
    ]

    def __init__(self, config: dict):
        self.client_secrets_path = Path(config.get('client_secrets_path', 'config/client_secrets.json'))
        self.token_path = Path(config.get('token_path', 'config/youtube_token.json'))
        self._youtube = None
        super().__init__(config)

    def _validate_config(self):
        """Validate YouTube config."""
        if not HAS_GOOGLE_API:
            logger.warning("Google API libraries not installed. Run: pip install google-api-python-client google-auth-oauthlib")
        if not self.client_secrets_path.exists():
            logger.warning(f"YouTube client_secrets.json not found at {self.client_secrets_path}")

    def is_configured(self) -> bool:
        """Check if YouTube is configured."""
        return HAS_GOOGLE_API and (self.token_path.exists() or self.client_secrets_path.exists())

    def _get_credentials(self) -> Optional[Credentials]:
        """Get or refresh OAuth credentials."""
        creds = None

        # Load existing token
        if self.token_path.exists():
            try:
                with open(self.token_path, 'r') as f:
                    token_data = json.load(f)
                creds = Credentials.from_authorized_user_info(token_data, self.SCOPES)
            except Exception as e:
                logger.error(f"Failed to load token: {e}")

        # Refresh if expired
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                self._save_credentials(creds)
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")
                creds = None

        # Run OAuth flow if no valid credentials
        if not creds or not creds.valid:
            if not self.client_secrets_path.exists():
                logger.error("No client_secrets.json found. Download from Google Cloud Console.")
                return None

            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.client_secrets_path), self.SCOPES
                )
                creds = flow.run_local_server(port=8586)
                self._save_credentials(creds)
            except Exception as e:
                logger.error(f"OAuth flow failed: {e}")
                return None

        return creds

    def _save_credentials(self, creds: Credentials):
        """Save credentials to file."""
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.token_path, 'w') as f:
            f.write(creds.to_json())

    def _get_youtube(self):
        """Get authenticated YouTube API client."""
        if self._youtube is None:
            creds = self._get_credentials()
            if creds:
                self._youtube = build('youtube', 'v3', credentials=creds)
        return self._youtube

    def _create_video_from_audio(
        self,
        audio_path: Path,
        image_path: Path,
        output_path: Path
    ) -> bool:
        """
        Create a video from audio + static image using FFmpeg.

        Args:
            audio_path: Path to audio file (mp3)
            image_path: Path to cover image (png/jpg)
            output_path: Output video path (mp4)

        Returns:
            True if successful
        """
        try:
            # FFmpeg command: combine image + audio into video
            cmd = [
                'ffmpeg', '-y',  # Overwrite output
                '-loop', '1',  # Loop the image
                '-i', str(image_path),  # Input image
                '-i', str(audio_path),  # Input audio
                '-c:v', 'libx264',  # Video codec
                '-tune', 'stillimage',  # Optimize for still image
                '-c:a', 'aac',  # Audio codec
                '-b:a', '192k',  # Audio bitrate
                '-pix_fmt', 'yuv420p',  # Pixel format for compatibility
                '-shortest',  # End when audio ends
                str(output_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr}")
                return False

            return output_path.exists()

        except FileNotFoundError:
            logger.error("FFmpeg not found. Install FFmpeg and add to PATH.")
            return False
        except Exception as e:
            logger.error(f"Video creation failed: {e}")
            return False

    def publish(
        self,
        article: ArticleData,
        audio_path: Optional[Path] = None,
        cover_image_path: Optional[Path] = None,
        privacy: str = "public",
        subtitle_path: Optional[Path] = None
    ) -> PublishResult:
        """
        Publish article as a YouTube video.

        Args:
            article: Article data
            audio_path: Path to audio file
            cover_image_path: Path to cover image
            privacy: "public", "unlisted", or "private"
            subtitle_path: Path to SRT subtitle file

        Returns:
            PublishResult with video URL
        """
        if not HAS_GOOGLE_API:
            return PublishResult(
                success=False,
                platform=self.platform_name,
                error="Google API libraries not installed. Run: pip install google-api-python-client google-auth-oauthlib"
            )

        if not audio_path or not Path(audio_path).exists():
            return PublishResult(
                success=False,
                platform=self.platform_name,
                error="Audio file required for YouTube upload"
            )

        audio_path = Path(audio_path)

        # Use provided cover image or article's cover
        print(f">>> YouTube: cover_image_path param: {cover_image_path}", flush=True)
        print(f">>> YouTube: article.cover_image_path: {article.cover_image_path}", flush=True)
        if cover_image_path and Path(cover_image_path).exists():
            image_path = Path(cover_image_path)
            print(f">>> YouTube: Using provided cover: {image_path}", flush=True)
        elif article.cover_image_path and Path(article.cover_image_path).exists():
            image_path = Path(article.cover_image_path)
            print(f">>> YouTube: Using article cover: {image_path}", flush=True)
        else:
            print(f">>> YouTube: No cover found, generating new one...", flush=True)
            # Generate a simple cover image
            try:
                from media.cover_image import CoverImageGenerator
                gen = CoverImageGenerator()
                image_path = gen.generate_for_article(article.title, tags=article.tags)
                if not image_path:
                    return PublishResult(
                        success=False,
                        platform=self.platform_name,
                        error="Could not generate cover image"
                    )
            except Exception as e:
                return PublishResult(
                    success=False,
                    platform=self.platform_name,
                    error=f"Cover image error: {e}"
                )

        # Create video file
        video_dir = Path("output/videos")
        video_dir.mkdir(parents=True, exist_ok=True)

        safe_title = "".join(c for c in article.title[:30] if c.isalnum() or c in ' -_').strip()
        safe_title = safe_title.replace(' ', '_')
        video_path = video_dir / f"video_{safe_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"

        print(f">>> YouTube: Creating video...", flush=True)
        print(f">>> YouTube: Image: {image_path} (exists: {image_path.exists()})", flush=True)
        print(f">>> YouTube: Audio: {audio_path} (exists: {audio_path.exists()})", flush=True)
        print(f">>> YouTube: Output: {video_path}", flush=True)
        if not self._create_video_from_audio(audio_path, image_path, video_path):
            return PublishResult(
                success=False,
                platform=self.platform_name,
                error="Failed to create video (is FFmpeg installed?)"
            )

        # Get YouTube client
        youtube = self._get_youtube()
        if not youtube:
            return PublishResult(
                success=False,
                platform=self.platform_name,
                error="Could not authenticate with YouTube"
            )

        # Prepare video metadata
        tags = [tag.lstrip('#') for tag in article.tags[:15]]  # YouTube allows up to 500 chars total

        # Build description
        description_parts = [
            article.content[:500] + "..." if len(article.content) > 500 else article.content,
            "",
            "---",
        ]
        if article.canonical_url:
            description_parts.append(f"Read the full article: {article.canonical_url}")
        description_parts.append("")
        description_parts.append(" ".join(f"#{tag}" for tag in tags[:10]))

        body = {
            'snippet': {
                'title': article.title[:100],  # YouTube title limit
                'description': "\n".join(description_parts)[:5000],  # Description limit
                'tags': tags,
                'categoryId': '27',  # Education category
            },
            'status': {
                'privacyStatus': privacy,
                'selfDeclaredMadeForKids': False,
            }
        }

        try:
            print(f"Uploading to YouTube...")
            media = MediaFileUpload(
                str(video_path),
                mimetype='video/mp4',
                resumable=True
            )

            request = youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )

            response = request.execute()
            video_id = response.get('id')
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            logger.info(f"Published to YouTube: {video_url}")
            print(f">>> YouTube: Video uploaded: {video_url}", flush=True)

            # Upload subtitles if provided
            if subtitle_path and Path(subtitle_path).exists():
                print(f">>> YouTube: Uploading subtitles...", flush=True)
                try:
                    self._upload_captions(youtube, video_id, subtitle_path, 'en')
                    print(f">>> YouTube: Subtitles uploaded!", flush=True)
                except Exception as e:
                    print(f">>> YouTube: Subtitle upload failed: {e}", flush=True)
                    logger.warning(f"Caption upload failed: {e}")

            return PublishResult(
                success=True,
                platform=self.platform_name,
                url=video_url,
                post_id=video_id
            )

        except Exception as e:
            logger.error(f"YouTube upload failed: {e}")
            return PublishResult(
                success=False,
                platform=self.platform_name,
                error=str(e)
            )

    def _upload_captions(self, youtube, video_id: str, subtitle_path: Path, language: str = 'en'):
        """
        Upload captions/subtitles to a YouTube video.

        Args:
            youtube: Authenticated YouTube API client
            video_id: ID of the video
            subtitle_path: Path to SRT file
            language: Language code (e.g., 'en', 'ja')
        """
        subtitle_path = Path(subtitle_path)

        body = {
            'snippet': {
                'videoId': video_id,
                'language': language,
                'name': f'{language.upper()} Subtitles',
                'isDraft': False
            }
        }

        media = MediaFileUpload(
            str(subtitle_path),
            mimetype='application/x-subrip',
            resumable=True
        )

        youtube.captions().insert(
            part='snippet',
            body=body,
            media_body=media
        ).execute()

    def test_connection(self) -> bool:
        """Test API connection."""
        youtube = self._get_youtube()
        if youtube:
            try:
                # Try to get channel info
                response = youtube.channels().list(
                    part='snippet',
                    mine=True
                ).execute()
                if response.get('items'):
                    channel = response['items'][0]['snippet']['title']
                    logger.info(f"YouTube connected as: {channel}")
                    print(f"YouTube connected as: {channel}")
                    return True
            except Exception as e:
                logger.error(f"YouTube connection test failed: {e}")
        return False


def run_oauth_flow(client_secrets_path: str = "config/client_secrets.json") -> bool:
    """
    Run OAuth flow to authenticate with YouTube.

    Downloads client_secrets.json from Google Cloud Console first.
    """
    if not HAS_GOOGLE_API:
        print("Install required libraries: pip install google-api-python-client google-auth-oauthlib")
        return False

    secrets_path = Path(client_secrets_path)
    if not secrets_path.exists():
        print(f"Download client_secrets.json from Google Cloud Console")
        print(f"Save it to: {secrets_path.absolute()}")
        return False

    publisher = YouTubePublisher({'client_secrets_path': str(secrets_path)})
    creds = publisher._get_credentials()

    if creds and creds.valid:
        print("YouTube OAuth successful!")
        print(f"Token saved to: {publisher.token_path}")
        return True

    print("OAuth flow failed")
    return False
