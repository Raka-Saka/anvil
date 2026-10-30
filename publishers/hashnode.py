"""
Hashnode Publisher - Publish articles to Hashnode via GraphQL API.

API Docs: https://apidocs.hashnode.com/
Cost: FREE
"""

import requests
import logging
from typing import Optional
from .base import BasePublisher, ArticleData, PublishResult

logger = logging.getLogger(__name__)


class HashnodePublisher(BasePublisher):
    """Publish articles to Hashnode."""

    platform_name = "hashnode"
    API_URL = "https://gql.hashnode.com"

    def __init__(self, config: dict):
        super().__init__(config)
        self.token = config.get('token', '')
        self.publication_id = config.get('publication_id', '')

    def _validate_config(self):
        """Validate Hashnode config."""
        if not self.config.get('token'):
            logger.warning("Hashnode token not configured")
        # publication_id is optional - will be auto-fetched

    def is_configured(self) -> bool:
        """Check if Hashnode is configured."""
        return bool(self.token)  # publication_id can be auto-fetched

    def _graphql_request(self, query: str, variables: dict = None) -> dict:
        """Make a GraphQL request to Hashnode."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": self.token
        }

        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        response = requests.post(
            self.API_URL,
            json=payload,
            headers=headers,
            timeout=30
        )

        return response.json()

    def _get_my_publication_id(self) -> Optional[str]:
        """Fetch the user's publication ID automatically."""
        query = """
        query Me {
            me {
                id
                username
                publications(first: 1) {
                    edges {
                        node {
                            id
                            title
                        }
                    }
                }
            }
        }
        """
        try:
            result = self._graphql_request(query)
            print(f"Hashnode API response: {result}")  # Debug

            if "errors" in result:
                logger.error(f"Hashnode API error: {result['errors']}")
                return None

            me = result.get("data", {}).get("me")
            if not me:
                logger.error("Hashnode: Could not get user info. Is the token valid?")
                return None

            print(f"Hashnode user: {me.get('username')}")  # Debug

            edges = me.get("publications", {}).get("edges", [])
            if edges:
                pub_id = edges[0]["node"]["id"]
                pub_title = edges[0]["node"].get("title", pub_id)
                print(f"Hashnode publication: {pub_title} (ID: {pub_id})")  # Debug
                logger.info(f"Auto-detected Hashnode publication: {pub_title}")
                return pub_id
            else:
                logger.error("No Hashnode publications found. Create one at hashnode.com first.")
        except Exception as e:
            logger.error(f"Failed to fetch Hashnode publication: {e}")
            import traceback
            traceback.print_exc()
        return None

    def publish(self, article: ArticleData, published: bool = True) -> PublishResult:
        """
        Publish an article to Hashnode.

        Args:
            article: Article data to publish
            published: True to publish immediately

        Returns:
            PublishResult with success status and URL
        """
        if not self.is_configured():
            return PublishResult(
                success=False,
                platform=self.platform_name,
                error="Hashnode not configured (need token)"
            )

        # Auto-fetch publication_id if not set
        pub_id = self.publication_id
        if not pub_id:
            pub_id = self._get_my_publication_id()
            if not pub_id:
                return PublishResult(
                    success=False,
                    platform=self.platform_name,
                    error="Could not find your Hashnode publication"
                )
            self.publication_id = pub_id  # Cache it

        # Prepare tags
        tags = self._clean_tags(article.tags, max_tags=5)
        tag_objects = [{"name": tag, "slug": tag} for tag in tags]

        # GraphQL mutation for publishing
        mutation = """
        mutation PublishPost($input: PublishPostInput!) {
            publishPost(input: $input) {
                post {
                    id
                    title
                    slug
                    url
                }
            }
        }
        """

        variables = {
            "input": {
                "publicationId": self.publication_id,
                "title": article.title,
                "contentMarkdown": article.content,
                "tags": tag_objects,
            }
        }

        # Add optional fields
        if article.cover_image_url:
            variables["input"]["coverImageOptions"] = {
                "coverImageURL": article.cover_image_url
            }

        if article.canonical_url:
            variables["input"]["originalArticleURL"] = article.canonical_url

        try:
            result = self._graphql_request(mutation, variables)

            if "errors" in result:
                error_msg = result["errors"][0].get("message", str(result["errors"]))
                logger.error(f"Hashnode publish failed: {error_msg}")
                return PublishResult(
                    success=False,
                    platform=self.platform_name,
                    error=error_msg
                )

            post_data = result.get("data", {}).get("publishPost", {}).get("post", {})

            if post_data:
                url = post_data.get("url", "")
                logger.info(f"Published to Hashnode: {url}")
                return PublishResult(
                    success=True,
                    platform=self.platform_name,
                    url=url,
                    post_id=post_data.get("id")
                )
            else:
                return PublishResult(
                    success=False,
                    platform=self.platform_name,
                    error="No post data in response"
                )

        except requests.RequestException as e:
            logger.error(f"Hashnode request failed: {e}")
            return PublishResult(
                success=False,
                platform=self.platform_name,
                error=str(e)
            )

    def get_publication(self) -> Optional[dict]:
        """Get publication info."""
        if not self.is_configured():
            return None

        query = """
        query GetPublication($id: ObjectId!) {
            publication(id: $id) {
                id
                title
                url
            }
        }
        """

        try:
            result = self._graphql_request(query, {"id": self.publication_id})
            return result.get("data", {}).get("publication")
        except requests.RequestException:
            pass

        return None

    def test_connection(self) -> bool:
        """Test API connection."""
        pub = self.get_publication()
        if pub:
            logger.info(f"Hashnode connected to: {pub.get('title')}")
            return True
        return False
