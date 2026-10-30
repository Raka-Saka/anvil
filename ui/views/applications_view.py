"""
Applications - every application as a card on a board: Ready to send, Sent, They replied, Interview, Closed.

Drag a card when something happens (or use the buttons in its side panel). Moving it sets the follow-up
date, starts the interview brief, or closes it; Anvil never sends anything itself.
Companies to email (speculative applications) open from the strip under the board.
"""

import asyncio
import os
import webbrowser
from datetime import date, timedelta
from pathlib import Path

import flet as ft
from core.pipeline import Pipeline, load_channels, channel_name, today
from ..theme import Colors, text
from ..tasks import TASKS
from ..components import open_path, mail_dialog
from .today_view import primary_button, quiet_button

PANEL_W = 460
COLUMNS = [
    ("ready", "Ready to send", ["found"], "found"),
    ("sent", "Sent", ["applied"], "applied"),
    ("replied", "They replied", ["screening"], "screening"),
    ("interview", "Interview", ["interview", "offer"], "interview"),
    ("closed", "Closed", ["rejected", "withdrawn", "ghosted"], None),
]
EMPTY = {
    "ready": "Apply to an offer and its CV and letter appear here.",
    "sent": "Nothing out yet.",
    "replied": "When someone answers, drag the card here. Your interview brief starts straight away.",
    "interview": "",
    "closed": "No answer after 30 days moves here by itself.",
}
COUNTRIES = [("JP", "Japan"), ("FR", "France"), ("ANY", "Elsewhere / remote")]


def _fmt(d):
    try:
        return date.fromisoformat(d).strftime("%d %b")
    except (TypeError, ValueError):
        return d or ""


class ApplicationsView(ft.Column):
    def __init__(self, page: ft.Page, outreach_view):
        self._page = page
        self.outreach_view = outreach_view
        self.selected = None
        self.prepping = set()         # interview briefs running
        self.drafting = set()         # follow-up drafts running
        from generators.application import BUSY
        self.busy = BUSY              # CV + letter running (shared with Offers)
        self.finding = set()          # phone numbers being looked up
        self.answering = set()        # answer kits being written
        self.search = ft.TextField(hint_text="Search company, agency or job", prefix_icon=ft.Icons.SEARCH,
                                   width=280, text_size=14, border_radius=12, dense=True,
                                   on_change=lambda e: self.refresh())

        self.board = ft.Row(spacing=12, vertical_alignment=ft.CrossAxisAlignment.STRETCH)
        self.panel_body = ft.Column(spacing=14, scroll=ft.ScrollMode.AUTO, expand=True)
        self.panel = ft.Container(content=self.panel_body, width=PANEL_W, visible=False, bgcolor=Colors.BG_SECONDARY,
                                  right=0, top=0, bottom=0,
                                  border_radius=16, border=ft.border.all(1, Colors.BORDER),
                                  shadow=ft.BoxShadow(blur_radius=24, color="#1A262321", offset=ft.Offset(0, 6)))
        self.strip = ft.Container()
        self.board_area = ft.Column([
            # the panel slides over the board's right side instead of squeezing five columns
            ft.Stack([ft.Container(self.board, left=0, right=0, top=0, bottom=0), self.panel], expand=True),
            self.strip,
        ], expand=True, spacing=12)
        self.back = ft.TextButton("← Back to the board", on_click=lambda e: self.show_board())
        self.body = ft.Container(self.board_area, expand=True)

        super().__init__(
            controls=[
                ft.Row([text("Applications", "title"),
                        text("Drag a card when something happens. Follow-ups are set for you.", "secondary"),
                        ft.Container(expand=True),
                        self.search,
                        quiet_button("Who called?", lambda e: self._who_called_dialog(), ft.Icons.PHONE_CALLBACK),
                        quiet_button("Add one I sent elsewhere", lambda e: self._add_dialog(), ft.Icons.ADD)],
                       spacing=16, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                self.body,
            ],
            spacing=16, expand=True,
        )
        TASKS.listen(lambda: None)
        self.refresh(update=False)
        from core.phones import missing
        if missing():                 # each open application gets its employer's numbers, once
            page.run_task(self.find_phones, missing())

    # ===== board =========================================================================

    @staticmethod
    def _offer_summary(a) -> str:
        """The researched employer summary (names the agency in English, e.g. Hays for ヘイズ)."""
        from core.offers import OfferLibrary
        oid = (a.get("fit") or {}).get("offer_id")
        o = OfferLibrary().get(oid) if oid else None
        return ((o or {}).get("company_info") or {}).get("summary", "")

    def _matches(self, a) -> bool:
        """Search box: every word must appear in the company, job, notes, channel or posting."""
        import unicodedata
        q = unicodedata.normalize("NFKC", self.search.value or "").lower().split()
        if not q:
            return True
        hay = unicodedata.normalize("NFKC", " ".join(
            [a["company"], a["role"], a.get("notes") or "", channel_name(a.get("channel")),
             (a.get("description") or "")[:1500], *[p["label"] for p in a.get("phones") or []],
             self._offer_summary(a)])).lower()
        return all(w in hay for w in q)

    def refresh(self, update=True):
        pipe = Pipeline()
        pipe.mark_ghosted()
        apps = Pipeline().apps
        due = {a["id"] for a in pipe.due()}
        cols = []
        for key, title, stages, _ in COLUMNS:
            items = [a for a in apps if a["stage"] in stages and self._matches(a)]
            items.sort(key=lambda a: a["history"][-1]["on"], reverse=True)
            if key == "closed":
                items = items[:12]
            cards = [ft.Draggable(group="app", content=self._card(a, a["id"] in due), data=a["id"],
                                  content_feedback=ft.Container(self._card(a, False), width=220, opacity=0.9))
                     for a in items]
            if not items and EMPTY[key]:
                cards = [text(EMPTY[key], "caption")]
            column = ft.Container(
                content=ft.Column([text(f"{title}  {len(items) if items else ''}".strip(), "strong"), *cards],
                                  spacing=10, scroll=ft.ScrollMode.AUTO,
                                  horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
                bgcolor=Colors.BG_TERTIARY, border_radius=12, padding=12, expand=True)
            cols.append(ft.Container(ft.DragTarget(group="app", content=column, data=key,
                                                   on_accept=lambda e, k=key: self._dropped(e.src.data if e.src else None, k)),
                                     expand=True))
        self.board.controls = cols

        from core.outreach import Outreach
        out = Outreach().items
        todo = [i for i in out if i["status"] in ("target", "drafted")]
        waiting = [i for i in out if i["status"] == "sent"]
        names = " · ".join(i["company"].split(" (")[0] for i in todo[:4]) or "none yet"
        self.strip.content = ft.Container(ft.Row([
            ft.Column([text("Companies to email (not posting)", "strong"),
                       text(f"{len(todo)} to write: {names}" + (f" · {len(waiting)} waiting for a reply" if waiting else ""),
                            "secondary")], spacing=2, expand=True),
            quiet_button("Open", lambda e: self.show_outreach()),
        ]), bgcolor=Colors.BG_SECONDARY, border=ft.border.all(1, Colors.BORDER), border_radius=12,
            padding=ft.padding.symmetric(horizontal=18, vertical=12))

        if self.selected:
            self._fill_panel(self.selected)
        if update:
            self._page.update()

    def _card(self, a, due):
        pack = a.get("pack") or {}
        stage = a["stage"]
        if stage == "found":
            if a["id"] in self.busy:
                status, color = "Writing your CV and letter…", Colors.ACCENT
            elif pack:
                status, color = f"CV + {pack.get('letter_kind', 'letter').lower()} ready", Colors.ACCENT
            else:
                status, color = "No CV or letter yet", Colors.TEXT_SECONDARY
        elif stage == "applied":
            status = f"Sent {_fmt(a.get('applied_on'))}"
            if a.get("next_due"):
                status += f" · follow up {_fmt(a['next_due'])}"
            color = Colors.WARNING if due else Colors.TEXT_SECONDARY
            if due:
                status = "⏰ Follow-up due · " + status
        elif stage in ("screening", "interview", "offer"):
            status = a.get("next_action") or stage.capitalize()
            color = Colors.WARNING if due else Colors.TEXT_SECONDARY
        else:
            status = {"rejected": "They said no", "withdrawn": "You withdrew", "ghosted": "No answer"}.get(stage, stage)
            color = Colors.TEXT_MUTED
        selected = a["id"] == self.selected
        return ft.Container(
            content=ft.Column([
                text(a["role"], "strong", max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                text(a["company"].split(" (")[0], "secondary", max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                text(status, "caption", color=color),
            ], spacing=2),
            bgcolor=Colors.BG_SECONDARY, border_radius=10, padding=12,
            border=ft.border.all(2 if selected else 1, Colors.ACCENT if selected else Colors.BORDER),
            ink=True, on_click=lambda e, i=a["id"]: self.open_app(i),
        )

    def _dropped(self, app_id, column):
        if not app_id:
            return
        target = next(c for c in COLUMNS if c[0] == column)
        a = Pipeline().get(app_id)
        if not a or a["stage"] in target[2]:
            return
        if column == "closed":
            self._close_dialog(app_id)
        else:
            self.move(app_id, target[3])

    # ===== moving =======================================================================

    def move(self, app_id, stage):
        before = Pipeline().get(app_id)
        Pipeline().move(app_id, stage)
        if stage in ("screening", "interview") and not (before or {}).get("interview_prep"):
            self._page.run_task(self.interview_brief, app_id)
        self.refresh()

    def _close_dialog(self, app_id):
        choice = ft.RadioGroup(value="rejected", content=ft.Column([
            ft.Radio(value="rejected", label="They said no"),
            ft.Radio(value="withdrawn", label="I withdrew"),
            ft.Radio(value="ghosted", label="No answer")], spacing=0))

        def done(e):
            self._page.pop_dialog()
            self.move(app_id, choice.value)

        self._page.show_dialog(ft.AlertDialog(
            title=text("Close this application", "title"), content=ft.Column([choice], tight=True, width=360),
            actions=[ft.TextButton("Cancel", on_click=lambda e: self._page.pop_dialog()),
                     primary_button("Close it", done)]))

    # ===== side panel ===================================================================

    def open_app(self, app_id):
        self.selected = app_id
        self.panel.visible = True
        self.show_board(update=False)
        self.refresh()

    def close_panel(self, e=None):
        self.selected = None
        self.panel.visible = False
        self.refresh()

    def focus_item(self, app_id=None, outreach_id=None, answer=None, **_):
        if app_id:
            self.open_app(app_id)
            if answer and app_id not in self.answering:
                self._page.run_task(self.answer_mail, app_id, answer)
        elif outreach_id:
            self.show_outreach()
            i = __import__("core.outreach", fromlist=["Outreach"]).Outreach().get(outreach_id)
            if i and i.get("body"):
                self.outreach_view._open_mail(outreach_id)

    def _section(self, title, *controls):
        return ft.Column([text(title, "strong"), *controls], spacing=4)

    def _fill_panel(self, app_id):
        a = Pipeline().get(app_id)
        if not a:
            self.selected = None
            self.panel.visible = False
            return
        pack = a.get("pack") or {}
        stage = a["stage"]
        # the salary from the offer (posted, or Anvil's estimate), as shown in Offers
        from core.offers import OfferLibrary, salary_text
        fit = a.get("fit") or {}
        offer = OfferLibrary().get(fit["offer_id"]) if fit.get("offer_id") else None
        salary = (offer or {}).get("salary") or fit.get("salary")
        net = ((offer or {}).get("company_info") or {}).get("net_monthly_eur")
        if net:
            from core.offers import fx_rates
            r = fx_rates()
            net = (f" · take-home about €{net:,.0f} / ${net * r.get('USD', 1.125):,.0f} / "
                   f"¥{net * r.get('JPY', 177.8):,.0f} a month")
        from core.offers import fx_note
        pay = [text(salary_text(salary) + (net or ""), "secondary"), text(fx_note(), "caption")] if salary else []
        head = ft.Row([
            ft.Column([text(a["role"], "title"),
                       text(f"{a['company']} · {dict(COUNTRIES).get(a.get('country'), a.get('country') or '')}",
                            "secondary"), *pay], spacing=2, expand=True),
            ft.IconButton(ft.Icons.CLOSE, tooltip="Close", icon_color=Colors.TEXT_SECONDARY, on_click=self.close_panel),
        ], vertical_alignment=ft.CrossAxisAlignment.START)

        acts = []
        i = a["id"]
        if stage == "found":
            acts.append(primary_button("I sent it", lambda e: self.move(i, "applied"), ft.Icons.SEND))
            if i in self.busy:
                acts.append(ft.Row([ft.ProgressRing(width=16, height=16, stroke_width=2, color=Colors.ACCENT),
                                    text("Writing your CV and letter…", "secondary")], spacing=8))
            elif a.get("url"):
                acts.append(quiet_button("Write it again" if pack else "Write my CV and letter",
                                         lambda e: self._page.run_task(self.write_pack, i), ft.Icons.AUTO_AWESOME))
        elif stage == "applied":
            acts.append(primary_button("They replied", lambda e: self.move(i, "screening")))
            acts.append(quiet_button("Write a follow-up", lambda e: self._page.run_task(self.follow_up, i),
                                     ft.Icons.EDIT_NOTE))
        elif stage == "screening":
            acts.append(primary_button("Interview booked", lambda e: self.move(i, "interview")))
        elif stage == "interview":
            acts.append(primary_button("They made an offer", lambda e: self.move(i, "offer")))
        if stage in ("screening", "interview", "offer"):
            if i in self.prepping:
                acts.append(ft.Row([ft.ProgressRing(width=16, height=16, stroke_width=2, color=Colors.ACCENT),
                                    text("Writing your interview brief…", "secondary")], spacing=8))
            else:
                acts.append(quiet_button("Write the interview brief again" if a.get("interview_prep")
                                         else "Interview brief", lambda e: self._page.run_task(self.interview_brief, i),
                                         ft.Icons.RECORD_VOICE_OVER))
        if stage in ("rejected", "withdrawn", "ghosted"):
            acts.append(quiet_button("Reopen", lambda e: self.move(i, "applied")))
        else:
            acts.append(ft.TextButton("Close it", on_click=lambda e: self._close_dialog(i),
                                      style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY)))

        parts = [head, ft.Row(acts, spacing=8, wrap=True, run_spacing=8)]

        if a.get("interview_prep") and Path(a["interview_prep"]["file"]).exists():
            parts.append(ft.Container(ft.Row([
                ft.Icon(ft.Icons.RECORD_VOICE_OVER, color=Colors.ACCENT),
                ft.Column([text("Your interview brief", "strong"),
                           text(f"Written {_fmt(a['interview_prep']['on'])}", "caption")], spacing=0, expand=True),
                quiet_button("Open", lambda e, p=a["interview_prep"]["file"]: open_path(p, self._page))]),
                bgcolor=Colors.ACCENT_SOFT, border_radius=12, padding=12))

        if pack:
            docs = [ft.TextButton(Path(d).name, icon=ft.Icons.DESCRIPTION, on_click=lambda e, d=d: open_path(d, self._page))
                    for d in a.get("documents", []) if Path(d).exists()]
            gloss = Path(pack["folder"]) / "letter_english.md"
            if gloss.exists():
                docs.append(ft.TextButton("Letter in English", icon=ft.Icons.TRANSLATE,
                                          on_click=lambda e, p=gloss: open_path(p, self._page)))
            docs.append(ft.TextButton("Folder", icon=ft.Icons.FOLDER_OPEN,
                                      on_click=lambda e, p=pack["folder"]: open_path(p, self._page)))
            parts.append(self._section(f"Your documents ({pack.get('letter_kind', 'letter')}, {a.get('language', '')})",
                                       ft.Row(docs, wrap=True, spacing=0)))
            if pack.get("how_to_apply"):
                how = [text(pack["how_to_apply"], "secondary", color=Colors.TEXT_PRIMARY)]
                if a.get("url"):
                    how.append(ft.TextButton("Open the posting", icon=ft.Icons.OPEN_IN_NEW,
                                             on_click=lambda e, u=a["url"]: webbrowser.open(u)))
                parts.append(self._section("How to apply", *how))
            if pack.get("violations"):
                parts.append(text("⚠ Check before sending: " + "; ".join(pack["violations"]), "secondary",
                                  color=Colors.ERROR))
            if pack.get("gaps"):
                parts.append(self._section("Not shown in your record",
                                           *[text(f"· {g}", "secondary", color=Colors.WARNING) for g in pack["gaps"]]))

        nxt = ft.TextField(label="Next step", value=a.get("next_action") or "", text_size=14, border_radius=10)
        due = ft.TextField(label="When (YYYY-MM-DD)", value=a.get("next_due") or "", width=170, text_size=14,
                           border_radius=10)
        parts.append(self._section("Next step", nxt, ft.Row([due, quiet_button(
            "Save", lambda e: self._save_next(i, nxt.value, due.value))], spacing=8)))

        links = []
        if a.get("url"):
            links.append(ft.TextButton("The posting", icon=ft.Icons.OPEN_IN_NEW,
                                       on_click=lambda e, u=a["url"]: webbrowser.open(u)))
        if links:
            parts.append(ft.Row(links, spacing=0))
        phones = [ft.Row([text(p["number"], "strong"), text(p["label"], "secondary", expand=True)], spacing=10)
                  for p in a.get("phones") or []]
        if i in self.finding:
            phones.append(ft.Row([ft.ProgressRing(width=14, height=14, stroke_width=2, color=Colors.ACCENT),
                                  text("Looking up their numbers…", "secondary")], spacing=8))
        else:
            if "phones" in a and not a["phones"]:
                phones.append(text("No official number found.", "secondary"))
            phones.append(ft.TextButton("Look again" if "phones" in a else "Find their numbers",
                                        icon=ft.Icons.PHONE,
                                        on_click=lambda e: self._page.run_task(self.find_phones, [i])))
        parts.append(self._section("Their phone numbers (any other caller may be a scam)", *phones))
        parts += self._answer_section(a)
        if a.get("mail_log"):
            parts.append(self._section("From your mail", *[text(l, "secondary") for l in a["mail_log"][-6:]]))
        hist = " → ".join(f"{h['stage']} {_fmt(h['on'])}" for h in a["history"])
        parts.append(text(f"{channel_name(a.get('channel'))} · {hist}", "caption"))
        parts.append(ft.TextButton("Delete this application", icon=ft.Icons.DELETE_OUTLINE,
                                   style=ft.ButtonStyle(color=Colors.TEXT_MUTED),
                                   on_click=lambda e: self._confirm_delete(i)))
        # SelectionArea: any text in the panel can be selected and copied (Ctrl+C)
        self.panel_body.controls = [ft.SelectionArea(ft.Container(ft.Column(parts, spacing=16), padding=22))]

    def _answer_section(self, a) -> list:
        """Their last e-mail that may need an answer, and the kit Anvil wrote for it."""
        from core import mail_watch
        from generators.reply import messages
        found = messages(a["id"])
        if not found:
            return []
        i, m = a["id"], found[0]
        kit = next((x for x in a.get("answers") or [] if x["msg"] == m["id"]), None)
        rows = [text(f"{m['date']} · {m['subject']}", "caption"), text(m["summary"], "secondary",
                                                                      color=Colors.TEXT_PRIMARY)]
        acts = [ft.TextButton("Open in Gmail", icon=ft.Icons.OPEN_IN_NEW,
                              on_click=lambda e: webbrowser.open(mail_watch.gmail_link(m)))]
        if i in self.answering:
            acts.insert(0, ft.Row([ft.ProgressRing(width=16, height=16, stroke_width=2, color=Colors.ACCENT),
                                   text("Preparing what they ask…", "secondary")], spacing=8))
        else:
            acts.insert(0, quiet_button("Prepare it again" if kit else "Prepare what they ask",
                                        lambda e: self._page.run_task(self.answer_mail, i, m["id"]),
                                        ft.Icons.AUTO_AWESOME))
        if kit and Path(kit["file"]).exists():
            files = [ft.TextButton(Path(f).name, icon=ft.Icons.DESCRIPTION,
                                   on_click=lambda e, f=f: open_path(f, self._page))
                     for f in kit["files"] if Path(f).exists()]
            rows.append(ft.Container(ft.Column([
                ft.Row([ft.Icon(ft.Icons.MARK_EMAIL_READ, color=Colors.ACCENT),
                        ft.Column([text("Your answer kit", "strong"),
                                   text(f"Written {_fmt(kit['on'])} · steps, documents"
                                        + (", reply" if kit.get("reply") else ""), "caption")],
                                  spacing=0, expand=True),
                        quiet_button("Open", lambda e, p=kit["file"]: open_path(p, self._page))]),
                ft.Row(files, wrap=True, spacing=0)] + ([ft.Row([ft.TextButton(
                    "Put the reply in Gmail drafts" + (" (files attached)" if kit["deliver"] == "email" else ""),
                    icon=ft.Icons.DRAFTS, on_click=lambda e: self._page.run_task(self.draft_reply, i, m["id"]))])]
                    if kit.get("reply") and mail_watch.can_sort() else []), spacing=4),
                bgcolor=Colors.ACCENT_SOFT, border_radius=12, padding=12))
            if kit.get("violations"):
                rows.append(text("⚠ Check before sending: " + "; ".join(kit["violations"]), "secondary",
                                 color=Colors.ERROR))
        return [self._section("Their e-mail", *rows, ft.Row(acts, spacing=8, wrap=True))]

    def _save_next(self, app_id, action, due):
        if due:
            try:
                date.fromisoformat(due)
            except ValueError:
                self._page.show_dialog(ft.SnackBar(ft.Text("The date must look like 2026-10-30.")))
                return
        Pipeline().set_next(app_id, action or "", due or None)
        self._page.show_dialog(ft.SnackBar(ft.Text("Saved.")))
        self.refresh()

    def _confirm_delete(self, app_id):
        def done(e):
            self._page.pop_dialog()
            Pipeline().delete(app_id)
            self.close_panel()

        self._page.show_dialog(ft.AlertDialog(
            title=text("Delete this application?", "title"),
            content=text("Its record goes; the CV and letter files stay in their folder.", "secondary"),
            actions=[ft.TextButton("Cancel", on_click=lambda e: self._page.pop_dialog()),
                     primary_button("Delete", done)]))

    # ===== long jobs ======================================================================

    async def write_pack(self, app_id):
        from generators.application import prepare
        a = Pipeline().get(app_id)
        self.busy.add(app_id)
        tid = TASKS.start(f"CV and letter for {a['company']}", "reading the posting and writing")
        self.refresh()
        try:
            await asyncio.to_thread(prepare, app_id)
            TASKS.finish(tid, "ready")
        except Exception as ex:
            TASKS.finish(tid, str(ex), ok=False)
            self._page.show_dialog(ft.SnackBar(ft.Text(f"Writing failed: {ex}")))
        finally:
            self.busy.discard(app_id)
            self.refresh()

    async def interview_brief(self, app_id):
        from generators.interview import prepare_interview
        a = Pipeline().get(app_id)
        self.prepping.add(app_id)
        tid = TASKS.start(f"Interview brief for {a['company']}", "researching the company")
        self.refresh()
        try:
            await asyncio.to_thread(prepare_interview, app_id)
            TASKS.finish(tid, "ready")
            self._page.show_dialog(ft.SnackBar(ft.Text(f"Your interview brief for {a['company']} is ready.")))
        except Exception as ex:
            TASKS.finish(tid, str(ex), ok=False)
        finally:
            self.prepping.discard(app_id)
            self.refresh()

    async def answer_mail(self, app_id, msg_id):
        from generators.reply import prepare_answer
        a = Pipeline().get(app_id)
        self.answering.add(app_id)
        tid = TASKS.start(f"Answer to {a['company']}", "reading their e-mail and writing")
        self.refresh()
        try:
            await asyncio.to_thread(prepare_answer, app_id, msg_id)
            TASKS.finish(tid, "ready")
            self._page.show_dialog(ft.SnackBar(ft.Text(f"Your answer to {a['company']} is ready.")))
        except Exception as ex:
            TASKS.finish(tid, str(ex), ok=False)
            self._page.show_dialog(ft.SnackBar(ft.Text(f"Preparing failed: {ex}")))
        finally:
            self.answering.discard(app_id)
            self.refresh()

    async def draft_reply(self, app_id, msg_id):
        from generators.reply import save_draft
        try:
            await asyncio.to_thread(save_draft, app_id, msg_id)
            msg = "The reply is in your Gmail drafts, in their thread. Check it and send it from Gmail."
        except Exception as ex:
            msg = f"The draft failed: {ex}"
        self._page.show_dialog(ft.SnackBar(ft.Text(msg)))

    async def find_phones(self, app_ids):
        from core.phones import find
        ids = [i for i in app_ids if i not in self.finding]
        if not ids:
            return
        self.finding.update(ids)
        tid = TASKS.start("Employers' phone numbers", f"0 of {len(ids)}")
        self.refresh()
        done = 0
        sem = asyncio.Semaphore(3)

        async def one(i):
            nonlocal done
            async with sem:
                try:
                    await asyncio.to_thread(find, i)
                except Exception:
                    pass
                finally:
                    done += 1
                    self.finding.discard(i)
                    TASKS.update(tid, f"{done} of {len(ids)}")
                    self.refresh()

        await asyncio.gather(*(one(i) for i in ids))
        TASKS.finish(tid, "done")

    def _who_called_dialog(self):
        number = ft.TextField(label="The number that called you", text_size=16, autofocus=True)
        result = ft.Column(spacing=6)
        busy = ft.ProgressRing(width=16, height=16, stroke_width=2, color=Colors.ACCENT, visible=False)

        async def check(e=None):
            from core.phones import who_called
            if not (number.value or "").strip():
                return
            busy.visible, result.controls = True, [text("Checking your applications, then the web…", "secondary")]
            self._page.update()
            try:
                r = await asyncio.to_thread(who_called, number.value)
            except Exception as ex:
                result.controls = [text(f"Could not check: {ex}", "secondary", color=Colors.ERROR)]
            else:
                if r["known"]:
                    result.controls = [text("✓ One of your applications", "strong", color=Colors.SUCCESS)] + [
                        text(f"{app['company']} · {app['role']} · {p['label']}", "secondary") for app, p in r["known"]]
                else:
                    color = {"employer": Colors.TEXT_PRIMARY, "scam_reports": Colors.ERROR}.get(r["verdict"],
                                                                                            Colors.WARNING)
                    head = {"employer": f"A company, not one you applied to: {r['who']}",
                            "scam_reports": "⚠ Reported as scam or spam",
                            "unknown": "Not one of your applications, and unknown on the web"}[r["verdict"]]
                    result.controls = [text(head, "strong", color=color), text(r["summary"], "secondary")] + [
                        text(s, "caption") for s in r["sources"][:3]]
            busy.visible = False
            self._page.update()

        number.on_submit = lambda e: self._page.run_task(check)
        self._page.show_dialog(ft.AlertDialog(
            title=text("Who called?", "title"),
            content=ft.SelectionArea(ft.Column(
                [text("Your applications' numbers are checked first. Unknown numbers are looked up on "
                      "number-report sites.", "secondary"), ft.Row([number, busy]), result],
                tight=True, spacing=12, width=520)),
            actions=[ft.TextButton("Check", on_click=lambda e: self._page.run_task(check)),
                     ft.TextButton("Close", on_click=lambda e: self._page.pop_dialog())]))

    async def follow_up(self, app_id):
        from core.outreach import draft_follow_up
        a0 = Pipeline().get(app_id)
        tid = TASKS.start(f"Follow-up email to {a0['company']}", "writing")
        try:
            a = await asyncio.to_thread(draft_follow_up, app_id)
            TASKS.finish(tid, "ready")
        except Exception as ex:
            TASKS.finish(tid, str(ex), ok=False)
            self._page.show_dialog(ft.SnackBar(ft.Text(f"Draft failed: {ex}")))
            return

        def sent(mail):
            Pipeline().update(app_id, notes=(a.get("notes") or "") + f"\nFollow-up sent {today()}.",
                              last_touch=today())
            Pipeline().set_next(app_id, "Second follow-up or close", (date.today() + timedelta(days=10)).isoformat())
            self.refresh()

        mail_dialog(self._page, a["follow_up_draft"], f"Follow-up: {a['role']} — {a['company']}", on_sent=sent)

    # ===== companies to email =============================================================

    def show_outreach(self):
        self.outreach_view.refresh(update=False)
        self.body.content = ft.Column([self.back, self.outreach_view], expand=True, spacing=4)
        self._page.update()

    def show_board(self, update=True):
        self.body.content = self.board_area
        if update:
            self._page.update()

    # ===== add one by hand ================================================================

    def _add_dialog(self):
        channels = load_channels()
        company = ft.TextField(label="Company", text_size=14)
        role = ft.TextField(label="Job", text_size=14)
        url = ft.TextField(label="Link (optional)", text_size=14)
        country = ft.Dropdown(label="Country", value="JP", options=[ft.dropdown.Option(k, v) for k, v in COUNTRIES])
        channel = ft.Dropdown(label="Where you applied", text_size=14)
        when = ft.TextField(label="Date sent", value=today(), width=160, text_size=14)

        def fill(c):
            opts = [ch for ch in channels if ch["country"] in (c, "ANY")]
            channel.options = [ft.dropdown.Option(ch["id"], ch["name"]) for ch in opts]
            channel.value = opts[0]["id"] if opts else None

        fill("JP")
        country.on_select = lambda e: (fill(e.control.value), self._page.update())

        def done(e):
            if not (company.value and role.value):
                return
            try:
                date.fromisoformat(when.value)
            except ValueError:
                return
            Pipeline().add(company=company.value.strip(), role=role.value.strip(), channel=channel.value or "other",
                           country=country.value, stage="applied", on=when.value, url=(url.value or "").strip())
            self._page.pop_dialog()
            self.refresh()

        self._page.show_dialog(ft.AlertDialog(
            title=text("Add an application you sent elsewhere", "title"),
            content=ft.Column([company, role, ft.Row([country, channel], spacing=8), url, when], tight=True,
                              spacing=10, width=480),
            actions=[ft.TextButton("Cancel", on_click=lambda e: self._page.pop_dialog()),
                     primary_button("Add", done)]))
