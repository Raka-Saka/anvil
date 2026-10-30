"""
Cover Letter View - Generate cover letters with job analysis.
"""

import flet as ft
from ..theme import Colors
from ..components import WarningPanel, PreviewBox, MatchScoreDisplay, create_button
from ..storage import DraftManager, JobTracker


class CoverLetterView(ft.Column):
    """Cover letter generation view."""

    def __init__(self, page: ft.Page):
        self._page = page
        self.draft_manager = DraftManager()
        self.job_tracker = JobTracker()
        self.current_analysis = None

        # Controls
        self.job_description = ft.TextField(
            label="Job Description",
            hint_text="Paste the job posting here...",
            multiline=True,
            min_lines=6,
            max_lines=10,
            border_color=Colors.BG_TERTIARY,
            bgcolor=Colors.BG_SECONDARY,
            expand=True,
        )

        self.company_field = ft.TextField(
            label="Company Name (optional)",
            width=250,
            border_color=Colors.BG_TERTIARY,
            bgcolor=Colors.BG_SECONDARY,
        )

        self.role_field = ft.TextField(
            label="Role Name (optional)",
            width=250,
            border_color=Colors.BG_TERTIARY,
            bgcolor=Colors.BG_SECONDARY,
        )

        self.generate_btn = create_button("Generate Letter", self._on_generate, ft.Icons.AUTO_AWESOME, Colors.ACCENT)
        self.track_btn = create_button("Track Application", self._on_track, ft.Icons.BOOKMARK_ADD, Colors.SUCCESS)
        self.track_btn.visible = False

        # Export format dropdown
        self.format_dropdown = ft.Dropdown(
            label="Export Format",
            value="pdf",
            width=150,
            options=[
                ft.dropdown.Option("pdf", "PDF"),
                ft.dropdown.Option("docx", "Word (DOCX)"),
                ft.dropdown.Option("html", "HTML"),
                ft.dropdown.Option("txt", "Plain Text"),
                ft.dropdown.Option("md", "Markdown"),
            ],
            border_color=Colors.BG_TERTIARY,
            focused_border_color=Colors.ACCENT,
            text_style=ft.TextStyle(color=Colors.TEXT_PRIMARY),
            label_style=ft.TextStyle(color=Colors.TEXT_SECONDARY),
        )
        self.format_dropdown.visible = False

        self.save_btn = create_button("Export Letter", self._on_save, ft.Icons.DOWNLOAD)
        self.save_btn.visible = False

        self.match_display = MatchScoreDisplay()
        self.preview = PreviewBox("Enter a job description and click 'Generate Letter'...")
        self.warnings = WarningPanel()

        super().__init__(
            controls=[
                ft.Text("Cover Letter Generator", size=24, weight=ft.FontWeight.BOLD, color=Colors.TEXT_PRIMARY),
                ft.Text("Match your experience to job requirements honestly", size=14, color=Colors.TEXT_SECONDARY),
                ft.Divider(height=20, color=Colors.BG_TERTIARY),
                self.job_description,
                ft.Row([self.company_field, self.role_field, self.generate_btn], spacing=20),
                ft.Divider(height=20, color=Colors.BG_TERTIARY),
                self.match_display,
                ft.Row([
                    ft.Container(content=self.preview, expand=3),
                    ft.Container(content=self.warnings, expand=1, padding=10),
                ], spacing=20, expand=True),
                ft.Row([self.track_btn, self.format_dropdown, self.save_btn], alignment=ft.MainAxisAlignment.END, spacing=10),
            ],
            spacing=15,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

    async def _on_generate(self, e):
        """Generate cover letter."""
        if not self.job_description.value:
            self._snack = ft.SnackBar(content=ft.Text("Please enter a job description"))
            self._page.show_dialog(self._snack)
            self._page.update()
            return

        self.generate_btn.disabled = True
        self.generate_btn.content.value = "Analyzing..."
        self._page.update()

        try:
            from generators.cover_letter import CoverLetterGenerator
            from core.config import load_api_key

            api_key = load_api_key()
            generator = CoverLetterGenerator(api_key=api_key)
            import asyncio
            result = await asyncio.to_thread(
                generator.generate, job_description=self.job_description.value,
                company_name=self.company_field.value or None, role_name=self.role_field.value or None)

            self.current_analysis = result.get('analysis', {})
            self.match_display.update_analysis(self.current_analysis)
            self.preview.set_content(result['content'])
            self.warnings.update_violations(result.get('violations', []))
            self.format_dropdown.visible = True
            self.save_btn.visible = True
            self.track_btn.visible = True

            self.draft_manager.save_draft(result['content'], 'cover_letter',
                {'company': self.company_field.value or 'unknown', 'role': self.role_field.value or 'unknown'})

        except Exception as ex:
            self.preview.set_content(f"Error: {ex}")

        finally:
            self.generate_btn.disabled = False
            self.generate_btn.content.value = "Generate Letter"
            self._page.update()

    def _on_track(self, e):
        """Track this job application."""
        self.job_tracker.add_job(
            company=self.company_field.value or "Unknown",
            role=self.role_field.value or "Unknown",
            job_description=self.job_description.value[:500],
        )
        self._snack = ft.SnackBar(content=ft.Text("Added to job tracker"))
        self._page.show_dialog(self._snack)
        self.track_btn.visible = False
        self._page.update()

    def _on_save(self, e):
        """Export cover letter to selected format."""
        content = self.preview.get_content()
        if not content:
            return

        format = self.format_dropdown.value
        self.save_btn.disabled = True
        self._page.update()

        try:
            from exporters.cover_letter_exporter import CoverLetterExporter
            from core.profile_manager import ProfileManager

            exporter = CoverLetterExporter()

            # Check if format is available
            formats = exporter.get_available_formats()
            format_info = next((f for f in formats if f['format'] == format), None)

            if format_info and not format_info['available']:
                self._snack = ft.SnackBar(
                    content=ft.Text(f"Format not available. Run: {format_info['install']}"),
                    bgcolor=Colors.ERROR
                )
                self._page.show_dialog(self._snack)
                self._page.update()
                return

            # Get applicant name from profile
            pm = ProfileManager()
            applicant_name = pm.get_name()

            # Export with metadata
            metadata = {
                'company': self.company_field.value or 'Company',
                'role': self.role_field.value or 'Position',
                'applicant_name': applicant_name
            }
            filepath = exporter.export(content, format, metadata=metadata)

            if filepath:
                self._snack = ft.SnackBar(
                    content=ft.Text(f"Exported to {filepath.name}"),
                    bgcolor=Colors.SUCCESS
                )
            else:
                self._snack = ft.SnackBar(
                    content=ft.Text("Export failed"),
                    bgcolor=Colors.ERROR
                )

            self._page.show_dialog(self._snack)

        except Exception as ex:
            self._snack = ft.SnackBar(
                content=ft.Text(f"Error: {ex}"),
                bgcolor=Colors.ERROR
            )
            self._page.show_dialog(self._snack)
            import traceback
            traceback.print_exc()

        finally:
            self.save_btn.disabled = False
            self._page.update()
