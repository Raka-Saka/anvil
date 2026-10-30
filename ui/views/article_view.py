"""
Article View - Generate articles from engineering logs.
"""

import flet as ft
from pathlib import Path
from ..theme import Colors
from ..components import WarningPanel, PreviewBox, create_button, save_content
from ..storage import DraftManager


class ArticleView(ft.Column):
    """Article generation view."""

    def __init__(self, page: ft.Page):
        self._page = page
        self.draft_manager = DraftManager()
        self.sections = []

        # Controls - use text field for path instead of file picker
        self.log_path_field = ft.TextField(
            label="Log File Path",
            hint_text="Enter path to engineering log (e.g., data/projects/chronos/logs/LOG.md)",
            width=500,
            border_color=Colors.BG_TERTIARY,
            bgcolor=Colors.BG_SECONDARY,
        )

        self.project_field = ft.TextField(
            label="Project Name",
            value="ChronOS",
            width=250,
            border_color=Colors.BG_TERTIARY,
            bgcolor=Colors.BG_SECONDARY,
        )

        self.scan_btn = create_button("Scan for Sections", self._on_scan, ft.Icons.SEARCH)

        self.section_dropdown = ft.Dropdown(
            label="Select Section",
            options=[],
            width=400,
            border_color=Colors.BG_TERTIARY,
            bgcolor=Colors.BG_SECONDARY,
            visible=False,
        )

        self.generate_btn = create_button("Generate Article", self._on_generate, ft.Icons.AUTO_AWESOME, Colors.ACCENT)
        self.generate_btn.visible = False

        self.title_display = ft.Text("", size=18, weight=ft.FontWeight.BOLD, color=Colors.TEXT_PRIMARY)
        self.word_count = ft.Text("", size=12, color=Colors.TEXT_SECONDARY)

        self.preview = PreviewBox("Enter a log file path, scan for sections, and generate an article...")
        self.warnings = WarningPanel()
        self.save_btn = create_button("Save as .md", self._on_save, ft.Icons.SAVE)
        self.save_btn.visible = False

        super().__init__(
            controls=[
                ft.Text("Article Generator", size=24, weight=ft.FontWeight.BOLD, color=Colors.TEXT_PRIMARY),
                ft.Text("Transform engineering logs into quiet, technical articles", size=14, color=Colors.TEXT_SECONDARY),
                ft.Divider(height=20, color=Colors.BG_TERTIARY),
                ft.Row([self.log_path_field], spacing=15),
                ft.Row([self.project_field, self.scan_btn], spacing=20),
                ft.Divider(height=20, color=Colors.BG_TERTIARY),
                ft.Row([self.section_dropdown, self.generate_btn], spacing=20),
                ft.Row([self.title_display, self.word_count], spacing=20),
                ft.Row([
                    ft.Container(content=self.preview, expand=3),
                    ft.Container(content=self.warnings, expand=1, padding=10),
                ], spacing=20, expand=True),
                ft.Row([self.save_btn], alignment=ft.MainAxisAlignment.END),
            ],
            spacing=15,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

    def _on_scan(self, e):
        """Scan log for publishable sections."""
        log_path = self.log_path_field.value
        if not log_path:
            self._snack = ft.SnackBar(content=ft.Text("Please enter a log file path"))
            self._page.show_dialog(self._snack)
            self._page.update()
            return

        # Try to resolve path
        path = Path(log_path)
        if not path.is_absolute():
            path = Path(__file__).parent.parent.parent / log_path

        if not path.exists():
            self._snack = ft.SnackBar(content=ft.Text(f"File not found: {path}"))
            self._page.show_dialog(self._snack)
            self._page.update()
            return

        self.scan_btn.disabled = True
        self.scan_btn.content.value = "Scanning..."
        self._page.update()

        try:
            from generators.article import ArticleGenerator
            from core.config import load_api_key
            api_key = load_api_key()
            generator = ArticleGenerator(api_key=api_key)
            self.sections = generator.scan_log(path)

            if self.sections:
                self.section_dropdown.options = [
                    ft.dropdown.Option(key=str(i), text=f"{s['title'][:50]} ({s['word_count']} words)")
                    for i, s in enumerate(self.sections)
                ]
                self.section_dropdown.visible = True
                self.generate_btn.visible = True
                self._snack = ft.SnackBar(content=ft.Text(f"Found {len(self.sections)} sections"))
            else:
                self._snack = ft.SnackBar(content=ft.Text("No publishable sections found"))
            self._page.show_dialog(self._snack)

        except Exception as ex:
            self._snack = ft.SnackBar(content=ft.Text(f"Error: {ex}"))
            self._page.show_dialog(self._snack)

        finally:
            self.scan_btn.disabled = False
            self.scan_btn.content.value = "Scan for Sections"
            self._page.update()

    def _on_generate(self, e):
        """Generate article from selected section."""
        if not self.section_dropdown.value:
            return

        section = self.sections[int(self.section_dropdown.value)]

        self.generate_btn.disabled = True
        self.generate_btn.content.value = "Generating..."
        self._page.update()

        try:
            from generators.article import ArticleGenerator
            from core.config import load_api_key
            api_key = load_api_key()
            generator = ArticleGenerator(api_key=api_key)
            result = generator.generate(source=section['content'], project_name=self.project_field.value or "Project")

            self.title_display.value = result.get('title', '')
            self.word_count.value = f"{result.get('word_count', 0)} words"
            self.preview.set_content(result['content'])
            self.warnings.update_violations(result.get('violations', []))
            self.save_btn.visible = True

            self.draft_manager.save_draft(result['content'], 'article', {'project': self.project_field.value, 'title': result.get('title', '')})

        except Exception as ex:
            self.preview.set_content(f"Error: {ex}")

        finally:
            self.generate_btn.disabled = False
            self.generate_btn.content.value = "Generate Article"
            self._page.update()

    def _on_save(self, e):
        """Save article to file."""
        content = self.preview.get_content()
        if content:
            filepath = save_content(content, "article", "articles")
            self._snack = ft.SnackBar(content=ft.Text(f"Saved to {filepath.name}"))
            self._page.show_dialog(self._snack)
            self._page.update()
