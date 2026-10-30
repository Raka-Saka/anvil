"""
LinkedIn Publisher - Publish posts to LinkedIn via REST API.

API Docs: https://learn.microsoft.com/en-us/linkedin/marketing/
Requires: OAuth2 setup with w_member_social scope
Cost: FREE

Setup:
1. Create app at https://www.linkedin.com/developers/
2. Request "Share on LinkedIn" and "Sign In with LinkedIn" products
3. Run the OAuth flow to get access token
4. Store access token in config
"""

import requests
import logging
import webbrowser
from urllib.parse import urlencode, parse_qs, urlparse
from typing import Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from .base import BasePublisher, ArticleData, PublishResult

logger = logging.getLogger(__name__)


class LinkedInPublisher(BasePublisher):
    """Publish posts to LinkedIn."""

    platform_name = "linkedin"
    API_BASE = "https://api.linkedin.com/v2"
    AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
    TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"

    def __init__(self, config: dict):
        super().__init__(config)
        self.client_id = config.get('client_id', '')
        self.client_secret = config.get('client_secret', '')
        self.access_token = config.get('access_token', '')
        self.person_urn = config.get('person_urn', '')  # Format: urn:li:person:XXXXX

    def _validate_config(self):
        """Validate LinkedIn config."""
        if not self.config.get('access_token'):
            logger.warning("LinkedIn access_token not configured")

    def is_configured(self) -> bool:
        """Check if LinkedIn is configured."""
        return bool(self.access_token)

    def needs_oauth_setup(self) -> bool:
        """Check if OAuth setup is needed."""
        return bool(self.client_id and self.client_secret and not self.access_token)

    def get_oauth_url(self, redirect_uri: str = "http://localhost:8585/callback") -> str:
        """Get OAuth authorization URL."""
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": "openid profile w_member_social",
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    def exchange_code_for_token(self, code: str, redirect_uri: str = "http://localhost:8585/callback") -> Optional[str]:
        """Exchange authorization code for access token."""
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        try:
            response = requests.post(self.TOKEN_URL, data=data, timeout=30)
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get("access_token")
                return self.access_token
        except requests.RequestException as e:
            logger.error(f"Token exchange failed: {e}")

        return None

    def get_profile(self) -> Optional[dict]:
        """Get user profile to obtain person URN."""
        if not self.access_token:
            return None

        headers = {
            "Authorization": f"Bearer {self.access_token}",
        }

        try:
            response = requests.get(
                "https://api.linkedin.com/v2/userinfo",
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                # Store person URN
                if "sub" in data:
                    self.person_urn = f"urn:li:person:{data['sub']}"
                return data
        except requests.RequestException:
            pass

        return None

    def publish(self, article: ArticleData, include_link: bool = True) -> PublishResult:
        """
        Publish a post to LinkedIn.

        Note: LinkedIn API creates posts, not long-form articles.
        We'll create a post with article summary and link.

        Args:
            article: Article data
            include_link: Include link to original article

        Returns:
            PublishResult with success status
        """
        if not self.is_configured():
            return PublishResult(
                success=False,
                platform=self.platform_name,
                error="LinkedIn access_token not configured"
            )

        # Get person URN if not set
        if not self.person_urn:
            profile = self.get_profile()
            if not profile:
                return PublishResult(
                    success=False,
                    platform=self.platform_name,
                    error="Could not get LinkedIn profile"
                )

        # Create post text (LinkedIn posts have ~3000 char limit)
        # Extract first few paragraphs as summary
        content_lines = article.content.split('\n')
        summary_lines = []
        char_count = 0

        for line in content_lines:
            if line.startswith('#'):
                continue  # Skip headers
            if line.strip():
                if char_count + len(line) > 2500:
                    break
                summary_lines.append(line)
                char_count += len(line)
                if char_count > 800:  # Keep it digestible
                    break

        summary = '\n\n'.join(summary_lines[:5])

        # Build post text
        post_text = f"{article.title}\n\n{summary}"

        if include_link and article.canonical_url:
            post_text += f"\n\nRead full article: {article.canonical_url}"

        # Add hashtags
        tags = self._clean_tags(article.tags, max_tags=5)
        if tags:
            post_text += "\n\n" + " ".join(f"#{tag}" for tag in tags)

        # Prepare API payload
        payload = {
            "author": self.person_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": post_text[:3000]  # LinkedIn limit
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }

        # Add article link if available
        if article.canonical_url:
            payload["specificContent"]["com.linkedin.ugc.ShareContent"]["shareMediaCategory"] = "ARTICLE"
            payload["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [{
                "status": "READY",
                "originalUrl": article.canonical_url,
            }]

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }

        try:
            response = requests.post(
                f"{self.API_BASE}/ugcPosts",
                json=payload,
                headers=headers,
                timeout=30
            )

            if response.status_code == 201:
                data = response.json()
                post_id = data.get("id", "")
                logger.info(f"Published to LinkedIn: {post_id}")
                return PublishResult(
                    success=True,
                    platform=self.platform_name,
                    post_id=post_id,
                    url=f"https://www.linkedin.com/feed/update/{post_id}"
                )
            else:
                error_msg = response.text
                logger.error(f"LinkedIn publish failed: {error_msg}")
                return PublishResult(
                    success=False,
                    platform=self.platform_name,
                    error=f"HTTP {response.status_code}: {error_msg}"
                )

        except requests.RequestException as e:
            logger.error(f"LinkedIn request failed: {e}")
            return PublishResult(
                success=False,
                platform=self.platform_name,
                error=str(e)
            )

    def test_connection(self) -> bool:
        """Test API connection."""
        profile = self.get_profile()
        if profile:
            logger.info(f"LinkedIn connected as: {profile.get('name', 'Unknown')}")
            return True
        return False


def run_oauth_flow(client_id: str, client_secret: str) -> Optional[str]:
    """
    Run interactive OAuth flow to get access token.

    Opens browser for authorization and captures callback.
    Returns access token if successful.
    """
    auth_code = None
    redirect_uri = "http://localhost:8585/callback"

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            nonlocal auth_code
            query = parse_qs(urlparse(self.path).query)
            if "code" in query:
                auth_code = query["code"][0]
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h1>Authorization successful!</h1><p>You can close this window.</p>")
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Authorization failed")

        def log_message(self, format, *args):
            pass  # Suppress logs

    # Create publisher for URL generation
    config = {"client_id": client_id, "client_secret": client_secret}
    publisher = LinkedInPublisher(config)

    # Start local server
    server = HTTPServer(("localhost", 8585), CallbackHandler)
    server_thread = threading.Thread(target=server.handle_request)
    server_thread.start()

    # Open browser
    auth_url = publisher.get_oauth_url(redirect_uri)
    print(f"Opening browser for LinkedIn authorization...")
    print(f"If browser doesn't open, visit: {auth_url}")
    webbrowser.open(auth_url)

    # Wait for callback
    server_thread.join(timeout=120)
    server.server_close()

    if auth_code:
        # Exchange for token
        token = publisher.exchange_code_for_token(auth_code, redirect_uri)
        if token:
            print(f"Access token obtained successfully!")
            print(f"Add this to your config/api_keys.yaml:")
            print(f"linkedin:")
            print(f"  access_token: \"{token}\"")
            return token

    print("OAuth flow failed")
    return None
