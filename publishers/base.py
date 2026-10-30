"""
Base Publisher - Abstract base class for all publishers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from pathlib import Path


@dataclass
class PublishResult:
    """Result of a publish operation."""
    success: bool
    platform: str
    url: Optional[str] = None
    post_id: Optional[str] = None
    error: Optional[str] = None


@dataclass
class ArticleData:
    """Article data for publishing."""
    title: str
    content: str  # Markdown content
    tags: list[str]
    canonical_url: Optional[str] = None
    cover_image_url: Optional[str] = None
    cover_image_path: Optional[Path] = None
    series: Optional[str] = None
    language: str = "en"


class BasePublisher(ABC):
    """Abstract base class for platform publishers."""

    platform_name: str = "unknown"

    def __init__(self, config: dict):
        """Initialize with platform-specific config."""
        self.config = config
        self._validate_config()

    @abstractmethod
    def _validate_config(self):
        """Validate required config fields."""
        pass

    @abstractmethod
    def publish(self, article: ArticleData) -> PublishResult:
        """Publish an article to the platform."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if publisher has valid configuration."""
        pass

    def _clean_tags(self, tags: list[str], max_tags: int = 4) -> list[str]:
        """Clean and limit tags for platform requirements."""
        # Remove # prefix, lowercase, limit count
        cleaned = []
        for tag in tags[:max_tags]:
            tag = tag.lstrip('#').lower().replace(' ', '')
            if tag and tag not in cleaned:
                cleaned.append(tag)
        return cleaned
