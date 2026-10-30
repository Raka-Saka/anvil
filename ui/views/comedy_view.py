"""
Comedy View - Generate diary-style comedy articles from ChronOS logs.
Simple: one button, generates the next chronological entry.
Includes publishing to multiple platforms (dev.to, Hashnode, LinkedIn, Bluesky).
"""

import flet as ft
from pathlib import Path
import json
import threading
from datetime import datetime
from ..theme import Colors
from ..components import WarningPanel, PreviewBox, create_button

# Try to import publishers
try:
    from publishers import PublishManager
    from publishers.base import ArticleData
    HAS_PUBLISHERS = True
except ImportError:
    HAS_PUBLISHERS = False
    PublishManager = None
    ArticleData = None


class ComedyView(ft.Column):
    """Comedy article generation - simple one-button interface."""

    def __init__(self, page: ft.Page):
        self._page = page

        # Paths
        self.log_path = Path("F:/chronos/ENGINEERING_LOG_V4.md")
        self.roadmap_path = Path("F:/chronos/ROADMAP_V4.md")
        self.output_dir = Path(__file__).parent.parent.parent / "output" / "articles" / "comedy"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.output_dir / ".history.json"

        # Status display
        self.status_text = ft.Text("", size=14, color=Colors.TEXT_SECONDARY)
        self.next_entry_text = ft.Text("", size=16, color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.W_500)

        # Main button
        self.generate_btn = create_button(
            "Generate Next Diary Entry",
            self._on_generate,
            ft.Icons.AUTO_STORIES,
            Colors.ACCENT
        )
        self.generate_btn.width = 300
        self.generate_btn.height = 50

        # Skip button
        self.skip_btn = ft.TextButton(
            "Skip this section",
            on_click=self._on_skip,
            style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
        )

        # Reset button
        self.reset_btn = ft.TextButton(
            "Reset history",
            on_click=self._on_reset,
            style=ft.ButtonStyle(color=Colors.TEXT_MUTED),
        )

        # Previous articles dropdown
        self.articles_dropdown = ft.Dropdown(
            label="Previous Articles",
            options=[],
            width=400,
            border_color=Colors.BG_TERTIARY,
            bgcolor=Colors.BG_SECONDARY,
        )

        self.view_btn = create_button("View", self._on_view_article, ft.Icons.VISIBILITY)
        self.view_ja_btn = create_button("View JA", self._on_view_article_ja, ft.Icons.TRANSLATE)

        # Result display (TextField so user can copy)
        self.title_display = ft.TextField(
            value="",
            read_only=True,
            border=ft.InputBorder.NONE,
            text_size=20,
            text_style=ft.TextStyle(weight=ft.FontWeight.BOLD),
            color=Colors.TEXT_PRIMARY,
            bgcolor=Colors.BG_PRIMARY,
            width=600,
        )
        self.word_count = ft.Text("", size=12, color=Colors.TEXT_SECONDARY)
        self.hashtags = ft.TextField(
            value="",
            read_only=True,
            border=ft.InputBorder.NONE,
            text_size=11,
            color=Colors.ACCENT,
            bgcolor=Colors.BG_PRIMARY,
            width=600,
        )

        self.preview = PreviewBox("Press the button to generate the next diary entry, or select a previous article to view...")
        self.warnings = WarningPanel()

        self.save_btn = create_button("Open in Folder", self._on_open_folder, ft.Icons.FOLDER_OPEN)
        self.save_btn.visible = False

        self.last_filepath = None
        self.current_article_base = None  # For switching EN/JA
        self.current_result = None  # Store full result for publishing

        # Publishing section
        self._init_publishing_ui()

        # Build layout
        super().__init__(
            controls=[
                ft.Text("Dear Diary...", size=28, weight=ft.FontWeight.BOLD, color=Colors.TEXT_PRIMARY, italic=True),
                ft.Text("Comedy articles from ChronOS development", size=14, color=Colors.TEXT_SECONDARY),
                ft.Divider(height=20, color=Colors.BG_TERTIARY),

                # Status section
                self.status_text,
                self.next_entry_text,
                ft.Container(height=10),

                # Action buttons
                ft.Row([self.generate_btn], alignment=ft.MainAxisAlignment.CENTER),
                ft.Row([self.skip_btn, self.reset_btn], alignment=ft.MainAxisAlignment.CENTER, spacing=30),

                ft.Divider(height=20, color=Colors.BG_TERTIARY),

                # Publishing section (moved up for visibility)
                self.publish_section,

                ft.Divider(height=20, color=Colors.BG_TERTIARY),

                # Previous articles
                ft.Row([self.articles_dropdown, self.view_btn, self.view_ja_btn], spacing=10),

                ft.Divider(height=10, color=Colors.BG_TERTIARY),

                # Result section
                ft.Row([self.title_display, self.word_count], spacing=20),
                self.hashtags,
                ft.Row([
                    ft.Container(content=self.preview, expand=3),
                    ft.Container(content=self.warnings, expand=1, padding=10),
                ], spacing=20, expand=True),
                ft.Row([self.save_btn], alignment=ft.MainAxisAlignment.END),
            ],
            spacing=10,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

        # Initialize status and load previous articles
        self._update_status()
        self._load_previous_articles()
        self._update_publish_status()

        # Debug: Check checkbox values after init
        print(f">>> INIT DONE - checkbox values: devto={self.cb_devto.value}, hashnode={self.cb_hashnode.value}, bluesky={self.cb_bluesky.value}, youtube={self.cb_youtube.value}", flush=True)

    def _init_publishing_ui(self):
        """Initialize the publishing UI controls."""
        # Platform checkboxes
        self.cb_devto = ft.Checkbox(label="Dev.to", value=True)
        self.cb_hashnode = ft.Checkbox(label="Hashnode", value=True)
        self.cb_linkedin = ft.Checkbox(label="LinkedIn", value=False)
        self.cb_bluesky = ft.Checkbox(label="Bluesky", value=True)
        self.cb_bluesky_thread = ft.Checkbox(label="as Thread", value=True)
        self.cb_youtube = ft.Checkbox(label="YouTube", value=False)

        # Media options
        self.cb_cover_image = ft.Checkbox(label="Generate Cover Image", value=True)
        self.cb_audio_en = ft.Checkbox(label="Audio (EN)", value=False)
        self.cb_audio_ja = ft.Checkbox(label="Audio (JA)", value=False)
        self.cb_bg_music = ft.Checkbox(label="+ Background Music", value=True)
        self.voice_dropdown = ft.Dropdown(
            label="Voice",
            value="male",
            options=[
                ft.dropdown.Option("male", "Male"),
                ft.dropdown.Option("female", "Female"),
            ],
            width=120,
            border_color=Colors.BG_TERTIARY,
        )

        # Publish button
        self.publish_btn = create_button(
            "Publish Article",
            self._on_publish,
            ft.Icons.PUBLISH,
            Colors.ACCENT
        )
        self.publish_btn.width = 200
        self.publish_btn.disabled = True

        # Status indicators
        self.publish_status = ft.Text("", size=12, color=Colors.TEXT_SECONDARY)

        # Platform status indicators
        self.platform_status = ft.Row([], spacing=10)

        # Build section
        if HAS_PUBLISHERS:
            platform_row = ft.Column([
                ft.Row([
                    ft.Text("Platforms:", size=14, color=Colors.TEXT_SECONDARY, width=80),
                    self.cb_devto,
                    self.cb_hashnode,
                    self.cb_linkedin,
                ], spacing=15),
                ft.Row([
                    ft.Container(width=80),  # Spacer
                    self.cb_bluesky,
                    self.cb_bluesky_thread,
                    self.cb_youtube,
                    ft.Text("(needs Audio)", size=11, color=Colors.TEXT_MUTED),
                ], spacing=15),
            ], spacing=5)

            media_row = ft.Row([
                ft.Text("Media:", size=14, color=Colors.TEXT_SECONDARY, width=80),
                self.cb_cover_image,
                self.cb_audio_en,
                self.cb_audio_ja,
                self.cb_bg_music,
                self.voice_dropdown,
            ], spacing=15)

            self.publish_section = ft.Container(
                content=ft.Column([
                    ft.Text("Publish", size=18, weight=ft.FontWeight.BOLD, color=Colors.TEXT_PRIMARY),
                    ft.Text("Publish to multiple platforms at once", size=12, color=Colors.TEXT_SECONDARY),
                    ft.Container(height=10),
                    platform_row,
                    media_row,
                    ft.Container(height=10),
                    self.platform_status,
                    ft.Row([self.publish_btn, self.publish_status], spacing=20),
                ], spacing=8),
                bgcolor=Colors.BG_SECONDARY,
                border_radius=8,
                padding=15,
            )
        else:
            self.publish_section = ft.Container(
                content=ft.Column([
                    ft.Text("Publishing Unavailable", size=14, color=Colors.TEXT_SECONDARY),
                    ft.Text("Install publishers module to enable cross-platform publishing.",
                            size=12, color=Colors.TEXT_MUTED),
                ], spacing=5),
                bgcolor=Colors.BG_SECONDARY,
                border_radius=8,
                padding=15,
            )

    def _update_publish_status(self):
        """Update publishing platform status indicators."""
        if not HAS_PUBLISHERS:
            return

        try:
            manager = PublishManager.from_config_file("config/api_keys.yaml")
            status = manager.get_platform_status()

            indicators = []
            for platform, info in status.items():
                if info['configured']:
                    color = Colors.ACCENT
                    icon = ft.Icons.CHECK_CIRCLE
                else:
                    color = Colors.TEXT_MUTED
                    icon = ft.Icons.CIRCLE_OUTLINED

                indicators.append(
                    ft.Row([
                        ft.Icon(icon, size=14, color=color),
                        ft.Text(platform, size=12, color=color),
                    ], spacing=4)
                )

            self.platform_status.controls = indicators
        except Exception as e:
            self.platform_status.controls = [
                ft.Text(f"Config error: {e}", size=12, color=Colors.WARNING)
            ]

    def _load_history(self) -> dict:
        """Load generation history."""
        if self.history_file.exists():
            return json.loads(self.history_file.read_text())
        return {'used_sections': []}

    def _save_history(self, history: dict):
        """Save generation history."""
        self.history_file.write_text(json.dumps(history, indent=2))

    def _load_previous_articles(self):
        """Load list of previous articles into dropdown."""
        articles = []

        # Find all EN articles (use as base)
        for f in sorted(self.output_dir.glob("*_EN.md"), reverse=True):
            # Extract title from filename
            name = f.stem.replace("_EN", "")
            # Get a cleaner display name
            parts = name.split("_", 2)  # comedy_timestamp_title
            if len(parts) >= 3:
                display = parts[2].replace("_", " ")[:50]
            else:
                display = name[:50]
            articles.append((str(f), display))

        # Also find articles without _EN suffix (old format)
        for f in sorted(self.output_dir.glob("comedy_*.md"), reverse=True):
            if "_EN.md" not in f.name and "_JA.md" not in f.name:
                name = f.stem
                parts = name.split("_", 2)
                if len(parts) >= 3:
                    display = parts[2].replace("_", " ")[:50] + " (EN only)"
                else:
                    display = name[:50]
                articles.append((str(f), display))

        self.articles_dropdown.options = [
            ft.dropdown.Option(path, display)
            for path, display in articles
        ]
        try:
            self._page.update()
        except Exception:
            pass  # May fail during init

    def _on_view_article(self, e):
        """View selected article in English."""
        selected = self.articles_dropdown.value
        if not selected:
            return

        filepath = Path(selected)
        self.current_article_base = filepath
        self._show_article(filepath, "en")

    def _on_view_article_ja(self, e):
        """View selected article in Japanese."""
        selected = self.articles_dropdown.value
        if not selected:
            return

        filepath = Path(selected)
        self.current_article_base = filepath
        self._show_article(filepath, "ja")

    def _show_article(self, base_path: Path, lang: str):
        """Display an article in the preview."""
        # Figure out the actual file path
        base_str = str(base_path)

        if "_EN.md" in base_str:
            if lang == "ja":
                filepath = Path(base_str.replace("_EN.md", "_JA.md"))
            else:
                filepath = base_path
        else:
            # Old format without _EN suffix
            if lang == "ja":
                # Try to find JA version
                ja_path = Path(base_str.replace(".md", "_JA.md"))
                if ja_path.exists():
                    filepath = ja_path
                else:
                    self.preview.set_content("No Japanese version available for this article.")
                    self._page.update()
                    return
            else:
                filepath = base_path

        if not filepath.exists():
            self.preview.set_content(f"File not found: {filepath}")
            self._page.update()
            return

        # Read and display
        content = filepath.read_text(encoding='utf-8')

        # Parse frontmatter and content
        title = ""
        body = content

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1]
                body = parts[2].strip()

                # Extract title from frontmatter
                for line in frontmatter.split("\n"):
                    if line.startswith("title:"):
                        title = line.replace("title:", "").strip().strip('"')
                    elif line.startswith("word_count:"):
                        wc = line.replace("word_count:", "").strip()
                        self.word_count.value = f"{wc} words"
                    elif line.startswith("hashtags:"):
                        tags = line.replace("hashtags:", "").strip()
                        self.hashtags.value = tags

        self.title_display.value = title
        self.preview.set_content(body)
        self.save_btn.visible = True
        self.last_filepath = filepath
        self.current_result = None  # Clear cached result, will load from file
        self.publish_btn.disabled = False  # Enable publishing
        self._page.update()

    def _get_sections(self) -> list:
        """Get available sections from logs."""
        from generators.comedy_article import ComedyArticleGenerator
        from core.config import load_api_key

        api_key = load_api_key()
        generator = ComedyArticleGenerator(api_key=api_key)

        sections = generator.scan_sources(
            self.log_path,
            self.roadmap_path if self.roadmap_path.exists() else None
        )
        return sections

    def _update_status(self):
        """Update the status display."""
        if not self.log_path.exists():
            self.status_text.value = "ChronOS log not found at F:/chronos/"
            self.next_entry_text.value = ""
            self.generate_btn.disabled = True
            self._page.update()
            return

        try:
            sections = self._get_sections()
            history = self._load_history()
            used = set(history['used_sections'])
            available = [s for s in sections if s['title'] not in used]

            self.status_text.value = f"{len(available)} entries remaining (of {len(sections)} total)"

            if available:
                self.next_entry_text.value = f"Next: {available[0]['title']}"
                self.generate_btn.disabled = False
                self.skip_btn.visible = True
            else:
                self.next_entry_text.value = "All entries completed! Reset to start over."
                self.generate_btn.disabled = True
                self.skip_btn.visible = False

        except Exception as e:
            self.status_text.value = f"Error: {e}"
            self.next_entry_text.value = ""
            self.generate_btn.disabled = True

        self._page.update()

    def _on_generate(self, e):
        """Generate the next diary entry - starts background thread."""
        self.generate_btn.disabled = True
        self.skip_btn.visible = False
        self.generate_btn.content.value = "Writing EN..."
        self._page.update()

        # Run generation in background thread
        thread = threading.Thread(target=self._do_generate, daemon=True)
        thread.start()

    def _do_generate(self):
        """Actual generation work - runs in background thread."""
        try:
            from generators.comedy_article import ComedyArticleGenerator
            from core.config import load_api_key

            api_key = load_api_key()

            generator = ComedyArticleGenerator(api_key=api_key)

            # Get next section
            sections = self._get_sections()
            history = self._load_history()
            used = set(history['used_sections'])
            available = [s for s in sections if s['title'] not in used]

            if not available:
                self._snack = ft.SnackBar(content=ft.Text("No more sections available"))
                self._page.show_dialog(self._snack)
                self._page.update()
                return

            section = available[0]

            # Update status
            self.generate_btn.content.value = "Writing EN..."
            self._page.update()

            # Generate (this includes Japanese translation)
            result = generator.generate(
                source=section['content'],
                project_name="ChronOS",
                section_title=section['title']
            )

            # Mark as used
            history['used_sections'].append(section['title'])
            self._save_history(history)

            # Display result
            self.title_display.value = result.get('title', '')
            self.word_count.value = f"{result.get('word_count', 0)} words"
            self.hashtags.value = ' '.join(result.get('hashtags', []))
            self.preview.set_content(result['content'])
            self.warnings.update_violations(result.get('violations', []))

            # Save to files (English and Japanese)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_title = result['title'].replace(' ', '_').replace(':', '').replace("'", '').replace('"', '')[:40]

            # English version
            filename_en = f"comedy_{timestamp}_{safe_title}_EN.md"
            filepath_en = self.output_dir / filename_en

            md_content_en = f"""---
title: "{result['title']}"
generated: {result.get('generated_at', datetime.now().isoformat())}
source_section: "{section['title']}"
style: comedy
word_count: {result['word_count']}
hashtags: {' '.join(result.get('hashtags', []))}
language: en
---

# {result['title']}

{result['content']}
"""
            filepath_en.write_text(md_content_en, encoding='utf-8')

            # Japanese version
            filename_ja = f"comedy_{timestamp}_{safe_title}_JA.md"
            filepath_ja = self.output_dir / filename_ja

            hashtags_ja = result.get('hashtags_ja', [])
            hashtags_ja_str = ' '.join(hashtags_ja)

            md_content_ja = f"""---
title: "{result.get('title_ja', result['title'])}"
generated: {result.get('generated_at', datetime.now().isoformat())}
source_section: "{section['title']}"
style: comedy
language: ja
hashtags: {hashtags_ja_str}
---

# {result.get('title_ja', result['title'])}

{result.get('content_ja', '')}

---

{hashtags_ja_str}
"""
            filepath_ja.write_text(md_content_ja, encoding='utf-8')

            self.last_filepath = filepath_en
            self.current_result = result  # Store for publishing
            self.save_btn.visible = True
            self.publish_btn.disabled = False  # Enable publishing

            self._snack = ft.SnackBar(content=ft.Text(f"Saved EN + JA versions"))
            self._page.show_dialog(self._snack)

        except Exception as ex:
            self.preview.set_content(f"Error: {ex}")
            self._snack = ft.SnackBar(content=ft.Text(f"Error: {ex}"))
            self._page.show_dialog(self._snack)

        finally:
            self.generate_btn.content.value = "Generate Next Diary Entry"
            self.generate_btn.disabled = False
            self._update_status()
            self._load_previous_articles()

    def _on_skip(self, e):
        """Skip the current section."""
        try:
            sections = self._get_sections()
            history = self._load_history()
            used = set(history['used_sections'])
            available = [s for s in sections if s['title'] not in used]

            if available:
                history['used_sections'].append(available[0]['title'])
                self._save_history(history)
                self._snack = ft.SnackBar(content=ft.Text(f"Skipped: {available[0]['title'][:40]}..."))
                self._page.show_dialog(self._snack)
                self._update_status()
        except Exception as ex:
            self._snack = ft.SnackBar(content=ft.Text(f"Error: {ex}"))
            self._page.show_dialog(self._snack)
            self._page.update()

    def _on_reset(self, e):
        """Reset the history."""
        self._save_history({'used_sections': []})
        self._snack = ft.SnackBar(content=ft.Text("History reset - starting from beginning"))
        self._page.show_dialog(self._snack)
        self._update_status()

    def _on_open_folder(self, e):
        """Open the output folder."""
        import subprocess
        import sys

        if sys.platform == 'win32':
            subprocess.run(['explorer', str(self.output_dir)])
        elif sys.platform == 'darwin':
            subprocess.run(['open', str(self.output_dir)])
        else:
            subprocess.run(['xdg-open', str(self.output_dir)])

    def _on_publish(self, e):
        """Publish the current article to selected platforms."""
        print(">>> PUBLISH BUTTON CLICKED <<<", flush=True)

        if not HAS_PUBLISHERS:
            print(">>> No publishers available", flush=True)
            self._show_snack("Publishers not available")
            return

        if not self.current_result and not self.last_filepath:
            print(">>> No article to publish", flush=True)
            self._show_snack("No article to publish - generate or select one first")
            return

        # Check which platforms are selected
        print(f">>> Checkbox values - devto:{self.cb_devto.value}, hashnode:{self.cb_hashnode.value}, linkedin:{self.cb_linkedin.value}, bluesky:{self.cb_bluesky.value}, youtube:{self.cb_youtube.value}", flush=True)
        platforms = []
        if self.cb_devto.value:
            platforms.append('devto')
        if self.cb_hashnode.value:
            platforms.append('hashnode')
        if self.cb_linkedin.value:
            platforms.append('linkedin')
        if self.cb_bluesky.value:
            platforms.append('bluesky')

        # YouTube is handled separately but track selection
        use_youtube = self.cb_youtube.value

        print(f">>> Selected platforms: {platforms}, youtube: {use_youtube}", flush=True)

        if not platforms and not use_youtube:
            self._show_snack("No platforms selected")
            return

        # Disable button and start publishing
        self.publish_btn.disabled = True
        self.publish_status.value = f"Publishing to {', '.join(platforms)}..."
        self.publish_status.color = Colors.TEXT_SECONDARY
        self._page.update()

        print(">>> Starting background thread...", flush=True)
        # Run publishing in background
        try:
            thread = threading.Thread(target=self._do_publish, args=(platforms,), daemon=True)
            thread.start()
            print(">>> Thread started successfully", flush=True)
        except Exception as ex:
            print(f">>> THREAD START FAILED: {ex}", flush=True)
            self.publish_status.value = f"Thread error: {ex}"
            self._page.update()

    def _show_snack(self, message: str):
        """Show a snackbar message."""
        self._snack = ft.SnackBar(content=ft.Text(message))
        self._page.show_dialog(self._snack)
        self._page.update()

    def _do_publish(self, platforms: list):
        """Actual publishing work - runs in background thread."""
        print(f">>> THREAD RUNNING - platforms: {platforms}", flush=True)
        try:
            # Get article data
            if self.current_result:
                title = self.current_result.get('title', 'Untitled')
                content = self.current_result.get('content', '')
                content_ja = self.current_result.get('content_ja', '')
                tags = [t.lstrip('#') for t in self.current_result.get('hashtags', [])]
            elif self.last_filepath:
                # Load from file
                file_content = self.last_filepath.read_text(encoding='utf-8')
                title = ""
                content = file_content
                content_ja = ""
                tags = []

                if file_content.startswith("---"):
                    parts = file_content.split("---", 2)
                    if len(parts) >= 3:
                        frontmatter = parts[1]
                        content = parts[2].strip()
                        for line in frontmatter.split("\n"):
                            if line.startswith("title:"):
                                title = line.replace("title:", "").strip().strip('"')
                            elif line.startswith("hashtags:"):
                                tags = line.replace("hashtags:", "").strip().split()
                                tags = [t.lstrip('#') for t in tags]

                # Try to load Japanese version
                ja_path = Path(str(self.last_filepath).replace("_EN.md", "_JA.md"))
                if ja_path.exists():
                    ja_content = ja_path.read_text(encoding='utf-8')
                    if ja_content.startswith("---"):
                        parts = ja_content.split("---", 2)
                        if len(parts) >= 3:
                            content_ja = parts[2].strip()
            else:
                self.publish_status.value = "No article data"
                self._page.update()
                return

            print(f">>> Article: {title[:50]}...", flush=True)
            print(f">>> Tags: {tags}", flush=True)

            # Create ArticleData
            article = ArticleData(
                title=title,
                content=content,
                tags=tags[:5],  # Most platforms limit tags
            )

            # Initialize manager
            print(">>> Loading config...", flush=True)
            manager = PublishManager.from_config_file("config/api_keys.yaml")

            available = manager.get_available_platforms()
            print(f">>> Available platforms: {available}", flush=True)

            # Filter to only available platforms
            platforms_to_use = [p for p in platforms if p in available]

            # Handle Bluesky thread separately
            use_bluesky_thread = self.cb_bluesky.value and self.cb_bluesky_thread.value and 'bluesky' in platforms_to_use
            if use_bluesky_thread:
                platforms_to_use = [p for p in platforms_to_use if p != 'bluesky']

            if not platforms_to_use and not use_bluesky_thread and not self.cb_youtube.value:
                print(f">>> No configured platforms! Selected: {platforms}, Available: {available}", flush=True)
                self.publish_status.value = f"No platforms configured. Go to Settings."
                self.publish_status.color = Colors.WARNING
                self._page.update()
                return

            # Publish to regular platforms
            all_platform_names = platforms_to_use.copy()
            if use_bluesky_thread:
                all_platform_names.append('bluesky (thread)')
            if self.cb_youtube.value:
                all_platform_names.append('youtube')

            print(f">>> === PUBLISHING START ===", flush=True)
            print(f">>> Platforms to use: {platforms_to_use}", flush=True)
            print(f">>> All platform names: {all_platform_names}", flush=True)
            self.publish_status.value = f"Publishing to {', '.join(all_platform_names)}..."
            self._page.update()

            report = manager.publish_article(
                article=article,
                platforms=platforms_to_use,
                generate_cover=self.cb_cover_image.value,
                generate_audio_en=self.cb_audio_en.value,
                generate_audio_ja=self.cb_audio_ja.value,
                content_ja=content_ja if self.cb_audio_ja.value else None,
                voice_gender=self.voice_dropdown.value or "male"
            )

            # Publish Bluesky thread separately
            if use_bluesky_thread:
                print(">>> Publishing Bluesky thread...", flush=True)
                from publishers.bluesky import BlueskyPublisher
                bluesky_config = manager.config.get('bluesky', {})
                bluesky = BlueskyPublisher(bluesky_config)
                thread_results = bluesky.publish_thread(article, max_posts=15, hashtags=tags)

                # Summarize thread results
                thread_success = sum(1 for r in thread_results if r.success)
                thread_total = len(thread_results)
                print(f">>> Bluesky thread: {thread_success}/{thread_total} posts", flush=True)

                if thread_success > 0:
                    # Add summary result to report
                    from publishers.base import PublishResult
                    report.results.append(PublishResult(
                        success=True,
                        platform="bluesky",
                        post_id=f"thread:{thread_total}posts",
                        url=None  # Thread doesn't have single URL
                    ))
                else:
                    from publishers.base import PublishResult
                    error_msg = thread_results[0].error if thread_results else "Unknown error"
                    report.results.append(PublishResult(
                        success=False,
                        platform="bluesky",
                        error=f"Thread failed: {error_msg}"
                    ))

            # Publish to YouTube (needs audio)
            if self.cb_youtube.value:
                print(">>> === YOUTUBE PUBLISH START ===", flush=True)
                print(f">>> Audio EN checked: {self.cb_audio_en.value}", flush=True)
                print(f">>> Audio path from report: {report.audio_en_path}", flush=True)

                # Generate YouTube script files
                subtitle_path = None
                try:
                    from media.youtube_script import YouTubeScriptGenerator
                    script_gen = YouTubeScriptGenerator(style='direct')
                    script_dir = Path("output/youtube_scripts")

                    # Get canonical URL from published results (prefer dev.to)
                    canonical_url = None
                    for r in report.results:
                        if r.success and r.url:
                            canonical_url = r.url
                            if r.platform == 'devto':
                                break  # Prefer dev.to URL

                    script_files = script_gen.save_all(
                        title=title,
                        content=content,
                        tags=tags,
                        output_dir=script_dir,
                        canonical_url=canonical_url
                    )
                    subtitle_path = script_files.get('subtitles')
                    print(f">>> YouTube: Generated {len(script_files)} script files", flush=True)
                    print(f">>> YouTube: Subtitle path: {subtitle_path}", flush=True)
                except Exception as e:
                    print(f">>> YouTube: Script generation error: {e}", flush=True)

                if report.audio_en_path or self.cb_audio_en.value:
                    try:
                        from publishers.youtube import YouTubePublisher
                        yt_config = manager.config.get('youtube', {})
                        print(f">>> YouTube config: {yt_config}", flush=True)
                        youtube = YouTubePublisher(yt_config)

                        print(f">>> YouTube configured: {youtube.is_configured()}", flush=True)
                        if youtube.is_configured():
                            # Generate audio if not already done
                            audio_path = report.audio_en_path
                            if not audio_path:
                                print(">>> Generating audio for YouTube...", flush=True)
                                from media.audio import AudioGenerator
                                audio_gen = AudioGenerator()
                                print(f">>> Audio generator available: {audio_gen.is_available()}", flush=True)
                                voice = self.voice_dropdown.value or 'male'
                                print(f">>> Voice selection: {voice}", flush=True)
                                audio_path = audio_gen.generate_for_article(
                                    title=title,
                                    content=content,
                                    lang='en',
                                    gender=voice
                                )
                                print(f">>> Audio generated: {audio_path}", flush=True)

                            if audio_path:
                                # Mix with background music if enabled
                                if self.cb_bg_music.value:
                                    try:
                                        from media.audio_mixer import AudioMixer
                                        mixer = AudioMixer(music_dir=Path("media/music"))
                                        available_music = mixer.get_available_music()
                                        print(f">>> Mixer: Found {len(available_music)} music files", flush=True)

                                        if available_music:
                                            mixed_path = mixer.mix_for_youtube(
                                                voice_path=audio_path,
                                                title=title,
                                                music_volume=0.12  # 12% volume for background
                                            )
                                            if mixed_path:
                                                audio_path = mixed_path
                                                print(f">>> Using mixed audio: {audio_path}", flush=True)
                                        else:
                                            print(f">>> Mixer: No music files in media/music/", flush=True)
                                    except Exception as e:
                                        print(f">>> Mixer error: {e}", flush=True)

                                print(f">>> Calling YouTube publish with audio: {audio_path}", flush=True)
                                print(f">>> Cover image: {report.cover_image_path}", flush=True)
                                print(f">>> Subtitles: {subtitle_path}", flush=True)
                                yt_result = youtube.publish(
                                    article=article,
                                    audio_path=audio_path,
                                    cover_image_path=report.cover_image_path,
                                    subtitle_path=subtitle_path
                                )
                                print(f">>> YouTube result: {yt_result}", flush=True)
                                report.results.append(yt_result)
                            else:
                                from publishers.base import PublishResult
                                report.results.append(PublishResult(
                                    success=False,
                                    platform="youtube",
                                    error="Could not generate audio"
                                ))
                        else:
                            from publishers.base import PublishResult
                            report.results.append(PublishResult(
                                success=False,
                                platform="youtube",
                                error="YouTube not configured (need OAuth setup)"
                            ))
                    except Exception as e:
                        from publishers.base import PublishResult
                        report.results.append(PublishResult(
                            success=False,
                            platform="youtube",
                            error=str(e)[:50]
                        ))
                else:
                    from publishers.base import PublishResult
                    report.results.append(PublishResult(
                        success=False,
                        platform="youtube",
                        error="Enable 'Audio (EN)' to upload to YouTube"
                    ))

            print(f">>> Publish complete. Results: {len(report.results)}", flush=True)

            # Show results
            success_count = report.success_count
            total = len(report.results)

            result_msgs = []
            for r in report.results:
                status = "OK" if r.success else f"FAIL: {r.error}"
                print(f">>>   {r.platform}: {status}", flush=True)
                result_msgs.append(f"{r.platform}: {status[:30]}")

            if report.all_success:
                self.publish_status.value = f"Published to {success_count}/{total} platforms!"
                self.publish_status.color = Colors.ACCENT
            else:
                failures = [f"{r.platform}: {r.error[:20]}" for r in report.results if not r.success]
                self.publish_status.value = f"{success_count}/{total} OK. Errors: {'; '.join(failures)}"
                self.publish_status.color = Colors.WARNING

            # Show URLs in snackbar
            urls = [r.url for r in report.results if r.success and r.url]
            if urls:
                self._snack = ft.SnackBar(
                    content=ft.Text(f"Published! {urls[0]}"),
                    duration=8000
                )
                self._page.show_dialog(self._snack)

        except Exception as ex:
            import traceback
            traceback.print_exc()  # Debug
            self.publish_status.value = f"Error: {str(ex)[:80]}"
            self.publish_status.color = Colors.WARNING

        finally:
            self.publish_btn.disabled = False
            self._page.update()
