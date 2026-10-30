"""
Offer library - every posting the web search has found, in data/offers.yaml.

- The same job on several sites is merged into one offer (all links kept).
- Offers older than WINDOW_DAYS are hidden but kept, so they are not shown as new again.
- Each offer knows whether it was opened, dismissed, or is already in the pipeline.
- Salaries are converted to yearly EUR and JPY at ECB rates (cached daily).
"""

import json
import re
import unicodedata
from datetime import date, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional

import yaml

from core.store import read_yaml, write_yaml, LOCK, fresh

try:
    import requests
except ImportError:
    requests = None

ROOT = Path(__file__).parent.parent
DATA_FILE = ROOT / "data" / "offers.yaml"
FX_FILE = ROOT / "data" / "fx.json"
WINDOW_DAYS = 7

# Used only when the rate service cannot be reached (EUR base, Oct 2026)
FX_FALLBACK = {"EUR": 1.0, "JPY": 177.8, "USD": 1.125, "GBP": 0.844, "CHF": 0.927, "PLN": 4.37,
               "RON": 5.33, "CZK": 24.3, "SEK": 11.1, "DKK": 7.47, "HUF": 363.0}
PERIOD_TO_YEAR = {"year": 1, "month": 12, "week": 52, "day": 220, "hour": 1800}


# --- money -------------------------------------------------------------------

def fx_rates() -> dict:
    """EUR-based rates from the ECB (frankfurter.dev): published each working day around 16:00 CET.
    Fetched once a day (30 minutes after a failed try). FX_FALLBACK is only used if the
    rates were never fetched at all."""
    import time
    cached = json.loads(FX_FILE.read_text(encoding="utf-8")) if FX_FILE.exists() else {}
    age = time.time() - cached.get("checked", 0)
    if cached.get("rates") and age < (1800 if cached.get("stale") else 24 * 3600):
        return cached["rates"]
    if requests:
        try:
            r = requests.get("https://api.frankfurter.dev/v1/latest?base=EUR", timeout=10)
            data = r.json()
            rates = {"EUR": 1.0, **data["rates"]}
            FX_FILE.parent.mkdir(parents=True, exist_ok=True)
            FX_FILE.write_text(json.dumps({"checked": time.time(), "date": data.get("date", ""), "rates": rates}),
                               encoding="utf-8")
            return rates
        except Exception:
            pass
    # Offline: keep the last rates, and try again in 30 minutes (not on every card)
    rates = cached.get("rates") or FX_FALLBACK
    try:
        FX_FILE.parent.mkdir(parents=True, exist_ok=True)
        FX_FILE.write_text(json.dumps({**cached, "checked": time.time(), "rates": rates, "stale": True}),
                           encoding="utf-8")
    except OSError:
        pass
    return rates


def fx_date() -> str:
    """The ECB date of the rates in use, e.g. "2026-10-21", or "" if unknown."""
    fx_rates()
    try:
        return json.loads(FX_FILE.read_text(encoding="utf-8")).get("date", "")
    except (OSError, ValueError):
        return ""


def fx_note() -> str:
    """One line for under a salary: which rates were used."""
    r, d = fx_rates(), fx_date()
    return f"€1 = ${r.get('USD', 0):.4f} = ¥{r.get('JPY', 0):.2f}" + (f" (ECB, {d})" if d else " (offline fallback)")


def yearly(salary: dict) -> Optional[tuple]:
    """(min_eur, max_eur, min_jpy, max_jpy) per year, or None."""
    if not salary or not salary.get("min"):
        return None
    rates = fx_rates()
    cur = (salary.get("currency") or "EUR").upper()
    if cur not in rates:
        return None
    k = PERIOD_TO_YEAR.get(salary.get("period") or "year", 1)
    lo = salary["min"] * k / rates[cur]
    hi = (salary.get("max") or salary["min"]) * k / rates[cur]
    return lo, hi, lo * rates["JPY"], hi * rates["JPY"]


def salary_text(salary: dict) -> str:
    y = yearly(salary)
    if not y:
        return "Salary unknown"
    lo, hi, jlo, jhi = y

    def eur(v):
        return f"€{v / 1000:.0f}k"

    def jpy(v):
        return f"¥{v / 1_000_000:.1f}M"

    def usd(v):
        return f"${v / 1000:.0f}k"

    usd_rate = fx_rates().get("USD", FX_FALLBACK["USD"])
    ulo, uhi = lo * usd_rate, hi * usd_rate
    rng_e = eur(lo) if abs(hi - lo) < 500 else f"{eur(lo)}–{eur(hi)}"
    rng_u = usd(ulo) if abs(uhi - ulo) < 500 else f"{usd(ulo)}–{usd(uhi)}"
    rng_j = jpy(jlo) if abs(jhi - jlo) < 50_000 else f"{jpy(jlo)}–{jpy(jhi)}"
    tag = "estimate" if salary.get("estimated") else "posted"
    return f"{rng_e} / {rng_u} / {rng_j} a year ({tag})"


# --- matching ------------------------------------------------------------------

SUFFIXES = r"\b(inc|ltd|llc|gmbh|sas|sa|sarl|srl|bv|ag|plc|co|corp|group|kk|株式会社)\b"


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFKC", text or "").lower()
    t = re.sub(r"\(.*?\)", " ", t)                       # (m/f/d), (for client)...
    t = re.sub(r"\b[hf]\s*/\s*[hf]\b|\bm\s*/\s*[wf]\s*/\s*d\b", " ", t)
    t = re.sub(SUFFIXES, " ", t)
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _places_differ(a: str, b: str) -> bool:
    """True only when both locations are given and share no place word (Lisbon vs Athens)."""
    wa = {w for w in _norm(a).split() if len(w) >= 4 and not w.isdigit()}
    wb = {w for w in _norm(b).split() if len(w) >= 4 and not w.isdigit()}
    return bool(wa and wb and not wa & wb)


def same_job(a_title, a_company, b_title, b_company, a_loc: str = "", b_loc: str = "") -> bool:
    ca, cb = _norm(a_company), _norm(b_company)
    ta, tb = _norm(a_title), _norm(b_title)
    company_match = ca and cb and (ca == cb or ca in cb or cb in ca)
    return bool(company_match and SequenceMatcher(None, ta, tb).ratio() >= 0.8
                and not _places_differ(a_loc, b_loc))


def posted_date(text: str, today: Optional[date] = None) -> Optional[str]:
    """ISO date from '2026-10-15', '3 days ago', '2 weeks ago', 'today'..."""
    today = today or date.today()
    t = (text or "").lower()
    m = re.search(r"(20\d\d)-(\d\d)-(\d\d)", t)
    if m:
        return m.group(0) if m.group(0) <= today.isoformat() else None   # a closing date is not a posting date
    if "today" in t or "hours ago" in t or "hour ago" in t:
        return today.isoformat()
    if "yesterday" in t:
        return (today - timedelta(days=1)).isoformat()
    m = re.search(r"(\d+)\s*(day|week|month)", t)
    if m:
        n = int(m.group(1)) * {"day": 1, "week": 7, "month": 30}[m.group(2)]
        return (today - timedelta(days=n)).isoformat()
    return None


# --- library -------------------------------------------------------------------

class OfferLibrary:
    def __init__(self, data_file: Path = DATA_FILE):
        self.data_file = data_file
        self.reload()

    def reload(self):
        self.offers: list[dict] = []
        if self.data_file.exists():
            self.offers = read_yaml(self.data_file).get("offers", [])

    def save(self):
        write_yaml(self.data_file, {"offers": self.offers})

    def get(self, offer_id: int) -> Optional[dict]:
        return next((o for o in self.offers if o["id"] == offer_id), None)

    def find(self, title: str, company: str, location: str = "") -> Optional[dict]:
        return next((o for o in self.offers
                     if same_job(title, company, o["title"], o["company"], location, o.get("location", ""))), None)

    def add(self, found: dict, today: Optional[str] = None) -> tuple[dict, bool]:
        """Add one search result. Returns (offer, is_new). Duplicates merge their links."""
        today = today or date.today().isoformat()
        links = [{"url": found["url"], "source": found.get("source", "")}] + \
                [{"url": u, "source": ""} for u in found.get("other_urls", [])]
        existing = self.find(found["title"], found["company"], found.get("location", ""))
        if existing:
            known = {l["url"] for l in existing["links"]}
            existing["links"] += [l for l in links if l["url"] not in known]
            existing["last_seen"] = today
            existing["posted"] = existing.get("posted") or posted_date(found.get("posted", ""))
            return existing, False
        offer = {
            "id": max((o["id"] for o in self.offers), default=0) + 1,
            "title": found["title"],
            "company": found["company"],
            "location": found.get("location", ""),
            "links": links,
            "posted": posted_date(found.get("posted", "")),
            "first_seen": today,
            "last_seen": today,
            "salary": found.get("salary"),
            "seniority": found.get("seniority", ""),
            "match": found.get("match"),
            "fit": found.get("fit", ""),
            "languages": found.get("languages", ""),
            "work_rights": found.get("work_rights", ""),
            "status": "new",          # new | seen | dismissed | applied
            "pipeline_id": None,
        }
        self.offers.append(offer)
        return offer, True

    def merge_into(self, offer_id: int, found: dict):
        """A search result that is a known job under another name or language: keep its links."""
        o = self.get(offer_id)
        links = [{"url": found["url"], "source": found.get("source", "")}] + \
                [{"url": u, "source": ""} for u in found.get("other_urls", [])]
        known = {l["url"] for l in o["links"]}
        o["links"] += [l for l in links if l["url"] not in known]
        o["last_seen"] = date.today().isoformat()
        aka = f"{found['title']} — {found['company']}"
        if aka != f"{o['title']} — {o['company']}" and aka not in o.setdefault("also_listed_as", []):
            o["also_listed_as"].append(aka)

    @fresh
    def set_status(self, offer_id: int, status: str, pipeline_id: Optional[int] = None):
        o = self.get(offer_id)
        if o:
            o["status"] = status
            if pipeline_id:
                o["pipeline_id"] = pipeline_id
            self.save()

    @fresh
    def reject(self, offer_id: int, reason: str, note: str = ""):
        """He turned it down. The reason is passed to later searches (core/wishes.py)."""
        o = self.get(offer_id)
        if o:
            o.update(status="dismissed", reject_reason=reason, reject_note=note, rejected_on=date.today().isoformat())
            self.save()

    @fresh
    def restore(self, offer_id: int):
        o = self.get(offer_id)
        if o:
            o["status"] = "seen"
            for k in ("reject_reason", "reject_note", "rejected_on"):
                o.pop(k, None)
            self.save()

    def age_days(self, offer: dict) -> int:
        ref = offer.get("posted") or offer["first_seen"]
        return (date.today() - date.fromisoformat(ref)).days

    def current(self, include_dismissed: bool = False) -> list[dict]:
        """Offers online for up to WINDOW_DAYS. Ranked as he asked: CV fit, place, Japanese community, money."""
        from core.wishes import load, place_rank
        out = [o for o in self.offers if self.age_days(o) <= WINDOW_DAYS
               and (include_dismissed or o["status"] != "dismissed")]
        w = load()
        return sorted(out, key=lambda o: rank_key(o, w, place_rank))

    def known_for_prompt(self, days: int = 21) -> str:
        """Recent offers, so Claude looks for other ones."""
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        rows = [f"- {o['title']} — {o['company']}" for o in self.offers if o["last_seen"] >= cutoff]
        return "\n".join(rows[-80:])


def rank_key(o: dict, w: dict, place_rank) -> tuple:
    """CV fit in steps of 10, then his place order, then what is left each month."""
    from analyzers.investigate import budget
    info = o.get("company_info") or {}
    where = info.get("city", "") + " " + info.get("country", "") if info else o.get("location", "")
    b = budget(o) if info else None
    community = {"strong": 0, "some": 1, "little": 2}.get((b or {}).get("community"), 1) \
        if w.get("japanese_community") else 0
    return (-((o.get("match") or 0) // 10), place_rank(where, w), community, -(b["left"] if b else -1e9))


TOO_MUCH_JAPANESE = ("N3", "N2", "N1")       # he has N4: above that, he will be refused


def japanese_too_high(o: dict) -> bool:
    return (o.get("company_info") or {}).get("japanese_required") in TOO_MUCH_JAPANESE


def in_pipeline(offer: dict) -> Optional[dict]:
    """The pipeline entry for this job, whatever site it was applied through."""
    from core.pipeline import Pipeline
    if offer.get("pipeline_id"):
        app = Pipeline().get(offer["pipeline_id"])
        if app:
            return app
    return next((a for a in Pipeline().apps
                 if (a.get("fit") or {}).get("offer_id") in (None, offer["id"])
                 and same_job(offer["title"], offer["company"], a["role"], a["company"])), None)
