"""
Triage View - paste a posting, get realistic / stretch / skip and the document to send.
"""

import os
import asyncio
from pathlib import Path

import flet as ft
from ..theme import Colors
from analyzers.triage import triage, ROOT
from core.pipeline import Pipeline, load_channels, today

VERDICT_COLORS = {"realistic": Colors.SUCCESS, "stretch": Colors.WARNING, "skip": Colors.ERROR}
FLAG_ICONS = {
    "blocker": (ft.Icons.BLOCK, Colors.ERROR), "stretch": (ft.Icons.WARNING_AMBER, Colors.WARNING),
    "plus": (ft.Icons.CHECK_CIRCLE_OUTLINE, Colors.SUCCESS), "note": (ft.Icons.INFO_OUTLINE, Colors.TEXT_SECONDARY),
}
COUNTRIES = [("JP", "Japan"), ("FR", "France"), ("ANY", "Remote / other")]


def _field(label, **kw):
    return ft.TextField(label=label, text_size=13, border_color=Colors.BG_TERTIARY,
                        bgcolor=Colors.BG_SECONDARY, **kw)


class TriageView(ft.Column):
    """Decide before writing anything."""

    def __init__(self, page: ft.Page):
        self._page = page
        self.channels = load_channels()
        self.result = None

        self.posting = _field("Paste the job posting", multiline=True, min_lines=10, max_lines=18, expand=True)
        self.company = _field("Company", expand=True)
        self.role = _field("Role", expand=True)
        self.url = _field("Link", expand=True)
        self.country = ft.Dropdown(label="Country", value="JP", width=150, text_size=13,
                                   options=[ft.dropdown.Option(k, v) for k, v in COUNTRIES],
                                   border_color=Colors.BG_TERTIARY, bgcolor=Colors.BG_SECONDARY)
        self.country.on_select = lambda e: self._fill_channels()
        self.channel = ft.Dropdown(label="Channel", width=260, text_size=13,
                                   border_color=Colors.BG_TERTIARY, bgcolor=Colors.BG_SECONDARY)
        self._fill_channels(update=False)
        self.use_claude = ft.Checkbox(label="Ask Claude too (uses API credit)", value=True)

        self.run_btn = ft.Button("Triage", icon=ft.Icons.RULE, on_click=self._on_run)
        self.result_box = ft.Column(spacing=8)
        self.save_row = ft.Row([
            ft.Button("Save as found", icon=ft.Icons.BOOKMARK_ADD, on_click=lambda e: self._save("found")),
            ft.Button("Log as applied", icon=ft.Icons.SEND, on_click=lambda e: self._save("applied")),
        ], visible=False)

        super().__init__(
            controls=[
                ft.Text("Triage", size=24, weight=ft.FontWeight.BOLD, color=Colors.TEXT_PRIMARY),
                ft.Text("Paste a posting. Get realistic / stretch / skip, the reasons, and which of your CVs to send.",
                        size=14, color=Colors.TEXT_SECONDARY),
                ft.Row([self.company, self.role], spacing=10),
                ft.Row([self.country, self.channel, self.url], spacing=10),
                self.posting,
                ft.Row([self.run_btn, self.use_claude], spacing=20),
                self.result_box,
                self.save_row,
            ],
            spacing=12, expand=True, scroll=ft.ScrollMode.AUTO,
        )

    def _fill_channels(self, update=True):
        opts = [c for c in self.channels if c["country"] in (self.country.value, "ANY")]
        self.channel.options = [ft.dropdown.Option(c["id"], c["name"]) for c in opts]
        self.channel.value = opts[0]["id"] if opts else None
        if update:
            self._page.update()

    async def _on_run(self, e):
        """Runs on Flet's event loop; triage itself runs in a worker thread."""
        text = (self.posting.value or "").strip()
        if not text:
            return
        self.run_btn.disabled = True
        self.result_box.controls = [ft.ProgressRing(width=28, height=28)]
        self.save_row.visible = False
        self._page.update()
        try:
            self.result = await asyncio.to_thread(triage, text, self.use_claude.value)
            self._show(self.result)
        except Exception as ex:
            self.result_box.controls = [ft.Text(f"Error: {ex}", color=Colors.ERROR)]
        self.run_btn.disabled = False
        self._page.update()

    def _show(self, r):
        color = VERDICT_COLORS.get(r.verdict, Colors.TEXT_PRIMARY)
        rows = [
            ft.Row([
                ft.Text(r.verdict.upper(), size=22, weight=ft.FontWeight.BOLD, color=color),
                ft.Text(f"Track: {r.track_label}", size=14, color=Colors.TEXT_SECONDARY),
                ft.Text(f"({r.by})", size=12, color=Colors.TEXT_MUTED),
            ], spacing=15),
        ]
        for f in r.flags:
            icon, c = FLAG_ICONS.get(f.level, FLAG_ICONS["note"])
            rows.append(ft.Row([ft.Icon(icon, color=c, size=18),
                                ft.Text(f.text, size=13, color=Colors.TEXT_PRIMARY, expand=True)]))
        for reason in r.reasons:
            rows.append(ft.Text(f"• {reason}", size=13, color=Colors.TEXT_PRIMARY))
        if r.motivation_angle:
            rows.append(ft.Text(f"Angle: {r.motivation_angle}", size=13, italic=True, color=Colors.ACCENT))
        if r.documents:
            rows.append(ft.Text("Send:", size=13, weight=ft.FontWeight.BOLD, color=Colors.TEXT_PRIMARY))
            for d in r.documents:
                rows.append(ft.Row([
                    ft.TextButton(Path(d["file"]).name, icon=ft.Icons.DESCRIPTION,
                                  on_click=lambda e, p=d["file"]: os.startfile(ROOT / p)),
                    ft.Text(d.get("note", ""), size=12, color=Colors.TEXT_SECONDARY),
                ]))
        if r.note:
            rows.append(ft.Text(r.note, size=12, color=Colors.TEXT_MUTED))
        self.result_box.controls = [ft.Container(content=ft.Column(rows, spacing=6), padding=15,
                                                 bgcolor=Colors.BG_SECONDARY, border_radius=8)]
        self.save_row.visible = True

    def _save(self, stage):
        r = self.result
        if not r:
            return
        app = Pipeline().add(
            company=(self.company.value or "Unknown").strip(), role=(self.role.value or "Unknown").strip(),
            channel=self.channel.value or "other", country=self.country.value, stage=stage, on=today(),
            url=(self.url.value or "").strip(), description=self.posting.value or "",
            documents=[d["file"] for d in r.documents], fit=r.to_fit(),
            language={"cs_jp": "ja", "hotel": "ja", "factory": "ja", "teaching_fr": "ja",
                      "support_fr": "fr"}.get(r.track or "", "en"),
        )
        self.save_row.visible = False
        self._page.show_dialog(ft.SnackBar(content=ft.Text(f"Saved to pipeline as #{app['id']} ({stage}).")))
        self._page.update()
