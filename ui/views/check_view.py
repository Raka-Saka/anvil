"""
Check View - Profile validation display.
"""

import flet as ft
from ..theme import Colors
from ..components import create_button


class CheckView(ft.Column):
    """Profile check/validation view."""

    def __init__(self, page: ft.Page):
        self._page = page

        # Status
        self.status_icon = ft.Icon(ft.Icons.CHECK_CIRCLE, size=48, color=Colors.SUCCESS)
        self.status_text = ft.Text("Checking...", size=18, weight=ft.FontWeight.BOLD)

        # Issues list
        self.issues_column = ft.Column(spacing=8)

        # Summary
        self.name_text = ft.Text("", size=14)
        self.email_text = ft.Text("", size=14)
        self.skills_text = ft.Text("", size=14)
        self.projects_text = ft.Text("", size=14)
        self.experience_text = ft.Text("", size=14)

        self.refresh_btn = create_button("Refresh", self._on_refresh, ft.Icons.REFRESH)

        super().__init__(
            controls=[
                ft.Text("Profile Check", size=24, weight=ft.FontWeight.BOLD, color=Colors.TEXT_PRIMARY),
                ft.Text("Validate your profile for completeness", size=14, color=Colors.TEXT_SECONDARY),
                ft.Divider(height=20, color=Colors.BG_TERTIARY),
                ft.Row([self.status_icon, self.status_text, self.refresh_btn], spacing=20),
                ft.Divider(height=20, color=Colors.BG_TERTIARY),
                ft.Container(
                    content=ft.Column([
                        ft.Text("Issues", size=16, weight=ft.FontWeight.BOLD, color=Colors.TEXT_PRIMARY),
                        self.issues_column,
                    ], spacing=10),
                    padding=15,
                    bgcolor=Colors.BG_SECONDARY,
                    border_radius=8,
                ),
                ft.Divider(height=20, color=Colors.BG_TERTIARY),
                ft.Container(
                    content=ft.Column([
                        ft.Text("Profile Summary", size=16, weight=ft.FontWeight.BOLD, color=Colors.TEXT_PRIMARY),
                        self.name_text,
                        self.email_text,
                        self.skills_text,
                        self.projects_text,
                        self.experience_text,
                    ], spacing=8),
                    padding=15,
                    bgcolor=Colors.BG_SECONDARY,
                    border_radius=8,
                ),
            ],
            spacing=15,
            expand=True,
        )

        self._run_check()

    def _run_check(self):
        """Run profile validation."""
        try:
            from core.profile_manager import ProfileManager
            pm = ProfileManager()
            issues = pm.validate()

            if issues:
                self.status_icon.name = ft.Icons.WARNING
                self.status_icon.color = Colors.WARNING
                self.status_text.value = f"{len(issues)} issue(s) found"
                self.status_text.color = Colors.WARNING

                self.issues_column.controls.clear()
                for issue in issues:
                    self.issues_column.controls.append(
                        ft.Row([
                            ft.Icon(ft.Icons.ERROR_OUTLINE, size=16, color=Colors.WARNING),
                            ft.Text(issue, size=13, color=Colors.TEXT_SECONDARY),
                        ], spacing=10)
                    )
            else:
                self.status_icon.name = ft.Icons.CHECK_CIRCLE
                self.status_icon.color = Colors.SUCCESS
                self.status_text.value = "Profile looks good"
                self.status_text.color = Colors.SUCCESS
                self.issues_column.controls.clear()
                self.issues_column.controls.append(ft.Text("No issues found", size=13, color=Colors.TEXT_MUTED, italic=True))

            self.name_text.value = f"Name: {pm.get_name()}"
            self.email_text.value = f"Email: {pm.get_email()}"
            self.skills_text.value = f"Skills: {len(pm.get_skills_direct())} direct, {len(pm.get_skills_ai_assisted())} AI-assisted"
            self.projects_text.value = f"Projects: {len(pm.get_projects())}"
            self.experience_text.value = f"Experience: {len(pm.get_experience())} entries"

        except Exception as ex:
            self.status_icon.name = ft.Icons.ERROR
            self.status_icon.color = Colors.ERROR
            self.status_text.value = f"Error: {ex}"

    def _on_refresh(self, e):
        """Refresh profile check."""
        self._run_check()
        self._page.update()
