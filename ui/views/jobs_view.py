"""
Pipeline View - every application, wherever it was sent, and what to do next.
"""

import os
import webbrowser
from datetime import date
from pathlib import Path
from urllib.parse import quote

import flet as ft
from ..theme import Colors
from ..components import open_path
from core.pipeline import Pipeline, ALL_STAGES, CLOSED, load_channels, channel_name, today

STAGE_COLORS = {
    'found': Colors.TEXT_SECONDARY, 'applied': Colors.ACCENT, 'screening': Colors.SEVERITY_LOW,
    'interview': Colors.WARNING, 'offer': Colors.SUCCESS,
    'rejected': Colors.TEXT_MUTED, 'withdrawn': Colors.TEXT_MUTED, 'ghosted': Colors.TEXT_MUTED,
}
COUNTRIES = [("JP", "Japan"), ("FR", "France"), ("ANY", "Remote / other")]


def _dropdown(label, value, options, width, on_select=None):
    d = ft.Dropdown(label=label, value=value, width=width, text_size=13,
                    options=[ft.dropdown.Option(k, v) for k, v in options],
                    border_color=Colors.BG_TERTIARY, bgcolor=Colors.BG_SECONDARY)
    if on_select:
        d.on_select = on_select
    return d


def _field(label, width=None, expand=None, hint=None, value=""):
    return ft.TextField(label=label, value=value, width=width, expand=expand, hint_text=hint,
                        text_size=13, border_color=Colors.BG_TERTIARY, bgcolor=Colors.BG_SECONDARY)


class JobsView(ft.Column):
    """Pipeline: log applications from any channel, see what is due, see what works."""

    def __init__(self, page: ft.Page):
        self._page = page
        self.pipeline = Pipeline()
        from generators.application import BUSY
        self._preparing = BUSY          # shared with Job Finder: never two packs for one entry
        self._prepping = set()
        self._drafting = set()
        self.review_btn = ft.Button("Weekly review", icon=ft.Icons.INSIGHTS,
                                    on_click=lambda e: self._page.run_task(self._review))
        self.channels = load_channels()

        self.stats_row = ft.Row(spacing=12, wrap=True)
        self.channel_table = ft.Column(spacing=4)
        self.due_column = ft.Column(spacing=6)
        self.list_column = ft.Column(spacing=8)

        # Search a channel
        self.search_country = _dropdown("Country", "JP", COUNTRIES, 150, self._on_search_country)
        self.search_channel = _dropdown("Channel", None, [], 260)
        self.search_keywords = _field("Keywords", expand=True, hint="e.g. QA lead, chef de projet")
        self._fill_channels(self.search_country.value, self.search_channel, searchable=True)

        # Log an application
        self.f_company = _field("Company", expand=True)
        self.f_role = _field("Role", expand=True)
        self.f_country = _dropdown("Country", "JP", COUNTRIES, 150, self._on_form_country)
        self.f_channel = _dropdown("Channel", None, [], 260)
        self.f_stage = _dropdown("Stage", "applied", [("found", "Found (not sent)"), ("applied", "Applied")], 170)
        self.f_date = _field("Date", width=130, value=today())
        self.f_url = _field("Link", expand=True)
        self.f_contact = _field("Contact", width=220, hint="name / email")
        self._fill_channels(self.f_country.value, self.f_channel)

        # List filters
        self.filter_view = _dropdown("Show", "open", [("open", "Open"), ("closed", "Closed"), ("all", "All")],
                                     130, lambda e: self._refresh())
        self.filter_country = _dropdown("Country", "all", [("all", "All")] + COUNTRIES, 160, lambda e: self._refresh())

        def section(title):
            return ft.Text(title, size=16, weight=ft.FontWeight.BOLD, color=Colors.TEXT_PRIMARY)

        super().__init__(
            controls=[
                ft.Row([ft.Text("Pipeline", size=24, weight=ft.FontWeight.BOLD, color=Colors.TEXT_PRIMARY),
                        ft.Container(expand=True), self.review_btn]),
                ft.Text("Apply on each country's own channels. Log it here. Anvil tells you what's due and what works.",
                        size=14, color=Colors.TEXT_SECONDARY),
                self.stats_row,
                section("Due"),
                self.due_column,
                section("Search a channel"),
                ft.Row([self.search_country, self.search_channel, self.search_keywords,
                        ft.Button("Open", icon=ft.Icons.OPEN_IN_NEW, on_click=self._on_open_search)], spacing=10),
                section("Log an application"),
                ft.Row([self.f_company, self.f_role], spacing=10),
                ft.Row([self.f_country, self.f_channel, self.f_stage, self.f_date], spacing=10),
                ft.Row([self.f_url, self.f_contact,
                        ft.Button("Add", icon=ft.Icons.ADD, on_click=self._on_add)], spacing=10),
                section("What gets replies"),
                self.channel_table,
                ft.Row([section("Applications"), self.filter_view, self.filter_country], spacing=15),
                self.list_column,
            ],
            spacing=12,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

        self.pipeline.mark_ghosted()
        self._refresh(update=False)

    # --- helpers -------------------------------------------------------------

    def _fill_channels(self, country, dropdown, searchable=False):
        opts = [c for c in self.channels
                if c["country"] in (country, "ANY") and (not searchable or c.get("search") or c.get("url"))]
        dropdown.options = [ft.dropdown.Option(c["id"], c["name"]) for c in opts]
        dropdown.value = opts[0]["id"] if opts else None

    def _toast(self, text, color=None):
        self._page.show_dialog(ft.SnackBar(content=ft.Text(text), bgcolor=color))

    def _stat(self, value, label, color=Colors.TEXT_PRIMARY):
        return ft.Container(
            content=ft.Column([
                ft.Text(str(value), size=22, weight=ft.FontWeight.BOLD, color=color),
                ft.Text(label, size=12, color=Colors.TEXT_SECONDARY),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
            padding=12, bgcolor=Colors.BG_SECONDARY, border_radius=8, width=120,
        )

    # --- rendering -----------------------------------------------------------

    def _refresh(self, update=True):
        self.pipeline = Pipeline()      # Job Finder writes here too
        self.pipeline.mark_ghosted()
        p = self.pipeline
        f = p.funnel()
        due = p.due()

        self.stats_row.controls = [
            self._stat(len(p.open_apps()), "Open"),
            self._stat(f.applied, "Applied", Colors.ACCENT),
            self._stat(f"{f.response_rate:.0%}", "Reply rate"),
            self._stat(f.interviews, "Interviews", Colors.WARNING),
            self._stat(f.offers, "Offers", Colors.SUCCESS),
            self._stat(len(due), "Due today", Colors.ERROR if due else Colors.TEXT_MUTED),
        ]

        self.due_column.controls = [self._due_row(a) for a in due] or [
            ft.Text("Nothing due.", size=13, color=Colors.TEXT_MUTED, italic=True)]

        rows = []
        for ch, cf in sorted(p.funnel_by("channel").items(), key=lambda kv: -kv[1].applied):
            rows.append(ft.Row([
                ft.Text(channel_name(ch), width=240, size=13, color=Colors.TEXT_PRIMARY),
                ft.Text(f"{cf.applied} sent", width=80, size=13, color=Colors.TEXT_SECONDARY),
                ft.Text(f"{cf.responded} replies", width=90, size=13, color=Colors.TEXT_SECONDARY),
                ft.Text(f"{cf.interviews} interviews", width=100, size=13, color=Colors.TEXT_SECONDARY),
                ft.Text(f"{cf.response_rate:.0%}", size=13,
                        color=Colors.SUCCESS if cf.response_rate >= 0.2 else Colors.TEXT_SECONDARY),
            ]))
        self.channel_table.controls = rows or [
            ft.Text("Log a few applications to see which channels answer.", size=13,
                    color=Colors.TEXT_MUTED, italic=True)]

        apps = p.apps
        if self.filter_view.value == "open":
            apps = [a for a in apps if a["stage"] not in CLOSED]
        elif self.filter_view.value == "closed":
            apps = [a for a in apps if a["stage"] in CLOSED]
        if self.filter_country.value != "all":
            apps = [a for a in apps if a.get("country") == self.filter_country.value]
        apps = sorted(apps, key=lambda a: a["history"][-1]["on"], reverse=True)
        self.list_column.controls = [self._card(a) for a in apps] or [
            ft.Text("No applications here yet.", size=13, color=Colors.TEXT_MUTED, italic=True)]

        if update:
            self._page.update()

    def _due_row(self, a):
        return ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.SCHEDULE, color=Colors.WARNING, size=18),
                ft.Text(f"{a['next_action']} — {a['role']} @ {a['company']}", size=13,
                        color=Colors.TEXT_PRIMARY, expand=True),
                ft.Text(a["next_due"], size=12, color=Colors.TEXT_SECONDARY),
                ft.TextButton("Draft follow-up", icon=ft.Icons.EDIT_NOTE, disabled=a["id"] in self._drafting,
                              on_click=lambda e, i=a["id"]: self._page.run_task(self._follow_up, i))
                if a["stage"] == "applied" else ft.Container(),
                ft.TextButton("Done +7d", on_click=lambda e, i=a["id"]: self._snooze(i, 7)),
            ]),
            padding=8, bgcolor=Colors.BG_SECONDARY, border_radius=6,
        )

    def _card(self, a):
        stage = a["stage"]
        color = STAGE_COLORS.get(stage, Colors.TEXT_SECONDARY)
        last = a["history"][-1]["on"]
        silent = (date.today() - date.fromisoformat(last)).days

        stage_dd = _dropdown(None, stage, [(s, s.capitalize()) for s in ALL_STAGES], 140,
                             lambda e, i=a["id"]: self._move(i, e.control.value))
        next_field = _field("Next action", expand=True, value=a.get("next_action") or "")
        due_field = _field("Due", width=130, value=a.get("next_due") or "", hint="YYYY-MM-DD")
        save_next = ft.IconButton(icon=ft.Icons.CHECK, tooltip="Save next action",
                                  on_click=lambda e, i=a["id"]: self._set_next(i, next_field.value, due_field.value))

        meta = f"{channel_name(a.get('channel'))} · {a.get('country') or '?'}"
        if a.get("applied_on"):
            meta += f" · applied {a['applied_on']}"
        if stage == "applied":
            meta += f" · {silent}d silent"

        buttons = []
        if a.get("url"):
            buttons.append(ft.IconButton(icon=ft.Icons.OPEN_IN_NEW, tooltip="Open posting",
                                         icon_color=Colors.TEXT_SECONDARY,
                                         on_click=lambda e, u=a["url"]: webbrowser.open(u)))
        if a.get("url") and stage == "found":
            busy = a["id"] in self._preparing
            buttons.append(ft.IconButton(
                icon=ft.Icons.AUTO_AWESOME, icon_color=Colors.ACCENT, disabled=busy,
                tooltip="Prepare again" if a.get("pack") else "Prepare a tailored CV and letter",
                on_click=lambda e, i=a["id"]: self._page.run_task(self._prepare, i)))
        if a.get("pack") and stage == "found":
            buttons.append(ft.IconButton(icon=ft.Icons.SEND, icon_color=Colors.SUCCESS,
                                         tooltip="I sent it: move to Applied",
                                         on_click=lambda e, i=a["id"]: self._move(i, "applied")))
        if stage in ("applied", "screening", "interview", "offer"):
            buttons.append(ft.IconButton(
                icon=ft.Icons.RECORD_VOICE_OVER, icon_color=Colors.ACCENT, disabled=a["id"] in self._prepping,
                tooltip="Prepare again for the interview" if a.get("interview_prep") else "Prepare for the interview",
                on_click=lambda e, i=a["id"]: self._page.run_task(self._interview, i)))
        buttons.append(ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, tooltip="Delete",
                                     icon_color=Colors.TEXT_MUTED,
                                     on_click=lambda e, i=a["id"]: self._delete(i)))

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Container(width=4, height=44, bgcolor=color, border_radius=2),
                    ft.Column([
                        ft.Text(f"{a['role']} — {a['company']}", size=14, weight=ft.FontWeight.BOLD,
                                color=Colors.TEXT_PRIMARY),
                        ft.Text(meta, size=12, color=Colors.TEXT_SECONDARY),
                    ], spacing=2, expand=True),
                    stage_dd, *buttons,
                ], spacing=12),
                self._pack_block(a),
                self._interview_block(a),
                ft.Row([next_field, due_field, save_next], spacing=8),
            ], spacing=8),
            padding=12, bgcolor=Colors.BG_SECONDARY, border_radius=8,
        )

    def _pack_block(self, a):
        """The tailored CV and letter for this application, and how to send them."""
        if a["id"] in self._preparing:
            return ft.Row([ft.ProgressRing(width=14, height=14),
                           ft.Text("Preparing the tailored CV and letter (1-3 min)...", size=12, color=Colors.ACCENT)])
        pack = a.get("pack")
        if not pack:
            return ft.Container()
        files = [ft.TextButton(Path(d).name, icon=ft.Icons.DESCRIPTION,
                               on_click=lambda e, d=d: open_path(d, self._page)) for d in a.get("documents", [])
                 if Path(d).exists()]
        gloss = Path(pack["folder"]) / "letter_english.md"
        if gloss.exists():
            files.append(ft.TextButton("Letter in English", icon=ft.Icons.TRANSLATE,
                                       on_click=lambda e, p=gloss: open_path(p, self._page)))
        files.append(ft.TextButton("Folder", icon=ft.Icons.FOLDER_OPEN,
                                   on_click=lambda e, p=pack["folder"]: open_path(p, self._page)))
        rows = [ft.Text(f"Pack ({pack['letter_kind']}, {a.get('language', '')}, {pack['on']}): {pack['how_to_apply']}",
                        size=12, color=Colors.TEXT_PRIMARY),
                ft.Row(files, spacing=0, wrap=True)]
        if pack.get("gaps"):
            rows.append(ft.Text("Not in your record: " + "; ".join(pack["gaps"]), size=11, color=Colors.WARNING))
        if pack.get("violations"):
            rows.append(ft.Text("Check before sending: " + "; ".join(pack["violations"]), size=11, color=Colors.ERROR))
        return ft.Container(content=ft.Column(rows, spacing=2), padding=8, bgcolor=Colors.BG_TERTIARY, border_radius=6)

    def _interview_block(self, a):
        if a["id"] in self._prepping:
            return ft.Row([ft.ProgressRing(width=14, height=14),
                           ft.Text("Researching the company and writing your interview brief (1-3 min)...",
                                   size=12, color=Colors.ACCENT)])
        prep = a.get("interview_prep")
        if not prep or not Path(prep["file"]).exists():
            return ft.Container()
        return ft.TextButton(f"Interview brief ({prep['on']})", icon=ft.Icons.RECORD_VOICE_OVER,
                             on_click=lambda e, p=prep["file"]: open_path(p, self._page))

    async def _interview(self, app_id):
        import asyncio
        from generators.interview import prepare_interview
        self._prepping.add(app_id)
        self._refresh()
        try:
            await asyncio.to_thread(prepare_interview, app_id)
            self._toast(f"Interview brief ready for #{app_id}.")
        except Exception as ex:
            self._toast(f"Interview brief failed: {ex}", Colors.ERROR)
        finally:
            self._prepping.discard(app_id)
            self._refresh()

    async def _follow_up(self, app_id):
        import asyncio
        from core.outreach import draft_follow_up
        from ..components import mail_dialog
        self._drafting.add(app_id)
        self._toast("Drafting the follow-up (under a minute)...")
        self._refresh()
        try:
            a = await asyncio.to_thread(draft_follow_up, app_id)
        except Exception as ex:
            self._toast(f"Draft failed: {ex}", Colors.ERROR)
            return
        finally:
            self._drafting.discard(app_id)
            self._refresh()

        def sent(mail):
            from datetime import timedelta
            self.pipeline.update(app_id, notes=(a.get("notes") or "") + f"\nFollow-up sent {today()}.",
                                 last_touch=today())
            self.pipeline.set_next(app_id, "Second follow-up or close", (date.today() + timedelta(days=10)).isoformat())
            self._refresh()

        mail_dialog(self._page, a["follow_up_draft"], f"Follow-up: {a['role']} — {a['company']}", on_sent=sent)

    async def _review(self):
        import asyncio
        from analyzers.review import weekly_review
        self.review_btn.disabled = True
        self._toast("Building the weekly review (under a minute)...")
        self._page.update()
        try:
            md, path = await asyncio.to_thread(weekly_review)
        except Exception as ex:
            self._toast(f"Review failed: {ex}", Colors.ERROR)
            return
        finally:
            self.review_btn.disabled = False
            self._page.update()
        self._page.show_dialog(ft.AlertDialog(
            title=ft.Text("Weekly review"),
            content=ft.Container(ft.Column([ft.Markdown(md, selectable=True)], scroll=ft.ScrollMode.AUTO),
                                 width=720, height=560),
            actions=[ft.TextButton("Open file", icon=ft.Icons.DESCRIPTION, on_click=lambda e: open_path(path, self._page)),
                     ft.TextButton("Close", on_click=lambda e: self._page.pop_dialog())],
        ))

    async def _prepare(self, app_id):
        import asyncio
        from generators.application import prepare
        self._preparing.add(app_id)
        self._refresh()
        try:
            await asyncio.to_thread(prepare, app_id)
            self._toast(f"Pack ready for #{app_id}.")
        except Exception as ex:
            self._toast(f"Pack failed: {ex}", Colors.ERROR)
        finally:
            self._preparing.discard(app_id)
            self._refresh()

    # --- events --------------------------------------------------------------

    def _on_search_country(self, e):
        self._fill_channels(e.control.value, self.search_channel, searchable=True)
        self._page.update()

    def _on_form_country(self, e):
        self._fill_channels(e.control.value, self.f_channel)
        self._page.update()

    def _on_open_search(self, e):
        ch = next((c for c in self.channels if c["id"] == self.search_channel.value), None)
        if not ch:
            return
        kw = (self.search_keywords.value or "").strip()
        url = ch["search"].replace("{q}", quote(kw)) if ch.get("search") and kw else ch.get("url") or ch.get("search", "").split("?")[0]
        if url:
            webbrowser.open(url)

    def _on_add(self, e):
        if not (self.f_company.value and self.f_role.value):
            self._toast("Company and role are needed.", Colors.ERROR)
            return
        try:
            date.fromisoformat(self.f_date.value)
        except ValueError:
            self._toast("Date must be YYYY-MM-DD.", Colors.ERROR)
            return
        self.pipeline.add(
            company=self.f_company.value.strip(), role=self.f_role.value.strip(),
            channel=self.f_channel.value or "other", country=self.f_country.value,
            stage=self.f_stage.value, on=self.f_date.value, url=(self.f_url.value or "").strip(),
            contact=(self.f_contact.value or "").strip(),
        )
        for f in (self.f_company, self.f_role, self.f_url, self.f_contact):
            f.value = ""
        self._toast("Logged.")
        self._refresh()

    def _move(self, app_id, stage):
        before = self.pipeline.get(app_id)
        first_reply = stage in ("screening", "interview") and not (before or {}).get("interview_prep")
        self.pipeline.move(app_id, stage)
        self._refresh()
        if first_reply:      # a reply: get the interview brief going straight away
            self._page.run_task(self._interview, app_id)

    def _set_next(self, app_id, action, due):
        if due:
            try:
                date.fromisoformat(due)
            except ValueError:
                self._toast("Due must be YYYY-MM-DD.", Colors.ERROR)
                return
        self.pipeline.set_next(app_id, action or "", due or None)
        self._toast("Saved.")
        self._refresh()

    def _snooze(self, app_id, days):
        from datetime import timedelta
        a = self.pipeline.get(app_id)
        self.pipeline.set_next(app_id, a.get("next_action") or "Follow up",
                               (date.today() + timedelta(days=days)).isoformat())
        self._refresh()

    def _delete(self, app_id):
        self.pipeline.delete(app_id)
        self._refresh()
