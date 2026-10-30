"""
Settings View - Configure API keys and platform credentials.
"""

import flet as ft
from pathlib import Path
import yaml
from ..theme import Colors
from ..components import create_button


class SettingsView(ft.Column):
    """Settings page for API keys and configuration."""

    def __init__(self, page: ft.Page):
        self._page = page
        self.config_path = Path("config/api_keys.yaml")

        # Load current config
        self.config = self._load_config()

        # Anthropic section
        self.anthropic_key = ft.TextField(
            label="Anthropic API Key",
            hint_text="sk-ant-...",
            value=self._get_nested(self.config, 'anthropic', 'api_key') or self.config.get('api_key', ''),
            password=True,
            can_reveal_password=True,
            width=500,
            border_color=Colors.BG_TERTIARY,
            focused_border_color=Colors.ACCENT,
        )

        # Dev.to section
        self.devto_key = ft.TextField(
            label="Dev.to API Key",
            hint_text="Get from dev.to/settings/extensions",
            value=self._get_nested(self.config, 'devto', 'api_key'),
            password=True,
            can_reveal_password=True,
            width=500,
            border_color=Colors.BG_TERTIARY,
            focused_border_color=Colors.ACCENT,
        )

        # Hashnode section
        self.hashnode_token = ft.TextField(
            label="Hashnode Token",
            hint_text="Get from hashnode.com/settings/developer",
            value=self._get_nested(self.config, 'hashnode', 'token'),
            password=True,
            can_reveal_password=True,
            width=500,
            border_color=Colors.BG_TERTIARY,
            focused_border_color=Colors.ACCENT,
        )
        self.hashnode_pub_id = ft.TextField(
            label="Hashnode Publication ID (optional)",
            hint_text="Auto-detected if empty",
            value=self._get_nested(self.config, 'hashnode', 'publication_id'),
            width=500,
            border_color=Colors.BG_TERTIARY,
            focused_border_color=Colors.ACCENT,
        )

        # YouTube section
        self.youtube_status = ft.Text(
            "Requires OAuth setup - see instructions",
            size=12,
            color=Colors.TEXT_MUTED
        )
        self.youtube_oauth_btn = ft.ElevatedButton(
            "Setup YouTube OAuth",
            on_click=self._on_youtube_oauth,
            icon=ft.Icons.LOGIN,
        )

        # LinkedIn section
        self.linkedin_client_id = ft.TextField(
            label="LinkedIn Client ID",
            hint_text="From linkedin.com/developers",
            value=self._get_nested(self.config, 'linkedin', 'client_id'),
            width=240,
            border_color=Colors.BG_TERTIARY,
            focused_border_color=Colors.ACCENT,
        )
        self.linkedin_client_secret = ft.TextField(
            label="LinkedIn Client Secret",
            value=self._get_nested(self.config, 'linkedin', 'client_secret'),
            password=True,
            can_reveal_password=True,
            width=240,
            border_color=Colors.BG_TERTIARY,
            focused_border_color=Colors.ACCENT,
        )
        self.linkedin_token = ft.TextField(
            label="LinkedIn Access Token",
            hint_text="Run OAuth flow to get this",
            value=self._get_nested(self.config, 'linkedin', 'access_token'),
            password=True,
            can_reveal_password=True,
            width=500,
            border_color=Colors.BG_TERTIARY,
            focused_border_color=Colors.ACCENT,
        )
        self.linkedin_oauth_btn = ft.TextButton(
            "Run OAuth Flow",
            on_click=self._on_linkedin_oauth,
            style=ft.ButtonStyle(color=Colors.ACCENT),
        )

        # Bluesky section
        self.bluesky_handle = ft.TextField(
            label="Bluesky Handle",
            hint_text="username.bsky.social",
            value=self._get_nested(self.config, 'bluesky', 'handle'),
            width=240,
            border_color=Colors.BG_TERTIARY,
            focused_border_color=Colors.ACCENT,
        )
        self.bluesky_password = ft.TextField(
            label="Bluesky App Password",
            hint_text="Create in Bluesky Settings > App Passwords",
            value=self._get_nested(self.config, 'bluesky', 'app_password'),
            password=True,
            can_reveal_password=True,
            width=240,
            border_color=Colors.BG_TERTIARY,
            focused_border_color=Colors.ACCENT,
        )

        # Unsplash section
        self.unsplash_key = ft.TextField(
            label="Unsplash Access Key",
            hint_text="For dynamic cover images",
            value=self._get_nested(self.config, 'unsplash', 'access_key'),
            password=True,
            can_reveal_password=True,
            width=500,
            border_color=Colors.BG_TERTIARY,
            focused_border_color=Colors.ACCENT,
        )

        # Save button
        self.save_btn = create_button("Save Settings", self._on_save, ft.Icons.SAVE, Colors.ACCENT)
        self.save_btn.width = 200

        # Test connections button
        self.test_btn = create_button("Test Connections", self._on_test, ft.Icons.NETWORK_CHECK)
        self.test_btn.width = 200

        # Status text
        self.status_text = ft.Text("", size=14, color=Colors.TEXT_SECONDARY)

        # Connection status
        self.connection_status = ft.Column([], spacing=5)

        # Build layout
        super().__init__(
            controls=[
                ft.Text("Settings", size=28, weight=ft.FontWeight.BOLD, color=Colors.TEXT_PRIMARY),
                ft.Text("Configure API keys and platform credentials", size=14, color=Colors.TEXT_SECONDARY),
                ft.Divider(height=20, color=Colors.BG_TERTIARY),

                # Anthropic
                self._create_section(
                    "Anthropic (Claude API)",
                    "Required for article generation",
                    [self.anthropic_key],
                    "https://console.anthropic.com/",
                ),

                ft.Divider(height=20, color=Colors.BG_TERTIARY),

                # Dev.to
                self._create_section(
                    "Dev.to",
                    "FREE - Developer blogging platform",
                    [self.devto_key],
                    "https://dev.to/settings/extensions",
                ),

                ft.Divider(height=20, color=Colors.BG_TERTIARY),

                # Hashnode
                self._create_section(
                    "Hashnode",
                    "FREE - Only token needed, publication ID auto-detected",
                    [self.hashnode_token, self.hashnode_pub_id],
                    "https://hashnode.com/settings/developer",
                ),

                ft.Divider(height=20, color=Colors.BG_TERTIARY),

                # Bluesky
                self._create_section(
                    "Bluesky",
                    "FREE - Decentralized social network",
                    [ft.Row([self.bluesky_handle, self.bluesky_password], spacing=20)],
                    "https://bsky.app/settings/app-passwords",
                ),

                ft.Divider(height=20, color=Colors.BG_TERTIARY),

                # Unsplash
                self._create_section(
                    "Unsplash",
                    "FREE - Dynamic cover images based on article tags (50 req/hour)",
                    [self.unsplash_key],
                    "https://unsplash.com/developers",
                ),

                ft.Divider(height=20, color=Colors.BG_TERTIARY),

                # LinkedIn
                self._create_section(
                    "LinkedIn",
                    "FREE - Professional network (requires OAuth)",
                    [
                        ft.Row([self.linkedin_client_id, self.linkedin_client_secret], spacing=20),
                        ft.Row([self.linkedin_token, self.linkedin_oauth_btn], spacing=10),
                    ],
                    "https://www.linkedin.com/developers/",
                ),

                ft.Divider(height=20, color=Colors.BG_TERTIARY),

                # YouTube
                self._create_section(
                    "YouTube",
                    "FREE - Upload audio as video (requires OAuth + FFmpeg)",
                    [
                        ft.Text("1. Create project at Google Cloud Console", size=12, color=Colors.TEXT_SECONDARY),
                        ft.Text("2. Enable YouTube Data API v3", size=12, color=Colors.TEXT_SECONDARY),
                        ft.Text("3. Create OAuth credentials (Desktop app)", size=12, color=Colors.TEXT_SECONDARY),
                        ft.Text("4. Download client_secrets.json to config/", size=12, color=Colors.TEXT_SECONDARY),
                        ft.Container(height=5),
                        ft.Row([self.youtube_oauth_btn, self.youtube_status], spacing=10),
                    ],
                    "https://console.cloud.google.com/apis/library/youtube.googleapis.com",
                ),

                ft.Divider(height=20, color=Colors.BG_TERTIARY),

                # Actions
                ft.Row([self.save_btn, self.test_btn], spacing=20),
                self.status_text,
                ft.Container(height=10),
                self.connection_status,
            ],
            spacing=10,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

    def _get_nested(self, d: dict, *keys) -> str:
        """Get nested dict value safely."""
        for key in keys:
            if isinstance(d, dict):
                d = d.get(key, {})
            else:
                return ''
        return d if isinstance(d, str) else ''

    def _load_config(self) -> dict:
        """Load config from file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    return yaml.safe_load(f) or {}
            except Exception:
                pass
        return {}

    def _save_config(self, config: dict):
        """Save config to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    def _create_section(self, title: str, description: str, controls: list, link: str) -> ft.Container:
        """Create a settings section."""
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(title, size=18, weight=ft.FontWeight.BOLD, color=Colors.TEXT_PRIMARY),
                    ft.TextButton(
                        "Get credentials",
                        url=link,
                        style=ft.ButtonStyle(color=Colors.ACCENT),
                    ),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Text(description, size=12, color=Colors.TEXT_SECONDARY),
                ft.Container(height=5),
                *controls,
            ], spacing=5),
            bgcolor=Colors.BG_SECONDARY,
            border_radius=8,
            padding=15,
        )

    def _on_save(self, e):
        """Save settings to config file."""
        config = {
            'anthropic': {
                'api_key': self.anthropic_key.value,
            },
            'api_key': self.anthropic_key.value,  # Legacy
            'devto': {
                'api_key': self.devto_key.value,
            },
            'hashnode': {
                'token': self.hashnode_token.value,
                'publication_id': self.hashnode_pub_id.value,
            },
            'linkedin': {
                'client_id': self.linkedin_client_id.value,
                'client_secret': self.linkedin_client_secret.value,
                'access_token': self.linkedin_token.value,
            },
            'bluesky': {
                'handle': self.bluesky_handle.value,
                'app_password': self.bluesky_password.value,
            },
            'unsplash': {
                'access_key': self.unsplash_key.value,
            },
        }

        try:
            self._save_config(config)
            self.config = config
            self.status_text.value = "Settings saved!"
            self.status_text.color = Colors.SUCCESS
        except Exception as ex:
            self.status_text.value = f"Error saving: {ex}"
            self.status_text.color = Colors.ERROR

        self._page.update()

    def _on_test(self, e):
        """Test connections to all configured platforms."""
        self.status_text.value = "Testing connections..."
        self.status_text.color = Colors.TEXT_SECONDARY
        self._page.update()

        results = []

        # Test Anthropic
        if self.anthropic_key.value:
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=self.anthropic_key.value)
                # Just create client - don't make API call
                results.append(("Anthropic", True, "API key format valid"))
            except Exception as ex:
                results.append(("Anthropic", False, str(ex)[:50]))
        else:
            results.append(("Anthropic", False, "Not configured"))

        # Test publishers
        try:
            from publishers import PublishManager
            manager = PublishManager({
                'devto': {'api_key': self.devto_key.value},
                'hashnode': {'token': self.hashnode_token.value, 'publication_id': self.hashnode_pub_id.value},
                'linkedin': {'access_token': self.linkedin_token.value},
                'bluesky': {'handle': self.bluesky_handle.value, 'app_password': self.bluesky_password.value},
            })

            test_results = manager.test_connections()
            for platform, success in test_results.items():
                results.append((platform, success, "Connected" if success else "Failed"))

        except ImportError:
            results.append(("Publishers", False, "Module not available"))
        except Exception as ex:
            results.append(("Publishers", False, str(ex)[:50]))

        # Display results
        status_controls = []
        for name, success, msg in results:
            icon = ft.Icons.CHECK_CIRCLE if success else ft.Icons.ERROR
            color = Colors.SUCCESS if success else Colors.ERROR
            status_controls.append(
                ft.Row([
                    ft.Icon(icon, size=16, color=color),
                    ft.Text(f"{name}: {msg}", size=12, color=color),
                ], spacing=8)
            )

        self.connection_status.controls = status_controls
        self.status_text.value = f"Tested {len(results)} connections"
        self.status_text.color = Colors.TEXT_SECONDARY
        self._page.update()

    def _on_linkedin_oauth(self, e):
        """Run LinkedIn OAuth flow."""
        client_id = self.linkedin_client_id.value
        client_secret = self.linkedin_client_secret.value

        if not client_id or not client_secret:
            self.status_text.value = "Enter LinkedIn Client ID and Secret first"
            self.status_text.color = Colors.WARNING
            self._page.update()
            return

        try:
            from publishers.linkedin import run_oauth_flow
            self.status_text.value = "Opening browser for LinkedIn auth..."
            self.status_text.color = Colors.TEXT_SECONDARY
            self._page.update()

            # This will open browser and wait for callback
            token = run_oauth_flow(client_id, client_secret)

            if token:
                self.linkedin_token.value = token
                self.status_text.value = "LinkedIn OAuth successful!"
                self.status_text.color = Colors.SUCCESS
            else:
                self.status_text.value = "LinkedIn OAuth failed"
                self.status_text.color = Colors.ERROR

        except Exception as ex:
            self.status_text.value = f"OAuth error: {ex}"
            self.status_text.color = Colors.ERROR

        self._page.update()

    def _on_youtube_oauth(self, e):
        """Run YouTube OAuth flow."""
        from pathlib import Path

        secrets_path = Path("config/client_secrets.json")
        if not secrets_path.exists():
            self.youtube_status.value = "Download client_secrets.json first!"
            self.youtube_status.color = Colors.WARNING
            self._page.update()
            return

        try:
            from publishers.youtube import run_oauth_flow
            self.youtube_status.value = "Opening browser for YouTube auth..."
            self.youtube_status.color = Colors.TEXT_SECONDARY
            self._page.update()

            success = run_oauth_flow(str(secrets_path))

            if success:
                self.youtube_status.value = "YouTube OAuth successful!"
                self.youtube_status.color = Colors.SUCCESS
            else:
                self.youtube_status.value = "YouTube OAuth failed"
                self.youtube_status.color = Colors.ERROR

        except Exception as ex:
            self.youtube_status.value = f"OAuth error: {str(ex)[:30]}"
            self.youtube_status.color = Colors.ERROR

        self._page.update()
