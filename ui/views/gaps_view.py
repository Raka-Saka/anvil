"""
Gaps View - what the jobs ask for that your record does not show, and the fix that opens most of them.
"""

import asyncio
import time
import webbrowser

import flet as ft
from ..theme import Colors

WORTH_COLORS = {"high": Colors.SUCCESS, "medium": Colors.ACCENT, "low": Colors.TEXT_MUTED}


class GapsView(ft.Column):
    def __init__(self, page: ft.Page):
        self._page = page
        self.refresh_btn = ft.Button("Update from my offers (Claude)", icon=ft.Icons.REFRESH, on_click=self._on_update)
        self.status = ft.Text("", size=12, color=Colors.TEXT_SECONDARY)
        self.list = ft.Column(spacing=8)
        super().__init__(
            controls=[
                ft.Text("Gaps", size=24, weight=ft.FontWeight.BOLD, color=Colors.TEXT_PRIMARY),
                ft.Text("What the jobs ask for that your record doesn't show. Fix the ones that open the most jobs.",
                        size=14, color=Colors.TEXT_SECONDARY),
                ft.Row([self.refresh_btn, self.status], spacing=12),
                self.list,
            ],
            spacing=12, expand=True, scroll=ft.ScrollMode.AUTO,
        )
        self.refresh(update=False)

    def refresh(self, update=True):
        from analyzers.gaps import load
        data = load()
        gaps = data.get("gaps", [])
        if data:
            self.status.value = f"Last updated {data['updated']} from {data['jobs']} jobs."
        else:
            self.status.value = "Not built yet: press Update (2-4 minutes)."
        self.list.controls = [self._card(g) for g in gaps] or [
            ft.Text("No gaps tracked yet.", size=13, color=Colors.TEXT_MUTED, italic=True)]
        if update:
            self._page.update()

    def _card(self, g):
        from analyzers.gaps import STATUSES, job_titles
        closed = g["status"] in ("done", "skip")
        n = len(g["refs"])
        status = ft.Dropdown(value=g["status"], width=160, text_size=12, dense=True,
                             options=[ft.dropdown.Option(k, v) for k, v in STATUSES.items()])
        status.on_select = lambda e, k=g["key"]: self._set(k, e.control.value)

        def chip(text, color):
            return ft.Container(content=ft.Text(text, size=10, color=color), bgcolor=Colors.BG_TERTIARY,
                                padding=ft.padding.symmetric(horizontal=8, vertical=2), border_radius=3)

        chips = [chip(f"BLOCKS {n} JOB{'S' if n != 1 else ''}", Colors.WARNING if n >= 3 else Colors.TEXT_SECONDARY),
                 chip(g["kind"].upper(), Colors.TEXT_SECONDARY)]
        if g["fixable"]:
            chips.append(chip(f"WORTH: {g['worth'].upper()}", WORTH_COLORS.get(g["worth"], Colors.TEXT_SECONDARY)))
        else:
            chips.append(chip("CAN'T FIX SOON: ANSWER IT", Colors.TEXT_MUTED))

        rows = [
            ft.Row([ft.Text(g["name"], size=15, weight=ft.FontWeight.BOLD,
                            color=Colors.TEXT_MUTED if closed else Colors.TEXT_PRIMARY, expand=True), status]),
            ft.Row(chips, spacing=4, wrap=True),
            ft.Text(g["why"], size=12, color=Colors.TEXT_SECONDARY),
            ft.Text(("Fix: " if g["fixable"] else "How to answer it: ") + g["fix"], size=12, color=Colors.TEXT_PRIMARY),
        ]
        if g["fixable"]:
            rows.append(ft.Text(f"Cost: {g['cost']} · Time: {g['time']} · Next date: {g['next_date']}",
                                size=12, color=Colors.ACCENT))
        if g["status"] == "done":
            rows.append(ft.Text("Done: add it to your profile (data/profile.yaml) so CVs and letters can use it.",
                                size=11, color=Colors.SUCCESS))
        titles = job_titles(g["refs"])
        if titles:
            rows.append(ft.ExpansionTile(
                title=ft.Text(f"The {len(titles)} jobs", size=12, color=Colors.TEXT_SECONDARY),
                controls=[ft.Text(f"• {t}", size=11, color=Colors.TEXT_SECONDARY) for t in titles],
            ))
        if g.get("sources"):
            rows.append(ft.Row([ft.TextButton(f"source {i + 1}", icon=ft.Icons.OPEN_IN_NEW,
                                              on_click=lambda e, u=u: webbrowser.open(u))
                                for i, u in enumerate(g["sources"][:4])], spacing=0, wrap=True))
        return ft.Container(content=ft.Column(rows, spacing=4), padding=12, bgcolor=Colors.BG_SECONDARY,
                            border_radius=8, opacity=0.6 if closed else 1)

    def _set(self, key, status):
        from analyzers.gaps import set_status
        set_status(key, status)
        self.refresh()

    async def _on_update(self, e):
        from analyzers.gaps import refresh
        if self.refresh_btn.disabled:
            return
        self.refresh_btn.disabled = True
        start = time.time()
        task = asyncio.ensure_future(asyncio.to_thread(refresh))
        while not task.done():
            self.status.value = f"Claude is grouping the gaps and looking up fixes... {int(time.time() - start)}s"
            self.status.color = Colors.ACCENT
            self._page.update()
            await asyncio.wait({task}, timeout=2)
        try:
            task.result()
            self.status.color = Colors.TEXT_SECONDARY
        except Exception as ex:
            self.status.value = f"Update failed: {ex}"
            self.status.color = Colors.ERROR
            self.refresh_btn.disabled = False
            self._page.update()
            return
        self.refresh_btn.disabled = False
        self.refresh()
