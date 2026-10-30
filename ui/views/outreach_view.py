"""
Outreach View - companies worth writing to even when they are not posting, and the emails to them.
"""

import asyncio
import time
import webbrowser

import flet as ft
from ..theme import Colors
from ..components import mail_dialog

STATUS_COLORS = {"target": Colors.TEXT_SECONDARY, "drafted": Colors.ACCENT, "sent": Colors.WARNING,
                 "replied": Colors.SUCCESS, "no_reply": Colors.TEXT_MUTED, "dropped": Colors.TEXT_MUTED}


class OutreachView(ft.Column):
    def __init__(self, page: ft.Page):
        self._page = page
        self._busy = set()
        self.place = ft.TextField(label="Where (empty = my places)", width=300, text_size=13)
        self.find_btn = ft.Button("Find companies (Claude)", icon=ft.Icons.TRAVEL_EXPLORE, on_click=self._on_find)
        self.status = ft.Text("Claude looks for employers who need what you do, posting or not. "
                              "You write; Anvil drafts. Nothing is sent for you.", size=12,
                              color=Colors.TEXT_SECONDARY)
        self.show = ft.Dropdown(label="Show", value="open", width=180, text_size=13,
                                options=[ft.dropdown.Option("open", "To do and waiting"),
                                         ft.dropdown.Option("closed", "Replied / closed"),
                                         ft.dropdown.Option("all", "All")])
        self.show.on_select = lambda e: self.refresh()
        self.list = ft.Column(spacing=8)
        super().__init__(
            controls=[
                ft.Text("Outreach", size=24, weight=ft.FontWeight.BOLD, color=Colors.TEXT_PRIMARY),
                ft.Text("Speculative applications: most jobs are never posted.", size=14,
                        color=Colors.TEXT_SECONDARY),
                ft.Row([self.place, self.find_btn, self.show], spacing=10),
                self.status,
                self.list,
            ],
            spacing=12, expand=True, scroll=ft.ScrollMode.AUTO,
        )
        self.refresh(update=False)

    # --- rendering ---------------------------------------------------------------

    def refresh(self, update=True):
        from core.outreach import Outreach
        out = Outreach()
        due = {i["id"] for i in out.due()}
        items = out.items
        if self.show.value == "open":
            items = [i for i in items if i["status"] in ("target", "drafted", "sent")]
        elif self.show.value == "closed":
            items = [i for i in items if i["status"] in ("replied", "no_reply", "dropped")]
        order = {"drafted": 0, "target": 1, "sent": 2}
        items = sorted(items, key=lambda i: (i["id"] not in due, order.get(i["status"], 3), -i["id"]))
        self.list.controls = [self._card(i, i["id"] in due) for i in items] or [
            ft.Text("Nothing here yet. Find companies to write to.", size=13, color=Colors.TEXT_MUTED, italic=True)]
        if update:
            self._page.update()

    def _card(self, i, due):
        color = STATUS_COLORS.get(i["status"], Colors.TEXT_SECONDARY)
        meta = f"{i['place']} · {i['language']} · {i['status'].upper()}"
        if i.get("sent_on"):
            meta += f" · sent {i['sent_on']}"
        if due:
            meta += " · FOLLOW UP DUE"
        busy = i["id"] in self._busy
        buttons = []
        if i["status"] in ("target", "drafted"):
            buttons.append(ft.IconButton(icon=ft.Icons.EDIT_NOTE, icon_color=Colors.ACCENT, disabled=busy,
                                         tooltip="Draft the email" if i["status"] == "target" else "Draft again",
                                         on_click=lambda e, n=i["id"]: self._page.run_task(self._draft, n)))
        if i.get("body"):
            buttons.append(ft.IconButton(icon=ft.Icons.EMAIL, icon_color=Colors.SUCCESS, tooltip="Open the draft",
                                         on_click=lambda e, n=i["id"]: self._open_mail(n)))
        if i["status"] == "sent":
            buttons += [
                ft.IconButton(icon=ft.Icons.MARK_EMAIL_READ, icon_color=Colors.SUCCESS,
                              tooltip="They replied: add to the pipeline",
                              on_click=lambda e, n=i["id"]: self._replied(n)),
                ft.IconButton(icon=ft.Icons.DO_NOT_DISTURB, icon_color=Colors.TEXT_MUTED, tooltip="No reply: close",
                              on_click=lambda e, n=i["id"]: self._set(n, status="no_reply")),
            ]
        if i["status"] in ("target", "drafted"):
            buttons.append(ft.IconButton(icon=ft.Icons.CLOSE, icon_color=Colors.TEXT_MUTED, tooltip="Not this one",
                                         on_click=lambda e, n=i["id"]: self._set(n, status="dropped")))
        rows = [
            ft.Text(i["company"], size=14, weight=ft.FontWeight.BOLD, color=Colors.TEXT_PRIMARY),
            ft.Text(meta, size=11, color=Colors.WARNING if due else Colors.TEXT_SECONDARY),
            ft.Text(i["what"], size=12, color=Colors.TEXT_SECONDARY),
            ft.Text(i["why"], size=12, color=Colors.TEXT_PRIMARY),
            ft.Row([ft.Text(f"Contact: {i['contact']}", size=12, color=Colors.ACCENT, expand=True),
                    ft.TextButton("source", icon=ft.Icons.OPEN_IN_NEW,
                                  on_click=lambda e, u=i["contact_url"]: webbrowser.open(u))]),
        ]
        if busy:
            rows.append(ft.Row([ft.ProgressRing(width=14, height=14),
                                ft.Text("Drafting...", size=11, color=Colors.ACCENT)]))
        return ft.Container(
            content=ft.Row([ft.Container(width=4, height=60, bgcolor=color, border_radius=2),
                            ft.Column(rows, spacing=2, expand=True), ft.Column(buttons, spacing=0)],
                           vertical_alignment=ft.CrossAxisAlignment.START, spacing=12),
            padding=12, bgcolor=Colors.BG_SECONDARY, border_radius=8,
        )

    # --- events ------------------------------------------------------------------

    def _set(self, item_id, **fields):
        from core.outreach import Outreach
        Outreach().set(item_id, **fields)
        self.refresh()

    async def _on_find(self, e):
        from core.outreach import find_targets
        if self.find_btn.disabled:
            return
        self.find_btn.disabled = True
        start = time.time()
        task = asyncio.ensure_future(asyncio.to_thread(find_targets, (self.place.value or "").strip()))
        while not task.done():
            self.status.value = f"Claude is looking for companies... {int(time.time() - start)}s (usually 2-5 minutes)"
            self.status.color = Colors.ACCENT
            self._page.update()
            await asyncio.wait({task}, timeout=2)
        try:
            new = task.result()
            self.status.value = f"{len(new)} new companies. Draft an email for the ones worth it."
            self.status.color = Colors.SUCCESS if new else Colors.WARNING
        except Exception as ex:
            self.status.value = f"Search failed: {ex}"
            self.status.color = Colors.ERROR
        finally:
            self.find_btn.disabled = False
            self.refresh()

    async def _draft(self, item_id):
        from core.outreach import draft
        self._busy.add(item_id)
        self.refresh()
        try:
            await asyncio.to_thread(draft, item_id)
            self._busy.discard(item_id)
            self.refresh()
            self._open_mail(item_id)
        except Exception as ex:
            self._busy.discard(item_id)
            self.status.value = f"Draft failed: {ex}"
            self.status.color = Colors.ERROR
            self.refresh()

    def _open_mail(self, item_id):
        from core.outreach import Outreach
        i = Outreach().get(item_id)
        mail_dialog(self._page, {"to": i.get("to", ""), "subject": i["subject"], "body": i["body"],
                                 "english": i.get("english", ""), "violations": i.get("violations", [])},
                    f"Email to {i['company']}",
                    on_sent=lambda m, n=item_id: self._set(n, status="sent", **m))

    def _replied(self, item_id):
        """A reply turns into a pipeline entry, so it is tracked with the rest."""
        from core.outreach import Outreach
        from core.pipeline import Pipeline
        i = Outreach().get(item_id)
        country = {"Japan": "JP", "France": "FR"}.get(i["place"].split(",")[-1].strip(), "ANY")
        app = Pipeline().add(company=i["company"], role=f"Speculative ({i['track']})", channel="company",
                             country=country, stage="screening", url=i["contact_url"],
                             on=i.get("sent_on"), contact=i.get("to") or i["contact"], language=i["language"],
                             notes=f"Outreach email sent {i.get('sent_on')}: {i['why']}")
        self._set(item_id, status="replied", pipeline_id=app["id"])
        self._page.show_dialog(ft.SnackBar(content=ft.Text(f"Added to the pipeline as #{app['id']}.")))
