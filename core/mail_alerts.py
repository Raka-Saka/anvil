"""
Job alerts in Gmail (LinkedIn, Indeed...) - read the daily flood, keep the few jobs that fit.

Read-only: the alerts stay where they are. Each alert's text is shortened (tracking links become
tags like [L3]) and Claude returns only the jobs his record supports; those go to Offers with the
alert's lines kept as the posting text. Alerts already read are remembered in data/mail.yaml.
"""

import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from core.store import LOCK

ALERT_SENDERS = [
    "jobalerts-noreply@linkedin.com",
    "jobs-noreply@linkedin.com",
    "donotreply@jobalert.indeed.com",
    "emploi@emails.hellowork.com",
]
DAYS = 7              # offers older than a week are not kept anyway
PER_CALL = 10         # alerts read by Claude in one go
MIN_MATCH = 55        # below this a job is not worth his time

_URL = re.compile(r"https?://[^\s<>\"')\]]+")
_LI_JOB = re.compile(r"linkedin\.com/(?:comm/)?jobs/view/(\d+)")


def _shorten(text: str, links: dict) -> str:
    """Tracking links -> [Ln] tags (LinkedIn job links are cleaned and kept as the real target)."""
    def tag(m):
        url = m.group(0)
        li = _LI_JOB.search(url)
        if li:
            url = f"https://www.linkedin.com/jobs/view/{li.group(1)}/"
        elif "alerts" in url or "unsubscribe" in url.lower() or "search-results" in url or "settings" in url:
            return ""
        key = f"L{len(links) + 1}"
        links[key] = url
        return f"[{key}]"
    text = _URL.sub(tag, text)
    return re.sub(r"\n{3,}", "\n\n", text)[:6000]


ASK = """These are job-alert e-mails sent to him (LinkedIn, Indeed...). Most jobs in them do not fit.
Return ONLY the jobs his record really supports (match {min} or more) that he may legally take and that
respect his wishes. Skip everything else, and skip anything that is not a job (settings, ads, courses).
For each job kept:
- url: the tag of that job's own link exactly as written, like "L7" (no brackets), or "" if it has none.
- text: that job's lines from the alert, copied as they are.
- posted: from the alert if shown, else "unknown". Salary: as shown, else estimate (estimated=true).
- other_urls: [].
Returning no job at all is a normal answer."""


def _read_batch(batch, links, system):
    from core.llm import run_claude_code
    from analyzers.web_search import PASTED_SCHEMA
    from core.wishes import for_prompt
    body = "\n\n".join(f"<alert n={n} from=\"{frm}\" subject=\"{subj}\">\n{text}\n</alert>"
                       for n, (frm, subj, text) in enumerate(batch))
    data = run_claude_code(
        ASK.format(min=MIN_MATCH) + f"\n\n<wishes>\n{for_prompt()}\n</wishes>\nToday: {date.today()}\n\n{body}",
        system=system, schema=PASTED_SCHEMA, effort="low")
    jobs = (data.get("structured_output") or {}).get("jobs") or []
    for j in jobs:
        j["url"] = links.get(j.get("url", "").strip("[] "), "")
    return jobs


def mine(progress=None) -> dict:
    """Read new job alerts from the last DAYS days. Returns {"alerts": n, "new": [offer ids]}."""
    from core import mail_watch
    from core.offers import OfferLibrary
    from core.wishes import avoided
    from analyzers.web_search import _system
    say = progress or (lambda s: None)
    svc = mail_watch._service()
    q = "{" + " ".join(f"from:{s}" for s in ALERT_SENDERS) + f"}} newer_than:{DAYS}d"
    ids, token = [], None
    while True:
        res = svc.users().messages().list(userId="me", q=q, maxResults=100, pageToken=token).execute()
        ids += [m["id"] for m in res.get("messages", [])]
        token = res.get("nextPageToken")
        if not token or len(ids) >= 400:
            break
    done = set(mail_watch.load().get("mined", []))
    todo = [i for i in ids if i not in done]
    if not todo:
        return {"alerts": 0, "new": []}

    say(f"Shortening {len(todo)} job alerts")
    links, alerts = {}, []
    for mid in todo:
        full = svc.users().messages().get(userId="me", id=mid, format="full").execute()
        alerts.append((mail_watch._header(full, "from"), mail_watch._header(full, "subject"),
                       _shorten(mail_watch._body(full["payload"]), links)))

    batches = [alerts[i:i + PER_CALL] for i in range(0, len(alerts), PER_CALL)]
    system = _system()
    found, done_n = [], {"n": 0}

    def run(b):
        try:
            return _read_batch(b, links, system)
        finally:
            done_n["n"] += 1
            say(f"Claude read {done_n['n']} of {len(batches)} bundles of alerts")

    say(f"Claude is reading {len(alerts)} alerts")
    with ThreadPoolExecutor(max_workers=3) as pool:
        for jobs in pool.map(run, batches):
            found += jobs

    new_ids = []
    with LOCK:
        lib = OfferLibrary()
        for j in found:
            if j.get("work_rights") == "not_eligible" or (j.get("match") or 0) < MIN_MATCH:
                continue
            if j.get("url") and avoided(j["url"]):
                continue
            j["source"] = j.get("source") or "job alert e-mail"
            text = j.pop("text", "")
            offer, is_new = lib.add(j)
            if text and not offer.get("posting_text"):
                offer["posting_text"] = text[:6000]
            if is_new:
                new_ids.append(offer["id"])
        lib.save()
        d = mail_watch.load()
        d["mined"] = (d.get("mined", []) + todo)[-3000:]
        mail_watch.save(d)
    return {"alerts": len(todo), "new": new_ids}
