"""
Me - what to learn next (gaps), the single-document tools, and the writing side (articles, diary).

Tools and writing are cards; opening one shows it full width with a way back.
"""

import flet as ft
from ..theme import Colors, text
from ..tasks import NAV


class MeView(ft.Column):
    def __init__(self, page: ft.Page, gaps, tools: list, writing: list):
        """tools / writing: (title, one line, icon, view or callable)."""
        self._page = page
        self.gaps = gaps
        self.tools = tools
        self.writing = writing
        self.switch = ft.SegmentedButton(
            segments=[ft.Segment(value="learn", label="What to learn"), ft.Segment(value="tools", label="Tools"),
                      ft.Segment(value="writing", label="Writing")],
            selected=["learn"], show_selected_icon=False, on_change=lambda e: self.show(e.control.selected[0]))
        self.body = ft.Container(expand=True)
        super().__init__([ft.Row([text("Me", "title"), self.switch], spacing=24,
                                 vertical_alignment=ft.CrossAxisAlignment.CENTER), self.body],
                         spacing=16, expand=True)
        self.show("learn", update=False)

    def _grid(self, items):
        cards = []
        for title, line, icon, target in items:
            cards.append(ft.Container(
                content=ft.Row([ft.Container(ft.Icon(icon, color=Colors.ACCENT, size=26), width=48, height=48,
                                             bgcolor=Colors.ACCENT_SOFT, border_radius=24, alignment=ft.Alignment.CENTER),
                                ft.Column([text(title, "strong"), text(line, "secondary")], spacing=2, expand=True)],
                               spacing=16),
                bgcolor=Colors.BG_SECONDARY, border=ft.border.all(1, Colors.BORDER), border_radius=12, padding=18,
                ink=True, col={"sm": 12, "md": 6}, on_click=lambda e, t=target, n=title: self.open(t, n)))
        return ft.ResponsiveRow(cards, spacing=12, run_spacing=12)

    def show(self, key, update=True):
        self.switch.selected = [key]
        if key == "learn":
            self.gaps.refresh(update=False)
            self.body.content = self.gaps
        elif key == "tools":
            self.body.content = ft.Column([self._grid(self.tools)], scroll=ft.ScrollMode.AUTO)
        else:
            self.body.content = ft.Column([self._grid(self.writing)], scroll=ft.ScrollMode.AUTO)
        if update:
            self._page.update()

    def open(self, target, name):
        if callable(target) and not isinstance(target, ft.Control):
            target()
            return
        back = ft.TextButton(f"← Back", on_click=lambda e: self.show(self.switch.selected[0]))
        self.body.content = ft.Column([back, ft.Container(target, expand=True)], spacing=4, expand=True)
        self._page.update()

    def focus_item(self, tool=None, **_):
        for title, _line, _icon, target in self.tools + self.writing:
            if title == tool:
                self.switch.selected = ["tools" if (title, _line, _icon, target) in self.tools else "writing"]
                self.open(target, title)
                return
