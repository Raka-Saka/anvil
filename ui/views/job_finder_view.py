"""
Job Finder View - Analyze job postings and search job boards.

Features:
- Analyze: Paste URL or job description, get instant match score
- Search: Search job boards for matching positions
- One-click cover letter generation
"""

from pathlib import Path

import flet as ft
from ..theme import Colors
from ..components import create_button


class JobFinderView(ft.Column):
    """Job analysis and search view with tabs."""

    def __init__(self, page: ft.Page, on_generate_cover_letter=None):
        self._page = page
        self._on_generate_cover_letter = on_generate_cover_letter
        self.current_job = None
        self.current_analysis = None
        self.search_results = []
        self._investigating = set()
        self._preparing_offers = set()
        from generators.application import BUSY
        self._preparing = BUSY
        self._last_new = set()
        self._selected_tab = 0

        # Create tabs content
        self._build_analyze_tab()
        self._build_search_tab()

        # Tab buttons (manual implementation for Flet compatibility)
        self.analyze_tab_btn = ft.ElevatedButton(
            content=ft.Row([
                ft.Icon(ft.Icons.ANALYTICS, size=18),
                ft.Text("Analyze Job"),
            ], spacing=5),
            on_click=lambda e: self._switch_tab(0),
            style=ft.ButtonStyle(bgcolor=Colors.ACCENT, color=Colors.TEXT_PRIMARY),
        )
        self.search_tab_btn = ft.ElevatedButton(
            content=ft.Row([
                ft.Icon(ft.Icons.SEARCH, size=18),
                ft.Text("Search Jobs"),
            ], spacing=5),
            on_click=lambda e: self._switch_tab(1),
            style=ft.ButtonStyle(bgcolor=Colors.BG_SECONDARY, color=Colors.TEXT_SECONDARY),
        )

        self.tab_buttons = ft.Row([
            self.analyze_tab_btn,
            self.search_tab_btn,
        ], spacing=10)

        # Content container that switches
        self.tab_content = ft.Container(
            content=self.analyze_content,
            expand=True,
        )

        super().__init__(
            controls=[
                ft.Text("Job Finder", size=24, weight=ft.FontWeight.BOLD, color=Colors.TEXT_PRIMARY),
                ft.Text("Analyze job postings or search for matching positions", size=14, color=Colors.TEXT_SECONDARY),
                ft.Divider(height=10, color=Colors.BG_TERTIARY),
                self.tab_buttons,
                self.tab_content,
            ],
            spacing=10,
            expand=True,
        )

    def _switch_tab(self, index: int):
        """Switch between tabs."""
        self._selected_tab = index

        if index == 0:
            self.tab_content.content = self.analyze_content
            self.analyze_tab_btn.style = ft.ButtonStyle(bgcolor=Colors.ACCENT, color=Colors.TEXT_PRIMARY)
            self.search_tab_btn.style = ft.ButtonStyle(bgcolor=Colors.BG_SECONDARY, color=Colors.TEXT_SECONDARY)
        else:
            self.tab_content.content = self.search_content
            self.analyze_tab_btn.style = ft.ButtonStyle(bgcolor=Colors.BG_SECONDARY, color=Colors.TEXT_SECONDARY)
            self.search_tab_btn.style = ft.ButtonStyle(bgcolor=Colors.ACCENT, color=Colors.TEXT_PRIMARY)

        self._page.update()

    def _build_analyze_tab(self):
        """Build the Analyze Job tab content."""
        # URL input
        self.url_input = ft.TextField(
            label="Job URL",
            hint_text="Paste LinkedIn, Indeed, or any job posting URL...",
            width=500,
            border_color=Colors.BG_TERTIARY,
            focused_border_color=Colors.ACCENT,
            text_style=ft.TextStyle(color=Colors.TEXT_PRIMARY),
            label_style=ft.TextStyle(color=Colors.TEXT_SECONDARY),
            on_submit=self._on_analyze_url,
        )

        # Or paste text
        self.job_text = ft.TextField(
            label="Or paste job description",
            hint_text="Paste the full job posting text here...",
            multiline=True,
            min_lines=4,
            max_lines=6,
            border_color=Colors.BG_TERTIARY,
            focused_border_color=Colors.ACCENT,
            text_style=ft.TextStyle(color=Colors.TEXT_PRIMARY),
            label_style=ft.TextStyle(color=Colors.TEXT_SECONDARY),
            expand=True,
        )

        # Company and role fields
        self.company_field = ft.TextField(
            label="Company",
            width=200,
            border_color=Colors.BG_TERTIARY,
            text_style=ft.TextStyle(color=Colors.TEXT_PRIMARY),
        )
        self.role_field = ft.TextField(
            label="Role",
            width=200,
            border_color=Colors.BG_TERTIARY,
            text_style=ft.TextStyle(color=Colors.TEXT_PRIMARY),
        )

        # Buttons
        self.analyze_url_btn = create_button("Analyze URL", self._on_analyze_url, ft.Icons.LINK)
        self.analyze_text_btn = create_button("Analyze Text", self._on_analyze_text, ft.Icons.TEXT_SNIPPET, Colors.ACCENT)

        # Results section
        self.match_score = ft.Container(
            content=ft.Column([
                ft.Text("MATCH SCORE", size=12, color=Colors.TEXT_SECONDARY),
                ft.Text("--", size=48, weight=ft.FontWeight.BOLD, color=Colors.TEXT_SECONDARY),
                ft.Text("Enter a job to analyze", size=11, color=Colors.TEXT_SECONDARY),
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            width=150,
            height=120,
            bgcolor=Colors.BG_SECONDARY,
            border_radius=10,
            padding=15,
        )

        self.job_info = ft.Container(
            content=ft.Column([
                ft.Text("Job Details", size=14, weight=ft.FontWeight.BOLD, color=Colors.TEXT_PRIMARY),
                ft.Text("Analyze a job to see details", size=12, color=Colors.TEXT_SECONDARY),
            ]),
            bgcolor=Colors.BG_SECONDARY,
            border_radius=10,
            padding=15,
            expand=True,
        )

        self.strengths_panel = ft.Container(
            content=ft.Column([
                ft.Text("YOUR STRENGTHS", size=12, weight=ft.FontWeight.BOLD, color=Colors.SUCCESS),
                ft.Text("Matching skills appear here", size=11, color=Colors.TEXT_SECONDARY),
            ], scroll=ft.ScrollMode.AUTO),
            bgcolor=Colors.BG_SECONDARY,
            border_radius=10,
            padding=15,
            expand=True,
        )

        self.gaps_panel = ft.Container(
            content=ft.Column([
                ft.Text("GAPS TO ADDRESS", size=12, weight=ft.FontWeight.BOLD, color=Colors.WARNING),
                ft.Text("Missing requirements appear here", size=11, color=Colors.TEXT_SECONDARY),
            ], scroll=ft.ScrollMode.AUTO),
            bgcolor=Colors.BG_SECONDARY,
            border_radius=10,
            padding=15,
            expand=True,
        )

        # Action buttons
        self.generate_letter_btn = create_button(
            "Generate Cover Letter", self._on_generate_letter,
            ft.Icons.MAIL, Colors.ACCENT
        )
        self.generate_letter_btn.visible = False

        self.save_job_btn = create_button(
            "Save to Tracker", self._on_save_job,
            ft.Icons.BOOKMARK_ADD, Colors.SUCCESS
        )
        self.save_job_btn.visible = False

        self.analyze_content = ft.Container(
            content=ft.Column([
                # URL input row
                ft.Row([self.url_input, self.analyze_url_btn], spacing=10),
                ft.Text("— OR —", size=12, color=Colors.TEXT_SECONDARY, text_align=ft.TextAlign.CENTER),
                # Text input
                self.job_text,
                ft.Row([self.company_field, self.role_field, self.analyze_text_btn], spacing=10),
                ft.Divider(height=10, color=Colors.BG_TERTIARY),
                # Results row
                ft.Row([self.match_score, self.job_info], spacing=20),
                # Strengths and gaps
                ft.Row([self.strengths_panel, self.gaps_panel], spacing=20, expand=True),
                # Action buttons
                ft.Row([self.generate_letter_btn, self.save_job_btn], alignment=ft.MainAxisAlignment.END, spacing=10),
            ], spacing=10, expand=True, scroll=ft.ScrollMode.AUTO),
            padding=10,
            expand=True,
        )

    def _build_search_tab(self):
        """Build the Search Jobs tab: web search via Claude, the offer library, and the old remote boards."""
        self.search_input = ft.TextField(
            label="What job?",
            hint_text="Empty = jobs that fit your CVs",
            width=400,
            border_color=Colors.BG_TERTIARY,
            focused_border_color=Colors.ACCENT,
            text_style=ft.TextStyle(color=Colors.TEXT_PRIMARY),
            label_style=ft.TextStyle(color=Colors.TEXT_SECONDARY),
            on_submit=self._on_web_search,
        )

        # Old remote-board search (Jobicy, Remotive)
        self.remote_only = ft.Checkbox(label="Remote only", value=True, fill_color=Colors.ACCENT)
        self.search_btn = ft.OutlinedButton("Search 2 remote boards", icon=ft.Icons.SEARCH, on_click=self._on_search)

        from analyzers.web_search import REGIONS
        self.region = ft.Dropdown(
            label="Where", value="wishes", width=170, text_size=13,
            options=[ft.dropdown.Option(k, "My places" if k == "wishes" else k.capitalize()) for k in REGIONS],
            border_color=Colors.BG_TERTIARY, bgcolor=Colors.BG_SECONDARY,
        )
        self.web_btn = ft.Button("Search the web (Claude)", icon=ft.Icons.TRAVEL_EXPLORE,
                                 on_click=self._on_web_search,
                                 tooltip="Leave the box empty to find jobs that fit your CVs")

        # Presets fill the query only; the "Where" choice stays as the user set it.
        presets = [
            ("Fits my CVs", ""),
            ("French CS team leader", "customer service team leader, French-speaking"),
            ("Support client FR", "conseiller support client francophone"),
            ("Technical support", "technical support / escalation specialist, English or French"),
            ("FR-speaking support", "French-speaking customer support"),
            ("Python developer", "Python / Django developer"),
        ]
        self.quick_searches = ft.Row([
            ft.OutlinedButton(label, on_click=lambda e, q=q: self._preset(q))
            for label, q in presets
        ], spacing=10, wrap=True)

        self.show_filter = ft.Dropdown(
            label="Show", value="week", width=210, text_size=13,
            options=[ft.dropdown.Option("new", "New, not opened"),
                     ft.dropdown.Option("week", "All from the last 7 days"),
                     ft.dropdown.Option("dismissed", "Dismissed")],
            border_color=Colors.BG_TERTIARY, bgcolor=Colors.BG_SECONDARY,
        )
        self.show_filter.on_select = lambda e: self._show_library()

        self.results_list = ft.ListView(spacing=6, padding=10, expand=True)
        self.search_status = ft.Text(
            "Leave the box empty to find jobs that fit your CVs, or type a job. Pick where, then 'Search the web'.",
            size=12, color=Colors.TEXT_SECONDARY)

        self._build_criteria()
        self.search_content = ft.Container(
            content=ft.Column([
                self.criteria,
                ft.Row([self.search_input, self.region, self.web_btn], spacing=10),
                ft.Text("Quick searches (in the place chosen under Where):", size=12, color=Colors.TEXT_SECONDARY),
                self.quick_searches,
                ft.Divider(height=10, color=Colors.BG_TERTIARY),
                ft.Row([self.search_status], wrap=True),
                ft.Row([self.show_filter,
                        ft.Container(expand=True),
                        self.remote_only, self.search_btn], spacing=10),
                self.results_list,
            ], spacing=10, expand=True),
            padding=10,
            expand=True,
        )
        self._show_library(update=False)

    # ===== Criteria: places, home, savings goal =====

    def _build_criteria(self):
        from core import wishes
        w = wishes.load()
        choices = list(dict.fromkeys(wishes.PLACE_CHOICES + w["places"]))

        def place_chip(p):
            return ft.Chip(label=ft.Text(p, size=12), selected=p in w["places"],
                           on_select=lambda e, p=p: self._toggle_place(p, e.control.selected))

        self.place_chips = ft.Row([place_chip(p) for p in choices], wrap=True, spacing=4, run_spacing=4)
        self.extra_place = ft.TextField(label="Add a place (City, Country)", width=260, text_size=13,
                                        on_submit=self._add_place)
        self.home_dd = ft.Dropdown(label="I live in", value=w["home"], width=200, text_size=13,
                                   options=[ft.dropdown.Option(p) for p in choices])
        self.home_dd.on_select = lambda e: self._save_wish("home", e.control.value)
        self.save_field = ft.TextField(label="Save each month (€)", value=str(w["save_eur"]), width=150,
                                       text_size=13, on_blur=self._on_save_goal, on_submit=self._on_save_goal)
        self.save_jpy = ft.Text(self._jpy_text(w["save_eur"]), size=12, color=Colors.TEXT_SECONDARY)
        self.criteria_summary = ft.Text(self._criteria_text(w), size=12, color=Colors.TEXT_SECONDARY)

        # Owned home in Osaka
        self.home_owned = ft.Checkbox(label="We own our home (no rent)", value=w.get("home_owned", True),
                                      on_change=lambda e: self._save_wish("home_owned", e.control.value))
        self.home_fees = ft.TextField(label="Building fees ¥/month (管理費+修繕)", value=str(w.get("home_fees_jpy_month", 0)),
                                      width=230, text_size=13, on_blur=lambda e: self._save_num("home_fees_jpy_month", e))
        self.home_tax = ft.TextField(label="Property tax ¥/year (固定資産税)", value=str(w.get("home_tax_jpy_year", 0)),
                                     width=220, text_size=13, on_blur=lambda e: self._save_num("home_tax_jpy_year", e))
        self.keep_home = ft.Checkbox(label="Keep paying for it if I move for a job", value=w.get("keep_home_when_moving", True),
                                     on_change=lambda e: self._save_wish("keep_home_when_moving", e.control.value))
        self.household = ft.TextField(label="If we move: who (for rent and living costs)", value=w["household"],
                                      width=300, text_size=13, on_blur=self._on_household)
        self.other_income = ft.TextField(label="Other household income €/month (net)",
                                         value=str(w.get("other_income_eur", 0)), width=250, text_size=13,
                                         on_blur=lambda e: self._save_num("other_income_eur", e))
        self.jp_community = ft.Checkbox(label="Prefer a strong Japanese community", value=w.get("japanese_community", True),
                                        on_change=lambda e: self._save_wish("japanese_community", e.control.value))
        self.have_car = ft.Checkbox(label="We would have a car", value=w.get("have_car", False),
                                    on_change=lambda e: self._save_wish("have_car", e.control.value))
        self.home_note = ft.Text("Estimate: enter your real figures." if w.get("home_estimated") else "",
                                 size=11, color=Colors.WARNING)

        # Facts Claude must respect
        from core.profile_manager import ProfileManager
        prof = ProfileManager().load()
        jp = next((l for l in prof["personal"].get("languages", []) if l["language"] == "Japanese"), None)
        import re as _re
        cur = _re.search(r"N([1-5])", jp["level"]).group(0) if jp and _re.search(r"N([1-5])", jp["level"]) else "N4"
        self.jp_level = ft.Dropdown(label="My Japanese (JLPT)", value=cur, width=170, text_size=13,
                                    options=[ft.dropdown.Option(n) for n in ("N5", "N4", "N3", "N2", "N1")])
        self.jp_level.on_select = lambda e: self._set_jp_level(e.control.value)
        self.facts = ft.TextField(label="Facts and corrections Claude must follow (one per line)",
                                  value="\n".join(prof.get("facts", [])), multiline=True, min_lines=2, max_lines=6,
                                  text_size=13, on_blur=self._save_facts,
                                  hint_text="e.g. I have never used Salesforce. I can start in January.")
        self.criteria = ft.ExpansionTile(
            title=ft.Text("My criteria", size=14, weight=ft.FontWeight.BOLD, color=Colors.TEXT_PRIMARY),
            subtitle=self.criteria_summary,
            controls=[ft.Container(content=ft.Column([
                ft.Text("Ranking: CV fit first, then your places in order, then what is left after costs.",
                        size=11, color=Colors.TEXT_MUTED),
                ft.Text("Places I would live and work (order = order clicked):", size=12, color=Colors.TEXT_SECONDARY),
                self.place_chips,
                ft.Row([self.extra_place, self.home_dd, self.save_field, self.save_jpy], spacing=10, wrap=True),
                ft.Text("Home:", size=12, color=Colors.TEXT_SECONDARY),
                ft.Row([self.home_owned, self.home_fees, self.home_tax, self.keep_home, self.home_note],
                       spacing=10, wrap=True),
                ft.Row([self.household, self.have_car, self.other_income, self.jp_community], spacing=10, wrap=True),
                ft.Text("About me (used in every CV, letter, email and brief):", size=12, color=Colors.TEXT_SECONDARY),
                ft.Row([self.jp_level, self.facts], spacing=10, vertical_alignment=ft.CrossAxisAlignment.START),
            ], spacing=8), padding=10)],
        )

    def _criteria_text(self, w):
        return (f"{' > '.join(w['places'])} · live in {w['home'].split(',')[0]} · "
                f"save €{w['save_eur']:,.0f}/month")

    def _jpy_text(self, eur):
        from core.offers import fx_rates
        return f"≈ ¥{float(eur) * fx_rates().get('JPY', 177.8):,.0f}/month"

    def _save_wish(self, key, value):
        from core import wishes
        w = wishes.load()
        w[key] = value
        wishes.save(w)
        self.criteria_summary.value = self._criteria_text(w)
        self._show_library()

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
        self.home_note.value = ""
        self._show_library()

    def _on_household(self, e):
        from core import wishes
        value = (self.household.value or "").strip()
        if not value or value == wishes.load()["household"]:
            return
        self._save_wish("household", value)
        self._page.run_task(self._refresh_cities)

    async def _refresh_cities(self):
        """City costs depend on the household: research them again (cached for 90 days)."""
        import asyncio
        from analyzers.investigate import refresh_cities
        self.search_status.value = "Researching rents and living costs again for your household..."
        self.search_status.color = Colors.ACCENT
        self._page.update()
        try:
            done = await asyncio.to_thread(refresh_cities)
            self.search_status.value = f"Costs updated for {len(done)} places."
            self.search_status.color = Colors.SUCCESS
        except Exception as ex:
            self.search_status.value = f"Cost update failed: {ex}"
            self.search_status.color = Colors.ERROR
        self._show_library()

    def _set_jp_level(self, level):
        """Rewrite the JLPT level in the profile; every generator reads it from there."""
        import re
        import yaml
        from core.profile_manager import ProfileManager
        path = ProfileManager().profile_path
        text = path.read_text(encoding="utf-8")
        new = re.sub(r'(- language: "Japanese"\s*\n\s*level: "[^"\n]*?)N[1-5]', lambda m: m.group(1) + level, text, count=1)
        if new != text:
            yaml.safe_load(new)                     # never write a broken profile
            path.write_text(new, encoding="utf-8")
        self._page.show_dialog(ft.SnackBar(content=ft.Text(f"Japanese level set to {level} in your profile.")))

    def _save_facts(self, e):
        """Save corrections to profile.yaml under facts:, keeping the rest of the file as written."""
        import yaml
        from core.profile_manager import ProfileManager
        facts = [l.strip() for l in (self.facts.value or "").splitlines() if l.strip()]
        path = ProfileManager().profile_path
        text = path.read_text(encoding="utf-8")
        block = "facts:\n" + "".join(f"  - {yaml.safe_dump(f, allow_unicode=True, default_style='\"').strip()}\n"
                                     for f in facts) if facts else "facts: []\n"
        import re
        if re.search(r"(?m)^facts:", text):
            text = re.sub(r"(?ms)^facts:.*?(?=^\S|\Z)", block, text, count=1)
        else:
            text = text.rstrip("\n") + "\n\n# Corrections he entered in Anvil; they override everything else.\n" + block
        yaml.safe_load(text)
        path.write_text(text, encoding="utf-8")

    def _toggle_place(self, place, on):
        from core import wishes
        w = wishes.load()
        places = [p for p in w["places"] if p != place] + ([place] if on else [])
        if not places:                     # at least one place: fall back to where he lives
            places = [w["home"]]
            for c in self.place_chips.controls:
                c.selected = c.label.value == w["home"]
        self._save_wish("places", places)

    def _add_place(self, e):
        place = (self.extra_place.value or "").strip()
        if "," not in place:
            self._page.show_dialog(ft.SnackBar(content=ft.Text("Write it as City, Country.")))
            return
        self.extra_place.value = ""
        self.place_chips.controls.append(ft.Chip(label=ft.Text(place, size=12), selected=True,
                                                 on_select=lambda e, p=place: self._toggle_place(p, e.control.selected)))
        self.home_dd.options.append(ft.dropdown.Option(place))
        self._toggle_place(place, True)

    def _on_save_goal(self, e):
        try:
            v = float(self.save_field.value)
        except (TypeError, ValueError):
            return
        self.save_jpy.value = self._jpy_text(v)
        self._save_wish("save_eur", v)

    # ===== Web search and the offer library =====

    def _preset(self, keywords: str):
        self.search_input.value = keywords
        self._page.run_task(self._run_web_search)

    async def _on_web_search(self, e):
        await self._run_web_search()

    async def _run_web_search(self):
        """Runs on Flet's event loop; the search itself runs in a worker thread."""
        import asyncio
        import time
        from analyzers.web_search import search_web

        if self.web_btn.disabled:
            return
        keywords = (self.search_input.value or "").strip()  # empty = jobs that fit the CVs
        region = self.region.value
        self.web_btn.disabled = True
        self.search_btn.disabled = True
        state = {"msg": "Claude is searching the web"}
        start = time.time()

        task = asyncio.ensure_future(asyncio.to_thread(
            search_web, keywords, region, progress=lambda s: state.__setitem__("msg", s)))
        while not task.done():
            self.search_status.value = f"{state['msg']}... {int(time.time() - start)}s (usually 2-6 minutes)"
            self.search_status.color = Colors.ACCENT
            self._page.update()
            await asyncio.wait({task}, timeout=2)

        mins = (time.time() - start) / 60
        try:
            res = task.result()
            what = f"'{keywords}'" if keywords else "your CVs"
            n = len(res["new"])
            extra = []
            if res["repeats"]:
                extra.append(f"{res['repeats']} already known")
            if res["dead"]:
                extra.append(f"{res['dead']} dead links dropped")
            self.search_status.value = (f"{n} new offers for {what} ({mins:.0f} min)"
                                        + (f" · {', '.join(extra)}" if extra else "") + ".")
            self.search_status.color = Colors.SUCCESS if n else Colors.WARNING
            self.show_filter.value = "week"
            self._show_library(highlight=set(res["new"]), update=False)
            self._last_new = set(res["new"])
            if res["new"]:
                self._page.run_task(self._run_investigations, res["new"])
        except Exception as ex:
            self.search_status.value = f"Web search failed: {ex}"
            self.search_status.color = Colors.ERROR
        finally:
            self.web_btn.disabled = False
            self.search_btn.disabled = False
            self._page.update()

    def _show_library(self, highlight: set = None, update: bool = True):
        from core.offers import OfferLibrary
        lib = OfferLibrary()
        mode = self.show_filter.value
        if mode == "dismissed":
            offers = [o for o in lib.current(include_dismissed=True) if o["status"] == "dismissed"]
        else:
            offers = lib.current()
            if mode == "new":
                offers = [o for o in offers if o["status"] == "new"]
        highlight = highlight or set()
        offers.sort(key=lambda o: o["id"] not in highlight)   # stable: keeps fit > place > money
        self.results_list.controls = [self._offer_card(o, o["id"] in highlight) for o in offers] or [
            ft.Text("No offers here yet. Run a web search.", size=13, color=Colors.TEXT_MUTED, italic=True)]
        if update:
            self._page.update()

    def _offer_card(self, o: dict, is_new: bool = False) -> ft.Container:
        from core.offers import salary_text, in_pipeline, OfferLibrary
        match = o.get("match")
        mcolor = (Colors.SUCCESS if (match or 0) >= 80 else Colors.ACCENT if (match or 0) >= 50
                  else Colors.TEXT_SECONDARY)
        age = OfferLibrary().age_days(o)
        posted = f"posted {age}d ago" if o.get("posted") else f"found {age}d ago, date unknown"
        app = in_pipeline(o)

        def chip(text, color=Colors.TEXT_SECONDARY):
            return ft.Container(content=ft.Text(text, size=10, color=color), bgcolor=Colors.BG_TERTIARY,
                                padding=ft.padding.symmetric(horizontal=8, vertical=2), border_radius=3)

        chips = []
        if is_new:
            chips.append(chip("NEW", Colors.SUCCESS))
        if o.get("seniority") and o["seniority"] != "unknown":
            chips.append(chip(o["seniority"].upper(), Colors.WARNING if o["seniority"] == "entry" else Colors.TEXT_SECONDARY))
        if o.get("work_rights") == "unclear":
            chips.append(chip("RIGHT TO WORK UNCLEAR", Colors.WARNING))
        if o["status"] == "seen":
            chips.append(chip("OPENED"))
        if len(o["links"]) > 1:
            chips.append(chip(f"{len(o['links'])} SITES", Colors.ACCENT))
        if app:
            chips.append(chip(f"IN PIPELINE #{app['id']} · {app['stage'].upper()}", Colors.ERROR))
        if o.get("reject_reason"):
            from core.wishes import REJECT_REASONS
            chips.append(chip("TURNED DOWN: " + REJECT_REASONS.get(o["reject_reason"], o["reject_reason"]).upper(),
                              Colors.ERROR))

        link_buttons = [
            ft.TextButton(l.get("source") or "link", icon=ft.Icons.OPEN_IN_NEW,
                          on_click=lambda e, u=l["url"], i=o["id"]: self._open_offer(i, u))
            for l in o["links"][:4]
        ]

        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Column([
                        ft.Text("MATCH", size=8, color=Colors.TEXT_SECONDARY),
                        ft.Text(f"{match}" if match is not None else "–", size=18,
                                weight=ft.FontWeight.BOLD, color=mcolor),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
                    width=48, tooltip="How much of the job's core duties your record shows (Claude's reading)",
                ),
                ft.Column([
                    ft.Text(o["title"], size=14, weight=ft.FontWeight.BOLD, color=Colors.TEXT_PRIMARY),
                    ft.Row([ft.Text(o["company"], size=12, color=Colors.ACCENT),
                            ft.Text(f"· {o.get('location', '')} · {posted}", size=12, color=Colors.TEXT_SECONDARY)],
                           spacing=4, wrap=True),
                    ft.Text(salary_text(o.get("salary")), size=12, color=Colors.TEXT_PRIMARY),
                    ft.Row(chips, spacing=4, wrap=True),
                    ft.Text(o.get("fit", ""), size=12, color=Colors.TEXT_SECONDARY),
                    ft.Text(f"Languages: {o.get('languages', '')}", size=11, color=Colors.TEXT_MUTED),
                    self._investigation_block(o),
                    ft.Row([ft.ProgressRing(width=14, height=14),
                            ft.Text("Preparing the tailored CV and letter (1-3 min)...", size=11, color=Colors.ACCENT)])
                    if o["id"] in self._preparing_offers else ft.Container(),
                    ft.Row(link_buttons, spacing=0, wrap=True),
                ], spacing=3, expand=True),
                ft.Column([
                    ft.IconButton(icon=ft.Icons.ASSIGNMENT_TURNED_IN, icon_color=Colors.SUCCESS,
                                  tooltip="Select: put it in the pipeline and prepare a tailored CV and letter",
                                  disabled=bool(app) or o["id"] in self._preparing_offers,
                                  on_click=lambda e, i=o["id"]: self._page.run_task(self._select_offer, i)),
                    ft.IconButton(icon=ft.Icons.MANAGE_SEARCH, tooltip="Investigate company and cost of living",
                                  icon_color=Colors.ACCENT,
                                  on_click=lambda e, i=o["id"]: self._page.run_task(self._run_investigations, [i])),
                    ft.IconButton(icon=ft.Icons.ANALYTICS, tooltip="Full analysis", icon_color=Colors.TEXT_SECONDARY,
                                  on_click=lambda e, oo=o: self._analyze_offer(oo)),
                    ft.IconButton(icon=ft.Icons.RESTORE if o["status"] == "dismissed" else ft.Icons.CLOSE,
                                  tooltip="Restore" if o["status"] == "dismissed" else "Turn down (with a reason)",
                                  icon_color=Colors.TEXT_MUTED,
                                  on_click=lambda e, i=o["id"], s=o["status"]: self._dismiss_offer(i, s)),
                ], spacing=0),
            ], vertical_alignment=ft.CrossAxisAlignment.START),
            bgcolor=Colors.BG_SECONDARY, border_radius=8, padding=10,
            border=ft.border.all(1, Colors.SUCCESS) if is_new else None,
        )

    def _investigation_block(self, o: dict):
        """Company facts and take-home pay against the city's cost of living."""
        from analyzers.investigate import budget
        from core.offers import fx_rates
        if o["id"] in self._investigating:
            return ft.Row([ft.ProgressRing(width=14, height=14),
                           ft.Text("Investigating company and cost of living...", size=11, color=Colors.ACCENT)])
        info = o.get("company_info")
        if not info:
            return ft.Container()
        jpy = fx_rates().get("JPY", 177.8)
        rows = [ft.Text(f"{info['summary']}  Size: {info['size']}.  Rating: {info['rating']}.",
                        size=11, color=Colors.TEXT_PRIMARY)]
        if info.get("employer_is_agency"):
            rows.append(ft.Text("Posted by an agency or outsourcer, hiring for a client.", size=11, color=Colors.WARNING))
        if info.get("pros"):
            rows.append(ft.Text("+ " + "  + ".join(info["pros"]), size=11, color=Colors.TEXT_SECONDARY))
        if info.get("cons"):
            rows.append(ft.Text("− " + "  − ".join(info["cons"]), size=11, color=Colors.TEXT_SECONDARY))
        for flag in info.get("red_flags", []):
            rows.append(ft.Text(f"⚠ {flag}", size=11, color=Colors.ERROR))
        c = info.get("contract")
        if c:
            kcolor = {"permanent": Colors.SUCCESS, "fixed_term": Colors.WARNING, "agency": Colors.WARNING,
                      "contractor": Colors.WARNING}.get(c["kind"], Colors.TEXT_SECONDARY)
            head = " · ".join(x for x in (c["local_term"] or c["kind"], c["hours"],
                                          f"trial {c['trial']}" if c["trial"] and c["trial"] != "unknown" else "") if x)
            rows.append(ft.Text(f"Contract: {head}", size=11, weight=ft.FontWeight.BOLD, color=kcolor))
            if c["benefits"]:
                rows.append(ft.Text("Stated: " + ", ".join(c["benefits"]), size=11, color=Colors.TEXT_SECONDARY))
            if c["missing"]:
                rows.append(ft.Text("Not mentioned: " + ", ".join(c["missing"]), size=11, color=Colors.TEXT_MUTED))
            for x in c["concerns"]:
                rows.append(ft.Text(f"⚠ {x}", size=11, color=Colors.WARNING))
        feas = info.get("feasibility")
        if feas:
            fcolor = {"ok": Colors.SUCCESS, "check": Colors.WARNING, "no": Colors.ERROR}.get(feas, Colors.TEXT_SECONDARY)
            where = f" From: {', '.join(info['remote_from'])}." if info.get("remote_from") else ""
            rows.append(ft.Text(f"Feasible: {feas.upper()}. {info.get('feasibility_note', '')}{where}",
                                size=11, color=fcolor))
        b = budget(o)
        if b:
            sign = lambda v: "+" if v >= 0 else "−"
            color = Colors.SUCCESS if b["meets"] else Colors.WARNING if b["left"] >= 0 else Colors.ERROR
            transport = "" if b["transport_how"] == "remote" else f" − {b['transport_how']} €{b['transport']:,.0f}"
            rows.append(ft.Text(
                f"{b['city']}: take-home ≈ €{b['net']:,.0f}/month (¥{b['net'] * jpy:,.0f}) − "
                f"{b.get('rent_label', 'rent')} €{b['rent']:,.0f} − living €{b['living']:,.0f}{transport}"
                + (f" − {b['home']} home kept €{b['kept_home']:,.0f}" if b.get("kept_home") else "")
                + f" = {sign(b['left'])}€{abs(b['left']):,.0f} a month"
                f" ({sign(b['left'])}¥{abs(b['left']) * jpy:,.0f})", size=12, weight=ft.FontWeight.BOLD, color=color))
            goal = (f"Meets your goal of saving €{b['target']:,.0f}/month." if b["meets"] else
                    f"Short of your €{b['target']:,.0f}/month savings goal by €{b['target'] - b['left']:,.0f}.")
            home = (f" {b['home']} costs ≈ €{b['home_cost']:,.0f}/month (¥{b['home_cost'] * jpy:,.0f})."
                    if b["home_cost"] else "")
            if b.get("community"):
                ccolor = {"strong": Colors.SUCCESS, "some": Colors.ACCENT}.get(b["community"], Colors.WARNING)
                rows.append(ft.Text(f"Japanese community: {b['community']}. {b.get('community_note', '')}",
                                    size=11, color=ccolor))
            if b.get("no_car_problem"):
                rows.append(ft.Text("⚠ Hard to reach without a car, and you would have none at first.",
                                    size=11, color=Colors.WARNING))
            rows.append(ft.Text(f"{goal}{home} {info.get('net_note', '')}", size=10,
                                color=Colors.SUCCESS if b["meets"] else Colors.TEXT_MUTED))
        return ft.Container(content=ft.Column(rows, spacing=2), padding=8, bgcolor=Colors.BG_TERTIARY,
                            border_radius=6)

    async def _run_investigations(self, offer_ids):
        """Investigate offers, 3 at a time; each card refreshes when its result is in."""
        import asyncio
        from analyzers.investigate import investigate
        ids = [i for i in offer_ids if i not in self._investigating]
        self._investigating.update(ids)
        self._show_library(highlight=self._last_new)
        sem = asyncio.Semaphore(3)

        async def one(i):
            async with sem:
                try:
                    await asyncio.to_thread(investigate, i)
                except Exception as ex:
                    self.search_status.value = f"Could not investigate offer {i}: {ex}"
                    self.search_status.color = Colors.WARNING
                finally:
                    self._investigating.discard(i)
                    self._show_library(highlight=self._last_new)

        await asyncio.gather(*(one(i) for i in ids))

    def _open_offer(self, offer_id: int, url: str):
        from core.offers import OfferLibrary
        lib = OfferLibrary()
        o = lib.get(offer_id)
        if o and o["status"] == "new":
            lib.set_status(offer_id, "seen")
        self._open_url(url)
        self._show_library()

    def _dismiss_offer(self, offer_id: int, status: str):
        from core.offers import OfferLibrary
        from core.wishes import REJECT_REASONS
        if status == "dismissed":
            OfferLibrary().restore(offer_id)
            self._show_library()
            return
        reason = ft.RadioGroup(value="experience", content=ft.Column(
            [ft.Radio(value=k, label=v) for k, v in REJECT_REASONS.items()], spacing=0))
        note = ft.TextField(label="Note (optional)", width=360, text_size=13)

        def done(e):
            OfferLibrary().reject(offer_id, reason.value, (note.value or "").strip())
            self._page.pop_dialog()
            self._show_library()

        self._page.show_dialog(ft.AlertDialog(
            title=ft.Text("Why not this one?"),
            content=ft.Column([ft.Text("Later searches avoid jobs turned down for the same reason.", size=12),
                               reason, note], tight=True, spacing=6),
            actions=[ft.TextButton("Cancel", on_click=lambda e: self._page.pop_dialog()),
                     ft.Button("Turn down", on_click=done)],
        ))

    async def _select_offer(self, offer_id: int):
        """Put the offer in the pipeline, then write the tailored CV and letter for it."""
        import asyncio
        from generators.application import prepare
        app_id = self._offer_to_pipeline(offer_id)
        if not app_id:
            return
        self._preparing.add(app_id)
        self._preparing_offers.add(offer_id)
        self._show_library()
        try:
            await asyncio.to_thread(prepare, app_id)
            msg = f"Pack ready: see Pipeline #{app_id} (CV, letter, how to apply)."
        except Exception as ex:
            msg = f"Saved to Pipeline #{app_id}, but the pack failed: {ex}. Retry from the Pipeline tab."
        finally:
            self._preparing.discard(app_id)
            self._preparing_offers.discard(offer_id)
        self._page.show_dialog(ft.SnackBar(content=ft.Text(msg)))
        self._show_library()

    def _offer_to_pipeline(self, offer_id: int):
        from core.offers import OfferLibrary
        from core.pipeline import Pipeline, load_channels
        lib = OfferLibrary()
        o = lib.get(offer_id)
        if not o:
            return
        loc = (o.get("location") or "").lower()
        country = "JP" if any(k in loc for k in ("japan", "osaka", "tokyo", "日本")) else \
                  "FR" if "france" in loc else "ANY"
        src = " ".join(l.get("source", "") for l in o["links"]).lower()
        channel = next((c["id"] for c in load_channels()
                        if c["country"] in (country, "ANY") and c["name"].split(" (")[0].lower() in src), "other")
        app = Pipeline().add(
            company=o["company"], role=o["title"], channel=channel, country=country, stage="found",
            url=o["links"][0]["url"], notes=f"Found by web search on {src or 'the web'}. {o.get('fit', '')}",
            fit={"match": o.get("match"), "salary": o.get("salary"), "seniority": o.get("seniority"),
                 "offer_id": offer_id},
        )
        lib.set_status(offer_id, "applied", pipeline_id=app["id"])
        return app["id"]

    def _analyze_offer(self, o: dict):
        from types import SimpleNamespace
        self._analyze_from_search(SimpleNamespace(url=o["links"][0]["url"], company=o["company"], title=o["title"]))

    # ===== Remote boards (Jobicy, Remotive) =====

    def _on_search(self, e):
        """Search the two remote job boards."""
        keywords = self.search_input.value.strip() if self.search_input.value else ""
        if not keywords:
            self._do_suggested_search()
        else:
            self._do_search(keywords)

    def _do_suggested_search(self):
        """Search using all profile-based suggestions."""
        self.search_btn.disabled = True
        self.search_status.value = "Searching worldwide remote jobs..."
        self.search_status.color = Colors.ACCENT
        self.results_list.controls.clear()
        self._page.update()

        try:
            from analyzers.job_searcher import JobSearcher

            searcher = JobSearcher()
            jobs = searcher.search_all_suggestions(limit_per_query=5)
            self.search_results = jobs

            if not jobs:
                self.search_status.value = "No jobs found. Try specific keywords."
                self.search_status.color = Colors.WARNING
            else:
                self.search_status.value = f"Found {len(jobs)} worldwide remote jobs"
                self.search_status.color = Colors.SUCCESS

                for job in jobs:
                    self.results_list.controls.append(self._create_job_card(job))

        except Exception as ex:
            self.search_status.value = f"Search error: {ex}"
            self.search_status.color = Colors.ERROR
            import traceback
            traceback.print_exc()

        finally:
            self.search_btn.disabled = False
            self._page.update()

    def _quick_search(self, keywords: str):
        """Perform a quick search with preset keywords."""
        self.search_input.value = keywords
        self._do_search(keywords)

    def _do_search(self, keywords: str):
        """Perform the actual search."""
        self.search_btn.disabled = True
        self.search_status.value = f"Searching for '{keywords}'..."
        self.search_status.color = Colors.ACCENT
        self.results_list.controls.clear()
        self._page.update()

        try:
            from analyzers.job_searcher import JobSearcher, SearchQuery

            searcher = JobSearcher()
            query = SearchQuery(
                keywords=keywords,
                remote_only=self.remote_only.value,
            )

            jobs = searcher.search(query, limit=15)
            self.search_results = jobs

            if not jobs:
                self.search_status.value = f"No jobs found for '{keywords}'. Try different keywords."
                self.search_status.color = Colors.WARNING
            else:
                self.search_status.value = f"Found {len(jobs)} jobs matching '{keywords}' (remote boards; REL = keyword relevance)"
                self.search_status.color = Colors.SUCCESS

                # Display results
                for job in jobs:
                    self.results_list.controls.append(
                        self._create_job_card(job)
                    )

        except Exception as ex:
            self.search_status.value = f"Search error: {ex}"
            self.search_status.color = Colors.ERROR
            import traceback
            traceback.print_exc()

        finally:
            self.search_btn.disabled = False
            self._page.update()

    def _create_job_card(self, job) -> ft.Container:
        """Create a card for a job listing."""
        # Score color
        score = job.quick_score
        if score >= 60:
            score_color = Colors.SUCCESS
        elif score >= 30:
            score_color = Colors.ACCENT
        else:
            score_color = Colors.TEXT_SECONDARY

        # Job type badge
        type_color = Colors.SUCCESS if job.job_type == 'remote' else Colors.TEXT_SECONDARY

        return ft.Container(
            content=ft.Row([
                # Relevance indicator (not a match score - just title/location relevance)
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("REL", size=8, color=Colors.TEXT_SECONDARY),
                            ft.Text(f"{score:.0f}", size=16, weight=ft.FontWeight.BOLD, color=score_color),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=0,
                    ),
                    width=40,
                ),
                # Job info
                ft.Column([
                    ft.Text(job.title, size=14, weight=ft.FontWeight.BOLD, color=Colors.TEXT_PRIMARY),
                    ft.Row([
                        ft.Text(job.company, size=12, color=Colors.ACCENT),
                        ft.Text(f" | {job.location}", size=12, color=Colors.TEXT_SECONDARY) if job.location else ft.Container(),
                        ft.Container(
                            content=ft.Text(job.job_type.upper(), size=10, color=type_color),
                            bgcolor=Colors.BG_TERTIARY,
                            padding=ft.padding.symmetric(horizontal=8, vertical=2),
                            border_radius=3,
                        ),
                    ], spacing=5),
                    ft.Text(job.snippet, size=12, color=Colors.TEXT_PRIMARY) if job.source not in ('jobicy', 'remotive', 'arbeitnow') and job.snippet else ft.Container(),
                    ft.Text(f"{job.source}" + (f" · posted {job.posted}" if job.posted else ""), size=10, color=Colors.TEXT_SECONDARY),
                ], spacing=2, expand=True),
                # Actions
                ft.Column([
                    ft.IconButton(
                        icon=ft.Icons.OPEN_IN_NEW,
                        icon_color=Colors.ACCENT,
                        tooltip="Open in browser",
                        on_click=lambda e, url=job.url: self._open_url(url),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.ANALYTICS,
                        icon_color=Colors.TEXT_SECONDARY,
                        tooltip="Full analysis",
                        on_click=lambda e, j=job: self._analyze_from_search(j),
                    ),
                ], spacing=0),
            ], alignment=ft.MainAxisAlignment.START),
            bgcolor=Colors.BG_SECONDARY,
            border_radius=8,
            padding=10,
            on_click=lambda e, url=job.url: self._open_url(url),
        )

    def _open_url(self, url: str):
        """Open URL in browser."""
        if url:
            import webbrowser
            webbrowser.open(url)

    def _analyze_from_search(self, job):
        """Switch to analyze tab and analyze this job."""
        # Fill in the URL and switch tabs
        self.url_input.value = job.url
        self.company_field.value = job.company
        self.role_field.value = job.title
        self._switch_tab(0)

        # Trigger analysis
        if job.url:
            self._page.run_task(self._on_analyze_url, None)

    # ===== Analyze tab methods =====

    async def _on_analyze_url(self, e):
        """Fetch the posting, then analyze it."""
        import asyncio
        url = self.url_input.value.strip()
        if not url:
            self._show_error("Please enter a job URL")
            return
        self._set_analyzing(True)
        try:
            from analyzers.job_analyzer import JobAnalyzer
            job = await asyncio.to_thread(JobAnalyzer().fetch_job, url)
            if not job:
                self._show_error("Could not fetch job posting. Try pasting the text instead.")
                return
            if job.company:
                self.company_field.value = job.company
            if job.title:
                self.role_field.value = job.title
            await self._analyze(job.raw_text, job=job)
        except Exception as ex:
            self._show_error(f"Error: {ex}")
        finally:
            self._set_analyzing(False)

    async def _on_analyze_text(self, e):
        """Analyze pasted posting text."""
        text = self.job_text.value.strip()
        if not text:
            self._show_error("Please paste a job description")
            return
        self._set_analyzing(True)
        try:
            await self._analyze(text)
        except Exception as ex:
            self._show_error(f"Error: {ex}")
        finally:
            self._set_analyzing(False)

    async def _analyze(self, text: str, job=None):
        """Claude's reading (triage) is the score; the keyword count is only a footnote."""
        import asyncio
        from analyzers.job_analyzer import JobAnalyzer
        from analyzers.triage import triage
        analyzer = JobAnalyzer()
        if job is not None:
            keyword = analyzer.analyze(job)
        else:
            keyword = analyzer.analyze_text(text, title=self.role_field.value or "",
                                            company=self.company_field.value or "")
        tri = await asyncio.to_thread(triage, text)
        self._display_results(keyword, tri)

    def _display_results(self, result, tri=None):
        """Display analysis results. `tri` (triage) drives the score; keywords are a footnote."""
        self.current_analysis = result
        self.current_job = result.job

        verdict_colors = {"realistic": Colors.SUCCESS, "stretch": Colors.WARNING, "skip": Colors.ERROR}
        if tri is not None and tri.match is not None:
            score, label = tri.match, f"{tri.verdict.upper()} · Claude's reading"
            color = verdict_colors.get(tri.verdict, Colors.ACCENT)
        elif tri is not None:
            score, label = None, f"{tri.verdict.upper()} · rules only ({tri.note or 'Claude unavailable'})"
            color = verdict_colors.get(tri.verdict, Colors.ACCENT)
        else:
            score, label, color = result.score, "keyword overlap only", Colors.TEXT_SECONDARY

        self.match_score.content = ft.Column([
            ft.Text("MATCH", size=12, color=Colors.TEXT_SECONDARY),
            ft.Text(f"{score:.0f}" if score is not None else "–", size=48, weight=ft.FontWeight.BOLD, color=color),
            ft.Text(label, size=10, color=color, text_align=ft.TextAlign.CENTER),
            ft.Text(f"Keyword overlap {result.score:.0f}% (word count, not a verdict)" if result.job.keywords
                    else "No keyword count: posting not in English", size=9,
                    color=Colors.TEXT_MUTED, text_align=ft.TextAlign.CENTER),
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

        # Update job info
        job = result.job
        if job:
            job_details = []
            if job.title:
                job_details.append(ft.Text(job.title, size=16, weight=ft.FontWeight.BOLD, color=Colors.TEXT_PRIMARY))
            if job.company:
                job_details.append(ft.Text(job.company, size=14, color=Colors.ACCENT))
            if job.location:
                job_details.append(ft.Text(f"Location: {job.location}", size=12, color=Colors.TEXT_SECONDARY))
            if job.job_type:
                type_color = Colors.SUCCESS if job.job_type == 'remote' else Colors.TEXT_SECONDARY
                job_details.append(ft.Text(f"Type: {job.job_type.title()}", size=12, color=type_color))
            if job.keywords:
                job_details.append(ft.Text(f"Keywords: {', '.join(job.keywords[:8])}", size=11, color=Colors.TEXT_SECONDARY))

            self.job_info.content = ft.Column(job_details, spacing=5)

        # Update strengths
        strength_items = [ft.Text("YOUR STRENGTHS", size=12, weight=ft.FontWeight.BOLD, color=Colors.SUCCESS)]
        if tri is not None:
            for r in tri.reasons:
                strength_items.append(ft.Text(f"• {r}", size=11, color=Colors.TEXT_PRIMARY))
            for fl in tri.flags:
                if fl.level == "plus":
                    strength_items.append(ft.Text(f"+ {fl.text}", size=11, color=Colors.TEXT_PRIMARY))
            if tri.documents:
                strength_items.append(ft.Text("Send: " + ", ".join(Path(d["file"]).name for d in tri.documents),
                                              size=11, color=Colors.ACCENT))
        for s in ([] if tri is not None else result.strengths[:8]):
            strength_items.append(ft.Text(f"+ {s}", size=11, color=Colors.TEXT_PRIMARY))
        if not result.strengths:
            strength_items.append(ft.Text("No direct matches found", size=11, color=Colors.TEXT_SECONDARY))
        self.strengths_panel.content = ft.Column(strength_items, scroll=ft.ScrollMode.AUTO, spacing=3)

        # Update gaps
        gap_items = [ft.Text("GAPS TO ADDRESS", size=12, weight=ft.FontWeight.BOLD, color=Colors.WARNING)]
        if tri is not None:
            for fl in tri.flags:
                if fl.level in ("blocker", "stretch", "note"):
                    gap_items.append(ft.Text(f"{'✗' if fl.level == 'blocker' else '!'} {fl.text}", size=11,
                                             color=Colors.ERROR if fl.level == "blocker" else Colors.TEXT_PRIMARY))
        for g in result.gaps[:5]:
            gap_items.append(ft.Text(f"- {g}", size=11, color=Colors.TEXT_PRIMARY))
        if result.keywords_missing:
            gap_items.append(ft.Text(f"Keywords: {', '.join(result.keywords_missing[:5])}", size=10, color=Colors.TEXT_SECONDARY))
        if not result.gaps and not result.keywords_missing:
            gap_items.append(ft.Text("No critical gaps identified", size=11, color=Colors.SUCCESS))
        self.gaps_panel.content = ft.Column(gap_items, scroll=ft.ScrollMode.AUTO, spacing=3)

        # Show action buttons
        self.generate_letter_btn.visible = True
        self.save_job_btn.visible = True

        self._page.update()

    def _on_generate_letter(self, e):
        """Generate cover letter for this job."""
        if self._on_generate_cover_letter and self.current_job:
            job_data = {
                'description': self.current_job.raw_text or self.job_text.value,
                'company': self.company_field.value or self.current_job.company,
                'role': self.role_field.value or self.current_job.title,
            }
            self._on_generate_cover_letter(job_data)

    def _on_save_job(self, e):
        """Save job to tracker."""
        try:
            from ..storage import JobTracker

            tracker = JobTracker()
            tracker.add_job(
                company=self.company_field.value or (self.current_job.company if self.current_job else "Unknown"),
                role=self.role_field.value or (self.current_job.title if self.current_job else "Unknown"),
                job_description=(self.current_job.raw_text[:500] if self.current_job else self.job_text.value[:500]),
                match_score=self.current_analysis.score if self.current_analysis else 0,
                url=self.current_job.url if self.current_job else "",
            )

            self._snack = ft.SnackBar(
                content=ft.Text("Job saved to tracker"),
                bgcolor=Colors.SUCCESS
            )
            self._page.show_dialog(self._snack)
            self.save_job_btn.visible = False
            self._page.update()

        except Exception as ex:
            self._show_error(f"Error saving job: {ex}")

    def _set_analyzing(self, analyzing: bool):
        """Update UI state during analysis."""
        self.analyze_url_btn.disabled = analyzing
        self.analyze_text_btn.disabled = analyzing

        if not analyzing and self.match_score.content.controls[0].value == "ANALYZING":
            self.match_score.content = ft.Column([      # failed: no spinner left behind
                ft.Text("MATCH", size=12, color=Colors.TEXT_SECONDARY),
                ft.Text("--", size=48, weight=ft.FontWeight.BOLD, color=Colors.TEXT_SECONDARY),
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        if analyzing:
            self.match_score.content = ft.Column([
                ft.Text("ANALYZING", size=12, color=Colors.TEXT_SECONDARY),
                ft.ProgressRing(width=40, height=40, color=Colors.ACCENT),
                ft.Text("Please wait...", size=11, color=Colors.TEXT_SECONDARY),
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

        self._page.update()

    def _show_error(self, message: str):
        """Show error message."""
        self._snack = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=Colors.ERROR
        )
        self._page.show_dialog(self._snack)
        self._page.update()
