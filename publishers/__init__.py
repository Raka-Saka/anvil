"""
Anvil Publishers - Cross-platform article publishing.

Supported platforms:
- dev.to (FREE)
- Hashnode (FREE)
- LinkedIn (FREE)
- Bluesky (FREE)

Usage:
    from publishers import PublishManager, ArticleData

    manager = PublishManager.from_config_file("config/api_keys.yaml")
    article = ArticleData(title="My Post", content="...", tags=["python"])
    report = manager.publish_article(article, platforms=['devto', 'bluesky'])
"""

from .base import ArticleData, PublishResult, BasePublisher
from .devto import DevToPublisher
from .hashnode import HashnodePublisher
from .linkedin import LinkedInPublisher
from .bluesky import BlueskyPublisher
from .youtube import YouTubePublisher
from .manager import PublishManager, PublishReport

__all__ = [
    # Base types
    'ArticleData',
    'PublishResult',
    'BasePublisher',
    # Publishers
    'DevToPublisher',
    'HashnodePublisher',
    'LinkedInPublisher',
    'BlueskyPublisher',
    'YouTubePublisher',
    # Manager
    'PublishManager',
    'PublishReport',
]
