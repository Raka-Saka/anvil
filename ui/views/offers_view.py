"""
Offers - the job offers Anvil found, ranked: CV fit, then his places, then the money left each month.

- Cards show the decision at a glance: title, place, money left per month, fit, one or two tags.
- Clicking a card opens the side panel: why it fits, the monthly budget, employer, contract, links,
  and the one main action: "Apply: write my CV and letter".
- "Compare" shows the same offers as a table.
- The criteria (places, savings goal, home, household, facts) open in the same side panel.
Searches and research run in the background (ui/tasks.py), whichever screen he is on.
"""

import asyncio
import time
import webbrowser

import flet as ft
from ..theme import Colors, text
from ..tasks import TASKS, NAV
from .today_view import primary_button, quiet_button

PANEL_W = 460
PRESETS = [
    ("Fits my CVs", ""),
    ("French CS team leader", "customer service team leader, French-speaking"),
    ("Support client FR", "conseiller support client francophone"),
    ("Technical support", "technical support / escalation specialist, English or French"),
    ("French-speaking support", "French-speaking customer support"),
    ("Python developer", "Python / Django developer"),
    ("Factory work (Japan)", "factory, manufacturing or light work in Osaka (製造, 工場, 軽作業), 外国人歓迎"),
]


def fit_label(m) -> str:
    if m is None:
        return "Fit unknown"
    return ("Strong fit" if m >= 80 else "Good fit" if m >= 60 else "Related" if m >= 45 else "Stretch") + f" · {m}"


def chip(label, fg=Colors.TEXT_SECONDARY, bg=Colors.BG_TERTIARY):
    return ft.Container(content=ft.Text(label, size=13, color=fg), bgcolor=bg, border_radius=12,
                        padding=ft.padding.symmetric(horizontal=10, vertical=2))


def to_pipeline(offer_id: int):
    """Put an offer in the pipeline (stage 'found'); returns the new id."""
    from core.offers import OfferLibrary
    from core.pipeline import Pipeline, load_channels
    lib = OfferLibrary()
    o = lib.get(offer_id)
    if not o:
        return None
    loc = (o.get("location") or "").lower()
    country = "JP" if any(k in loc for k in ("japan", "osaka", "tokyo", "日本", "大阪")) else \
              "FR" if "france" in loc else "ANY"
    src = " ".join(l.get("source", "") for l in o["links"]).lower()
    channel = next((c["id"] for c in load_channels()
                    if c["country"] in (country, "ANY") and c["name"].split(" (")[0].lower() in src), "other")
    app = Pipeline().add(
        company=o["company"], role=o["title"], channel=channel, country=country, stage="found",
        url=o["links"][0]["url"], notes=f"Found by web search on {src or 'the web'}. {o.get('fit', '')}",
        description=o.get("posting_text", ""),
        fit={"match": o.get("match"), "salary": o.get("salary"), "seniority": o.get("seniority"), "offer_id": offer_id},
    )
    lib.set_status(offer_id, "applied", pipeline_id=app["id"])
    return app["id"]


class OffersView(ft.Column):
    def __init__(self, page: ft.Page):
        self._page = page
        self.selected = None              # offer id in the panel
        self.panel_mode = None            # "offer" | "criteria" | None
        self.searching = False
        self.investigating = set()
        self.preparing = set()
        self.last_new = set()

        # Header
        self.criteria_btn = ft.OutlinedButton(
            "", on_click=lambda e: self.open_criteria(),
            style=ft.ButtonStyle(color=Colors.TEXT_PRIMARY, side=ft.BorderSide(1, Colors.BORDER),
                                 shape=ft.RoundedRectangleBorder(radius=20), bgcolor=Colors.BG_SECONDARY))
        self.query = ft.TextField(hint_text="What job? Leave empty for jobs that fit your CVs", expand=True,
                                  text_size=15, border_radius=12, border_color=Colors.BORDER, filled=True,
                                  fill_color=Colors.BG_SECONDARY, on_submit=lambda e: self._page.run_task(self.search))
        from analyzers.web_search import REGIONS
        self.region = ft.Dropdown(value="wishes", width=170, text_size=14, border_radius=12, border_color=Colors.BORDER,
                                  filled=True, fill_color=Colors.BG_SECONDARY,
                                  options=[ft.dropdown.Option(k, "My places" if k == "wishes" else k.capitalize())
                                           for k in REGIONS])
        self.search_btn = primary_button("Search", lambda e: self._page.run_task(self.search), ft.Icons.TRAVEL_EXPLORE)
        self.presets = ft.Row([ft.TextButton(label, on_click=lambda e, q=q: self._preset(q),
                                             style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY))
                               for label, q in PRESETS], spacing=0, wrap=True)
        self.status = text("", "secondary")
        from analyzers.web_search import BROWSE_JAPAN
        self.browse = ft.Row(
            [text("Japan sites Anvil cannot read, browse them yourself:", "caption")] +
            [ft.TextButton(name, on_click=lambda e, u=u: webbrowser.open(u),
                           style=ft.ButtonStyle(color=Colors.ACCENT, padding=ft.padding.symmetric(horizontal=6)))
             for name, u in BROWSE_JAPAN] +
            [quiet_button("Add an offer", lambda e: self._add_dialog(), ft.Icons.ADD)],
            spacing=0, wrap=True, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        # Views of the list
        self.mode = ft.SegmentedButton(segments=[ft.Segment(value="cards", label="Cards"),
                                                 ft.Segment(value="compare", label="Compare")],
                                       selected=["cards"], show_selected_icon=False,
                                       on_change=lambda e: self.refresh())
        self.show = ft.SegmentedButton(segments=[ft.Segment(value="week", label="This week"),
                                                 ft.Segment(value="new", label="Not opened"),
                                                 ft.Segment(value="dismissed", label="Turned down")],
                                       selected=["week"], show_selected_icon=False,
                                       on_change=lambda e: self.refresh())
        self.count = text("", "secondary")
        self.order = ft.Dropdown(value="best", width=200, text_size=14, border_radius=12, border_color=Colors.BORDER,
                                 filled=True, fill_color=Colors.BG_SECONDARY, label="Order by",
                                 options=[ft.dropdown.Option(k, v) for k, v in self.ORDERS.items()])
        self.order.on_select = lambda e: self.refresh()
        self.list = ft.ListView(spacing=10, expand=True, padding=ft.padding.only(right=8, bottom=24))
        self.panel_body = ft.Column(spacing=14, scroll=ft.ScrollMode.AUTO, expand=True)
        self.panel = ft.Container(
            content=self.panel_body, width=PANEL_W, visible=False, bgcolor=Colors.BG_SECONDARY, border_radius=16,
            border=ft.border.all(1, Colors.BORDER), padding=0, clip_behavior=ft.ClipBehavior.HARD_EDGE,
            animate_opacity=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            shadow=ft.BoxShadow(blur_radius=24, color="#1A262321", offset=ft.Offset(0, 6)),
        )

        super().__init__(
            controls=[
                ft.Row([text("Offers", "title"), self.criteria_btn], spacing=16,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row([self.query, self.region, self.search_btn], spacing=10),
                self.presets,
                self.browse,
                self.status,
                ft.Row([self.mode, self.show, self.order, self.count], spacing=16, wrap=True,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row([ft.Container(self.list, expand=True), self.panel], expand=True, spacing=16,
                       vertical_alignment=ft.CrossAxisAlignment.STRETCH),
            ],
            spacing=12, expand=True,
        )
        self._update_criteria_chip()
        self.refresh(update=False)
        from ..tasks import HOOKS
        HOOKS["investigate"] = lambda ids: self._page.run_task(self.investigate, ids)
        HOOKS["offers_refresh"] = self.refresh

    # ===== list ========================================================================

    def _offers(self):
        from core.offers import OfferLibrary, in_pipeline
        lib = OfferLibrary()
        mode = self.show.selected[0]
        # an application closed in Applications (they said no, you withdrew, no answer) counts as turned down
        def closed(o):
            app = in_pipeline(o) if o["status"] == "applied" else None
            return bool(app) and app["stage"] in ("rejected", "withdrawn", "ghosted")

        if mode == "dismissed":
            offers = [o for o in lib.current(include_dismissed=True) if o["status"] == "dismissed" or closed(o)]
        else:
            offers = [o for o in lib.current() if o["status"] != "applied" and not in_pipeline(o)]
            if mode == "new":
                offers = [o for o in offers if o["status"] == "new"]
        self._order(offers)
        offers.sort(key=lambda o: o["id"] not in self.last_new)    # stable: keeps the chosen order
        return offers

    ORDERS = {"best": "Best overall", "fit_money": "Fit and money", "fit": "Fit", "money": "Left / month",
              "newest": "Newest", "company": "Company"}

    def _order(self, offers):
        """Sort in place. "best" is the library order (fit > your places > money).
        "fit_money": half CV fit, half money left, each scaled 0-100 over the offers shown."""
        from analyzers.investigate import budget
        from core.offers import japanese_too_high
        how = self.order.value or "best"
        left = {o["id"]: (budget(o) or {}).get("left") for o in offers}
        known = [v for v in left.values() if v is not None]
        lo, hi = (min(known), max(known)) if known else (0, 1)

        def money(o):
            v = left[o["id"]]
            return 0 if v is None else 100 * (v - lo) / ((hi - lo) or 1)

        if how == "fit_money":
            offers.sort(key=lambda o: -((o.get("match") or 0) + money(o)) / 2)
        elif how == "fit":
            offers.sort(key=lambda o: -(o.get("match") or 0))
        elif how == "money":
            offers.sort(key=lambda o: -(left[o["id"]] if left[o["id"]] is not None else -1e9))
        elif how == "newest":
            offers.sort(key=lambda o: o.get("posted") or o.get("first_seen") or "", reverse=True)
        elif how == "company":
            offers.sort(key=lambda o: o["company"].lower())
        offers.sort(key=japanese_too_high)          # jobs needing N3+ go last, whatever the order

    def _set_order(self, key):
        self.order.value = key
        self.refresh()

    def refresh(self, update=True):
        offers = self._offers()
        self.count.value = f"{len(offers)} offer{'s' if len(offers) != 1 else ''}"
        if self.mode.selected[0] == "compare":
            self.list.controls = [self._table(offers)] if offers else [self._empty()]
        else:
            self.list.controls = [self._card(o) for o in offers] or [self._empty()]
        if self.panel_mode == "offer" and self.selected:
            self._fill_offer_panel(self.selected)
        if update:
            self._page.update()

    def _empty(self):
        msg = {"dismissed": "Nothing turned down this week.", "new": "You have opened every offer."}.get(
            self.show.selected[0], "No offers this week yet. Search above: empty box = jobs that fit your CVs.")
        return ft.Container(text(msg, "secondary"), padding=24)

    def _money(self, o):
        """(big text, small text, colour) for the money column."""
        from analyzers.investigate import budget
        if o["id"] in self.investigating:
            return "…", "researching costs", Colors.TEXT_MUTED
        b = budget(o)
        if not b:
            return "–", "costs not researched", Colors.TEXT_MUTED
        left = b["left"]
        color = Colors.SUCCESS if b["meets"] else Colors.TEXT_PRIMARY if left >= 0 else Colors.ERROR
        return (f"+€{left:,.0f}" if left >= 0 else f"−€{abs(left):,.0f}"), \
               ("left each month" if left >= 0 else "short each month"), color

    def _tags(self, o):
        """At most two: the kind of job, and the worst concern."""
        from core.offers import in_pipeline
        info = o.get("company_info") or {}
        c = info.get("contract") or {}
        tags = []
        if info.get("remote"):
            tags.append(chip("Remote"))
        elif c.get("local_term"):
            tags.append(chip(c["local_term"].split("(")[0].strip()[:28]))
        app = in_pipeline(o)
        if app:
            tags.append(chip(f"In Applications · {app['stage']}", Colors.ACCENT, Colors.ACCENT_SOFT))
        elif info.get("japanese_required") in ("N3", "N2", "N1"):
            tags.append(chip(f"⚠ Needs Japanese {info['japanese_required']}", Colors.ERROR, Colors.ERROR_SOFT))
        elif info.get("red_flags"):
            tags.append(chip(f"⚠ {info['red_flags'][0][:40]}", Colors.ERROR, Colors.ERROR_SOFT))
        elif o.get("work_rights") == "unclear" or info.get("feasibility") == "no":
            tags.append(chip("⚠ Right to work unclear", Colors.WARNING, Colors.WARNING_SOFT))
        elif info.get("employer_is_agency"):
            tags.append(chip("Agency", Colors.WARNING, Colors.WARNING_SOFT))
        if o.get("reject_reason"):
            from core.wishes import REJECT_REASONS
            tags.append(chip(REJECT_REASONS.get(o["reject_reason"], o["reject_reason"])))
        return tags[:2]

    def _fit_bar(self, m):
        w = 120 * max(0, min(m or 0, 100)) / 100
        color = Colors.ACCENT if (m or 0) >= 60 else "#9A8F84"
        return ft.Row([ft.Container(content=ft.Container(width=w, height=6, bgcolor=color, border_radius=3),
                                    width=120, height=6, bgcolor=Colors.BG_TERTIARY, border_radius=3,
                                    alignment=ft.Alignment.CENTER_LEFT),
                       text(fit_label(m), "secondary", color=Colors.TEXT_PRIMARY)], spacing=10)

    def _card(self, o):
        from core.offers import OfferLibrary, in_pipeline
        big, small, color = self._money(o)
        age = OfferLibrary().age_days(o)
        when = f"posted {age} day{'s' if age != 1 else ''} ago" if o.get("posted") else "date unclear"
        if age == 0 and o.get("posted"):
            when = "posted today"
        place = (o.get("company_info") or {}).get("city") or o.get("location", "")
        is_new = o["status"] == "new"
        selected = o["id"] == self.selected and self.panel_mode == "offer"
        title_row = [ft.Container(text(o["title"], "strong", max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                                  expand=True)]
        if o["status"] in ("new", "seen") and o["id"] not in self.preparing and not in_pipeline(o):
            # first triage straight from the list: no need to open the panel
            title_row.append(ft.IconButton(ft.Icons.CLOSE, icon_size=18, icon_color=Colors.TEXT_MUTED,
                                           tooltip="Not for me", width=32, height=32, padding=0,
                                           on_click=lambda e, i=o["id"]: self._turn_down(i)))
        if is_new:
            title_row.insert(0, ft.Container(width=8, height=8, bgcolor=Colors.ACCENT, border_radius=4,
                                             tooltip="Not opened yet"))
        busy = []
        if o["id"] in self.preparing:
            busy = [ft.Row([ft.ProgressRing(width=14, height=14, stroke_width=2, color=Colors.ACCENT),
                            text("Writing your CV and letter…", "secondary")], spacing=8)]
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Column([ft.Row(title_row, spacing=8), text(f"{o['company']} · {place} · {when}", "secondary",
                                                                   max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)],
                              spacing=2, expand=True),
                    ft.Column([ft.Text(big, size=20, font_family="Plex SemiBold", color=color),
                               text(small, "caption")], spacing=0,
                              horizontal_alignment=ft.CrossAxisAlignment.END),
                ], vertical_alignment=ft.CrossAxisAlignment.START, spacing=12),
                ft.Row([self._fit_bar(o.get("match")), *self._tags(o)], spacing=10, wrap=True),
                *busy,
            ], spacing=8),
            bgcolor=Colors.BG_SECONDARY, border_radius=12, padding=ft.padding.symmetric(horizontal=18, vertical=14),
            border=ft.border.all(2 if selected else 1, Colors.ACCENT if selected else Colors.BORDER),
            ink=True, on_click=lambda e, i=o["id"]: self.open_offer(i),
        )

    def _table(self, offers):
        from analyzers.investigate import budget
        rows = []
        for o in offers:
            b = budget(o)
            info = o.get("company_info") or {}
            concern = (info.get("red_flags") or [""])[0] or (
                "Agency" if info.get("employer_is_agency") else "")
            jp = info.get("japanese_required") or "–"
            jp_cell = ft.DataCell(ft.Text(jp, color=Colors.ERROR if jp in ("N3", "N2", "N1") else Colors.TEXT_PRIMARY,
                                          tooltip=info.get("japanese_note") or None))
            left = "–" if not b else (f"+€{b['left']:,.0f}" if b["left"] >= 0 else f"−€{abs(b['left']):,.0f}")
            rows.append(ft.DataRow(
                cells=[ft.DataCell(ft.Text(str(o.get("match") or "–"))),
                       ft.DataCell(ft.Text(o["title"][:48], max_lines=1)),
                       ft.DataCell(ft.Text(o["company"][:28], max_lines=1)),
                       ft.DataCell(ft.Text((info.get("city") or o.get("location", ""))[:22], max_lines=1)),
                       ft.DataCell(ft.Text(left, color=(Colors.ERROR if b and b["left"] < 0 else Colors.TEXT_PRIMARY))),
                       jp_cell,
                       ft.DataCell(ft.Text(((info.get("contract") or {}).get("local_term") or "")[:20])),
                       ft.DataCell(ft.Text((concern[:34] + "…") if len(concern) > 34 else concern, color=Colors.ERROR if concern else Colors.TEXT_PRIMARY))],
                on_select_change=lambda e, i=o["id"]: self.open_offer(i),
            ))
        return ft.Container(ft.DataTable(
            columns=[ft.DataColumn(ft.Text(c), on_sort=(lambda e, k=k: self._set_order(k)) if k else None,
                                   tooltip="Click to order by this" if k else None)
                     for c, k in (("Fit", "fit"), ("Job", None), ("Company", "company"), ("Place", None),
                                  ("Left / month", "money"), ("Japanese", None), ("Contract", None),
                                  ("Concern", None))],
            rows=rows, heading_text_style=ft.TextStyle(size=13, color=Colors.TEXT_SECONDARY),
            data_text_style=ft.TextStyle(size=14, color=Colors.TEXT_PRIMARY), column_spacing=26,
            show_checkbox_column=False), bgcolor=Colors.BG_SECONDARY, border_radius=12,
            border=ft.border.all(1, Colors.BORDER), padding=8)

    # ===== side panel ==================================================================

    def _open_panel(self):
        self.panel.visible = True

    def close_panel(self, e=None):
        self.panel.visible = False
        self.panel_mode = None
        self.selected = None
        self.refresh()

    def open_offer(self, offer_id):
        from core.offers import OfferLibrary
        lib = OfferLibrary()
        o = lib.get(offer_id)
        if o and o["status"] == "new":
            lib.set_status(offer_id, "seen")
        self.selected, self.panel_mode = offer_id, "offer"
        self._open_panel()
        self.refresh()

    def focus_item(self, offer_id=None, criteria=False, **_):
        if offer_id:
            self.open_offer(offer_id)
        elif criteria:
            self.open_criteria()

    def _section(self, title, *controls):
        return ft.Column([text(title, "strong"), *controls], spacing=4)

    def _fill_offer_panel(self, offer_id):
        from core.offers import OfferLibrary, salary_text, in_pipeline, fx_rates, fx_note
        from analyzers.investigate import budget
        o = OfferLibrary().get(offer_id)
        if not o:
            self.panel_body.controls = []
            return
        info = o.get("company_info") or {}
        app = in_pipeline(o)
        jpy = fx_rates().get("JPY", 177.8)

        head = ft.Row([
            ft.Column([text(o["title"], "title"), text(f"{o['company']} · {o.get('location', '')}", "secondary"),
                       text(salary_text(o.get("salary")), "secondary"),
                       text(fx_note(), "caption")],
                      spacing=2, expand=True),
            ft.IconButton(ft.Icons.CLOSE, tooltip="Close", icon_color=Colors.TEXT_SECONDARY, on_click=self.close_panel),
        ], vertical_alignment=ft.CrossAxisAlignment.START)

        if app:
            act = [primary_button("Open in Applications", lambda e, i=app["id"]: NAV.go("applications", app_id=i))]
        elif o["id"] in self.preparing:
            act = [ft.Row([ft.ProgressRing(width=16, height=16, stroke_width=2, color=Colors.ACCENT),
                           text("Writing your CV and letter (1-3 min)…", "secondary")], spacing=8)]
        else:
            act = [primary_button("Apply: write my CV and letter",
                                  lambda e, i=o["id"]: self._page.run_task(self.select, i)),
                   quiet_button("Not for me", lambda e, i=o["id"]: self._turn_down(i))]
        if o["status"] == "dismissed":
            act = [quiet_button("Put it back", lambda e, i=o["id"]: self._restore(i))]

        parts = [head, ft.Row(act, spacing=8, wrap=True)]
        if o.get("fit"):
            parts.append(self._section("Why it fits", text(o["fit"], "secondary", color=Colors.TEXT_PRIMARY)))

        b = budget(o)
        if b:
            def line(label, value, strong=False, color=None):
                return ft.Row([text(label, "strong" if strong else "secondary",
                                    color=Colors.TEXT_PRIMARY if strong else None, expand=True),
                               text(value, "strong" if strong else "secondary", color=color)])
            lines = [line("Take-home pay", f"€{b['pay']:,.0f}")]
            if b.get("other_income"):
                lines.append(line("Other household income", f"€{b['other_income']:,.0f}"))
            lines.append(line("Your share of the house" if b.get("japan") else
                              "Home costs (owned)" if b.get("rent_label", "").startswith("home") else "Rent, 2 rooms",
                              f"−€{b['rent']:,.0f}"))
            if b.get("kept_home"):
                lines.append(line(f"Keeping the {b['home']} home", f"−€{b['kept_home']:,.0f}"))
            lines.append(line("Your own spending" if b.get("japan") else "Living costs", f"−€{b['living']:,.0f}"))
            if b["transport"]:
                lines.append(line("Transport", f"−€{b['transport']:,.0f}"))
            elif b.get("transport_how") == "commute paid by the employer":
                lines.append(line("Transport", "paid by the employer"))
            sign = "+" if b["left"] >= 0 else "−"
            lines.append(ft.Divider(height=1, color=Colors.BORDER))
            lines.append(line("Left each month", f"{sign}€{abs(b['left']):,.0f} · {sign}¥{abs(b['left']) * jpy:,.0f}",
                              strong=True, color=Colors.SUCCESS if b["meets"] else
                              (Colors.ERROR if b["left"] < 0 else Colors.TEXT_PRIMARY)))
            goal = (f"Meets your goal of saving €{b['target']:,.0f}." if b["meets"] else
                    f"€{b['target'] - b['left']:,.0f} short of your €{b['target']:,.0f} savings goal.")
            lines.append(text(goal, "caption", color=Colors.SUCCESS if b["meets"] else None))
            if b.get("no_car_problem"):
                lines.append(text("⚠ Hard to reach without a car, and you would have none at first.", "caption",
                                  color=Colors.WARNING))
            parts.append(ft.Container(ft.Column([text(f"Money each month in {b['city']}", "strong"), *lines],
                                                spacing=4),
                                      bgcolor=Colors.BG_PRIMARY, border_radius=12, padding=14))
            if b.get("community"):
                parts.append(self._section(f"Japanese community: {b['community']}",
                                           text(b.get("community_note", ""), "secondary")))
        elif o["id"] in self.investigating:
            parts.append(ft.Row([ft.ProgressRing(width=16, height=16, stroke_width=2, color=Colors.ACCENT),
                                 text("Researching the employer and the costs…", "secondary")], spacing=8))
        else:
            parts.append(quiet_button("Research the employer and costs",
                                      lambda e, i=o["id"]: self._page.run_task(self.investigate, [i]),
                                      ft.Icons.MANAGE_SEARCH))

        if info:
            emp = [text(f"{info['summary']} Size: {info['size']}. Rating: {info['rating']}.", "secondary",
                        color=Colors.TEXT_PRIMARY)]
            if info.get("employer_is_agency"):
                emp.append(text("Posted by an agency or outsourcer, hiring for a client.", "secondary",
                                color=Colors.WARNING))
            emp += [text(f"+ {p}", "secondary") for p in info.get("pros", [])]
            emp += [text(f"− {c}", "secondary") for c in info.get("cons", [])]
            emp += [text(f"⚠ {f}", "secondary", color=Colors.ERROR) for f in info.get("red_flags", [])]
            parts.append(self._section("Employer", *emp))
            c = info.get("contract")
            con = []
            if c:
                con.append(text(" · ".join(x for x in (c.get("local_term") or c["kind"], c.get("hours"),
                                                        f"trial {c['trial']}" if c.get("trial") and c["trial"] not in
                                                        ("unknown", "not stated") else "") if x),
                                "secondary", color=Colors.TEXT_PRIMARY))
                if c.get("benefits"):
                    con.append(text("Stated: " + ", ".join(c["benefits"]), "secondary"))
                if c.get("missing"):
                    con.append(text("Not mentioned: " + ", ".join(c["missing"]), "caption"))
                con += [text(f"⚠ {x}", "secondary", color=Colors.WARNING) for x in c.get("concerns", [])]
            if info.get("japanese_required") and info["japanese_required"] != "unknown":
                too = info["japanese_required"] in ("N3", "N2", "N1")
                con.append(text(f"Japanese asked: {info['japanese_required']}"
                                + (" (above your N4: likely refused)" if too else "")
                                + (f". {info['japanese_note']}" if info.get("japanese_note") else ""),
                                "secondary", color=Colors.ERROR if too else Colors.TEXT_PRIMARY))
            if info.get("feasibility"):
                where = f" From: {', '.join(info['remote_from'])}." if info.get("remote_from") else ""
                con.append(text(f"Can you take it? {info['feasibility'].upper()}. {info.get('feasibility_note', '')}"
                                f"{where}", "secondary",
                                color={"ok": Colors.SUCCESS, "no": Colors.ERROR}.get(info["feasibility"], Colors.WARNING)))
            if con:
                parts.append(self._section("Contract and place", *con))
            if info.get("net_note"):
                parts.append(text(f"How the pay was estimated: {info['net_note']}", "caption"))

        parts.append(self._section("Links", ft.Row(
            [ft.TextButton(l.get("source") or "posting", icon=ft.Icons.OPEN_IN_NEW,
                           on_click=lambda e, u=l["url"]: webbrowser.open(u)) for l in o["links"][:5]],
            wrap=True, spacing=0)))
        if o["links"] and o["links"][0].get("checked") is False:
            parts.append(text("This site blocks Anvil, so the posting could not be checked. Open it first: "
                              "it may have closed.", "caption", color=Colors.WARNING))
        if o.get("languages"):
            parts.append(text(f"Languages asked: {o['languages']}", "caption"))
        # SelectionArea: any text in the panel can be selected and copied (Ctrl+C)
        self.panel_body.controls = [ft.SelectionArea(ft.Container(ft.Column(parts, spacing=16), padding=22))]

    # ===== criteria (same panel) =======================================================

    def _criteria_text(self, w=None):
        from core import wishes
        w = w or wishes.load()
        places = " › ".join(p.split(",")[0] for p in w["places"][:4]) + ("…" if len(w["places"]) > 4 else "")
        car = "" if w.get("have_car") else ", no car"
        return f"{places} · save €{w['save_eur']:,.0f}/mo · {w['household']}{car}  ·  Change"

    def _update_criteria_chip(self):
        self.criteria_btn.content = self._criteria_text()

    def open_criteria(self):
        self.panel_mode, self.selected = "criteria", None
        self._fill_criteria()
        self._open_panel()
        self.refresh()

    def _fill_criteria(self):
        import re
        from core import wishes
        from core.profile_manager import ProfileManager
        w = wishes.load()
        choices = list(dict.fromkeys(wishes.PLACE_CHOICES + w["places"]))

        def field(label, value, on_save, width=None, suffix=None):
            return ft.TextField(label=label, value=str(value), width=width, text_size=14, border_radius=10,
                                suffix=suffix, on_blur=on_save, on_submit=on_save)

        self.place_chips = ft.Row(
            [ft.Chip(label=ft.Text(p.split(",")[0], size=13), selected=p in w["places"], tooltip=p,
                     on_select=lambda e, p=p: self._toggle_place(p, e.control.selected)) for p in choices],
            wrap=True, spacing=4, run_spacing=4)
        extra = ft.TextField(label="Add a place (City, Country)", text_size=14, border_radius=10,
                             on_submit=lambda e: self._add_place(e.control))
        home = ft.Dropdown(label="I live in", value=w["home"], text_size=14, border_radius=10,
                           options=[ft.dropdown.Option(p) for p in choices])
        home.on_select = lambda e: self._save_wish("home", e.control.value)

        prof = ProfileManager().load()
        jp = next((l for l in prof["personal"].get("languages", []) if l["language"] == "Japanese"), None)
        m = re.search(r"N[1-5]", jp["level"]) if jp else None
        jlpt = ft.Dropdown(label="My Japanese (JLPT)", value=m.group(0) if m else "N4", width=180, text_size=14,
                           border_radius=10, options=[ft.dropdown.Option(n) for n in ("N5", "N4", "N3", "N2", "N1")])
        jlpt.on_select = lambda e: self._set_jp_level(e.control.value)
        facts = ft.TextField(label="Facts and corrections Claude must follow (one per line)", multiline=True,
                             min_lines=3, max_lines=8, text_size=14, border_radius=10,
                             value="\n".join(prof.get("facts", [])), on_blur=lambda e: self._save_facts(e.control.value),
                             hint_text="e.g. I have never used Salesforce.")

        def checkbox(label, key):
            return ft.Checkbox(label=label, value=bool(w.get(key)),
                               on_change=lambda e, k=key: self._save_wish(k, e.control.value))

        body = [
            ft.Row([text("Your criteria", "title", expand=True),
                    ft.IconButton(ft.Icons.CLOSE, tooltip="Close", on_click=self.close_panel)]),
            text("Offers are ranked by CV fit, then your places in this order, then the money left.", "secondary"),
            self._section("Places you would live and work", self.place_chips, extra, home),
            self._section("Money", field("Save each month", w["save_eur"], lambda e: self._save_num("save_eur", e),
                                         suffix="€"),
                          field("Other household income each month (net)", w.get("other_income_eur", 0),
                                lambda e: self._save_num("other_income_eur", e), suffix="€"),
                          field("Working from Japan: your share of the house each month",
                                w.get("japan_share_jpy", 105000), lambda e: self._save_num("japan_share_jpy", e),
                                suffix="¥"),
                          field("Working from Japan: your own spending each month",
                                w.get("japan_personal_jpy", 35000), lambda e: self._save_num("japan_personal_jpy", e),
                                suffix="¥")),
            self._section("Your home", checkbox("We own our home (no rent)", "home_owned"),
                          field("Building fees each month (管理費 + 修繕積立金)", w.get("home_fees_jpy_month", 0),
                                lambda e: self._save_num("home_fees_jpy_month", e), suffix="¥"),
                          field("Property tax each year (固定資産税)", w.get("home_tax_jpy_year", 0),
                                lambda e: self._save_num("home_tax_jpy_year", e), suffix="¥"),
                          checkbox("Keep paying for it if we move for a job", "keep_home_when_moving"),
                          text("These are estimates until you enter your own figures." if w.get("home_estimated")
                               else "", "caption", color=Colors.WARNING)),
            self._section("If you move", field("Who moves (for rent and living costs)", w["household"],
                                               lambda e: self._on_household(e.control.value)),
                          checkbox("We would have a car", "have_car"),
                          checkbox("Prefer a strong Japanese community", "japanese_community"),
                          checkbox("In Japan, factory and manual work are fine", "manual_ok_japan")),
            self._section("Sites you do not trust (never searched or linked)",
                          ft.TextField(value=", ".join(w.get("avoid_sites", [])), text_size=14, border_radius=10,
                                       hint_text="e.g. stanby.com, example.jp",
                                       on_blur=lambda e: self._save_wish(
                                           "avoid_sites", [s.strip().lower() for s in (e.control.value or "")
                                                           .replace("\n", ",").split(",") if s.strip()]))),
            self._section("About you (used in every CV, letter, email and brief)", jlpt, facts),
        ]
        self.panel_body.controls = [ft.Container(ft.Column(body, spacing=18), padding=22)]

    def _save_wish(self, key, value):
        from core import wishes
        w = wishes.load()
        w[key] = value
        wishes.save(w)
        self._update_criteria_chip()
        self.refresh()

    def _save_num(self, key, e):
        try:
            v = float(e.control.value)
        except (TypeError, ValueError):
            return
        from core import wishes
        w = wishes.load()
        w[key] = v
        if key.startswith("home_"):
            w["home_estimated"] = False
        wishes.save(w)
        self._update_criteria_chip()
        self.refresh()

    def _toggle_place(self, place, on):
        from core import wishes
        w = wishes.load()
        places = [p for p in w["places"] if p != place] + ([place] if on else [])
        if not places:
            places = [w["home"]]
        self._save_wish("places", places)

    def _add_place(self, field):
        place = (field.value or "").strip()
        if "," not in place:
            self._page.show_dialog(ft.SnackBar(ft.Text("Write it as City, Country.")))
            return
        field.value = ""
        self._toggle_place(place, True)
        self._fill_criteria()
        self._page.update()

    def _on_household(self, value):
        from core import wishes
        value = (value or "").strip()
        if value and value != wishes.load()["household"]:
            self._save_wish("household", value)
            self._page.run_task(self._refresh_cities)

    async def _refresh_cities(self):
        from analyzers.investigate import refresh_cities
        tid = TASKS.start("Rents and living costs for your household", "researching every city again")
        try:
            done = await asyncio.to_thread(refresh_cities)
            TASKS.finish(tid, f"{len(done)} places updated")
        except Exception as ex:
            TASKS.finish(tid, str(ex), ok=False)
        self.refresh()

    def _set_jp_level(self, level):
        import re
        import yaml
        from core.profile_manager import ProfileManager
        path = ProfileManager().profile_path
        t = path.read_text(encoding="utf-8")
        new = re.sub(r'(- language: "Japanese"\s*\n\s*level: "[^"\n]*?)N[1-5]', lambda m: m.group(1) + level, t, count=1)
        if new != t:
            yaml.safe_load(new)
            path.write_text(new, encoding="utf-8")
        self._page.show_dialog(ft.SnackBar(ft.Text(f"Japanese level set to {level} in your profile.")))

    def _save_facts(self, value):
        import re
        import yaml
        from core.profile_manager import ProfileManager
        facts = [l.strip() for l in (value or "").splitlines() if l.strip()]
        path = ProfileManager().profile_path
        t = path.read_text(encoding="utf-8")
        block = ("facts:\n" + "".join(f"  - {yaml.safe_dump(f, allow_unicode=True, default_style=chr(34)).strip()}\n"
                                      for f in facts)) if facts else "facts: []\n"
        if re.search(r"(?m)^facts:", t):
            t = re.sub(r"(?ms)^facts:.*?(?=^\S|\Z)", block, t, count=1)
        else:
            t = t.rstrip("\n") + "\n\n# Corrections he entered in Anvil; they override everything else.\n" + block
        yaml.safe_load(t)
        path.write_text(t, encoding="utf-8")

    # ===== actions =====================================================================

    def _add_dialog(self):
        """An offer he found himself (Indeed Japan, GaijinPot... refuse automatic reading)."""
        link = ft.TextField(label="Link (optional)", text_size=14)
        body = ft.TextField(label="A posting (Ctrl+A on its page, copy) or a job alert from LINE: paste here",
                            multiline=True, min_lines=8, max_lines=14, text_size=13)

        def done(e):
            self._page.pop_dialog()
            self._page.run_task(self.add_offer, body.value or "", link.value or "")

        self._page.show_dialog(ft.AlertDialog(
            title=text("Add offers you found", "title"),
            content=ft.Column([text("One job or a whole alert with several: Anvil reads each, scores the fit "
                                    "honestly and works out the money left.",
                                    "secondary"), link, body], tight=True, spacing=10, width=560,
                              horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
            actions=[ft.TextButton("Cancel", on_click=lambda e: self._page.pop_dialog()),
                     primary_button("Add it", done)]))

    async def add_offer(self, posting, url):
        from analyzers.web_search import add_offers
        tid = TASKS.start("Reading what you pasted", "Claude is reading it")
        self.status.value, self.status.color = "Reading what you pasted…", Colors.ACCENT
        self._page.update()
        try:
            res = await asyncio.to_thread(add_offers, posting, url)
            new = [o for o, is_new in res if is_new]
            known = len(res) - len(new)
            if not res:
                msg = "Nothing added: every job was on a site you avoid."
            elif len(res) == 1:
                o = res[0][0]
                msg = f"Added: {o['title']} ({o['company']})" if new else f"Already in your offers: {o['title']}"
            else:
                msg = f"Added {len(new)} offer{'s' if len(new) != 1 else ''}" + \
                      (f", {known} already known" if known else "") + ". Best fit first below."
            self.status.value, self.status.color = msg, Colors.SUCCESS if res else Colors.WARNING
            TASKS.finish(tid, msg)
            self.show.selected = ["week"]
            self.last_new = {o["id"] for o in new}
            if len(res) == 1:
                self.open_offer(res[0][0]["id"])
            else:
                self.refresh()
            if new:
                self._page.run_task(self.investigate, [o["id"] for o in new])
        except Exception as ex:
            self.status.value, self.status.color = f"Could not add it: {ex}", Colors.ERROR
            TASKS.finish(tid, str(ex), ok=False)
            self.refresh()

    def _preset(self, q):
        self.query.value = q
        self._page.run_task(self.search)

    async def search(self):
        from analyzers.web_search import search_web
        if self.searching:
            return
        self.searching = True
        keywords = (self.query.value or "").strip()
        region = self.region.value
        what = f"'{keywords}'" if keywords else "jobs that fit your CVs"
        tid = TASKS.start(f"Searching {what}", "searching job sites")
        self.search_btn.disabled = True
        state = {"msg": "searching job sites"}
        start = time.time()
        task = asyncio.ensure_future(asyncio.to_thread(
            search_web, keywords, region, progress=lambda s: state.__setitem__("msg", s)))
        while not task.done():
            TASKS.update(tid, state["msg"])
            self.status.value = f"Searching {what}: {state['msg'].lower()} · {int(time.time() - start)} s " \
                                f"(usually 2-6 minutes; you can go elsewhere)"
            self.status.color = Colors.ACCENT
            self._page.update()
            await asyncio.wait({task}, timeout=2)
        try:
            res = task.result()
            n = len(res["new"])
            extra = [f"{res['repeats']} already known"] if res["repeats"] else []
            if res["dead"]:
                extra.append(f"{res['dead']} dead links dropped")
            self.status.value = f"{n} new offer{'s' if n != 1 else ''} for {what}" + \
                                (f" · {', '.join(extra)}" if extra else "") + "."
            self.status.color = Colors.SUCCESS if n else Colors.WARNING
            TASKS.finish(tid, self.status.value)
            self.last_new = set(res["new"])
            self.show.selected = ["week"]
            if n:
                self._page.show_dialog(ft.SnackBar(ft.Text(f"{n} new offers ready."),
                                                   action="See offers", on_action=lambda e: NAV.go("offers")))
                self._page.run_task(self.investigate, res["new"])
        except Exception as ex:
            self.status.value = f"The search failed: {ex}"
            self.status.color = Colors.ERROR
            TASKS.finish(tid, str(ex), ok=False)
        finally:
            self.searching = False
            self.search_btn.disabled = False
            self.refresh()

    async def investigate(self, offer_ids):
        """Employer research and costs, 3 at a time; each card updates when its result is in."""
        from analyzers.investigate import investigate
        ids = [i for i in offer_ids if i not in self.investigating]
        if not ids:
            return
        self.investigating.update(ids)
        tid = TASKS.start(f"Researching {len(ids)} employer{'s' if len(ids) > 1 else ''} and costs", f"0 of {len(ids)}")
        self.refresh()
        sem = asyncio.Semaphore(3)
        done = {"n": 0, "failed": 0}

        async def one(i):
            async with sem:
                try:
                    await asyncio.to_thread(investigate, i)
                except Exception:
                    done["failed"] += 1
                finally:
                    done["n"] += 1
                    self.investigating.discard(i)
                    TASKS.update(tid, f"{done['n']} of {len(ids)}")
                    self.refresh()

        await asyncio.gather(*(one(i) for i in ids))
        TASKS.finish(tid, f"{len(ids) - done['failed']} researched" +
                     (f", {done['failed']} failed" if done["failed"] else ""), ok=not done["failed"])

    async def select(self, offer_id):
        """Apply: put it in Applications and write the tailored CV and letter."""
        from generators.application import prepare, BUSY
        from core.offers import OfferLibrary
        app_id = to_pipeline(offer_id)
        if not app_id:
            return
        o = OfferLibrary().get(offer_id)
        BUSY.add(app_id)
        self.preparing.add(offer_id)
        tid = TASKS.start(f"CV and letter for {o['company']}", "reading the posting and writing")
        self.refresh()
        try:
            await asyncio.to_thread(prepare, app_id)
            TASKS.finish(tid, "ready to review in Applications")
            self._page.show_dialog(ft.SnackBar(ft.Text(f"Your CV and letter for {o['company']} are ready."),
                                               action="Review",
                                               on_action=lambda e, i=app_id: NAV.go("applications", app_id=i)))
        except Exception as ex:
            TASKS.finish(tid, str(ex), ok=False)
            self._page.show_dialog(ft.SnackBar(ft.Text(f"Saved in Applications, but writing failed: {ex}")))
        finally:
            BUSY.discard(app_id)
            self.preparing.discard(offer_id)
            self.refresh()

    def _turn_down(self, offer_id):
        from core.offers import OfferLibrary
        from core.wishes import REJECT_REASONS
        reason = ft.RadioGroup(value="experience", content=ft.Column(
            [ft.Radio(value=k, label=v) for k, v in REJECT_REASONS.items()], spacing=0))
        note = ft.TextField(label="Note (optional)", text_size=14)

        def done(e):
            OfferLibrary().reject(offer_id, reason.value, (note.value or "").strip())
            self._page.pop_dialog()
            if self.selected == offer_id:
                self.close_panel()
            else:
                self.refresh()

        self._page.show_dialog(ft.AlertDialog(
            title=text("Why not this one?", "title"),
            content=ft.Column([text("Later searches avoid jobs turned down for the same reason.", "secondary"),
                               reason, note], tight=True, spacing=8, width=420),
            actions=[ft.TextButton("Cancel", on_click=lambda e: self._page.pop_dialog()),
                     primary_button("Turn down", done)],
        ))

    def _restore(self, offer_id):
        from core.offers import OfferLibrary
        OfferLibrary().restore(offer_id)
        self.refresh()
