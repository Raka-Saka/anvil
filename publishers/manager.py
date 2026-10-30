"""
Publish Manager - Unified interface for multi-platform publishing.

Handles:
- Loading publisher configurations
- Publishing to multiple platforms simultaneously
- Generating cover images and audio
- Tracking publish results
"""

import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime
import yaml
import json

from .base import ArticleData, PublishResult
from .devto import DevToPublisher
from .hashnode import HashnodePublisher
from .linkedin import LinkedInPublisher
from .bluesky import BlueskyPublisher

logger = logging.getLogger(__name__)


@dataclass
class PublishReport:
    """Complete report of a multi-platform publish operation."""
    article_title: str
    timestamp: datetime
    results: list[PublishResult] = field(default_factory=list)
    cover_image_path: Optional[Path] = None
    audio_en_path: Optional[Path] = None
    audio_ja_path: Optional[Path] = None

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.results if r.success)

    @property
    def failure_count(self) -> int:
        return sum(1 for r in self.results if not r.success)

    @property
    def all_success(self) -> bool:
        return all(r.success for r in self.results)

    def to_dict(self) -> dict:
        return {
            'article_title': self.article_title,
            'timestamp': self.timestamp.isoformat(),
            'results': [
                {
                    'platform': r.platform,
                    'success': r.success,
                    'url': r.url,
                    'post_id': r.post_id,
                    'error': r.error
                }
                for r in self.results
            ],
            'cover_image_path': str(self.cover_image_path) if self.cover_image_path else None,
            'audio_en_path': str(self.audio_en_path) if self.audio_en_path else None,
            'audio_ja_path': str(self.audio_ja_path) if self.audio_ja_path else None,
        }


class PublishManager:
    """
    Unified manager for multi-platform publishing.

    Usage:
        manager = PublishManager.from_config("config/api_keys.yaml")
        report = manager.publish_article(article_data, platforms=['devto', 'hashnode', 'bluesky'])
    """

    PLATFORM_CLASSES = {
        'devto': DevToPublisher,
        'hashnode': HashnodePublisher,
        'linkedin': LinkedInPublisher,
        'bluesky': BlueskyPublisher,
    }

    def __init__(self, config: dict):
        """
        Initialize with platform configurations.

        Args:
            config: Dict with platform configs, e.g.:
                {
                    'devto': {'api_key': '...'},
                    'hashnode': {'token': '...', 'publication_id': '...'},
                    'linkedin': {'access_token': '...'},
                    'bluesky': {'handle': '...', 'app_password': '...'}
                }
        """
        self.config = config
        self._publishers = {}
        self._init_publishers()

    @classmethod
    def from_config_file(cls, config_path: str = "config/api_keys.yaml") -> 'PublishManager':
        """Load manager from config file."""
        config_path = Path(config_path)

        if not config_path.exists():
            logger.warning(f"Config file not found: {config_path}")
            return cls({})

        with open(config_path, 'r') as f:
            config = yaml.safe_load(f) or {}

        return cls(config)

    def _init_publishers(self):
        """Initialize all configured publishers."""
        for platform, publisher_class in self.PLATFORM_CLASSES.items():
            platform_config = self.config.get(platform, {})
            if platform_config:
                try:
                    self._publishers[platform] = publisher_class(platform_config)
                except Exception as e:
                    logger.error(f"Failed to init {platform} publisher: {e}")

    def get_available_platforms(self) -> list[str]:
        """Get list of configured and available platforms."""
        return [
            platform for platform, publisher in self._publishers.items()
            if publisher.is_configured()
        ]

    def get_platform_status(self) -> dict[str, dict]:
        """Get status of all platforms."""
        status = {}
        for platform, publisher_class in self.PLATFORM_CLASSES.items():
            publisher = self._publishers.get(platform)
            status[platform] = {
                'configured': publisher is not None and publisher.is_configured(),
                'has_config': platform in self.config,
            }
        return status

    def test_connections(self) -> dict[str, bool]:
        """Test connections to all configured platforms."""
        results = {}
        for platform, publisher in self._publishers.items():
            if publisher.is_configured():
                try:
                    results[platform] = publisher.test_connection()
                except Exception as e:
                    logger.error(f"Connection test failed for {platform}: {e}")
                    results[platform] = False
            else:
                results[platform] = False
        return results

    def publish_article(
        self,
        article: ArticleData,
        platforms: Optional[list[str]] = None,
        generate_cover: bool = True,
        generate_audio_en: bool = False,
        generate_audio_ja: bool = False,
        content_ja: Optional[str] = None,
        voice_gender: str = "male"
    ) -> PublishReport:
        """
        Publish article to multiple platforms.

        Args:
            article: Article data to publish
            platforms: List of platform names (default: all configured)
            generate_cover: Generate cover image
            generate_audio_en: Generate English audio
            generate_audio_ja: Generate Japanese audio (requires content_ja)
            content_ja: Japanese content for audio generation

        Returns:
            PublishReport with all results
        """
        report = PublishReport(
            article_title=article.title,
            timestamp=datetime.now()
        )

        # Generate cover image if requested
        print(f">>> Manager: generate_cover={generate_cover}, generate_audio_en={generate_audio_en}", flush=True)
        print(f">>> Manager: Article tags: {article.tags}", flush=True)
        if generate_cover:
            try:
                print(">>> Manager: Generating cover image...", flush=True)
                from media.cover_image import CoverImageGenerator
                cover_gen = CoverImageGenerator()
                if cover_gen.is_available():
                    cover_path = cover_gen.generate_for_article(
                        article_title=article.title,
                        tags=article.tags
                    )
                    print(f">>> Manager: Cover path: {cover_path}", flush=True)
                    print(f">>> Manager: Unsplash URL: {cover_gen.last_unsplash_url}", flush=True)
                    if cover_path:
                        report.cover_image_path = cover_path
                        # Update article with cover image
                        if not article.cover_image_path:
                            article.cover_image_path = cover_path
                        # Use Unsplash URL for blog platforms (they need URL, not local path)
                        if cover_gen.last_unsplash_url:
                            article.cover_image_url = cover_gen.last_unsplash_url
            except ImportError:
                print(">>> Manager: Cover image - ImportError", flush=True)
                logger.warning("Cover image generator not available")
            except Exception as e:
                print(f">>> Manager: Cover image error: {e}", flush=True)
                logger.error(f"Cover image generation failed: {e}")

        print(f">>> Manager: Cover image done. Path: {report.cover_image_path}", flush=True)

        # Generate audio if requested
        if generate_audio_en or generate_audio_ja:
            try:
                from media.audio import AudioGenerator
                audio_gen = AudioGenerator()
                if audio_gen.is_available():
                    if generate_audio_en:
                        audio_path = audio_gen.generate_for_article(
                            title=article.title,
                            content=article.content,
                            lang='en',
                            gender=voice_gender
                        )
                        report.audio_en_path = audio_path

                    if generate_audio_ja and content_ja:
                        audio_path = audio_gen.generate_for_article(
                            title=article.title,
                            content=content_ja,
                            lang='ja',
                            gender=voice_gender
                        )
                        report.audio_ja_path = audio_path
            except ImportError:
                logger.warning("Audio generator not available")
            except Exception as e:
                logger.error(f"Audio generation failed: {e}")

        # Determine which platforms to publish to
        if platforms is None:
            platforms = self.get_available_platforms()
        else:
            # Filter to only configured platforms
            platforms = [p for p in platforms if p in self._publishers and self._publishers[p].is_configured()]

        print(f">>> Manager: Publishing to platforms: {platforms}", flush=True)

        # Publish to each platform
        for platform in platforms:
            print(f">>> Manager: Starting {platform}...", flush=True)
            publisher = self._publishers.get(platform)
            if not publisher:
                print(f">>> Manager: {platform} - no publisher found", flush=True)
                report.results.append(PublishResult(
                    success=False,
                    platform=platform,
                    error="Publisher not configured"
                ))
                continue

            try:
                result = publisher.publish(article)
                print(f">>> Manager: {platform} done - success={result.success}", flush=True)
                report.results.append(result)
                if result.success:
                    logger.info(f"Published to {platform}: {result.url or result.post_id}")
                else:
                    logger.error(f"Failed to publish to {platform}: {result.error}")
            except Exception as e:
                print(f">>> Manager: {platform} EXCEPTION: {e}", flush=True)
                logger.error(f"Exception publishing to {platform}: {e}")
                report.results.append(PublishResult(
                    success=False,
                    platform=platform,
                    error=str(e)
                ))

        print(">>> Manager: All platforms done", flush=True)

        # Save publish report
        self._save_report(report)

        return report

    def _save_report(self, report: PublishReport):
        """Save publish report to file."""
        reports_dir = Path("output/publish_reports")
        reports_dir.mkdir(parents=True, exist_ok=True)

        safe_title = "".join(c for c in report.article_title[:30] if c.isalnum() or c in ' -_').strip()
        safe_title = safe_title.replace(' ', '_')
        filename = f"publish_{safe_title}_{report.timestamp.strftime('%Y%m%d_%H%M%S')}.json"

        report_path = reports_dir / filename
        with open(report_path, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)

        logger.info(f"Saved publish report: {report_path}")

    def publish_to_bluesky_thread(
        self,
        article: ArticleData,
        max_posts: int = 10
    ) -> list[PublishResult]:
        """
        Publish article as a Bluesky thread.

        Args:
            article: Article data
            max_posts: Maximum thread length

        Returns:
            List of results for each thread post
        """
        bluesky = self._publishers.get('bluesky')
        if not bluesky or not bluesky.is_configured():
            return [PublishResult(
                success=False,
                platform='bluesky',
                error="Bluesky not configured"
            )]

        return bluesky.publish_thread(article, max_posts)
