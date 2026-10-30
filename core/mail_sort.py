"""
Sort the recruiting flood out of the inbox: job alerts, LinkedIn groups and notifications, hiring
newsletters go under the Gmail label "Job alerts" and leave the inbox. Nothing is deleted; moving a
message back to the inbox in Gmail undoes it. Needs the gmail.modify scope (mail_watch.can_sort()).

Never sorted: employers writing through Indeed (indeedemail.com), LinkedIn InMail and messages,
sign-in codes, and any message from a company in Applications.
Alerts are read for fitting jobs (core/mail_alerts.py) before they are sorted.
"""

import re

LABEL = "Job alerts"
SORT_SENDERS = [
    "jobalerts-noreply@linkedin.com",
    "jobs-noreply@linkedin.com",
    "groups-noreply@linkedin.com",
    "notifications-noreply@linkedin.com",
    "linkedin@em.linkedin.com",
    "donotreply@jobalert.indeed.com",
    "emploi@emails.hellowork.com",
    "careers@marriotthiring.com",
]
# senders whose mail is only noise: offered for unsubscribing (alerts are kept: they feed Offers)
NOISE = ["groups-noreply@linkedin.com", "notifications-noreply@linkedin.com", "linkedin@em.linkedin.com",
         "careers@marriotthiring.com"]


def _query(senders=None, inbox=True) -> str:
    return ("in:inbox " if inbox else "") + "{" + " ".join(f"from:{s}" for s in (senders or SORT_SENDERS)) + "}"


def _label_id(svc) -> str:
    labels = svc.users().labels().list(userId="me").execute().get("labels", [])
    for l in labels:
        if l["name"] == LABEL:
            return l["id"]
    return svc.users().labels().create(userId="me", body={
        "name": LABEL, "labelListVisibility": "labelShow", "messageListVisibility": "show"}).execute()["id"]


def _senders() -> list:
    """The bot senders to sort, minus any whose address names a company he applied or wrote to
    (e.g. if he applies to Marriott, careers@marriotthiring.com stays in the inbox).
    Every listed sender is an automated address, so no message needs to be opened one by one."""
    from core import mail_watch
    names = [n for r in mail_watch._watched() for n in r[5]]
    return [s for s in SORT_SENDERS if not any(n in s.replace(".", "") or n in s for n in names)]


def sort(progress=None) -> int:
    """Move the recruiting flood out of the inbox. Returns how many messages were moved."""
    from core import mail_watch
    say = progress or (lambda s: None)
    if not mail_watch.can_sort():
        return 0
    svc = mail_watch._service()
    senders = _senders()
    if not senders:
        return 0
    move, token = [], None
    while True:
        res = svc.users().messages().list(userId="me", q=_query(senders), maxResults=500, pageToken=token).execute()
        move += [m["id"] for m in res.get("messages", [])]
        token = res.get("nextPageToken")
        say(f"Found {len(move)} recruiting e-mails in your inbox")
        if not token:
            break
    if not move:
        return 0
    label = _label_id(svc)
    for n in range(0, len(move), 1000):
        svc.users().messages().batchModify(userId="me", body={
            "ids": move[n:n + 1000], "addLabelIds": [label], "removeLabelIds": ["INBOX"]}).execute()
    say(f"{len(move)} moved to \"{LABEL}\"")
    return len(move)


def noise_senders() -> list:
    """[{sender, count, subject, url, one_click}] for senders worth unsubscribing from (last 30 days)."""
    from core import mail_watch
    svc = mail_watch._service()
    out = []
    for s in NOISE:
        res = svc.users().messages().list(userId="me", q=f"from:{s} newer_than:30d", maxResults=50).execute()
        msgs = res.get("messages", [])
        if not msgs:
            continue
        meta = svc.users().messages().get(userId="me", id=msgs[0]["id"], format="metadata",
                                          metadataHeaders=["Subject", "List-Unsubscribe", "List-Unsubscribe-Post"]).execute()
        lu = mail_watch._header(meta, "list-unsubscribe")
        url = next((u for u in re.findall(r"<([^>]+)>", lu) if u.startswith("https://")), "")
        out.append({"sender": s, "count": len(msgs), "subject": mail_watch._header(meta, "subject"), "url": url,
                    "one_click": "one-click" in mail_watch._header(meta, "list-unsubscribe-post").lower()})
    return out


def unsubscribe(item: dict) -> str:
    """He clicked Unsubscribe: one-click (RFC 8058) when the sender supports it, else open its page."""
    import webbrowser
    if not item.get("url"):
        return "This sender gives no unsubscribe link."
    if item.get("one_click"):
        import requests
        r = requests.post(item["url"], data={"List-Unsubscribe": "One-Click"}, timeout=15)
        if r.status_code < 400:
            return "Unsubscribed."
    webbrowser.open(item["url"])
    return "Their unsubscribe page is open in your browser."
