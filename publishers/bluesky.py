"""
Bluesky Publisher - Publish posts to Bluesky via AT Protocol.

API Docs: https://docs.bsky.app/
Cost: FREE (no rate limits for reasonable usage)

Setup:
1. Go to Settings > App Passwords in Bluesky
2. Create an app password
3. Add handle and app_password to config
"""

import logging
from typing import Optional
from datetime import datetime, timezone
from .base import BasePublisher, ArticleData, PublishResult

logger = logging.getLogger(__name__)

# Try to import atproto
try:
    from atproto import Client
    HAS_ATPROTO = True
except ImportError:
    HAS_ATPROTO = False
    Client = None


class BlueskyPublisher(BasePublisher):
    """Publish posts to Bluesky."""

    platform_name = "bluesky"

    def __init__(self, config: dict):
        super().__init__(config)
        self.handle = config.get('handle', '')  # e.g., "username.bsky.social"
        self.app_password = config.get('app_password', '')
        self._client = None

    def _validate_config(self):
        """Validate Bluesky config."""
        if not HAS_ATPROTO:
            logger.warning("atproto package not installed. Run: pip install atproto")
        if not self.config.get('handle'):
            logger.warning("Bluesky handle not configured")
        if not self.config.get('app_password'):
            logger.warning("Bluesky app_password not configured")

    def is_configured(self) -> bool:
        """Check if Bluesky is configured."""
        return bool(HAS_ATPROTO and self.handle and self.app_password)

    def _get_client(self) -> Optional[Client]:
        """Get authenticated Bluesky client."""
        if not self.is_configured():
            return None

        if self._client is None:
            try:
                self._client = Client()
                self._client.login(self.handle, self.app_password)
            except Exception as e:
                logger.error(f"Bluesky login failed: {e}")
                self._client = None

        return self._client

    def publish(self, article: ArticleData, include_link: bool = True) -> PublishResult:
        """
        Publish a post to Bluesky.

        Bluesky posts have a 300 character limit, so we create a summary post
        with a link to the full article.

        Args:
            article: Article data
            include_link: Include link to original article

        Returns:
            PublishResult with success status
        """
        if not HAS_ATPROTO:
            return PublishResult(
                success=False,
                platform=self.platform_name,
                error="atproto package not installed. Run: pip install atproto"
            )

        if not self.is_configured():
            return PublishResult(
                success=False,
                platform=self.platform_name,
                error="Bluesky not configured (need handle and app_password)"
            )

        client = self._get_client()
        if not client:
            return PublishResult(
                success=False,
                platform=self.platform_name,
                error="Could not connect to Bluesky"
            )

        # Create post text (300 char limit)
        # Format: Title + brief teaser + link
        title = article.title[:100]

        # Extract first sentence or two as teaser
        content_clean = article.content.replace('#', '').strip()
        first_para = content_clean.split('\n\n')[0] if '\n\n' in content_clean else content_clean[:200]
        teaser = first_para[:150].rsplit(' ', 1)[0] + "..."

        post_text = f"{title}\n\n{teaser}"

        # We'll use facets to add the link properly
        link_url = article.canonical_url if article.canonical_url else None

        try:
            if link_url:
                # Post with link card
                # atproto will handle link detection and card generation
                post_text_with_link = f"{post_text}\n\n{link_url}"

                if len(post_text_with_link) > 300:
                    # Truncate teaser to fit
                    available = 300 - len(title) - len(link_url) - 10
                    teaser = first_para[:available].rsplit(' ', 1)[0] + "..."
                    post_text_with_link = f"{title}\n\n{teaser}\n\n{link_url}"

                response = client.send_post(text=post_text_with_link[:300])
            else:
                response = client.send_post(text=post_text[:300])

            # Extract post URI
            post_uri = response.uri if hasattr(response, 'uri') else str(response)

            # Convert URI to web URL
            # URI format: at://did:plc:xxx/app.bsky.feed.post/yyy
            # Web URL: https://bsky.app/profile/handle/post/yyy
            web_url = None
            if post_uri and 'app.bsky.feed.post' in post_uri:
                post_id = post_uri.split('/')[-1]
                web_url = f"https://bsky.app/profile/{self.handle}/post/{post_id}"

            logger.info(f"Published to Bluesky: {web_url or post_uri}")
            return PublishResult(
                success=True,
                platform=self.platform_name,
                url=web_url,
                post_id=post_uri
            )

        except Exception as e:
            logger.error(f"Bluesky publish failed: {e}")
            return PublishResult(
                success=False,
                platform=self.platform_name,
                error=str(e)
            )

    def publish_thread(self, article: ArticleData, max_posts: int = 10, hashtags: list[str] = None) -> list[PublishResult]:
        """
        Publish article as a thread (multiple connected posts).

        Args:
            article: Article data
            max_posts: Maximum number of posts in thread
            hashtags: List of hashtags to include in final post

        Returns:
            List of PublishResults for each post
        """
        if not self.is_configured():
            return [PublishResult(
                success=False,
                platform=self.platform_name,
                error="Bluesky not configured"
            )]

        client = self._get_client()
        if not client:
            return [PublishResult(
                success=False,
                platform=self.platform_name,
                error="Could not connect to Bluesky"
            )]

        results = []

        # Split content into thread posts
        thread_posts = self._split_into_thread(article, max_posts, hashtags or article.tags)

        parent_ref = None
        root_ref = None

        for i, post_text in enumerate(thread_posts):
            try:
                if parent_ref is None:
                    # First post
                    response = client.send_post(text=post_text)
                else:
                    # Reply to previous post
                    response = client.send_post(
                        text=post_text,
                        reply_to={
                            "parent": parent_ref,
                            "root": root_ref
                        }
                    )

                # Store references for threading
                post_ref = {
                    "uri": response.uri,
                    "cid": response.cid
                }

                if root_ref is None:
                    root_ref = post_ref

                parent_ref = post_ref

                results.append(PublishResult(
                    success=True,
                    platform=self.platform_name,
                    post_id=response.uri
                ))

            except Exception as e:
                results.append(PublishResult(
                    success=False,
                    platform=self.platform_name,
                    error=str(e)
                ))
                break  # Stop thread on error

        return results

    def _split_into_thread(self, article: ArticleData, max_posts: int, hashtags: list[str] = None) -> list[str]:
        """Split article into thread posts with hashtags."""
        posts = []

        # Prepare hashtags string (for last post)
        hashtag_str = ""
        if hashtags:
            hashtag_str = " ".join(f"#{tag}" for tag in hashtags[:5])

        # Calculate available space (300 limit minus safety margin)
        POST_LIMIT = 295

        # First post: Title and hook
        first_post = f"🧵 {article.title}\n\nThread:"
        posts.append(first_post[:POST_LIMIT])

        # Split content into paragraphs
        paragraphs = article.content.split('\n\n')

        # Clean paragraphs
        clean_paragraphs = []
        for para in paragraphs:
            # Skip markdown headers but keep text
            if para.startswith('#'):
                para = para.lstrip('#').strip()
            # Skip empty
            para = para.strip()
            if para and not para.startswith('```'):  # Skip code blocks
                clean_paragraphs.append(para)

        current_post = ""
        for para in clean_paragraphs:
            # Check if adding this paragraph exceeds limit
            test_post = (current_post + "\n\n" + para).strip() if current_post else para

            if len(test_post) < POST_LIMIT - 10:  # Leave room for post number
                current_post = test_post
            else:
                # Save current post and start new one
                if current_post:
                    posts.append(current_post[:POST_LIMIT])
                current_post = para

            if len(posts) >= max_posts - 2:  # Leave room for final posts
                break

        # Add remaining content
        if current_post and len(posts) < max_posts - 1:
            posts.append(current_post[:POST_LIMIT])

        # Last post: Link + hashtags
        if len(posts) < max_posts:
            final_parts = []
            if article.canonical_url:
                final_parts.append(f"📖 Full article:\n{article.canonical_url}")
            if hashtag_str:
                final_parts.append(hashtag_str)

            if final_parts:
                final_post = "\n\n".join(final_parts)
                posts.append(final_post[:POST_LIMIT])

        # Add post numbers
        total = len(posts)
        numbered_posts = []
        for i, post in enumerate(posts):
            number = f"[{i+1}/{total}] "
            # Make sure number + post fits
            available = POST_LIMIT - len(number)
            numbered_posts.append(number + post[:available])

        return numbered_posts[:max_posts]

    def test_connection(self) -> bool:
        """Test API connection."""
        client = self._get_client()
        if client:
            logger.info(f"Bluesky connected as: {self.handle}")
            return True
        return False
