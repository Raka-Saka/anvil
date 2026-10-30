"""
Pipeline - every application, wherever it was sent.

Applications live in data/applications.yaml. Anvil does not apply for you;
it records what you sent, where, and what should happen next.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import yaml

from core.store import read_yaml, write_yaml, LOCK, fresh

ROOT = Path(__file__).parent.parent
DATA_FILE = ROOT / "data" / "applications.yaml"
CHANNELS_FILE = ROOT / "config" / "channels.yaml"

# Order matters: it is the funnel.
STAGES = ["found", "applied", "screening", "interview", "offer"]
CLOSED = ["rejected", "withdrawn", "ghosted"]
ALL_STAGES = STAGES + CLOSED

# A reply of any kind moves an application past "applied".
RESPONDED = {"screening", "interview", "offer", "rejected"}

FOLLOW_UP_DAYS = 10   # nudge after this long without a reply
GHOST_DAYS = 30       # mark ghosted after this long


def today() -> str:
    return date.today().isoformat()


def load_channels() -> list[dict]:
    if not CHANNELS_FILE.exists():
        return []
    return read_yaml(CHANNELS_FILE).get("channels", [])


def channel_name(channel_id: str) -> str:
    for c in load_channels():
        if c["id"] == channel_id:
            return c["name"]
    return channel_id or "unknown"


@dataclass
class Funnel:
    total: int
    applied: int
    responded: int
    interviews: int
    offers: int

    @property
    def response_rate(self) -> float:
        return self.responded / self.applied if self.applied else 0.0


class Pipeline:
    """Load, change and summarise applications."""

    def __init__(self, data_file: Path = DATA_FILE):
        self.data_file = data_file
        self.apps: list[dict] = []
        self.last_id = 0
        self._load()

    # --- storage -----------------------------------------------------------

    def reload(self):
        self._load()

    def _load(self):
        if self.data_file.exists():
            data = read_yaml(self.data_file)
            self.apps = data.get("applications", [])
            self.last_id = data.get("last_id", 0)

    def save(self):
        # last_id: a deleted entry's id is never given again (offers, packs and gaps point at ids)
        write_yaml(self.data_file, {"last_id": self.last_id, "applications": self.apps})

    # --- changes -----------------------------------------------------------

    @fresh
    def add(self, company: str, role: str, channel: str = "other", country: str = "",
            stage: str = "applied", url: str = "", on: Optional[str] = None,
            contact: str = "", notes: str = "", language: str = "",
            documents: Optional[list] = None, fit: Optional[dict] = None,
            description: str = "") -> dict:
        if stage not in ALL_STAGES:
            raise ValueError(f"Unknown stage: {stage}")
        on = on or today()
        app = {
            "id": max([a["id"] for a in self.apps] + [self.last_id]) + 1,
            "company": company,
            "role": role,
            "country": country,
            "channel": channel,
            "url": url,
            "stage": stage,
            "applied_on": on if stage != "found" else None,
            "history": [{"stage": stage, "on": on}],
            "next_action": "",
            "next_due": None,
            "contact": contact,
            "language": language,
            "documents": documents or [],
            "fit": fit,
            "notes": notes,
            "description": description[:4000],
        }
        self.last_id = app["id"]
        if stage == "applied":
            app["next_action"] = "Follow up if no reply"
            app["next_due"] = (date.fromisoformat(on) + timedelta(days=FOLLOW_UP_DAYS)).isoformat()
        self.apps.append(app)
        self.save()
        return app

    def get(self, app_id: int) -> Optional[dict]:
        return next((a for a in self.apps if a["id"] == app_id), None)

    @fresh
    def move(self, app_id: int, stage: str, on: Optional[str] = None, note: str = "") -> dict:
        if stage not in ALL_STAGES:
            raise ValueError(f"Unknown stage: {stage}")
        app = self.get(app_id)
        if app is None:
            raise KeyError(app_id)
        on = on or today()
        app["stage"] = stage
        app["history"].append({"stage": stage, "on": on, **({"note": note} if note else {})})
        if stage == "applied" and not app.get("applied_on"):
            app["applied_on"] = on
            app["next_action"] = "Follow up if no reply"
            app["next_due"] = (date.fromisoformat(on) + timedelta(days=FOLLOW_UP_DAYS)).isoformat()
        elif stage in ("screening", "interview"):
            app["next_action"] = "Prepare (interview brief) and reply" if stage == "screening" else "Interview"
            app["next_due"] = on
        elif stage in CLOSED or stage == "offer":
            app["next_action"], app["next_due"] = "", None
        self.save()
        return app

    @fresh
    def set_next(self, app_id: int, action: str, due: Optional[str] = None) -> dict:
        app = self.get(app_id)
        if app is None:
            raise KeyError(app_id)
        app["next_action"], app["next_due"] = action, due
        self.save()
        return app

    @fresh
    def update(self, app_id: int, **fields) -> dict:
        app = self.get(app_id)
        if app is None:
            raise KeyError(app_id)
        app.update(fields)
        self.save()
        return app

    @fresh
    def delete(self, app_id: int):
        self.apps = [a for a in self.apps if a["id"] != app_id]
        self.save()

    # --- views -------------------------------------------------------------

    def open_apps(self) -> list[dict]:
        return [a for a in self.apps if a["stage"] not in CLOSED]

    def due(self, on: Optional[str] = None) -> list[dict]:
        """Open applications whose next action is due on or before `on`."""
        on = on or today()
        return sorted((a for a in self.open_apps() if a.get("next_due") and a["next_due"] <= on),
                      key=lambda a: a["next_due"])

    def silent_since(self, days: int, on: Optional[str] = None) -> list[dict]:
        """Applied, no reply, and last change older than `days`."""
        cutoff = (date.fromisoformat(on or today()) - timedelta(days=days)).isoformat()
        return [a for a in self.apps if a["stage"] == "applied"
                and max(a["history"][-1]["on"], a.get("last_touch") or "") <= cutoff
                and (a.get("next_due") or "") < (on or today())]   # a planned follow-up still ahead: not ghosted

    @fresh
    def mark_ghosted(self, on: Optional[str] = None) -> list[dict]:
        ghosts = self.silent_since(GHOST_DAYS, on)
        for a in ghosts:
            self.move(a["id"], "ghosted", on, note=f"No reply in {GHOST_DAYS} days")
        return ghosts

    def funnel(self, apps: Optional[list] = None) -> Funnel:
        apps = self.apps if apps is None else apps
        reached = lambda a, s: any(h["stage"] == s for h in a["history"])
        sent = [a for a in apps if a.get("applied_on")]
        return Funnel(
            total=len(apps),
            applied=len(sent),
            responded=sum(1 for a in sent if any(h["stage"] in RESPONDED for h in a["history"])),
            interviews=sum(1 for a in apps if reached(a, "interview")),
            offers=sum(1 for a in apps if reached(a, "offer")),
        )

    def funnel_by(self, key: str) -> dict[str, Funnel]:
        """Funnel per channel or per country - shows what actually gets replies."""
        groups: dict[str, list] = {}
        for a in self.apps:
            groups.setdefault(a.get(key) or "unknown", []).append(a)
        return {k: self.funnel(v) for k, v in sorted(groups.items())}
