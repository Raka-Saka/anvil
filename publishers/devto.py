"""
Dev.to Publisher - Publish articles to dev.to via REST API.

API Docs: https://developers.forem.com/api
Rate Limit: 30 requests/minute
Cost: FREE
"""

import requests
import logging
from typing import Optional
from .base import BasePublisher, ArticleData, PublishResult

logger = logging.getLogger(__name__)


class DevToPublisher(BasePublisher):
    """Publish articles to dev.to."""

    platform_name = "dev.to"
    API_BASE = "https://dev.to/api"

    def __init__(self, config: dict):
        super().__init__(config)
        self.api_key = config.get('api_key', '')

    def _validate_config(self):
        """Validate dev.to config."""
        if not self.config.get('api_key'):
            logger.warning("dev.to API key not configured")

    def is_configured(self) -> bool:
        """Check if dev.to is configured."""
        return bool(self.api_key)

    def publish(self, article: ArticleData, published: bool = True) -> PublishResult:
        """
        Publish an article to dev.to.

        Args:
            article: Article data to publish
            published: True to publish immediately, False for draft

        Returns:
            PublishResult with success status and URL
        """
        if not self.is_configured():
            return PublishResult(
                success=False,
                platform=self.platform_name,
                error="dev.to API key not configured"
            )

        # Prepare article data
        tags = self._clean_tags(article.tags, max_tags=4)

        payload = {
            "article": {
                "title": article.title,
                "body_markdown": article.content,
                "published": published,
                "tags": tags,
            }
        }

        # Add optional fields
        if article.canonical_url:
            payload["article"]["canonical_url"] = article.canonical_url

        if article.cover_image_url:
            payload["article"]["main_image"] = article.cover_image_url

        if article.series:
            payload["article"]["series"] = article.series

        # Make API request
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(
                f"{self.API_BASE}/articles",
                json=payload,
                headers=headers,
                timeout=30
            )

            if response.status_code == 201:
                data = response.json()
                logger.info(f"Published to dev.to: {data.get('url')}")
                return PublishResult(
                    success=True,
                    platform=self.platform_name,
                    url=data.get('url'),
                    post_id=str(data.get('id'))
                )
            else:
                error_msg = response.json().get('error', response.text)
                logger.error(f"dev.to publish failed: {error_msg}")
                return PublishResult(
                    success=False,
                    platform=self.platform_name,
                    error=f"HTTP {response.status_code}: {error_msg}"
                )

        except requests.RequestException as e:
            logger.error(f"dev.to request failed: {e}")
            return PublishResult(
                success=False,
                platform=self.platform_name,
                error=str(e)
            )

    def get_user(self) -> Optional[dict]:
        """Get authenticated user info."""
        if not self.is_configured():
            return None

        headers = {"api-key": self.api_key}

        try:
            response = requests.get(
                f"{self.API_BASE}/users/me",
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
        except requests.RequestException:
            pass

        return None

    def test_connection(self) -> bool:
        """Test API connection."""
        user = self.get_user()
        if user:
            logger.info(f"dev.to connected as: {user.get('username')}")
            return True
        return False
