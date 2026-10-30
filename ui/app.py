"""
Anvil UI - main window.

Four places (Today, Offers, Applications, Me) plus Settings, instead of eleven tabs.
Every view is built once and kept, so work started on one screen keeps running on the others;
the task centre (ui/tasks.py) shows what is running from anywhere.
"""

import flet as ft
from .theme import Colors, style_page, text
from .tasks import TASKS, NAV
from .views import (CVView, CoverLetterView, ArticleView, CheckView, JobsView, JobFinderView, ComedyView,
                    SettingsView, TriageView, OutreachView, GapsView, TodayView,
                    OffersView, ApplicationsView, MeView)


class SubNav(ft.Column):
    """A place with a few sections: a segmented switch on top, one section shown below."""

    def __init__(self, page, sections: list[tuple[str, str, object]]):
        self._page = page
        self.sections = {key: view for key, _, view in sections}
        self.switch = ft.SegmentedButton(
            segments=[ft.Segment(value=key, label=label) for key, label, _ in sections],
            selected=[sections[0][0]], show_selected_icon=False,
            on_change=lambda e: self.show(e.control.selected[0]),
        )
        self.body = ft.Container(content=sections[0][2], expand=True,
                                 padding=ft.padding.only(left=28, right=28, top=12))
        super().__init__([ft.Container(self.switch, padding=ft.padding.only(left=28, top=20)), self.body],
                         expand=True, spacing=0)

    def show(self, key, update=True):
        self.switch.selected = [key]
        view = self.sections[key]
        self.body.content = view
        _refresh(view)
        if update:
            self._page.update()

    def current(self):
        return self.body.content


def _refresh(view):
    """Reload lists that other places write to, when a view comes into sight."""
    if isinstance(view, ft.Container) and view.content is not None and not isinstance(view, SubNav):
        view = view.content
    for name in ("_refresh", "refresh"):
        fn = getattr(view, name, None)
        if fn:
            try:
                fn(update=False)
            except TypeError:
                pass
            return
    if isinstance(view, JobFinderView):
        view._show_library(update=False)


def main(page: ft.Page):
    page.title = "Anvil"
    page.window.width = 1280
    page.window.height = 860
    page.window.min_width = 960
    page.window.min_height = 640
    style_page(page)
    _soften_errors(page)

    cover_letter_view = CoverLetterView(page)
    outreach = OutreachView(page)
    finder = JobFinderView(page, on_generate_cover_letter=lambda d: open_letter(d))
    # Offers shows the search and the library; "check a posting" moved under Me
    finder.tab_content.content = finder.search_content
    finder.tab_buttons.visible = False
    finder.controls[0].value = "Offers"
    finder.controls[1].value = "Best fit first, then your places, then the money left each month."

    applications = ApplicationsView(page, outreach)
    me = MeView(page, GapsView(page), tools=[
        ("Your criteria and facts", "Places, savings goal, home, household, JLPT level, corrections",
         ft.Icons.TUNE, lambda: go("offers", criteria=True)),
        ("Check a posting", "Paste a link or text: fit, gaps and what to send", ft.Icons.FACT_CHECK,
         _analyze_only(finder)),
        ("Cover letter", "Write one letter for any posting", ft.Icons.EMAIL_OUTLINED, cover_letter_view),
        ("CV", "A general CV from your profile", ft.Icons.DESCRIPTION_OUTLINED, CVView(page)),
        ("Quick triage", "Realistic, stretch or skip for a pasted posting", ft.Icons.RULE, TriageView(page)),
        ("Profile check", "Is your profile complete and honest?", ft.Icons.VERIFIED_OUTLINED, CheckView(page)),
    ], writing=[
        ("Articles", "Posts from your engineering logs", ft.Icons.ARTICLE_OUTLINED, ArticleView(page)),
        ("Diary", "The ChronOS diary, EN + JA", ft.Icons.AUTO_STORIES_OUTLINED, ComedyView(page)),
    ])
    places = [
        ("today", "Today", ft.Icons.WB_SUNNY_OUTLINED, ft.Icons.WB_SUNNY, TodayView(page)),
        ("offers", "Offers", ft.Icons.SEARCH_OUTLINED, ft.Icons.SEARCH, padded(OffersView(page))),
        ("applications", "Applications", ft.Icons.WORK_OUTLINE, ft.Icons.WORK, padded(applications)),
        ("me", "Me", ft.Icons.PERSON_OUTLINE, ft.Icons.PERSON, padded(me)),
    ]
    settings = padded(SettingsView(page))
    index = {key: i for i, (key, *_rest) in enumerate(places)}

    content_area = ft.Container(content=places[0][4], expand=True, bgcolor=Colors.BG_PRIMARY)

    def show_view(view):
        content_area.content = view
        _refresh(view)

    def go(place, **focus):
        if place == "settings":
            rail.select("settings")
            show_view(settings)
        else:
            rail.select(place)
            view = places[index[place]][4]
            show_view(view)
            target = view.content if isinstance(view, ft.Container) else view
            if focus and hasattr(target, "focus_item"):
                target.focus_item(**focus)
            if focus.get("search") and hasattr(target, "search"):
                page.run_task(target.search)
        page.update()

    NAV.bind(go)

    def open_letter(job_data: dict):
        cover_letter_view.job_description.value = job_data.get('description', '')
        cover_letter_view.company_field.value = job_data.get('company', '')
        cover_letter_view.role_field.value = job_data.get('role', '')
        go("me", tool="Cover letter")

    # Running tasks, always visible at the bottom of the rail
    activity_ring = ft.ProgressRing(width=18, height=18, stroke_width=2, color=Colors.ACCENT, visible=False)
    activity_text = ft.Text("", size=12, color=Colors.TEXT_SECONDARY, text_align=ft.TextAlign.CENTER, width=88)
    activity = ft.Container(
        content=ft.Column([activity_ring, activity_text], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                          spacing=4, tight=True),
        padding=8, border_radius=12, ink=True, tooltip="What Anvil is doing",
        on_click=lambda e: show_tasks(),
    )

    def on_tasks():
        n = len(TASKS.running())
        activity_ring.visible = bool(n)
        activity_text.value = f"{n} running" if n else ""
        try:
            page.update()
        except Exception:
            pass

    TASKS.listen(on_tasks)

    def show_tasks():
        rows = [ft.Row([ft.ProgressRing(width=14, height=14, stroke_width=2, color=Colors.ACCENT),
                        ft.Column([text(t["label"], "strong"),
                                   text(" · ".join(x for x in (t["stage"], TASKS.elapsed(t)) if x), "secondary")],
                                  spacing=0, expand=True)]) for t in TASKS.running()]
        rows += [ft.Row([ft.Icon(ft.Icons.CHECK if t.get("ok") else ft.Icons.ERROR_OUTLINE,
                                 color=Colors.SUCCESS if t.get("ok") else Colors.ERROR, size=16),
                         ft.Column([text(t["label"], "body"), text(t.get("result", ""), "caption")],
                                   spacing=0, expand=True)]) for t in TASKS.recent[:5]]
        page.show_dialog(ft.AlertDialog(
            title=text("What Anvil is doing", "title"),
            content=ft.Container(ft.Column(rows or [text("Nothing running.", "secondary")], spacing=12,
                                           scroll=ft.ScrollMode.AUTO), width=520),
            actions=[ft.TextButton("Close", on_click=lambda e: page.pop_dialog())],
        ))

    rail = Rail([(key, label, icon, sel) for key, label, icon, sel, _ in places], go, activity)

    page.add(ft.Row([rail, content_area], expand=True, spacing=0,
                    vertical_alignment=ft.CrossAxisAlignment.STRETCH))


class Rail(ft.Container):
    """The left menu: four places, then what is running, then Settings.
    Built from plain containers: Flutter's NavigationRail could lose its layout when the bundled
    font finished loading after the first frame (blank window, seen in about 1 start in 4)."""

    def __init__(self, items, go, activity):
        self._items = {}
        rows = [ft.Container(text("Anvil", "section", color=Colors.ACCENT), padding=ft.padding.only(top=20, bottom=20))]
        for key, label, icon, sel in items:
            pill = ft.Container(ft.Icon(icon, color=Colors.TEXT_SECONDARY, size=22), width=56, height=32,
                                border_radius=16, alignment=ft.Alignment.CENTER)
            lab = ft.Text(label, size=13, color=Colors.TEXT_SECONDARY, text_align=ft.TextAlign.CENTER)
            box = ft.Container(ft.Column([pill, lab], spacing=4, tight=True,
                                         horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                               width=96, padding=ft.padding.symmetric(vertical=6), border_radius=12, ink=True,
                               on_click=lambda e, k=key: go(k))
            self._items[key] = (pill, lab, icon, sel)
            rows.append(box)
        self.settings = ft.IconButton(icon=ft.Icons.SETTINGS_OUTLINED, icon_color=Colors.TEXT_SECONDARY,
                                      tooltip="Settings", on_click=lambda e: go("settings"))
        rows += [ft.Container(expand=True), activity, ft.Container(self.settings, padding=ft.padding.only(bottom=16))]
        super().__init__(content=ft.Column(rows, spacing=6, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                         width=104, bgcolor=Colors.BG_TERTIARY,
                         border=ft.Border(right=ft.BorderSide(1, Colors.BORDER)))
        self.select(items[0][0])

    def select(self, key):
        for k, (pill, lab, icon, sel) in self._items.items():
            on = k == key
            pill.bgcolor = Colors.ACCENT_SOFT if on else None
            pill.content = ft.Icon(sel if on else icon, color=Colors.ACCENT if on else Colors.TEXT_SECONDARY, size=22)
            lab.color = Colors.TEXT_PRIMARY if on else Colors.TEXT_SECONDARY
            lab.font_family = "Plex SemiBold" if on else None
        self.settings.icon_color = Colors.ACCENT if key == "settings" else Colors.TEXT_SECONDARY


def _soften_errors(page: ft.Page):
    """An error in one button must not replace the whole window with an error page (Flet's default).
    Log it to logs/errors.log and show a short notice; everything else keeps running."""
    import datetime
    from pathlib import Path
    log = Path(__file__).parent.parent / "logs" / "errors.log"

    def soft(message: str):
        try:
            log.parent.mkdir(exist_ok=True)
            with open(log, "a", encoding="utf-8") as f:
                f.write("--- %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + chr(10) + message + chr(10))
        except OSError:
            pass
        first = (message or "").strip().splitlines()[0][:160] if message else "unknown error"
        try:
            page.show_dialog(ft.SnackBar(ft.Text(f"Something went wrong: {first}. Details in logs/errors.log."),
                                         bgcolor=Colors.ERROR))
            page.update()
        except Exception:
            pass

    try:
        page.session.error = soft
    except Exception:
        pass


def padded(view):
    """A place's page margins; the view stays reachable as .content."""
    box = ft.Container(content=view, expand=True, padding=ft.padding.only(left=28, right=28, top=24))
    return box


def _analyze_only(finder: JobFinderView):
    """The 'check a posting' part of the old Job Finder, on its own."""
    return ft.Container(content=finder.analyze_content, expand=True, padding=ft.padding.only(left=18, right=18))


def run():
    """Run the Anvil UI."""
    from pathlib import Path
    ft.run(main, assets_dir=str(Path(__file__).parent / "assets"))


if __name__ == "__main__":
    run()
