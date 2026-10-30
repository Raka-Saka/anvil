"""
Outreach - write to companies that need his profile but may not be posting, and to recruiters.

- find_targets(): Claude searches the web for employers in his places with a real need for what he
  does (French-speaking customers, French firms in Kansai, support teams...), with a contact route.
- draft(): a short speculative email in the company's language (candidature spontanée, 自己PRメール...).
- draft_follow_up(): a polite nudge for a pipeline entry with no reply.
Anvil never sends anything: drafts open in the mail program or are copied, he sends them himself.
Stored in data/outreach.yaml. Status: target -> drafted -> sent -> replied | no_reply | dropped.
"""

from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import yaml

from core.store import read_yaml, write_yaml, LOCK, fresh

ROOT = Path(__file__).parent.parent
DATA_FILE = ROOT / "data" / "outreach.yaml"
FOLLOW_UP_DAYS = 10
STATUSES = ["target", "drafted", "sent", "replied", "no_reply", "dropped"]

TARGETS_SCHEMA = {
    "type": "object",
    "properties": {"targets": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "company": {"type": "string"}, "place": {"type": "string"}, "what": {"type": "string"},
            "why": {"type": "string"}, "track": {"type": "string"},
            "contact": {"type": "string"}, "contact_url": {"type": "string"},
            "language": {"type": "string", "enum": ["en", "fr", "ja"]},
        },
        "required": ["company", "place", "what", "why", "track", "contact", "contact_url", "language"],
        "additionalProperties": False,
    }}},
    "required": ["targets"],
    "additionalProperties": False,
}

EMAIL_SCHEMA = {
    "type": "object",
    "properties": {"subject": {"type": "string"}, "body": {"type": "string"}, "to": {"type": "string"},
                   "english": {"type": "string"}},
    "required": ["subject", "body", "to", "english"],
    "additionalProperties": False,
}

FIND_SYSTEM = """You find employers worth a speculative application for the candidate, using web search.
Look for companies with a real, visible need for what his record shows, whether or not they post a job now:
French companies and French-speaking customer bases in his places (e.g. members of CCI France Japon or
the local French chamber, French brands' Japan offices, inbound travel firms with French guests),
multilingual support teams, outsourcers with French desks, schools, hotels with French guests.
{rights}
Rules:
- Only real companies you saw on the web. contact_url: the page where you found the contact route.
- contact: the best route: a careers or recruitment email, a contact form, or the role to look for on
  LinkedIn (e.g. "Head of Customer Service"). Never invent an email address.
- why: one honest sentence, written to him as 'you', linking their need to your record. track: the track id that fits.
- what: what they do, in a few words. language: the language to write to them in.
- Leave out the companies listed as already contacted, in the pipeline or found as postings."""

EMAIL_SYSTEM = """You write one short email for the candidate. Rules:
- Use only facts in his profile. Never invent a skill, number or story.
- Voice: quiet, plain, first person, short sentences, no exclamation marks. Never use: {forbidden}.
- Write in the requested language. en/fr: 120-180 words. ja: polite ビジネスメール form, 300-400 characters,
  with a proper greeting and signature.
- `to`: the contact address only if it is written in the input, else an empty string.
- Sign with his name, phone and email from the profile.
- english: for a Japanese email, a faithful English translation so he can check it; else ""."""


def _profile_contact() -> str:
    from core.profile_manager import ProfileManager
    p = ProfileManager().load()["personal"]
    return f"Name: {p.get('name')}. Email: {p.get('email', '')}. Phone: {p.get('phone', '')}."


def _forbidden() -> str:
    from generators.application import _forbidden
    return ", ".join(f'"{x}"' for x in _forbidden())


class Outreach:
    def __init__(self, data_file: Path = DATA_FILE):
        self.data_file = data_file
        self.reload()

    def reload(self):
        self.items: list[dict] = []
        if self.data_file.exists():
            self.items = read_yaml(self.data_file).get("outreach", [])

    def save(self):
        write_yaml(self.data_file, {"outreach": self.items})

    def get(self, item_id: int) -> Optional[dict]:
        return next((i for i in self.items if i["id"] == item_id), None)

    def known(self, company: str) -> bool:
        from core.offers import _norm
        c = _norm(company)
        return any(c and (c in _norm(i["company"]) or _norm(i["company"]) in c) for i in self.items)

    def add(self, t: dict) -> dict:
        item = {"id": max((i["id"] for i in self.items), default=0) + 1, **t, "status": "target",
                "found_on": date.today().isoformat(), "subject": "", "body": "", "to": "",
                "sent_on": None, "follow_up": None, "pipeline_id": None}
        self.items.append(item)
        return item

    @fresh
    def set(self, item_id: int, **fields) -> dict:
        item = self.get(item_id)
        item.update(fields)
        if fields.get("status") == "sent":
            item["sent_on"] = date.today().isoformat()
            item["follow_up"] = (date.today() + timedelta(days=FOLLOW_UP_DAYS)).isoformat()
        self.save()
        return item

    def due(self) -> list[dict]:
        return [i for i in self.items if i["status"] == "sent" and i.get("follow_up")
                and i["follow_up"] <= date.today().isoformat()]


def find_targets(place: str = "", count: int = 8) -> list[int]:
    """Search for companies worth writing to. Returns the new ids. Takes a few minutes."""
    from analyzers.triage import profile_summary, load_library
    from analyzers.web_search import WORK_RIGHTS
    from core.llm import run_claude_code, LLMError
    from core.pipeline import Pipeline
    from core.wishes import load as load_wishes
    out = Outreach()
    w = load_wishes()
    where = place or "; ".join(w["places"])
    tracks = "\n".join(f"- {k}: {v['label']}" for k, v in load_library().get("tracks", {}).items())
    from core.offers import OfferLibrary
    skip = sorted({i["company"] for i in out.items} | {a["company"] for a in Pipeline().apps}
                  | {o["company"] for o in OfferLibrary().offers})
    data = run_claude_code(
        f"Find up to {count} employers in or near: {where}.\n\n<profile>\n{profile_summary()}\n</profile>\n\n"
        f"<tracks>\n{tracks}\n</tracks>\n\nAlready contacted, in the pipeline or found as postings:\n"
        + ("\n".join(f"- {c}" for c in skip) or "- none") + f"\n\nToday: {date.today()}",
        system=FIND_SYSTEM.format(rights=WORK_RIGHTS), schema=TARGETS_SCHEMA,
        tools=["WebSearch", "WebFetch"], effort="medium",
    )
    found = (data.get("structured_output") or {}).get("targets")
    if found is None:
        raise LLMError(data.get("result") or "No targets.")
    with LOCK:
        out.reload()
        new = [out.add(t)["id"] for t in found if not out.known(t["company"])]
        out.save()
    return new


def draft(item_id: int) -> dict:
    """Speculative email for one target."""
    from analyzers.triage import profile_summary
    from core.llm import run_claude_code, LLMError
    out = Outreach()
    t = out.get(item_id)
    data = run_claude_code(
        f"Write a speculative application email (language: {t['language']}).\nCompany: {t['company']} ({t['place']}): "
        f"{t['what']}\nWhy him: {t['why']}\nContact route: {t['contact']}\n\n"
        f"<profile>\n{profile_summary()}\n{_profile_contact()}\n</profile>\n"
        "Ask for a short call or to be considered for future openings; say a CV is attached.",
        system=EMAIL_SYSTEM.format(forbidden=_forbidden()), schema=EMAIL_SCHEMA,
    )
    mail = data.get("structured_output")
    if not mail:
        raise LLMError(data.get("result") or "No draft.")
    return out.set(item_id, status="drafted", violations=check(mail["body"]), **mail)


def draft_follow_up(app_id: int) -> dict:
    """A polite follow-up for a pipeline entry with no reply. Stored on the entry as follow_up_draft."""
    from analyzers.triage import profile_summary
    from core.llm import run_claude_code, LLMError
    from core.pipeline import Pipeline
    pipe = Pipeline()
    a = pipe.get(app_id)
    lang = a.get("language") or {"JP": "ja", "FR": "fr"}.get(a.get("country"), "en")
    data = run_claude_code(
        f"Write a short follow-up email (language: {lang}) about an application with no reply.\n"
        f"Role: {a['role']}\nCompany: {a['company']}\nApplied on: {a.get('applied_on')}\n"
        f"Contact: {a.get('contact') or 'unknown'}\nPosting: {a.get('url', '')}\n\n"
        f"<profile>\n{profile_summary()}\n{_profile_contact()}\n</profile>\n"
        "Restate interest in one line, add one relevant fact from his record not already obvious, ask where "
        "the process stands. en/fr: under 110 words.",
        system=EMAIL_SYSTEM.format(forbidden=_forbidden()), schema=EMAIL_SCHEMA,
    )
    mail = data.get("structured_output")
    if not mail:
        raise LLMError(data.get("result") or "No draft.")
    mail["violations"] = check(mail["body"])
    return pipe.update(app_id, follow_up_draft=mail)


MAILTO_MAX = 1800   # Windows drops longer mailto links


def check(text: str) -> list[str]:
    """Fraud check (forbidden phrases, inflated language levels) for an email."""
    from basin.method import OrangeLayer
    from core.profile_manager import ProfileManager
    pm = ProfileManager()
    return [v["found"] for v in OrangeLayer(pm.load(), pm.load_voice()).validate(text)
            if v["type"] != "missing_ai_acknowledgment"]


def mailto(mail: dict, with_body: bool = True) -> str:
    from urllib.parse import quote
    url = f"mailto:{quote(mail.get('to', ''), safe='@,')}?subject={quote(mail['subject'])}"
    return url + (f"&body={quote(mail['body'])}" if with_body else "")
