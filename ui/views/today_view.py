"""
Today - the home screen: what is running, what to do next (at most 5 things), and the week in numbers.
"""

from datetime import datetime

import flet as ft
from ..theme import Colors, text
from ..tasks import TASKS, NAV

MAX_ITEMS = 5


def _card(content, padding=20):
    return ft.Container(content=content, bgcolor=Colors.BG_SECONDARY, border=ft.border.all(1, Colors.BORDER),
                        border_radius=12, padding=padding)


def primary_button(label, on_click, icon=None):
    return ft.FilledButton(label, icon=icon, on_click=on_click,
                           style=ft.ButtonStyle(bgcolor=Colors.ACCENT, color="#FFFFFF",
                                                shape=ft.RoundedRectangleBorder(radius=20),
                                                padding=ft.padding.symmetric(horizontal=18, vertical=12)))


def quiet_button(label, on_click, icon=None):
    return ft.OutlinedButton(label, icon=icon, on_click=on_click,
                             style=ft.ButtonStyle(color=Colors.ACCENT, side=ft.BorderSide(1, Colors.ACCENT),
                                                  shape=ft.RoundedRectangleBorder(radius=20),
                                                  padding=ft.padding.symmetric(horizontal=18, vertical=12)))


class TodayView(ft.Column):
    def __init__(self, page: ft.Page):
        self._page = page
        self.greeting = text("", "display")
        self.status = text("", "body", color=Colors.TEXT_SECONDARY)
        self.running = ft.Column(spacing=10)
        self.todo = ft.Column(spacing=10)
        self.answers = ft.Column(spacing=10)
        self.mail_line = ft.Row(spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        self.checking = False
        self.week = ft.Row(spacing=12)
        self.week_title = text("This week", "section")
        body = ft.Column([
            ft.Column([self.greeting, self.status], spacing=6),
            self.running,
            self.answers,
            ft.Column([text("Do next", "section"), self.todo], spacing=10),
            ft.Column([self.week_title, self.week], spacing=10),
            ft.Row([ft.TextButton("Weekly review", icon=ft.Icons.INSIGHTS,
                                  on_click=lambda e: self._page.run_task(self._review)),
                    ft.Container(expand=True), self.mail_line]),
        ], spacing=28, width=760)
        super().__init__(
            controls=[ft.Container(content=body, padding=ft.padding.only(top=40, bottom=40),
                                   alignment=ft.Alignment.TOP_CENTER)],
            expand=True, scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        TASKS.listen(self._on_tasks)
        self.refresh(update=False)
        from core import mail_watch
        if mail_watch.due():
            page.run_task(self.check_mail)

    # --- data ------------------------------------------------------------------------

    def _todo_items(self) -> list:
        from core.pipeline import Pipeline
        from core.outreach import Outreach
        from core.offers import OfferLibrary
        items = []
        pipe = Pipeline()
        for a in pipe.apps:
            if a["stage"] == "found" and a.get("pack"):
                kind = a["pack"].get("letter_kind", "letter")
                items.append((f"Send your application to {a['company']}",
                              f"{a['role']} · CV and {kind.lower()} are ready",
                              "Review and send", lambda e, i=a["id"]: NAV.go("applications", app_id=i), True))
        for a in pipe.due():
            if a["stage"] == "applied":
                items.append((f"Follow up with {a['company']}", f"{a['role']} · sent {a.get('applied_on')}, no reply yet",
                              "Write the follow-up", lambda e, i=a["id"]: NAV.go("applications", app_id=i), False))
            elif a["stage"] in ("screening", "interview"):
                items.append((f"Reply to {a['company']}", f"{a['role']} · {a.get('next_action') or 'they answered'}",
                              "Open", lambda e, i=a["id"]: NAV.go("applications", app_id=i), True))
        out = Outreach()
        due_ids = {i["id"] for i in out.due()}
        for i in out.items:
            if i["status"] == "drafted":
                items.append((f"Email {i['company']}", f"Draft ready · {i['what']}", "Open draft",
                              lambda e, n=i["id"]: NAV.go("applications", outreach_id=n), False))
            elif i["id"] in due_ids:
                items.append((f"Follow up your email to {i['company']}", f"Sent {i.get('sent_on')}, no reply",
                              "Open", lambda e, n=i["id"]: NAV.go("applications", outreach_id=n), False))
        new = [o for o in OfferLibrary().current() if o["status"] == "new"]
        if new:
            items.append((f"{len(new)} new offer{'s' if len(new) > 1 else ''} to look at",
                          "Best fit first, with the money left each month", "See offers",
                          lambda e: NAV.go("offers"), False))
        return items

    def _status_line(self) -> str:
        from core.pipeline import Pipeline, RESPONDED
        apps = Pipeline().apps
        out = [a for a in apps if a.get("applied_on") and a["stage"] not in ("withdrawn",)]
        replies = sum(1 for a in out if any(h["stage"] in RESPONDED for h in a["history"]))
        if not out:
            line = "Nothing sent yet."
        else:
            line = f"{len(out)} application{'s' if len(out) > 1 else ''} out, {replies} repl{'ies' if replies != 1 else 'y'}."
            if not replies:
                line += " Replies often take one to two weeks."
        if TASKS.running():
            line += " Anvil is working in the background."
        return line

    # --- rendering ---------------------------------------------------------------------

    def refresh(self, update=True):
        from core.profile_manager import ProfileManager
        h = datetime.now().hour
        part = "morning" if h < 12 else "afternoon" if h < 18 else "evening"
        first = (ProfileManager().load()["personal"].get("name") or "").split(" ")[0]
        self.greeting.value = f"Good {part}, {first}"
        self.status.value = self._status_line()
        self._render_running()

        items = self._todo_items()
        rows = []
        for title, sub, label, action, primary in items[:MAX_ITEMS]:
            btn = primary_button(label, action) if primary else quiet_button(label, action)
            rows.append(_card(ft.Row([ft.Column([text(title, "strong"), text(sub, "secondary")], spacing=2, expand=True),
                                      btn], spacing=16), padding=ft.padding.symmetric(horizontal=20, vertical=16)))
        if len(items) > MAX_ITEMS:
            rows.append(text(f"And {len(items) - MAX_ITEMS} more in Applications.", "secondary"))
        if not items:
            rows.append(_card(ft.Row([ft.Column([text("Nothing waiting for you.", "strong"),
                                                 text("Look for new offers in your places.", "secondary")],
                                                spacing=2, expand=True),
                                      primary_button("Find offers", lambda e: NAV.go("offers", search=True))])))
        self.todo.controls = rows
        self._render_mail()

        from analyzers.review import stats
        s = stats()
        from core.outreach import Outreach
        to_email = sum(1 for i in Outreach().items if i["status"] in ("target", "drafted"))

        def stat(n, label):
            return ft.Container(_card(ft.Column([text(str(n), "title"), text(label, "secondary")], spacing=0),
                                      padding=ft.padding.symmetric(horizontal=16, vertical=14)), expand=True)

        self.week.controls = [stat(s["offers_found"], "new offers"), stat(s["applied"], "sent"),
                              stat(len(s["replies"]), "replies"), stat(to_email, "to email")]
        self.week_title.value = "This week"
        if update:
            self._page.update()

    # --- mail ------------------------------------------------------------------------------

    def _render_mail(self):
        from core import mail_watch
        from core.pipeline import STAGES
        stage_names = {"screening": "They replied", "interview": "Interview", "offer": "Interview",
                       "rejected": "Closed"}
        rows = []
        for m in mail_watch.waiting():
            acts = []
            target = mail_watch.MOVE_TO.get(m["kind"])
            if m["for"] == "app" and target:
                from core.pipeline import Pipeline
                a = Pipeline().get(m["item_id"])
                if a and a["stage"] != target and (target not in STAGES or a["stage"] not in STAGES or
                                                   STAGES.index(target) > STAGES.index(a["stage"])):
                    acts.append(primary_button(f"Move to {stage_names[target]}",
                                               lambda e, m=m, t=target: self._move_from_mail(m, t)))
            if m["for"] == "app" and m["kind"] in ("reply", "interview", "offer"):
                acts.append(quiet_button("Prepare what they ask", lambda e, m=m: NAV.go(
                    "applications", app_id=m["item_id"], answer=m["id"]), ft.Icons.AUTO_AWESOME))
            acts.append(quiet_button("Open in Gmail", lambda e, m=m: __import__("webbrowser").open(
                mail_watch.gmail_link(m))))
            acts.append(ft.IconButton(ft.Icons.CLOSE, tooltip="Done with this", icon_color=Colors.TEXT_MUTED,
                                      on_click=lambda e, i=m["id"]: self._mail_done(i)))
            color = {"rejection": Colors.TEXT_SECONDARY, "interview": Colors.SUCCESS,
                     "offer": Colors.SUCCESS}.get(m["kind"], Colors.ACCENT)
            rows.append(_card(ft.Column([
                ft.Row([text(f"{m['company'].split(' (')[0]}: {mail_watch.KINDS[m['kind']].lower()}", "strong",
                             color=color, expand=True), text(m["date"], "caption")]),
                text(m["summary"] + (f" ({m['when']})" if m.get("when") else ""), "secondary",
                     color=Colors.TEXT_PRIMARY),
                text(f"{m['role']} · {m['subject']}", "caption", max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Row(acts, spacing=8, wrap=True),
            ], spacing=6), padding=ft.padding.symmetric(horizontal=20, vertical=16)))
        self.answers.controls = [text("Answers in your mail", "section"), *rows] if rows else []

        if not mail_watch.connected():
            again = bool(mail_watch.load().get("last_check"))
            label = "Reconnect Gmail (Google asks every 7 days)" if again else "Connect Gmail to watch for answers"
            self.mail_line.controls = [ft.TextButton(label, icon=ft.Icons.MAIL_OUTLINE,
                                                     on_click=lambda e: self._page.run_task(self.connect_mail))]
        elif self.checking:
            self.mail_line.controls = [ft.ProgressRing(width=14, height=14, stroke_width=2, color=Colors.ACCENT),
                                       text("Checking your mail…", "caption")]
        else:
            last = mail_watch.load().get("last_check")
            when = "never"
            if last:
                mins = int((datetime.now() - datetime.fromisoformat(last)).total_seconds() // 60)
                when = "just now" if mins < 2 else f"{mins} min ago" if mins < 60 else f"{mins // 60} h ago"
            self.mail_line.controls = [text(f"Mail checked {when}", "caption"),
                                       ft.TextButton("Check now", on_click=lambda e: self._page.run_task(self.check_mail))]
            if not mail_watch.can_sort():
                self.mail_line.controls.append(ft.TextButton(
                    "Let Anvil sort job alerts (reconnect)", icon=ft.Icons.FILTER_LIST,
                    on_click=lambda e: self._page.run_task(self.connect_mail)))
            else:
                self.mail_line.controls.append(ft.TextButton(
                    "Unsubscribe…", on_click=lambda e: self._page.run_task(self._unsubscribe_dialog)))

    def _move_from_mail(self, m, stage):
        from core import mail_watch
        from core.pipeline import Pipeline
        Pipeline().move(m["item_id"], stage, note=f"mail {m['date']}: {m['summary']}")
        mail_watch.mark_done(m["id"])
        if stage in ("screening", "interview"):
            NAV.go("applications", app_id=m["item_id"])     # the interview brief starts from there
        self.refresh()

    def _mail_done(self, msg_id):
        from core import mail_watch
        mail_watch.mark_done(msg_id)
        self.refresh()

    async def connect_mail(self):
        import asyncio
        from core import mail_watch
        tid = TASKS.start("Connecting Gmail", "waiting for you in the browser")
        try:
            await asyncio.to_thread(mail_watch.connect)
            TASKS.finish(tid, "connected (read only)")
        except Exception as ex:
            TASKS.finish(tid, str(ex), ok=False)
            self._page.show_dialog(ft.SnackBar(ft.Text(f"Gmail was not connected: {ex}")))
            self.refresh()
            return
        await self.check_mail()

    async def check_mail(self):
        import asyncio
        from core import mail_watch
        if self.checking:
            return
        self.checking = True
        self.refresh()
        tid = TASKS.start("Checking your mail for answers", "reading your inbox")
        try:
            res = await asyncio.to_thread(mail_watch.check, lambda s: TASKS.update(tid, s))
            n = len(res["new"])
            TASKS.finish(tid, f"{n} new answer{'s' if n != 1 else ''}" if n else "nothing new")
        except Exception as ex:
            TASKS.finish(tid, str(ex), ok=False)
            self.checking = False
            self.refresh()
            return
        await self._read_alerts()
        await self._sort_mail()
        self.checking = False
        self.refresh()

    async def _sort_mail(self):
        """Job alerts and recruiting noise leave the inbox for the "Job alerts" label (after being read)."""
        import asyncio
        from core import mail_watch, mail_sort
        if not mail_watch.can_sort():
            return
        tid = TASKS.start("Sorting recruiting mail out of your inbox", "")
        try:
            n = await asyncio.to_thread(mail_sort.sort, lambda s: TASKS.update(tid, s))
            TASKS.finish(tid, f"{n} moved to \"{mail_sort.LABEL}\"" if n else "inbox already tidy")
        except Exception as ex:
            TASKS.finish(tid, str(ex), ok=False)

    async def _unsubscribe_dialog(self):
        import asyncio
        from core import mail_sort
        try:
            items = await asyncio.to_thread(mail_sort.noise_senders)
        except Exception as ex:
            self._page.show_dialog(ft.SnackBar(ft.Text(f"Could not read your mail: {ex}")))
            return
        rows = []
        for it in items:
            state = text("", "caption")

            def go(e, it=it, state=state):
                e.control.disabled = True
                state.value = mail_sort.unsubscribe(it)
                self._page.update()

            rows.append(ft.Row([ft.Column([text(it["sender"], "strong"),
                                           text(f"{it['count']} in 30 days · {it['subject'][:60]}", "caption"), state],
                                          spacing=2, expand=True),
                                quiet_button("Unsubscribe", go) if it["url"] else text("no link", "caption")]))
        if not rows:
            rows = [text("No noisy senders in the last 30 days.", "secondary")]
        self._page.show_dialog(ft.AlertDialog(
            title=text("Unsubscribe from recruiting noise", "title"),
            content=ft.Column([text("Job alerts are kept: Anvil reads them for jobs that fit, then files them.",
                                    "secondary"), *rows], tight=True, spacing=12, width=560,
                              scroll=ft.ScrollMode.AUTO),
            actions=[ft.TextButton("Close", on_click=lambda e: self._page.pop_dialog())]))

    async def _read_alerts(self):
        """The LinkedIn / Indeed alert flood: keep only the jobs that fit, in Offers."""
        import asyncio
        from core import mail_alerts
        from ..tasks import HOOKS
        tid = TASKS.start("Reading your job alerts", "looking for the few that fit")
        try:
            res = await asyncio.to_thread(mail_alerts.mine, lambda s: TASKS.update(tid, s))
        except Exception as ex:
            TASKS.finish(tid, str(ex), ok=False)
            return
        n = len(res["new"])
        TASKS.finish(tid, f"{res['alerts']} alerts read, {n} job{'s' if n != 1 else ''} worth a look"
                     if res["alerts"] else "no new alerts")
        if n:
            if "offers_refresh" in HOOKS:
                HOOKS["offers_refresh"]()
            if "investigate" in HOOKS:
                HOOKS["investigate"](res["new"])
            self._page.show_dialog(ft.SnackBar(ft.Text(f"{n} jobs from your alerts are worth a look."),
                                               action="See offers", on_action=lambda e: NAV.go("offers")))

    def _render_running(self):
        tasks = TASKS.running()
        if not tasks:
            self.running.controls = []
            return
        rows = []
        for t in tasks:
            rows.append(ft.Row([ft.ProgressRing(width=16, height=16, stroke_width=2, color=Colors.ACCENT),
                                ft.Column([text(t["label"], "strong"),
                                           text(" · ".join(x for x in (t["stage"], TASKS.elapsed(t)) if x), "secondary")],
                                          spacing=0, expand=True)], spacing=12))
        self.running.controls = [_card(ft.Column(
            [text("In progress", "section"), *rows,
             text("You can keep working. Results appear where they belong when they are ready.", "secondary")],
            spacing=12))]

    def _on_tasks(self):
        self.status.value = self._status_line()
        self._render_running()
        try:
            self._page.update()
        except Exception:
            pass

    async def _review(self):
        import asyncio
        import os
        from analyzers.review import weekly_review
        tid = TASKS.start("Weekly review", "reading your week")
        try:
            md, path = await asyncio.to_thread(weekly_review)
        except Exception as ex:
            TASKS.finish(tid, str(ex), ok=False)
            return
        TASKS.finish(tid, "ready")
        self._page.show_dialog(ft.AlertDialog(
            title=text("Weekly review", "title"),
            content=ft.Container(ft.Column([ft.Markdown(md, selectable=True)], scroll=ft.ScrollMode.AUTO),
                                 width=720, height=560),
            actions=[ft.TextButton("Open file", on_click=lambda e: os.startfile(path)),
                     ft.TextButton("Close", on_click=lambda e: self._page.pop_dialog())],
        ))
