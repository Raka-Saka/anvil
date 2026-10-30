"""
Task centre - every long job Anvil runs (web searches, research, CVs and letters, briefs), in one place.

Views register a task when they start one and finish it when it ends, so it keeps running and stays
visible whichever screen he is on. Call start/update/finish from Flet's event loop (async handlers);
listeners then refresh their part of the screen.
"""

import itertools
import time
from typing import Callable, Optional


class TaskCenter:
    def __init__(self):
        self.tasks: dict[int, dict] = {}
        self.recent: list[dict] = []          # finished, newest first (last 10)
        self._ids = itertools.count(1)
        self._listeners: list[Callable[[], None]] = []

    def listen(self, fn: Callable[[], None]):
        self._listeners.append(fn)

    def _changed(self):
        for fn in list(self._listeners):
            try:
                fn()
            except Exception:
                pass

    def start(self, label: str, stage: str = "", where: str = "") -> int:
        tid = next(self._ids)
        self.tasks[tid] = {"id": tid, "label": label, "stage": stage, "where": where, "started": time.time()}
        self._changed()
        return tid

    def update(self, tid: int, stage: str):
        if tid in self.tasks and self.tasks[tid]["stage"] != stage:
            self.tasks[tid]["stage"] = stage
            self._changed()

    def finish(self, tid: int, result: str = "", ok: bool = True):
        t = self.tasks.pop(tid, None)
        if t:
            t.update(result=result, ok=ok, ended=time.time())
            self.recent = [t] + self.recent[:9]
            self._changed()

    def running(self) -> list[dict]:
        return sorted(self.tasks.values(), key=lambda t: t["started"])

    @staticmethod
    def elapsed(t: dict) -> str:
        s = int(time.time() - t["started"])
        return f"{s // 60} min {s % 60:02d} s" if s >= 60 else f"{s} s"


TASKS = TaskCenter()


class Navigator:
    """Lets any view send him to another place (and an item there): NAV.go("applications", app_id=3)."""

    def __init__(self):
        self._go: Optional[Callable] = None

    def bind(self, fn: Callable):
        self._go = fn

    def go(self, place: str, **focus):
        if self._go:
            self._go(place, **focus)


NAV = Navigator()

# Named actions one view offers the others, e.g. HOOKS["investigate"](offer_ids) set by Offers.
HOOKS: dict = {}
