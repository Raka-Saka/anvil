"""
Mail watch - Gmail check for answers from the companies he applied to or wrote to.

Scope gmail.modify (older tokens: gmail.readonly): Anvil reads, and may label and archive job-alert
mail (core/mail_sort.py). It never sends or deletes. The token stays in
config/gmail_token.json (gitignored). Only mail from the last 60 days that names a company in
Applications or Companies to email is looked at, and only those messages go to Claude, which says
what each one is (a real reply, an interview invitation, a rejection, an automatic receipt).
Results wait in data/mail.yaml until he moves the card or dismisses them; nothing moves by itself.
"""

import base64
import re
from datetime import date, datetime, timedelta
from pathlib import Path

from core.store import read_yaml, write_yaml, LOCK

ROOT = Path(__file__).parent.parent
SECRETS = ROOT / "config" / "client_secrets.json"
TOKEN = ROOT / "config" / "gmail_token.json"
DATA = ROOT / "data" / "mail.yaml"
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]       # read + label/archive; never send or delete
READ_ONLY = "https://www.googleapis.com/auth/gmail.readonly"
LOOKBACK_DAYS = 60
EVERY_HOURS = 12

KINDS = {
    "interview": "Interview invitation",
    "reply": "They replied",
    "rejection": "They said no",
    "offer": "Job offer",
    "auto_ack": "Automatic receipt",
    "other": "Other",
}
# what the card should become for each kind (None: no move suggested)
MOVE_TO = {"interview": "interview", "reply": "screening", "rejection": "rejected", "offer": "offer"}

# legal forms and noise words that never identify a company on their own
_NOISE = re.compile(r"株式会社|有限会社|合同会社|\(株\)|（株）|\b(co|ltd|inc|llc|gmbh|sas|sarl|sa|kk|corp|corporation|"
                    r"company|group|japan|france|the|and|recruitment|recrutement|jobs?)\b\.?", re.IGNORECASE)


def connected() -> bool:
    return TOKEN.exists()


def connect():
    """Opens the browser once for his consent (read-only). Blocks until he answers."""
    from google_auth_oauthlib.flow import InstalledAppFlow
    flow = InstalledAppFlow.from_client_secrets_file(str(SECRETS), SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent",
                                  success_message="Anvil can now read your Gmail and sort job alerts. You can close this tab.")
    TOKEN.write_text(creds.to_json(), encoding="utf-8")


def can_sort() -> bool:
    """True when the token allows labelling and archiving (granted after the job-alert sorting came in)."""
    import json
    try:
        return SCOPES[0] in json.loads(TOKEN.read_text(encoding="utf-8")).get("scopes", [])
    except Exception:
        return False


def disconnect():
    TOKEN.unlink(missing_ok=True)


def _service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    creds = Credentials.from_authorized_user_file(str(TOKEN))     # the scopes he granted, old or new
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as ex:
                # unpublished (testing) Google apps lose access after 7 days: forget the token so Today
                # shows the connect button again
                TOKEN.unlink(missing_ok=True)
                raise RuntimeError("Gmail access ended (Google allows 7 days for a private app). "
                                   "Click Reconnect Gmail on Today.") from ex
            TOKEN.write_text(creds.to_json(), encoding="utf-8")
        else:
            raise RuntimeError("Gmail is not connected.")
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


# --- store ------------------------------------------------------------------------------

def load() -> dict:
    d = read_yaml(DATA, {"seen": [], "found": [], "last_check": None})
    d.setdefault("seen", [])
    d.setdefault("found", [])
    return d


def save(d: dict):
    d["seen"] = d["seen"][-3000:]
    write_yaml(DATA, d)


def waiting() -> list:
    """Messages that need his eye: not dismissed, not handled."""
    return [m for m in load()["found"] if not m.get("done")]


def mark_done(msg_id: str):
    with LOCK:
        d = load()
        for m in d["found"]:
            if m["id"] == msg_id:
                m["done"] = True
        save(d)


def due() -> bool:
    if not connected():
        return False
    last = load().get("last_check")
    return not last or datetime.fromisoformat(last) < datetime.now() - timedelta(hours=EVERY_HOURS)


# --- who to look for ----------------------------------------------------------------------

def _names(company: str) -> list:
    """Words that identify a company in a sender, subject or snippet: 'Medtronic', 'セントラルクルー'."""
    parts = re.split(r"[()（）/|,·–—]| - ", company)
    out = []
    for p in parts:
        if re.match(r"\s*[a-z]", p) and len(p.split()) > 2:     # "(recruiter for an electronics manufacturer)"
            continue
        p = _NOISE.sub(" ", p).strip(" .&・")
        p = re.sub(r"\s+", "", p).lower()                       # "Work & You" also matches "Work&You"
        if len(p) >= 3 or re.search(r"[぀-ヿ一-鿿]{2,}", p):
            out.append(p)
    return out


def _watched() -> list:
    """(kind, id, company, role, since, names) for every live application and every email he sent."""
    from core.pipeline import Pipeline
    from core.outreach import Outreach
    rows = []
    for a in Pipeline().apps:
        if a["stage"] in ("applied", "screening", "interview", "offer") or \
                (a["stage"] in ("rejected", "ghosted") and a.get("applied_on")):
            # a contact's e-mail also identifies the sender: n_nishida@sagawa-logi.co.jp → "sagawa-logi.co.jp"
            mails = [m.lower().split("@")[1] for m in re.findall(r"[\w.+-]+@[\w.-]+", a.get("contact") or "")]
            rows.append(("app", a["id"], a["company"], a["role"], a.get("applied_on") or a["history"][0]["on"],
                         _names(a["company"]) + mails))
    for i in Outreach().items:
        if i["status"] in ("sent", "no_reply"):
            rows.append(("outreach", i["id"], i["company"], i.get("what", ""), i.get("sent_on") or i["found_on"],
                         _names(i["company"])))
    return [r for r in rows if r[5]]


# --- reading ----------------------------------------------------------------------------

def _header(msg, name):
    return next((h["value"] for h in msg["payload"].get("headers", []) if h["name"].lower() == name), "")


def _body(payload) -> str:
    """Plain text of a message (text/plain preferred, else text/html stripped)."""
    plain, html = [], []

    def walk(p):
        data = (p.get("body") or {}).get("data")
        if data:
            txt = base64.urlsafe_b64decode(data + "==").decode("utf-8", "replace")
            (plain if p.get("mimeType") == "text/plain" else html if p.get("mimeType") == "text/html" else []).append(txt)
        for c in p.get("parts", []) or []:
            walk(c)

    walk(payload)
    text = "\n".join(plain) or re.sub(r"<[^>]+>", " ", "\n".join(html))
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n\n", text)).strip()


CLASSIFY_SCHEMA = {
    "type": "object",
    "properties": {"messages": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "n": {"type": "integer"},
            "match": {"type": "string", "description": "the watched item it answers, like 'app:5' or 'outreach:2', or 'none'"},
            "kind": {"type": "string", "enum": list(KINDS)},
            "summary": {"type": "string"},
            "when": {"type": "string", "description": "interview or deadline date/time if one is given, else ''"},
        },
        "required": ["n", "match", "kind", "summary", "when"],
        "additionalProperties": False,
    }}},
    "required": ["messages"],
    "additionalProperties": False,
}

CLASSIFY_SYSTEM = """You sort e-mails a job seeker received. For each message say which of his applications or
sent e-mails it answers, if any, and what it is:
- interview: they invite him to an interview, a call or a test, or ask for his availability.
- reply: a person answered (a question, a request for documents, "we will get back to you" written by a person).
- rejection: they say no or the position is filled.
- offer: a job offer.
- auto_ack: an automatic "we received your application" or a no-reply system message.
- other: newsletters, job alerts, ads, or anything unrelated (match "none").
Match only when the sender or the content clearly concerns that company and application; a job alert or an ad
that merely names the company is "other" with match "none". The messages may be in Japanese, French or English.
summary: one short sentence in English, addressed to him as "you", saying what they want and any deadline."""


def check(progress=None) -> dict:
    """Look for new answers. Returns {"checked": n, "new": [found items]}."""
    from core.llm import run_claude_code
    say = progress or (lambda s: None)
    svc = _service()
    watched = _watched()
    if not watched:
        with LOCK:
            d = load()
            d["last_check"] = datetime.now().isoformat(timespec="seconds")
            save(d)
        return {"checked": 0, "new": []}

    since = min(r[4] for r in watched) or (date.today() - timedelta(days=LOOKBACK_DAYS)).isoformat()
    since = max(since, (date.today() - timedelta(days=LOOKBACK_DAYS)).isoformat())
    query = f"after:{since.replace('-', '/')} -from:me -category:promotions -category:social"
    say("Reading your inbox")
    ids, token = [], None
    while len(ids) < 500:
        res = svc.users().messages().list(userId="me", q=query, maxResults=100, pageToken=token).execute()
        ids += [m["id"] for m in res.get("messages", [])]
        token = res.get("nextPageToken")
        if not token:
            break

    d = load()
    seen = set(d["seen"])
    fresh_ids = [i for i in ids if i not in seen]
    candidates = []
    for mid in fresh_ids:
        meta = svc.users().messages().get(userId="me", id=mid, format="metadata",
                                          metadataHeaders=["From", "Subject", "Date"]).execute()
        hay = re.sub(r"\s+", "", f"{_header(meta, 'from')} {_header(meta, 'subject')} {meta.get('snippet', '')}").lower()
        hits = [r for r in watched if any(n in hay for n in r[5])]
        if hits:
            candidates.append((mid, meta, hits))

    found = []
    if candidates:
        say(f"Claude is reading {len(candidates)} e-mail{'s' if len(candidates) > 1 else ''}")
        blocks, items = [], {}
        for n, (mid, meta, hits) in enumerate(candidates):
            full = svc.users().messages().get(userId="me", id=mid, format="full").execute()
            body = _body(full["payload"])[:4000]
            for r in hits:
                items[f"{r[0]}:{r[1]}"] = r
            blocks.append(f"<message n={n}>\nFrom: {_header(meta, 'from')}\nSubject: {_header(meta, 'subject')}\n"
                          f"Date: {_header(meta, 'date')}\nCould be about: " +
                          "; ".join(f"{r[0]}:{r[1]} = {r[2]} ({r[3]})" for r in hits) + f"\n\n{body}\n</message>")
        data = run_claude_code("\n\n".join(blocks), system=CLASSIFY_SYSTEM, schema=CLASSIFY_SCHEMA, effort="low")
        for c in (data.get("structured_output") or {}).get("messages", []):
            if not 0 <= c["n"] < len(candidates) or c["match"] not in items or c["kind"] == "other":
                continue
            mid, meta, _ = candidates[c["n"]]
            r = items[c["match"]]
            found.append({
                "id": mid, "thread": meta.get("threadId", mid), "for": r[0], "item_id": r[1], "company": r[2],
                "role": r[3], "kind": c["kind"], "summary": c["summary"], "when": c["when"],
                "from": _header(meta, "from"), "subject": _header(meta, "subject"),
                "date": datetime.fromtimestamp(int(meta.get("internalDate", 0)) / 1000).date().isoformat(),
                "done": c["kind"] == "auto_ack",     # a receipt is shown once in the history, nothing to do
            })

    with LOCK:
        d = load()
        d["seen"] = list(dict.fromkeys(d["seen"] + fresh_ids))
        known = {m["id"] for m in d["found"]}
        d["found"] += [m for m in found if m["id"] not in known]
        d["last_check"] = datetime.now().isoformat(timespec="seconds")
        save(d)
    _log_on_cards(found)
    return {"checked": len(fresh_ids), "new": [m for m in found if not m["done"]]}


def _log_on_cards(found):
    """Note each answer on its application, so the history shows it even after the message is dismissed."""
    from core.pipeline import Pipeline
    from core.outreach import Outreach
    for m in found:
        line = f"{m['date']} mail: {KINDS[m['kind']].lower()} - {m['summary']}"
        try:
            if m["for"] == "app":
                a = Pipeline().get(m["item_id"])
                if a:
                    Pipeline().update(m["item_id"], mail_log=(a.get("mail_log") or []) + [line])
            elif m["kind"] != "auto_ack":
                Outreach().set(m["item_id"], status="replied")
        except Exception:
            pass


def gmail_link(m: dict) -> str:
    return f"https://mail.google.com/mail/u/0/#all/{m['thread']}"
