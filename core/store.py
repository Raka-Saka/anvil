"""
One lock for the YAML stores (pipeline, offers, outreach, gaps, cities).

Claude calls run in worker threads for minutes; a store loaded before the call and saved after it
would overwrite what other threads wrote meanwhile. Mutating methods marked @fresh reload from
disk under the lock, change, and save, so no write is lost.
"""

import functools
import threading

LOCK = threading.RLock()


def fresh(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        with LOCK:
            self.reload()
            return method(self, *args, **kwargs)
    return wrapper


# --- fast, cached YAML reads -------------------------------------------------------
# The pure-Python YAML parser took ~80 ms per read and the UI read the same files hundreds of
# times while drawing (29 s to open the window). Reads now use libyaml and are cached until the
# file changes on disk (mtime + size); each caller gets its own copy, so mutating it is safe.

import copy
import os

import yaml

_Loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
_cache: dict = {}


def read_yaml(path, default=None):
    """Parsed YAML of `path` ({} or `default` if missing/empty). Cached until the file changes."""
    p = os.fspath(path)
    try:
        st = os.stat(p)
    except FileNotFoundError:
        return copy.deepcopy(default) if default is not None else {}
    key = (st.st_mtime_ns, st.st_size)
    hit = _cache.get(p)
    if not hit or hit[0] != key:
        with open(p, encoding="utf-8") as f:
            data = yaml.load(f, Loader=_Loader)
        hit = (key, data)
        _cache[p] = hit
    data = hit[1]
    if data is None:
        return copy.deepcopy(default) if default is not None else {}
    return copy.deepcopy(data)


def write_yaml(path, data):
    """Write YAML (fast dumper when available)."""
    dumper = getattr(yaml, "CSafeDumper", yaml.SafeDumper)
    os.makedirs(os.path.dirname(os.fspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, Dumper=dumper, allow_unicode=True, sort_keys=False)
