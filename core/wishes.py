"""
Wishes - what a job must give him, in data/wishes.yaml.

Order of importance (his words): CV and experience first, then where, then money.
- places: where he would live and work, in order of preference. A remote job may be done from any of them
  if the employer and the countries allow it.
- save_eur: what he hopes to save each month, after tax, rent, living and transport costs.
- Reasons he turned offers down, so the search stops proposing the same kind of job.
"""

from pathlib import Path

import yaml

from core.store import read_yaml

ROOT = Path(__file__).parent.parent
WISHES_FILE = ROOT / "data" / "wishes.yaml"

# Choices shown in the UI. Each is "City, Country" so the cost of living can be looked up.
PLACE_CHOICES = [
    "Osaka, Japan", "Kyoto, Japan", "Kobe, Japan", "Tokyo, Japan", "Fukuoka, Japan",
    "Paris, France", "Lyon, France", "Toulouse, France", "Bordeaux, France", "Lille, France",
    "Marseille, France", "Nantes, France", "Montpellier, France",
    "Lisbon, Portugal", "Porto, Portugal", "Barcelona, Spain", "Madrid, Spain", "Valencia, Spain",
    "Malaga, Spain", "Brussels, Belgium", "Luxembourg, Luxembourg", "Geneva, Switzerland",
    "Dublin, Ireland", "Amsterdam, Netherlands", "Berlin, Germany", "Athens, Greece",
    "Sofia, Bulgaria", "Bucharest, Romania", "Warsaw, Poland", "Prague, Czechia",
]

REJECT_REASONS = {
    "experience": "Not enough experience for it",
    "savings": "Could not save enough",
    "place": "Wrong place / would need a move I don't want",
    "language": "Language I don't have",
    "rights": "Can't legally do it (work rights, remote from here)",
    "employer": "Employer red flags or agency",
    "contract": "Contract, hours or shifts",
    "too_low": "Below my level",
    "other": "Other",
}

DEFAULTS = {
    "places": ["Osaka, Japan"],
    "home": "Osaka, Japan",          # where he lives now; remote jobs are costed here unless he picks another place
    "save_eur": 500,
    # The Osaka home is owned outright: no rent, but building fees and property tax.
    # Starting figures are estimates (building fees from listings for the building); he corrects them.
    "home_owned": True,
    "home_fees_jpy_month": 19000,      # 管理費 + 修繕積立金
    "home_tax_jpy_year": 120000,       # 固定資産税・都市計画税
    "home_estimated": True,
    "keep_home_when_moving": True,     # the Osaka home costs continue if he takes a job elsewhere
    # Who would move: rent and living costs are for this household, in a convenient area.
    "household": "a couple aged 50 and 55",
    "have_car": False,                 # no car at first after a move
    "other_income_eur": 0,
    # Working from Japan (Osaka job, or remote from Japan): his wife works too, so he pays a share.
    "japan_share_jpy": 105000,         # his part of the house spending (home costs included)
    "japan_personal_jpy": 35000,       # his own subscriptions and spending             # the household's other monthly income, net (e.g. his wife's)
    "manual_ok_japan": True,           # factory, warehouse and other manual work in Japan are fine
    "japanese_community": True,        # prefer places with a strong Japanese community (for his wife)
    "avoid_sites": ["stanby.com"],     # sites he does not trust: never linked, never searched
}


def avoided(url: str, w: dict = None) -> bool:
    """True when the link is on a site he chose to avoid."""
    from urllib.parse import urlparse
    host = (urlparse(url or "").hostname or "").lower()
    sites = (w or load()).get("avoid_sites") or []
    return any(host == s or host.endswith("." + s) for s in (x.strip().lower() for x in sites) if s)


def home_cost_eur(w: dict = None) -> float:
    """Monthly cost of the owned home, in EUR (0 if he does not own)."""
    from core.offers import fx_rates
    w = w or load()
    if not w.get("home_owned"):
        return 0.0
    jpy = w.get("home_fees_jpy_month", 0) + w.get("home_tax_jpy_year", 0) / 12
    return jpy / fx_rates().get("JPY", 177.8)


def load() -> dict:
    w = dict(DEFAULTS)
    if WISHES_FILE.exists():
        w.update(read_yaml(WISHES_FILE))
    return w


def save(w: dict):
    WISHES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(WISHES_FILE, "w", encoding="utf-8") as f:
        yaml.dump(w, f, allow_unicode=True, sort_keys=False)


def split_place(place: str) -> tuple[str, str]:
    city, _, country = place.partition(",")
    return city.strip(), country.strip() or city.strip()


def place_rank(location: str, w: dict = None) -> int:
    """0 for his first place, 1 for the second... len(places) when it is none of them."""
    w = w or load()
    loc = (location or "").lower()
    for i, p in enumerate(w["places"]):
        city, country = split_place(p)
        if city.lower() in loc:
            return i
    for i, p in enumerate(w["places"]):          # same country, other city
        if split_place(p)[1].lower() in loc:
            return i + 0.5
    return len(w["places"])


def for_prompt(w: dict = None) -> str:
    """The wishes and past rejections, for the search prompt."""
    from core.offers import OfferLibrary
    w = w or load()
    lines = [f"Places he would live and work, best first: {'; '.join(w['places'])}. He lives in {w['home']} now.",
             f"He wants to save about €{w['save_eur']:,.0f} a month after tax, social charges, rent, "
             "living and transport costs in that place. Prefer pay that allows it there."]
    lines.append(f"Household if he moves: {w['household']}, no car at first." if not w.get("have_car")
                 else f"Household if he moves: {w['household']}.")
    if w.get("manual_ok_japan"):
        lines.append("In Japan, factory, manufacturing, warehouse, logistics and other manual work (製造, 工場, "
                     "軽作業, 倉庫) are fine for him: he worked 4 years in a Japanese plating plant (Eishin Techno). "
                     "Include such jobs in Japan alongside office roles.")
    if w.get("avoid_sites"):
        lines.append("Sites he does not trust, never use or link them (find the original listing on the "
                     "employer's site or another board instead): " + ", ".join(w["avoid_sites"]) + ".")
    if w.get("japanese_community"):
        lines.append("His wife is Japanese: among equal jobs, prefer cities with a strong Japanese community.")
    rejected = [o for o in OfferLibrary().offers if o.get("reject_reason")]
    if rejected:
        lines.append("He turned these down before; do not propose jobs like them for the same reason:")
        lines += [f"- {o['title']} — {o['company']} ({o.get('location', '')}): "
                  f"{REJECT_REASONS.get(o['reject_reason'], o['reject_reason'])}"
                  + (f" — {o['reject_note']}" if o.get("reject_note") else "")
                  for o in rejected[-40:]]
    return "\n".join(lines)
