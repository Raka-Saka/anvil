"""
Weekly review - what happened in the last 7 days, what gets replies, what to change.

Numbers come from the offer library, the pipeline and the outreach log. Claude then reads the
numbers and suggests a few changes (optional; the numbers stand on their own).
Saved to output/reviews/<date>.md.
"""

from collections import Counter
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
OUT_DIR = ROOT / "output" / "reviews"
MIN_SAMPLE = 5   # below this many applications, a reply rate means little

SCHEMA = {
    "type": "object",
    "properties": {"actions": {"type": "array", "items": {"type": "string"}}},
    "required": ["actions"],
    "additionalProperties": False,
}

SYSTEM = """You review one week of a job search with the candidate. Read the numbers and give 3-5 concrete
actions for next week, most useful first, each one or two short sentences. Base each on a number shown;
say when a sample is too small to conclude. Plain, calm, no cheerleading, no exclamation marks."""


def _rate(apps: list) -> str:
    from core.pipeline import RESPONDED
    sent = [a for a in apps if a.get("applied_on")]
    replied = sum(1 for a in sent if any(h["stage"] in RESPONDED for h in a["history"]))
    if not sent:
        return "nothing sent"
    note = "" if len(sent) >= MIN_SAMPLE else " (too few to judge)"
    return f"{replied}/{len(sent)} replied ({replied / len(sent):.0%}){note}"


def _table(title: str, groups: dict) -> list[str]:
    rows = [f"### {title}"] + [f"- {k}: {_rate(v)}" for k, v in sorted(groups.items()) if v]
    return rows + [""]


def stats(on: date = None) -> dict:
    from core.offers import OfferLibrary
    from core.outreach import Outreach
    from core.pipeline import Pipeline, RESPONDED, channel_name
    from core.wishes import REJECT_REASONS
    on = on or date.today()
    start = (on - timedelta(days=7)).isoformat()
    in_week = lambda d: bool(d) and d > start

    offers = OfferLibrary().offers
    apps = Pipeline().apps
    out = Outreach()

    s = {"from": start, "to": on.isoformat()}
    s["offers_found"] = sum(1 for o in offers if in_week(o["first_seen"]))
    s["offers_opened"] = sum(1 for o in offers if in_week(o["first_seen"]) and o["status"] in ("seen", "applied"))
    s["turned_down"] = Counter(REJECT_REASONS.get(o["reject_reason"], o["reject_reason"])
                               for o in offers if in_week(o.get("rejected_on")))
    s["selected"] = sum(1 for a in apps if in_week(a["history"][0]["on"]))
    s["packs"] = sum(1 for a in apps if in_week((a.get("pack") or {}).get("on")))
    s["applied"] = sum(1 for a in apps if in_week(a.get("applied_on")))
    s["replies"] = [f"{a['role']} — {a['company']}: {h['stage']}" for a in apps for h in a["history"]
                    if h["stage"] in RESPONDED and in_week(h["on"])]
    s["outreach_found"] = sum(1 for i in out.items if in_week(i["found_on"]))
    s["outreach_sent"] = sum(1 for i in out.items if in_week(i.get("sent_on")))
    s["outreach_replied"] = sum(1 for i in out.items if i["status"] == "replied")
    s["outreach_total_sent"] = sum(1 for i in out.items if i.get("sent_on"))
    s["due"] = [f"{a['next_action']} — {a['role']} @ {a['company']}" for a in Pipeline().due()]
    s["due"] += [f"Follow up the email to {i['company']}" for i in out.due()]

    # What gets replies, all time
    def group(key):
        g = {}
        for a in apps:
            g.setdefault(key(a) or "unknown", []).append(a)
        return g

    def match_band(a):
        m = (a.get("fit") or {}).get("match")
        return None if m is None else "80+" if m >= 80 else "50-79" if m >= 50 else "under 50"

    s["by_track"] = group(lambda a: (a.get("pack") or {}).get("track") or (a.get("fit") or {}).get("track"))
    s["by_country"] = group(lambda a: a.get("country"))
    s["by_channel"] = group(lambda a: channel_name(a.get("channel")))
    s["by_match"] = group(match_band)
    s["by_letter"] = group(lambda a: "tailored pack" if a.get("pack") else "no pack")
    s["gaps"] = Counter(g.lower() for a in apps for g in (a.get("pack") or {}).get("gaps", []))
    s["all_time"] = _rate(apps)
    return s


def to_markdown(s: dict, actions: list = None) -> str:
    out = [f"# Weekly review {s['from']} to {s['to']}", "",
           "## This week",
           f"- Offers found: {s['offers_found']}, opened: {s['offers_opened']}, selected: {s['selected']}",
           f"- Packs prepared: {s['packs']}, applications sent: {s['applied']}",
           f"- Outreach: {s['outreach_found']} companies found, {s['outreach_sent']} emails sent "
           f"({s['outreach_replied']}/{s['outreach_total_sent']} replied so far)"]
    if s["turned_down"]:
        out.append("- Turned down: " + ", ".join(f"{k} ({v})" for k, v in s["turned_down"].most_common()))
    out.append("- Replies: " + ("; ".join(s["replies"]) if s["replies"] else "none"))
    out.append("")
    if actions:
        out += ["## Next week"] + [f"{n}. {a}" for n, a in enumerate(actions, 1)] + [""]
    if s["due"]:
        out += ["## Due now"] + [f"- {d}" for d in s["due"]] + [""]
    out += [f"## What gets replies (all time: {s['all_time']})", ""]
    out += _table("By track", s["by_track"]) + _table("By country", s["by_country"])
    out += _table("By channel", s["by_channel"]) + _table("By CV fit", s["by_match"])
    out += _table("Tailored pack or not", s["by_letter"])
    from analyzers.gaps import load as load_gaps
    tracked = [g for g in load_gaps().get("gaps", []) if g["fixable"] and g["status"] in ("open", "working")]
    if tracked:
        out += ["## Gaps worth fixing (Gaps tab)"] + [
            f"- {g['name']}: blocks {len(g['refs'])} jobs; {g['fix']} ({g['cost']}, {g['time']}) [{g['status']}]"
            for g in tracked[:5]] + [""]
    elif s["gaps"]:
        out += ["## Gaps the postings ask for most"] + [f"- {g} ({n})" for g, n in s["gaps"].most_common(8)] + [""]
    return "\n".join(out)


def weekly_review(use_claude: bool = True) -> tuple[str, Path]:
    """Build, save and return the review (markdown, path)."""
    s = stats()
    actions = None
    if use_claude:
        try:
            from core.llm import ask_json
            actions = ask_json(to_markdown(s), system=SYSTEM, schema=SCHEMA)["actions"]
        except Exception:
            actions = None
    md = to_markdown(s, actions)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{date.today().isoformat()}.md"
    path.write_text(md, encoding="utf-8")
    return md, path
