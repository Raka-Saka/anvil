"""
Web job search through Claude Code - any role, any country, any language.

Claude searches the web (job boards, company pages, agencies) and returns
postings with links, salary, seniority, a match score and the right-to-work
check. Anvil checks each link itself, drops dead links and jobs he cannot
legally take, and stores the rest in the offer library (core/offers.py).
Takes a few minutes; call it off the UI thread.
"""

import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from typing import Callable, Optional

from core.llm import run_claude_code, LLMError
from core.offers import OfferLibrary

try:
    import requests
except ImportError:
    requests = None

REGIONS = {
    "wishes": "My places (set in the criteria)",
    "europe": "Europe: EU/EEA countries and Switzerland, or remote open to EU residents",
    "france": "France, or remote for a French employer",
    "japan": "Japan (Osaka / Kansai preferred), or remote open to Japan residents",
    "remote": "Fully remote roles whose posting accepts EU or Japan residents (or says worldwide)",
    "anywhere": "Anywhere he may legally work",
}

# Where he may work: French national (EU/EEA + Switzerland free movement), Japan spouse visa.
WORK_RIGHTS = ("He may work in EU/EEA countries and Switzerland (French national) and in Japan "
               "(spouse visa, no restrictions). He may NOT work in the US, UK, Canada, Australia or "
               "anywhere else without a visa, even remotely, unless the posting says it hires "
               "worldwide or from the EU/Japan (e.g. via an employer of record).")

SALARY = {
    "type": "object",
    "properties": {
        "min": {"type": "number"}, "max": {"type": "number"},
        "currency": {"type": "string", "description": "ISO code, e.g. EUR, JPY, GBP, CHF, PLN"},
        "period": {"type": "string", "enum": ["year", "month", "week", "day", "hour"]},
        "estimated": {"type": "boolean"},
    },
    "required": ["min", "max", "currency", "period", "estimated"],
    "additionalProperties": False,
}

SCHEMA = {
    "type": "object",
    "properties": {"jobs": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "title": {"type": "string"}, "company": {"type": "string"}, "location": {"type": "string"},
            "url": {"type": "string"},
            "other_urls": {"type": "array", "items": {"type": "string"}},
            "posted": {"type": "string"}, "languages": {"type": "string"}, "source": {"type": "string"},
            "salary": SALARY,
            "seniority": {"type": "string", "enum": ["entry", "mid", "senior", "lead", "unknown"]},
            "match": {"type": "integer"},
            "work_rights": {"type": "string", "enum": ["eligible", "not_eligible", "unclear"]},
            "fit": {"type": "string"},
        },
        "required": ["title", "company", "location", "url", "other_urls", "posted", "languages", "source",
                     "salary", "seniority", "match", "work_rights", "fit"],
        "additionalProperties": False,
    }}},
    "required": ["jobs"],
    "additionalProperties": False,
}

RULES = f"""You find real, current job postings on the web for the candidate below.
Rules:
- Only postings you saw in search results or opened, with the direct URL to the posting. Never guess a URL.
- Only postings that still take applications. A page saying expired, closed, filled or no longer accepting
  applications (募集終了, 掲載終了, 受付終了, offre expirée, n'est plus disponible) is not a posting: skip it.
- Only postings from the last 7 days. `posted`: the date (YYYY-MM-DD) or age ("3 days ago"), or "unknown".
- If the same job is on several sites, return it once; put the extra links in `other_urls`.
- Right to work: {WORK_RIGHTS} Set `work_rights` and leave out jobs he cannot take.
- Japanese: he has N4 (basic). Skip postings that require business-level Japanese (ビジネスレベル), N3 or
  above, or reading and writing Japanese documents. Keep jobs open to basic Japanese (簡単な日本語でOK,
  外国人歓迎); when a job asks for everyday conversation (日常会話), keep it and say so in `fit`.
  Skip postings that need another language he lacks (German, Dutch...) as a hard requirement.
- Only roles his record supports: match the tracks and the experience below, not generic jobs. Exception:
  manual and factory work in Japan when his wishes say it is fine.
- `salary`: the posted range if shown (estimated=false). Otherwise your best estimate of the usual yearly
  pay for this role, level and city (estimated=true). Use the local currency. Where pay comes in 14
  instalments (Portugal, Spain, Greece...), give the yearly total.
- `seniority`: the level the posting asks for.
- `match` 0-100: how much of the job's core duties his record shows directly. 80+ means he has done this
  job; 50-79 related experience with a gap; under 50 a stretch.
- `fit`: one short honest sentence in English naming the CV evidence it matches, or the main gap.
  Keep `title` and `company` as the posting writes them (any language).
- In Japan, search in Japanese as well as English: most postings on Indeed Japan, Recruit and Hello Work
  are only in Japanese (e.g. 「大阪 外国人歓迎 製造」, 「大阪 英語 カスタマーサポート」, 「フランス語 求人 大阪」).
  Indeed Japan often shows age as 「3日前」 or 「新着」; when no date is shown, `posted` is "unknown".
- Where to look first. Japan, in this order: Indeed Japan (jp.indeed.com), Recruit's sites (リクナビNEXT,
  タウンワーク, Recruit Agent), GaijinPot Jobs, YOLO WORK (yolo-japan.com), Hello Work (ハローワークインターネットサービス).
  France: France Travail, APEC, Welcome to the Jungle, Indeed France, HelloWork.com (a private French job site, unrelated to Japan's ハローワーク). Elsewhere in Europe: Indeed,
  LinkedIn, the company's own careers page. Company pages are fine everywhere.
- He applies from Japan. HelloWork.com refuses applications from Japanese IPs (offers can be read): when a job is listed there, find the
  same posting on the employer's or recruiter's own site (or another board) and give that link first.
  Skip the job if HelloWork.com is the only place it can be applied to.
- Work fast: a few searches, open a posting only when the search snippet is unclear."""


def _system() -> str:
    from analyzers.triage import profile_summary, load_library
    tracks = "\n".join(f"- {v['label']}" for v in load_library().get("tracks", {}).values())
    return (f"{RULES}\n\n<candidate>\n{profile_summary()}\n</candidate>\n\n"
            f"<tracks_he_applies_for>\n{tracks}\n</tracks_he_applies_for>")


DUP_SCHEMA = {
    "type": "object",
    "properties": {"same": {"type": "array", "items": {
        "type": "object", "properties": {"new": {"type": "integer"}, "known": {"type": "integer"}},
        "required": ["new", "known"], "additionalProperties": False}}},
    "required": ["same"], "additionalProperties": False,
}


def _cross_language_duplicates(found: list, lib) -> dict:
    """{index in found: known offer id} for jobs already in the library under another language or name.
    Title/company matching cannot see that 'Chargé(e) de service clients' at Medtronic or
    'カスタマーサポート' at 株式会社ゼングループ are known jobs; Claude can."""
    from datetime import timedelta
    cutoff = (date.today() - timedelta(days=30)).isoformat()
    recent = [o for o in lib.offers if o["last_seen"] >= cutoff]
    if not found or not recent:
        return {}
    new = "\n".join(f"{i}: {j['title']} — {j['company']} — {j['location']}" for i, j in enumerate(found))
    known = "\n".join(f"{o['id']}: {o['title']} — {o['company']} — {o.get('location', '')}" for o in recent)
    try:
        data = run_claude_code(
            f"<new>\n{new}\n</new>\n<known>\n{known}\n</known>",
            system="List each new job that is the same position as a known job: same employer (names may be in "
                   "another language or script, or an agency vs. the client), same role (titles may be translated), "
                   "same place. Different cities or clearly different roles are not the same. Be strict.",
            schema=DUP_SCHEMA, effort="low")
        pairs = (data.get("structured_output") or {}).get("same", [])
    except LLMError:
        return {}
    ids = {o["id"] for o in recent}
    return {p["new"]: p["known"] for p in pairs if 0 <= p["new"] < len(found) and p["known"] in ids}


# words a job board shows on a posting that no longer takes applications
_CLOSED = re.compile(r"(this job (has )?(expired|is no longer)|job (has )?expired|no longer (accepting|available)|"
                     r"position has been filled|posting (has )?(closed|expired)|募集(は)?終了|掲載(は)?終了|"
                     r"受付(は)?終了|offre (a )?expir|n'est plus disponible|plus d'actualité)", re.I)


def _check(url: str) -> str:
    """'ok', 'dead' (gone or closed), or 'unchecked' (bot wall / timeout)."""
    if not requests or not url.startswith("http"):
        return "dead"
    try:
        r = requests.get(url, timeout=12, allow_redirects=True,
                         headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"})
        if r.status_code in (404, 410):
            return "dead"
        if r.status_code >= 400:
            return "unchecked"
        return "dead" if _CLOSED.search(r.text[:200000]) else "ok"
    except Exception:
        return "unchecked"


def search_web(keywords: str = "", region: str = "europe", count: int = 8,
               progress: Optional[Callable[[str], None]] = None) -> dict:
    """Search, then store in the library. Returns counts and the new offer ids."""
    say = progress or (lambda s: None)
    lib = OfferLibrary()
    from core.wishes import load as load_wishes, for_prompt
    wishes = load_wishes()
    if region == "wishes":
        where = ("One of his places: " + "; ".join(wishes["places"]) +
                 ", or remote work he may legally do from one of them")
    else:
        where = REGIONS.get(region, region)
    if keywords:
        ask = f"Find up to {count} current job postings for: {keywords}"
    else:
        ask = (f"Find up to {count} current job postings that fit his CVs. Spread them across the tracks "
               "that make sense for this location, best fits first.")
    known = lib.known_for_prompt()
    if known:
        ask += f"\n\nAlready found earlier (find other ones):\n{known}"

    ask += f"\n\n<wishes>\n{for_prompt(wishes)}\n</wishes>"
    say("Claude is searching the web")
    data = run_claude_code(
        f"{ask}\nWhere: {where}\nToday: {date.today()}",
        system=_system(), schema=SCHEMA, tools=["WebSearch", "WebFetch"], effort="medium",
    )
    found = (data.get("structured_output") or {}).get("jobs", [])
    if not found and data.get("structured_output") is None:
        raise LLMError(data.get("result") or "Claude returned nothing.")

    found = [j for j in found if j["work_rights"] != "not_eligible"]
    # sites he does not trust: drop their links; a job left with no other link is dropped
    from core.wishes import avoided
    kept = []
    for j in found:
        urls = [u for u in [j["url"], *j.get("other_urls", [])] if not avoided(u, wishes)]
        if urls:
            j["url"], j["other_urls"] = urls[0], urls[1:]
            kept.append(j)
    found = kept
    say(f"Checking {len(found)} links")
    with ThreadPoolExecutor(max_workers=8) as pool:
        status = list(pool.map(_check, [j["url"] for j in found]))

    say("Checking for jobs already found in another language")
    dups = _cross_language_duplicates(found, OfferLibrary())

    from core.store import LOCK
    new_ids, repeats, dead = [], 0, 0
    with LOCK:
        lib.reload()
        for n, (j, st) in enumerate(zip(found, status)):
            if st == "dead":
                dead += 1
                continue
            if n in dups and lib.get(dups[n]):
                lib.merge_into(dups[n], j)
                repeats += 1
                continue
            offer, is_new = lib.add(j)
            if is_new:
                offer["links"][0]["checked"] = st == "ok"
                new_ids.append(offer["id"])
            else:
                repeats += 1
        lib.save()
    return {"new": new_ids, "repeats": repeats, "dead": dead}


# Sites that refuse automatic reading (403 to Claude and to Anvil). He browses them himself and adds
# what he likes with add_offers(). Searches are in Japanese, Osaka first.
BROWSE_JAPAN = [
    ("Indeed Japan", "https://jp.indeed.com/jobs?q=%E5%A4%96%E5%9B%BD%E4%BA%BA%E6%AD%93%E8%BF%8E&l=%E5%A4%A7%E9%98%AA%E5%BA%9C"),
    ("Indeed: factory", "https://jp.indeed.com/jobs?q=%E8%A3%BD%E9%80%A0+%E5%A4%96%E5%9B%BD%E4%BA%BA%E6%AD%93%E8%BF%8E&l=%E5%A4%A7%E9%98%AA%E5%BA%9C"),
    ("Indeed: English", "https://jp.indeed.com/jobs?q=%E8%8B%B1%E8%AA%9E&l=%E5%A4%A7%E9%98%AA%E5%BA%9C"),
    ("Indeed: French", "https://jp.indeed.com/jobs?q=%E3%83%95%E3%83%A9%E3%83%B3%E3%82%B9%E8%AA%9E&l=%E5%A4%A7%E9%98%AA%E5%BA%9C"),
    ("GaijinPot", "https://jobs.gaijinpot.com/job/index/lang/en?location=Osaka"),
    ("Hello Work", "https://www.hellowork.mhlw.go.jp/kensaku/GECA110010.do?action=initDisp&screenId=GECA110010"),
    ("Recruit (Townwork)", "https://townwork.net/"),
]

_PASTED_JOB = dict(SCHEMA["properties"]["jobs"]["items"])
_PASTED_JOB["properties"] = {**_PASTED_JOB["properties"], "text": {"type": "string"}}
_PASTED_JOB["required"] = [*_PASTED_JOB["required"], "text"]
PASTED_SCHEMA = {"type": "object", "properties": {"jobs": {"type": "array", "items": _PASTED_JOB}},
                 "required": ["jobs"], "additionalProperties": False}


def add_offers(posting: str, url: str = "") -> list:
    """Offers he found himself: one posting's text, a job alert pasted from LINE or e-mail with
    several jobs, and/or one link. Returns [(offer, is_new)]. Each job's own text is kept, so the CV
    and letter can be written even when the site refuses to be read. Sites he avoids are dropped."""
    from core.wishes import for_prompt, avoided
    posting, url = (posting or "").strip(), (url or "").strip()
    if not posting and not url:
        raise ValueError("Paste the posting text or its link.")
    if posting:
        ask = ("He pasted this himself: one job posting, or a job alert (from LINE or e-mail) listing several "
               "jobs" + (f"; the link he gave is {url}" if url else "") + ". Return every job in it, read from "
               "the text. Do not search for other jobs.\n"
               "For each job: `url` is its own link from the text (alerts often have one link per job), or \"\"; "
               "`text` is that job's part of the paste, copied as it is; `posted` from the text or \"unknown\". "
               "Skip ads, settings links and anything that is not a job.\n\n"
               f"<pasted>\n{posting[:30000]}\n</pasted>")
    else:
        ask = (f"He found this posting himself: {url}\nOpen it with WebFetch. Do not search for other jobs. "
               "Return this one job; `text`: the posting's text as read.")
    ask += ("\nReturn every job even if it is a poor fit or needs more Japanese than he has: say so honestly in "
            "`fit` and `match`. `other_urls`: []. If the alert gives little detail, estimate salary "
            f"(estimated=true) and keep `match` cautious.\n\n<wishes>\n{for_prompt()}\n</wishes>\nToday: {date.today()}")
    data = run_claude_code(ask, system=_system(), schema=PASTED_SCHEMA,
                           tools=None if posting else ["WebFetch"], effort="medium")
    jobs = (data.get("structured_output") or {}).get("jobs")
    if not jobs:
        raise LLMError(data.get("result") or "Claude found no job in what you pasted.")
    from core.store import LOCK
    out = []
    with LOCK:
        lib = OfferLibrary()
        for job in jobs:
            if len(jobs) == 1 and url:
                job["url"] = url
            if job.get("url") and avoided(job["url"]):
                continue
            job["source"] = job.get("source") or "added by you"
            text = job.pop("text", "") or (posting if len(jobs) == 1 else "")
            offer, is_new = lib.add(job)
            if text and not offer.get("posting_text"):
                offer["posting_text"] = text[:20000]
            out.append((offer, is_new))
        lib.save()
    return out
