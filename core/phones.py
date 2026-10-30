"""
Phone numbers of the employers he applied to, so a call can be checked: a real employer, or a scam.

- find(app_id): the employer's (and recruiter's) official numbers, from the posting and the web.
  Stored on the application as phones: [{number, label, source}].
- who_called(number): first his applications; if no match, the number is looked up on the web
  (Japanese number-report sites such as jpnumber.com, telnavi.jp) for scam reports.
Only the caller's number is searched; nothing about him is sent.
"""

import re

from core.llm import run_claude_code, LLMError
from core.pipeline import Pipeline

ACTIVE = ("found", "applied", "screening", "interview", "offer")

PHONES_SCHEMA = {
    "type": "object",
    "properties": {
        "phones": {"type": "array", "items": {
            "type": "object",
            "properties": {"number": {"type": "string"}, "label": {"type": "string"}, "source": {"type": "string"}},
            "required": ["number", "label", "source"], "additionalProperties": False}},
    },
    "required": ["phones"],
    "additionalProperties": False,
}

PHONES_SYSTEM = """You find the official phone numbers of an employer, for a job seeker who gets scam calls
and wants to recognise the real ones. Use web search and the posting.
- Only numbers you saw on the posting, the employer's own website, the recruiter's own website, or an official
  register (e.g. 国税庁法人番号, gBizINFO, company registry). Never a number from a forum or aggregator alone.
- label: whose number and which office, in English (e.g. "Head office, Osaka", "Recruiting desk (Indeed posting)",
  "Agency Hays, Osaka branch"). Include the hiring office / 採用担当 number first when there is one.
- source: the URL where you saw it.
- Write numbers as published (e.g. 06-1234-5678, +33 1 23 45 67 89). At most 5. Empty list if none found.
Never invent a number."""

CALLER_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["employer", "scam_reports", "unknown"]},
        "who": {"type": "string"},
        "summary": {"type": "string"},
        "sources": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["verdict", "who", "summary", "sources"],
    "additionalProperties": False,
}

CALLER_SYSTEM = """A job seeker in Japan got a call from a number he does not know. Look it up on the web:
Japanese number-report sites (jpnumber.com, telnavi.jp, denwa-ninsiki.com), the company that owns it, and
any report of scams (迷惑電話, 詐欺, 勧誘, 架空請求, 求人詐欺). Write to him as 'you', in English, briefly.
- verdict: "employer" if the number belongs to a real company that hires (say which); "scam_reports" if people
  report it as a scam, spam or a sales call; "unknown" if you found nothing reliable.
- who: the owner if known, else "unknown". summary: two sentences at most, with what the reports say.
- sources: the URLs you used. Never guess an owner."""


def digits(number: str) -> str:
    """Comparable form: digits only, +81 / 0081 turned into a leading 0."""
    d = re.sub(r"\D", "", number or "")
    for cc in ("0081", "81"):
        if d.startswith(cc) and len(d) >= 11:
            return "0" + d[len(cc):]
    return d


_PHONE = re.compile(r"(?:\+\d{1,3}[\s-]?)?(?:\(?0\d{1,4}\)?[\s-]?)\d{1,4}[\s-]?\d{3,4}")


def from_text(text: str) -> list:
    """Numbers written in a posting (cheap, no web)."""
    out = []
    for m in _PHONE.findall(text or ""):
        if 10 <= len(digits(m)) <= 12 and m not in out:
            out.append(m.strip())
    return out


def find(app_id: int) -> list:
    """Look up the employer's official numbers and store them on the application."""
    a = Pipeline().get(app_id)
    if not a:
        raise KeyError(app_id)
    seen = from_text(a.get("description", ""))
    data = run_claude_code(
        f"Employer: {a['company']}\nJob: {a['role']}\nPosting: {a.get('url') or 'unknown'}\n"
        + (f"Numbers already in the posting text: {', '.join(seen)}\n" if seen else ""),
        system=PHONES_SYSTEM, schema=PHONES_SCHEMA, tools=["WebSearch", "WebFetch"], effort="low")
    res = data.get("structured_output")
    if res is None:
        raise LLMError("No answer about phone numbers.")
    phones = res["phones"]
    for n in seen:                                   # numbers printed in the posting always count
        if not any(digits(p["number"]) == digits(n) for p in phones):
            phones.append({"number": n, "label": "In the posting", "source": a.get("url", "")})
    Pipeline().update(app_id, phones=phones)
    return phones


def missing() -> list:
    """Applications still open that have no numbers looked up yet."""
    return [a["id"] for a in Pipeline().apps if a["stage"] in ACTIVE and "phones" not in a]


def match(number: str) -> list:
    """[(app, phone)] whose number is this one (any application, closed ones too)."""
    d = digits(number)
    if len(d) < 6:
        return []
    return [(a, p) for a in Pipeline().apps for p in a.get("phones") or []
            if digits(p["number"]) == d or (len(d) >= 9 and digits(p["number"]).endswith(d[-9:]))]


def who_called(number: str) -> dict:
    """{"known": [(app, phone)], "verdict", "who", "summary", "sources"}."""
    known = match(number)
    if known:
        return {"known": known, "verdict": "employer", "who": known[0][0]["company"], "summary": "", "sources": []}
    data = run_claude_code(f"The number: {number.strip()}", system=CALLER_SYSTEM, schema=CALLER_SCHEMA,
                           tools=["WebSearch", "WebFetch"], effort="low")
    res = data.get("structured_output")
    if res is None:
        raise LLMError("No answer about this number.")
    return {"known": [], **res}
