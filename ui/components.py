"""
Anvil UI Components - Reusable UI pieces.
Compatible with Flet 0.80+
"""

import flet as ft
from pathlib import Path
from datetime import datetime
from .theme import Colors


class WarningPanel(ft.Column):
    """Panel showing violations/warnings with severity colors."""

    def __init__(self):
        super().__init__(spacing=5, scroll=ft.ScrollMode.AUTO)
        self.visible = False

    def update_violations(self, violations: list):
        """Update the violations display."""
        self.controls.clear()

        if not violations:
            self.visible = False
        else:
            self.visible = True
            self.controls.append(
                ft.Text("Warnings", size=14, weight=ft.FontWeight.BOLD, color=Colors.TEXT_SECONDARY)
            )
            for v in violations:
                severity = v.get('severity', 'low')
                color = {
                    'high': Colors.SEVERITY_HIGH,
                    'medium': Colors.SEVERITY_MEDIUM,
                    'low': Colors.SEVERITY_LOW,
                }.get(severity, Colors.SEVERITY_LOW)

                self.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Container(
                                    content=ft.Text(severity.upper(), size=10, color=Colors.BG_PRIMARY),
                                    bgcolor=color,
                                    padding=ft.padding.symmetric(horizontal=8, vertical=2),
                                    border_radius=4,
                                ),
                                ft.Text(v.get('type', ''), size=12, color=Colors.TEXT_PRIMARY),
                            ], spacing=10),
                            ft.Text(f"Found: {v.get('found', '')}", size=11, color=Colors.TEXT_SECONDARY),
                            ft.Text(f"Fix: {v.get('suggestion', '')}", size=11, color=Colors.TEXT_MUTED, italic=True),
                        ], spacing=3),
                        padding=10,
                        bgcolor=Colors.BG_SECONDARY,
                        border_radius=6,
                    )
                )


class PreviewBox(ft.TextField):
    """Scrollable text preview area."""

    def __init__(self, placeholder: str = "Generated content will appear here..."):
        super().__init__(
            value="",
            multiline=True,
            read_only=True,
            min_lines=20,
            max_lines=30,
            border_color=Colors.BG_TERTIARY,
            bgcolor=Colors.BG_SECONDARY,
            color=Colors.TEXT_PRIMARY,
            text_size=13,
            hint_text=placeholder,
            expand=True,
        )

    def set_content(self, text: str):
        """Set the preview content."""
        self.value = text
        try:
            self.update()
        except Exception:
            pass

    def get_content(self) -> str:
        """Get the current content."""
        return self.value or ""


class MatchScoreDisplay(ft.Column):
    """Display match score with visual indicator."""

    def __init__(self):
        self.score_text = ft.Text("--", size=32, weight=ft.FontWeight.BOLD)
        self.score_label = ft.Text("Match Score", size=12, color=Colors.TEXT_SECONDARY)
        self.matches_column = ft.Column(spacing=3)
        self.gaps_column = ft.Column(spacing=3)

        super().__init__(
            controls=[
                ft.Container(
                    content=ft.Column([
                        self.score_text,
                        self.score_label,
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
                    padding=20,
                    bgcolor=Colors.BG_TERTIARY,
                    border_radius=8,
                ),
                ft.Row([
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Matches", size=12, weight=ft.FontWeight.BOLD, color=Colors.SUCCESS),
                            self.matches_column,
                        ], spacing=5),
                        expand=True,
                        padding=10,
                        bgcolor=Colors.BG_SECONDARY,
                        border_radius=6,
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Gaps", size=12, weight=ft.FontWeight.BOLD, color=Colors.WARNING),
                            self.gaps_column,
                        ], spacing=5),
                        expand=True,
                        padding=10,
                        bgcolor=Colors.BG_SECONDARY,
                        border_radius=6,
                    ),
                ], spacing=10),
            ],
            spacing=10,
            visible=False,
        )

    def update_analysis(self, analysis: dict):
        """Update with analysis results."""
        self.visible = True

        score = analysis.get('match_score', 0)
        self.score_text.value = f"{score:.0f}%"
        self.score_text.color = Colors.SUCCESS if score >= 70 else Colors.WARNING if score >= 50 else Colors.ERROR

        self.matches_column.controls.clear()
        for m in analysis.get('matches', [])[:5]:
            self.matches_column.controls.append(
                ft.Text(f"- {m.get('skill', '')}", size=11, color=Colors.TEXT_SECONDARY)
            )

        self.gaps_column.controls.clear()
        for g in analysis.get('gaps', [])[:5]:
            self.gaps_column.controls.append(
                ft.Text(f"- {g}", size=11, color=Colors.TEXT_SECONDARY)
            )


def create_dropdown(label: str, value: str, options: list, on_change_fn=None, width: int = 250) -> ft.Dropdown:
    """Create a styled dropdown."""
    dropdown = ft.Dropdown(
        label=label,
        value=value,
        options=[ft.dropdown.Option(key=k, text=v) for k, v in options],
        width=width,
        border_color=Colors.BG_TERTIARY,
        bgcolor=Colors.BG_SECONDARY,
    )
    if on_change_fn:
        dropdown.on_change = on_change_fn
    return dropdown


def create_button(text: str, on_click_fn, icon=None, bgcolor=None, disabled=False) -> ft.ElevatedButton:
    """Create a styled button."""
    btn = ft.ElevatedButton(
        content=ft.Text(text),
        on_click=on_click_fn,
        disabled=disabled,
    )
    if icon:
        btn.icon = icon
    if bgcolor:
        btn.style = ft.ButtonStyle(bgcolor=bgcolor, color=Colors.TEXT_PRIMARY)
    return btn


def save_content(content: str, filename_prefix: str, subdir: str = "") -> Path:
    """Save content to file and return path."""
    output_dir = Path(__file__).parent.parent / "output"
    if subdir:
        output_dir = output_dir / subdir
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.md"
    filepath = output_dir / filename

    filepath.write_text(content, encoding='utf-8')
    return filepath


def copy_text(text: str):
    """Put text on the Windows clipboard (Unicode safe)."""
    import subprocess
    subprocess.run(["clip"], input=text.encode("utf-16"), check=False)


def open_path(target, page=None):
    """Open a file, folder or mailto link; a missing file is reported, not raised."""
    import os
    try:
        os.startfile(str(target))
    except OSError as ex:
        if page:
            page.show_dialog(ft.SnackBar(content=ft.Text(f"Could not open {target}: {ex}")))


def mail_dialog(page, mail: dict, title: str, on_sent=None):
    """Show a drafted email: edit it, open it in the mail program, or copy it. Anvil never sends."""
    import os
    from core.outreach import mailto
    to = ft.TextField(label="To", value=mail.get("to", ""), text_size=13)
    subject = ft.TextField(label="Subject", value=mail["subject"], text_size=13)
    body = ft.TextField(label="Body", value=mail["body"], multiline=True, min_lines=10, max_lines=18, text_size=13)

    warn = [ft.Text("Check before sending: " + "; ".join(mail["violations"]), size=12, color=Colors.ERROR)] \
        if mail.get("violations") else []
    gloss = ([ft.Text("English meaning:", size=12, color=Colors.TEXT_SECONDARY),
              ft.Text(mail["english"], size=12, color=Colors.TEXT_SECONDARY, selectable=True)]
             if mail.get("english") else [])

    def current():
        return {"to": to.value or "", "subject": subject.value or "", "body": body.value or ""}

    def sent(e):
        page.pop_dialog()
        if on_sent:
            on_sent(current())

    def open_mail(e):
        from core.outreach import MAILTO_MAX
        m = current()
        url = mailto(m)
        if len(url) > MAILTO_MAX:          # too long for Windows: body goes to the clipboard
            copy_text(m["body"])
            url = mailto(m, with_body=False)
            page.show_dialog(ft.SnackBar(content=ft.Text("Body copied: paste it into the email (Ctrl+V).")))
        open_path(url)

    actions = [
        ft.TextButton("Copy", icon=ft.Icons.CONTENT_COPY,
                      on_click=lambda e: copy_text(f"{subject.value}\n\n{body.value}")),
        ft.TextButton("Open in mail", icon=ft.Icons.EMAIL, on_click=open_mail),
    ]
    if on_sent:
        actions.append(ft.Button("I sent it", icon=ft.Icons.SEND, on_click=sent))
    actions.append(ft.TextButton("Close", on_click=lambda e: page.pop_dialog()))
    page.show_dialog(ft.AlertDialog(
        title=ft.Text(title),
        content=ft.Container(ft.Column([*warn, to, subject, body, *gloss], tight=True, spacing=8, scroll=ft.ScrollMode.AUTO),
                             width=640),
        actions=actions,
    ))
