"""
Investigate an offer: who the employer is, and whether the pay is livable there.

Two Claude Code calls with web search:
- company + take-home pay for this offer (per offer)
- monthly cost of living for a city (cached 90 days in data/cities.yaml, shared by all offers)
Remote jobs are costed in the first of his places (core/wishes.py) he could legally work from.
Take-home includes local taxes; transport is a transit pass, or a car where one is needed.
"""

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import yaml

from core.llm import run_claude_code, LLMError
from core.offers import OfferLibrary, yearly
from analyzers.web_search import WORK_RIGHTS

ROOT = Path(__file__).parent.parent
CITIES_FILE = ROOT / "data" / "cities.yaml"
CITY_TTL_DAYS = 90
from core.store import read_yaml, LOCK as _write_lock   # shared with every other store

CONTRACT = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": ["permanent", "fixed_term", "agency", "contractor", "unknown"]},
        "local_term": {"type": "string"},
        "trial": {"type": "string"},
        "hours": {"type": "string"},
        "benefits": {"type": "array", "items": {"type": "string"}},
        "missing": {"type": "array", "items": {"type": "string"}},
        "concerns": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["kind", "local_term", "trial", "hours", "benefits", "missing", "concerns"],
    "additionalProperties": False,
}

COMPANY_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "size": {"type": "string"},
        "rating": {"type": "string"},
        "pros": {"type": "array", "items": {"type": "string"}},
        "cons": {"type": "array", "items": {"type": "string"}},
        "red_flags": {"type": "array", "items": {"type": "string"}},
        "employer_is_agency": {"type": "boolean"},
        "net_monthly_eur": {"type": "number"},
        "net_note": {"type": "string"},
        "city": {"type": "string"},
        "country": {"type": "string"},
        "remote": {"type": "boolean"},
        "remote_from": {"type": "array", "items": {"type": "string"}},
        "feasibility": {"type": "string", "enum": ["ok", "check", "no"]},
        "feasibility_note": {"type": "string"},
        "car_needed": {"type": "boolean"},
        "commute_paid": {"type": "boolean"},
        "japanese_required": {"type": "string",
                              "enum": ["none", "N5", "N4", "conversational", "N3", "N2", "N1", "unknown"]},
        "japanese_note": {"type": "string"},
        "contract": CONTRACT,
        "sources": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["summary", "size", "rating", "pros", "cons", "red_flags", "employer_is_agency",
                 "net_monthly_eur", "net_note", "city", "country", "remote", "remote_from", "feasibility",
                 "feasibility_note", "car_needed", "commute_paid", "japanese_required", "japanese_note",
                 "contract", "sources"],
    "additionalProperties": False,
}

CITY_SCHEMA = {
    "type": "object",
    "properties": {
        "rent_eur": {"type": "number"},
        "living_eur": {"type": "number"},
        "transit_eur": {"type": "number"},
        "car_eur": {"type": "number"},
        "transit_good": {"type": "boolean"},
        "japanese_community": {"type": "string", "enum": ["strong", "some", "little"]},
        "community_note": {"type": "string"},
        "note": {"type": "string"},
        "sources": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["rent_eur", "living_eur", "transit_eur", "car_eur", "transit_good", "japanese_community",
                 "community_note", "note", "sources"],
    "additionalProperties": False,
}

COMPANY_SYSTEM = """You research an employer and the job's practical side for a job seeker, using web search.
Be factual and brief. The job seeker: {rights} Moving within the EU needs no permit for him.
Write every note to him directly, as 'you'/'your' (never 'he' or 'his').
- summary: one sentence on what the company does. size: employees or "unknown".
- rating: employee review score with source and review count (e.g. "Glassdoor 3.4/5, 1,200 reviews"), or "none found".
- pros / cons: up to 3 each, from employee reviews or reliable reporting. red_flags: only real ones
  (mass layoffs, unpaid wages, lawsuits, fake-job reports, very high churn), else empty.
- employer_is_agency: true if the poster is a recruiter or outsourcer hiring for someone else.
- remote: true if the job can be done fully remote.
- remote_from: for a remote job, which of his places he could legally do it from, given the employer's
  country, the posting (hiring countries, employer of record, contractor) and tax/social-security residency.
  Inside the EU this is usually fine; from Japan for a European employer it usually needs a contractor
  or employer-of-record setup. Empty for an on-site job.
- feasibility: "ok" he can take this job from one of his places without a legal or practical problem;
  "check" something must be confirmed (contractor status, residency, relocation); "no" he cannot.
  feasibility_note: one line saying why.
- city / country: where he would live for this job. On site: the job's city. Remote: the first of his places
  in remote_from (his places are listed in the prompt, best first).
- net_monthly_eur: estimated monthly take-home pay in EUR for a single person living in that city, at the
  middle of the given gross salary, after income tax, social charges AND local or resident taxes (e.g.
  Japan's 住民税, Spain's regional rate). For a contractor setup, after self-employed charges.
  net_note: one line on how.
- car_needed: true if the workplace is hard to reach without a car (on-site jobs only).
- commute_paid: true only if the posting or the employer says commuting costs are paid
  (交通費支給 / 交通費全額支給, transport allowance, prise en charge transport). False if unknown or remote.
- japanese_required: the Japanese level the job really needs, read from the posting itself (open it):
  "none" (no Japanese needed), "N5", "N4" (簡単な日本語, 挨拶程度, 外国人歓迎 with simple Japanese),
  "conversational" (日常会話 with no level given), "N3", "N2" (ビジネスレベル, 読み書き, 敬語), "N1" (ネイティブ,
  流暢), "unknown". A JLPT level written in the posting wins. A Japanese posting with no language line,
  for a job dealing with customers or documents in Japanese, is at least "N3".
  japanese_note: the exact words of the posting about Japanese (keep the Japanese), or why you chose.
- contract: the terms, from the posting (and the employer's usual practice if the posting is silent):
  kind; local_term (正社員 / 契約社員 / 派遣 / 業務委託, CDI / CDD / intérim / freelance, etc.);
  trial (probation length); hours (full-time, shifts, nights, weekends);
  benefits actually stated (social insurance 社会保険, transport allowance 交通費, bonus 賞与, paid leave 有給,
  13th month, tickets restaurant, mutuelle, remote allowance...); missing: the usual ones for that country
  the posting does not mention; concerns: real ones only (fixed term with no renewal, agency margin,
  contractor without social cover, unpaid training week, commission-only).
- sources: the URLs you used. Never invent numbers; say "unknown" when you found nothing."""

CITY_SYSTEM = """You estimate the monthly cost of living in EUR for the household described, using web search
(Numbeo, national statistics, current rental listings).
rent_eur: a flat that suits this household: two rooms (one bedroom plus living room, about 50-65 m²), in a
  convenient, quiet residential area a short walk from a train/metro/tram stop and shops, not student or shared
  housing, not luxury. Use listing prices, which are higher than averages for long-time tenants.
living_eur: everything else for the whole household except transport (food, utilities, phones, internet,
  top-up health cover). Do not count public health insurance or pension: they are taken from the salary.
transit_eur: monthly public transport passes for all adults in the household. car_eur: running one small used
  car (insurance, fuel, parking, upkeep, amortisation). transit_good: true if this household can live there
  comfortably without a car.
japanese_community: how present Japanese life is there for a Japanese spouse: "strong" (a sizeable Japanese
  resident community, Japanese grocers and restaurants, associations, a Japanese school or church, consulate),
  "some", or "little". community_note: one line with the facts (resident numbers, places, groups).
Always search the web first: current rental listings for that city, a cost-of-living index, and the Japanese
community (e.g. Japan's MOFA overseas residents statistics, local associations). Never answer from memory;
sources must be the pages you used.
note: one line with the main source and date. sources: the URLs you used."""


# --- cities -------------------------------------------------------------------

def _load_cities() -> dict:
    if CITIES_FILE.exists():
        return read_yaml(CITIES_FILE)
    return {}


def city_key(city: str, country: str) -> str:
    return f"{city.strip().lower()}, {country.strip().lower()}"


def _household() -> str:
    from core.wishes import load
    return load()["household"]


def get_city(city: str, country: str) -> dict:
    cities = _load_cities()
    key = city_key(city, country)
    hit = cities.get(key)
    if hit and hit.get("household") == _household() and hit.get("sources") and "japanese_community" in hit and \
            hit["fetched"] >= (date.today() - timedelta(days=CITY_TTL_DAYS)).isoformat():
        return hit
    data = run_claude_code(f"City: {city}, {country}. Household: {_household()}. Today: {date.today()}",
                           system=CITY_SYSTEM,
                           schema=CITY_SCHEMA, tools=["WebSearch", "WebFetch"], effort="low")
    out = data.get("structured_output")
    if out and not out.get("sources"):          # answered from memory: insist once on a real search
        data = run_claude_code(f"City: {city}, {country}. Household: {_household()}. Today: {date.today()}\n"
                               "Search the web now (listings, cost index, Japanese community) and cite the pages.",
                               system=CITY_SYSTEM, schema=CITY_SCHEMA, tools=["WebSearch", "WebFetch"],
                               effort="medium")
        out = data.get("structured_output") or out
    if not out:
        raise LLMError("No cost-of-living answer.")
    out.update({"city": city, "country": country, "household": _household(), "fetched": date.today().isoformat()})
    with _write_lock:
        cities = _load_cities()      # re-read: another thread may have written
        cities[key] = out
        CITIES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CITIES_FILE, "w", encoding="utf-8") as f:
            yaml.dump(cities, f, allow_unicode=True, sort_keys=False)
    return out


def cached_city(city: str, country: str):
    """The cached costs, only if they were researched for the current household."""
    hit = _load_cities().get(city_key(city, country))
    return hit if hit and hit.get("household") == _household() and "japanese_community" in hit else None


def refresh_cities() -> list[str]:
    """Research again every city used by an investigated offer, plus home (after a household change)."""
    from core.wishes import load, split_place
    places = {split_place(load()["home"])}
    for o in OfferLibrary().offers:
        info = o.get("company_info")
        if info and info.get("city") and info.get("country"):
            places.add((info["city"], info["country"]))
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda p: get_city(*p), places))
    return sorted(f"{c}, {k}" for c, k in places)


# --- offers -------------------------------------------------------------------

def investigate(offer_id: int) -> dict:
    """Research one offer and store the result on it. Safe to run in parallel threads."""
    o = OfferLibrary().get(offer_id)
    if not o:
        raise KeyError(offer_id)
    from core.wishes import load as load_wishes, split_place
    w = load_wishes()
    y = yearly(o.get("salary"))
    gross = f"€{(y[0] + y[1]) / 2:,.0f} gross a year" if y else "unknown"
    data = run_claude_code(
        f"Employer: {o['company']}\nJob: {o['title']}\nLocation: {o.get('location', '')}\n"
        f"Posting: {o['links'][0]['url']}\nGross salary (midpoint): {gross}\n"
        f"His places, best first: {'; '.join(w['places'])}. He lives in {w['home']} now. "
        f"Household if he moves: {w['household']}; {'they have a car' if w.get('have_car') else 'no car at first'}.\n"
        f"Today: {date.today()}",
        system=COMPANY_SYSTEM.format(rights=WORK_RIGHTS), schema=COMPANY_SCHEMA, tools=["WebSearch", "WebFetch"], effort="low",
    )
    info = data.get("structured_output")
    if not info:
        raise LLMError("No company answer.")

    if not info["city"].strip() or not info["country"].strip():
        info["city"], info["country"] = split_place(w["home"])
    # City costs: the job's city, and his home for comparison (both cached)
    with ThreadPoolExecutor(max_workers=2) as pool:
        here = pool.submit(get_city, info["city"], info["country"])
        home = pool.submit(get_city, *split_place(w["home"]))
        here.result(), home.result()

    with _write_lock:
        lib = OfferLibrary()         # re-read before writing
        o = lib.get(offer_id)
        o["company_info"] = info
        o["investigated"] = date.today().isoformat()
        lib.save()
    return info


def budget(o: dict):
    """Monthly money in EUR for this offer's city: take-home, costs, what is left, against his savings goal."""
    from core.wishes import load as load_wishes, split_place
    info = o.get("company_info")
    if not info or not info.get("net_monthly_eur"):
        return None
    here = cached_city(info["city"], info["country"])
    if not here:
        return None
    w = load_wishes()
    home = cached_city(*split_place(w["home"]))
    net = info["net_monthly_eur"] + w.get("other_income_eur", 0)
    if info.get("remote"):
        transport, how = 0, "remote"
    elif info.get("commute_paid"):
        transport, how = 0, "commute paid by the employer"
    elif (info.get("car_needed") or not here.get("transit_good", True)) and w.get("have_car"):
        transport, how = here.get("car_eur", 0), "car"
    else:
        transport, how = here.get("transit_eur", 0), "public transport"
    from core.wishes import home_cost_eur
    owned = home_cost_eur(w)
    home_city = split_place(w["home"])[0]
    at_home = info["city"].strip().lower() == home_city.lower()
    if at_home and w.get("home_owned"):
        rent, rent_label, kept = owned, "home costs (owned)", 0.0      # no rent: fees and property tax
    else:
        rent, rent_label = here["rent_eur"], "rent"
        kept = owned if w.get("keep_home_when_moving") else 0.0       # the Osaka home is still paid for
    living = here["living_eur"]
    # Staying in Japan (job at home, or remote from Japan): his wife works too, so the household
    # costs are his share of the house plus his own spending, and her income is not counted.
    remote_jp = info.get("remote") and any(home_city.lower() in p.lower() or "japan" in p.lower()
                                           for p in info.get("remote_from") or [])
    japan = at_home or bool(remote_jp)
    if japan:
        from core.offers import fx_rates
        jpy = fx_rates().get("JPY", 177.8)
        net = info["net_monthly_eur"]
        rent, rent_label, kept = w.get("japan_share_jpy", 105000) / jpy, "your share of the house", 0.0
        living = w.get("japan_personal_jpy", 35000) / jpy
        if remote_jp:
            transport, how = 0, "remote"
        elif not info.get("commute_paid") and "交通費" in (o.get("posting_text") or "") and \
                any(k in o["posting_text"] for k in ("交通費支給", "交通費全額", "交通費規定支給", "交通費あり")):
            transport, how = 0, "commute paid by the employer"
    left = net - rent - living - transport - kept
    home_rent = owned if w.get("home_owned") else (home["rent_eur"] if home else 0)
    home_cost = (home_rent + home["living_eur"] + home.get("transit_eur", 0)) if home else None
    return {"net": net, "rent": rent, "rent_label": rent_label, "kept_home": kept, "japan": japan,
            "living": living, "transport": transport,
            "transport_how": how, "left": left, "home_cost": home_cost,
            "home": home_city, "target": w["save_eur"], "meets": left >= w["save_eur"],
            "city": "Japan (remote)" if remote_jp and not at_home else info["city"],
            "community": here.get("japanese_community"), "community_note": here.get("community_note", ""),
            "pay": info["net_monthly_eur"], "other_income": 0 if japan else w.get("other_income_eur", 0),
            "no_car_problem": bool(not w.get("have_car") and not info.get("remote")
                                   and (info.get("car_needed") or not here.get("transit_good", True)))}
