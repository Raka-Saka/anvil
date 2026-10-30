"""
Gaps tracker - what the postings ask for that his record does not show, and which fix opens most jobs.

Gaps come from every offer's fit note, every application pack, and offers he turned down for
experience or language. Claude groups them into named gaps (e.g. "JLPT N3", "Lean Six Sigma Green
Belt", "recent support work"), counts the offers each one blocks, and looks up a concrete fix:
course or exam, cost, time, next date. Some gaps cannot be fixed (age, years of experience); they are
marked so and not pushed.
Stored in data/gaps.yaml. His status per gap (open / working / done / skip) survives refreshes.
"""

from datetime import date
from pathlib import Path

import yaml

from core.store import read_yaml

ROOT = Path(__file__).parent.parent
DATA_FILE = ROOT / "data" / "gaps.yaml"
STATUSES = {"open": "Open", "working": "Working on it", "done": "Done", "skip": "Not worth it"}

SCHEMA = {
    "type": "object",
    "properties": {"gaps": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "key": {"type": "string"},
            "name": {"type": "string"},
            "kind": {"type": "string", "enum": ["language", "certificate", "skill", "experience", "degree", "other"]},
            "refs": {"type": "array", "items": {"type": "string"}},
            "fixable": {"type": "boolean"},
            "fix": {"type": "string"},
            "cost": {"type": "string"},
            "time": {"type": "string"},
            "next_date": {"type": "string"},
            "worth": {"type": "string", "enum": ["high", "medium", "low"]},
            "why": {"type": "string"},
            "sources": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["key", "name", "kind", "refs", "fixable", "fix", "cost", "time", "next_date", "worth",
                     "why", "sources"],
        "additionalProperties": False,
    }}},
    "required": ["gaps"],
    "additionalProperties": False,
}

SYSTEM = """You group the gaps between a job seeker's record and the jobs he looks at, and find the fix for each.
Input: notes on each job (ref id, title, the gap text), his profile, and the gaps already tracked.
- Group notes that mean the same thing into one gap. Keep the `key` of an already tracked gap when it is the same
  gap, so his progress is kept; new keys are short snake_case.
- name: short and concrete ("Japanese above his level", "Live chat support experience", "Lean Six Sigma Green Belt").
- refs: every ref id whose note shows this gap.
- fixable: false for what cannot be changed by him soon (age, years of experience, a degree that takes years);
  then fix explains how to answer it honestly in applications instead.
- fix: the cheapest credible way to close it, with the provider (exam, online course, volunteer work,
  a small project). cost in EUR (and JPY if in Japan), time to get it, next_date: next exam or intake date if any.
  Use web search for dates and prices; never invent them, write "check" when unknown.
- worth: high if it opens several of these jobs at low cost; low if it opens one job or costs a lot.
- why: one line: what it opens, in numbers (e.g. "blocks 5 of 18 offers, all in Japan").
- Only real gaps in the notes. Do not add generic advice."""


def load() -> dict:
    if DATA_FILE.exists():
        return read_yaml(DATA_FILE)
    return {}


def save(data: dict):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)


def collect() -> list[dict]:
    """Every note that names a gap, with a ref id: offer:<id> or app:<id>."""
    from core.offers import OfferLibrary
    from core.pipeline import Pipeline
    notes = []
    for o in OfferLibrary().offers:
        text = o.get("fit", "")
        if o.get("reject_reason") in ("experience", "language"):
            text += f" Turned down: {o['reject_reason']}. {o.get('reject_note', '')}"
        if text.strip():
            notes.append({"ref": f"offer:{o['id']}", "job": f"{o['title']} — {o['company']} ({o.get('location', '')})",
                          "text": text.strip()})
    for a in Pipeline().apps:
        gaps = (a.get("pack") or {}).get("gaps") or []
        if gaps:
            notes.append({"ref": f"app:{a['id']}", "job": f"{a['role']} — {a['company']}", "text": "; ".join(gaps)})
    return notes


def refresh() -> dict:
    """Regroup all gaps with Claude. Keeps his status and notes per gap. Takes a few minutes."""
    from analyzers.triage import profile_summary
    from core.llm import run_claude_code, LLMError
    old = {g["key"]: g for g in load().get("gaps", [])}
    notes = collect()
    tracked = "\n".join(f"- {k}: {g['name']} (status {g['status']})" for k, g in old.items()) or "- none"
    data = run_claude_code(
        "<jobs>\n" + "\n".join(f"[{n['ref']}] {n['job']}: {n['text']}" for n in notes) + "\n</jobs>\n\n"
        f"<profile>\n{profile_summary()}\n</profile>\n\n<tracked_gaps>\n{tracked}\n</tracked_gaps>\n\n"
        f"Today: {date.today()}",
        system=SYSTEM, schema=SCHEMA, tools=["WebSearch", "WebFetch"], effort="medium",
    )
    found = (data.get("structured_output") or {}).get("gaps")
    if found is None:
        raise LLMError(data.get("result") or "No gaps.")
    from core.store import LOCK
    with LOCK:
        old = {g["key"]: g for g in load().get("gaps", [])}    # statuses may have changed meanwhile
        return _merge(found, old, len(notes))


def _merge(found, old, n_jobs):
    gaps = []
    for g in found:
        prev = old.pop(g["key"], {})
        g["status"] = prev.get("status", "open")
        g["note"] = prev.get("note", "")
        gaps.append(g)
    for g in old.values():          # no longer in any offer: kept if he worked on it
        if g["status"] != "open":
            g["refs"] = []
            gaps.append(g)
    out = {"updated": date.today().isoformat(), "jobs": n_jobs, "gaps": ranked(gaps)}
    save(out)
    return out


def ranked(gaps: list) -> list:
    order = {"high": 0, "medium": 1, "low": 2}
    return sorted(gaps, key=lambda g: (g["status"] in ("done", "skip"), not g["fixable"],
                                       order.get(g["worth"], 3), -len(g["refs"])))


def set_status(key: str, status: str, note: str = None):
    from core.store import LOCK
    with LOCK:
        _set_status(key, status, note)


def _set_status(key, status, note):
    data = load()
    for g in data.get("gaps", []):
        if g["key"] == key:
            g["status"] = status
            if note is not None:
                g["note"] = note
            if status == "done":
                g["done_on"] = date.today().isoformat()
    data["gaps"] = ranked(data.get("gaps", []))
    save(data)


def job_titles(refs: list) -> list[str]:
    from core.offers import OfferLibrary
    from core.pipeline import Pipeline
    lib, pipe = OfferLibrary(), Pipeline()
    out = []
    for r in refs:
        kind, _, n = r.partition(":")
        item = lib.get(int(n)) if kind == "offer" else pipe.get(int(n)) if kind == "app" else None
        if item:
            out.append(f"{item.get('title') or item.get('role')} — {item['company']}")
    return out
