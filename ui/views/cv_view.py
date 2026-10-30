"""
CV View - Generate CVs with role and emphasis options.

Features:
- ATS keyword optimization (97.8% of Fortune 500 use ATS)
- F-pattern layout for 6-second recruiter scan
- Role-based tailoring
- Quantified achievements (2.5x more interviews)
"""

import flet as ft
from ..theme import Colors
from ..components import WarningPanel, PreviewBox, create_dropdown, create_button, save_content
from ..storage import DraftManager


class CVView(ft.Column):
    """CV generation view with ATS optimization."""

    def __init__(self, page: ft.Page):
        self._page = page
        self.draft_manager = DraftManager()

        # Role dropdown
        self.role_dropdown = create_dropdown(
            "Target Role", "general",
            [("general", "General"), ("technical_pm", "Technical PM"),
             ("qa_lead", "QA Lead"), ("process_improvement", "Process Improvement"),
             ("ai_dev", "AI/ML Project Lead")]
        )

        # Emphasis dropdown
        self.emphasis_dropdown = create_dropdown(
            "Emphasis", "balanced",
            [("balanced", "Balanced"), ("problem_solving", "Problem Solving"),
             ("project_management", "Project Management"), ("technical", "Technical")]
        )

        # Job title input for ATS matching
        self.job_title_input = ft.TextField(
            label="Exact Job Title (optional)",
            hint_text="e.g., 'Senior QA Lead' - matches ATS exactly",
            width=300,
            border_color=Colors.BG_TERTIARY,
            focused_border_color=Colors.ACCENT,
            text_style=ft.TextStyle(color=Colors.TEXT_PRIMARY),
            label_style=ft.TextStyle(color=Colors.TEXT_SECONDARY),
        )

        self.generate_btn = create_button("Generate CV", self._on_generate, ft.Icons.AUTO_AWESOME, Colors.ACCENT)

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

        self.save_btn = create_button("Export CV", self._on_save, ft.Icons.DOWNLOAD)
        self.save_btn.visible = False

        # ATS Score display
        self.ats_score = ft.Container(
            content=ft.Column([
                ft.Text("ATS SCORE", size=12, color=Colors.TEXT_SECONDARY),
                ft.Text("--", size=32, weight=ft.FontWeight.BOLD, color=Colors.ACCENT),
                ft.Text("Generate CV to see score", size=10, color=Colors.TEXT_SECONDARY),
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            width=120,
            height=100,
            bgcolor=Colors.BG_SECONDARY,
            border_radius=10,
            padding=10,
        )

        self.preview = PreviewBox("Click 'Generate CV' to create your CV...\n\nFeatures:\n• ATS keyword optimization\n• F-pattern layout for 6-second scan\n• Role-based tailoring\n• Quantified achievements")
        self.warnings = WarningPanel()

        super().__init__(
            controls=[
                ft.Text("CV Generator", size=24, weight=ft.FontWeight.BOLD, color=Colors.TEXT_PRIMARY),
                ft.Text("ATS-optimized, evidence-based CVs that get interviews", size=14, color=Colors.TEXT_SECONDARY),
                ft.Divider(height=20, color=Colors.BG_TERTIARY),

                # Row 1: Role + Emphasis
                ft.Row([self.role_dropdown, self.emphasis_dropdown], spacing=20),

                # Row 2: Job title + Generate + ATS Score
                ft.Row([
                    self.job_title_input,
                    self.generate_btn,
                    self.ats_score,
                ], spacing=20, alignment=ft.MainAxisAlignment.START),

                ft.Divider(height=20, color=Colors.BG_TERTIARY),
                ft.Row([
                    ft.Container(content=self.preview, expand=3),
                    ft.Container(content=self.warnings, expand=1, padding=10),
                ], spacing=20, expand=True),
                ft.Row([
                    self.format_dropdown,
                    self.save_btn,
                ], alignment=ft.MainAxisAlignment.END, spacing=10),
            ],
            spacing=15,
            expand=True,
        )

    async def _on_generate(self, e):
        """Generate CV with ATS optimization."""
        self.generate_btn.disabled = True
        self.generate_btn.content.value = "Generating..."
        self._page.update()

        try:
            from generators.cv import CVGenerator
            from core.config import load_api_key

            api_key = load_api_key()
            generator = CVGenerator(api_key=api_key)

            # Get job title if provided
            job_title = self.job_title_input.value.strip() if self.job_title_input.value else None

            import asyncio
            result = await asyncio.to_thread(
                generator.generate, target_role=self.role_dropdown.value,
                emphasis=self.emphasis_dropdown.value, job_title=job_title)

            self.preview.set_content(result['content'])
            self.warnings.update_violations(result.get('violations', []))
            self.save_btn.visible = True

            # Update ATS score display
            ats = result.get('ats_score', {})
            score = ats.get('score', 0)
            self._update_ats_display(score, ats.get('missing', []))

            # Auto-save draft
            self.draft_manager.save_draft(
                result['content'],
                'cv',
                {
                    'role': self.role_dropdown.value,
                    'emphasis': self.emphasis_dropdown.value,
                    'job_title': job_title,
                    'ats_score': score
                }
            )

        except Exception as ex:
            self.preview.set_content(f"Error: {ex}")
            import traceback
            traceback.print_exc()

        finally:
            self.generate_btn.disabled = False
            self.generate_btn.content.value = "Generate CV"
            self._page.update()

    def _update_ats_display(self, score: float, missing: list):
        """Update ATS score display with color coding."""
        # Color based on score
        if score >= 75:
            color = Colors.SUCCESS  # Green
            status = "Excellent"
        elif score >= 65:
            color = Colors.ACCENT  # Blue
            status = "Good"
        else:
            color = Colors.WARNING  # Orange
            status = "Needs work"

        # Update the ATS score container
        score_text = f"{score:.0f}%"
        missing_text = f"Missing: {len(missing)}" if missing else "All keywords matched"

        self.ats_score.content = ft.Column([
            ft.Text("ATS SCORE", size=12, color=Colors.TEXT_SECONDARY),
            ft.Text(score_text, size=32, weight=ft.FontWeight.BOLD, color=color),
            ft.Text(status, size=10, color=color),
            ft.Text(missing_text, size=9, color=Colors.TEXT_SECONDARY),
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2)

    def _on_save(self, e):
        """Export CV to selected format."""
        content = self.preview.get_content()
        if not content:
            return

        format = self.format_dropdown.value
        self.save_btn.disabled = True
        self._page.update()

        try:
            from exporters.cv_exporter import CVExporter

            exporter = CVExporter()

            # Check if format is available
            formats = exporter.get_available_formats()
            format_info = next((f for f in formats if f['format'] == format), None)

            if format_info and not format_info['available']:
                # Show install instructions
                self._snack = ft.SnackBar(
                    content=ft.Text(f"Format not available. Run: {format_info['install']}"),
                    bgcolor=Colors.ERROR
                )
                self._page.show_dialog(self._snack)
                self._page.update()
                return

            # Export
            metadata = {'name': 'Florent_Herisson', 'role': self.role_dropdown.value}
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
