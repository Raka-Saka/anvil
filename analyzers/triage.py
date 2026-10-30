"""
Triage - is this posting worth an application, and which document goes with it?

Rules run first and need no API: Japanese level, French/English, location, age
limits, nationality, driving licence. Claude, when available, adds a reasoned
read on top. Verdicts: realistic / stretch / skip.
"""

import json
import re
from dataclasses import dataclass, field, asdict
from datetime import date
from pathlib import Path
from typing import Optional

import yaml

ROOT = Path(__file__).parent.parent
DOCUMENTS_FILE = ROOT / "data" / "documents.yaml"

AGE = 49  # from the rirekisho; update with the profile


@dataclass
class Flag:
    level: str   # blocker | stretch | plus | note
    text: str


@dataclass
class Triage:
    verdict: str                      # realistic | stretch | skip
    track: Optional[str]
    track_label: str
    documents: list
    flags: list = field(default_factory=list)
    reasons: list = field(default_factory=list)   # Claude's reading, if any
    motivation_angle: str = ""
    match: int = None                              # 0-100, Claude only
    by: str = "rules"
    note: str = ""

    def to_fit(self) -> dict:
        """Compact form stored on a pipeline entry."""
        return {
            "verdict": self.verdict, "track": self.track, "by": self.by, "on": date.today().isoformat(),
            "flags": [f"{f.level}: {f.text}" for f in self.flags],
            "reasons": self.reasons, "match": self.match,
        }


def load_library() -> dict:
    from core.store import read_yaml
    return read_yaml(DOCUMENTS_FILE)


# --- rules -------------------------------------------------------------------

JP_HIGH = [   # a bare "N2" is a support level in French/English postings; only count it next to Japanese/JLPT
    r"JLPT\s*N[123]", r"(japanese|日本語)[^.\n]{0,30}\bN[123]\b", r"\bN[123]\b[^.\n]{0,20}(japanese|日本語|以上)", r"日本語能力試験\s*N[123]", r"日本語能力試験\s*[123]級",
    r"日本語.{0,6}(ビジネス|ネイティブ|堪能|流暢|上級)", r"(ビジネス|ネイティブ)レベルの日本語",
    r"(business|native|fluent|advanced)[- ](level )?japanese", r"japanese[^.\n]{0,25}(business|native|fluent)",
]
JP_LOW_OK = [r"日常会話", r"\bN4\b", r"conversational japanese", r"daily conversation", r"basic japanese", r"日本語(不問|不要)",
             r"japanese (not required|is a plus|a plus)", r"no japanese"]
FRENCH = [r"french", r"フランス語", r"français", r"francophone", r"francés", r"frances\b", r"francês",
          r"französisch", r"francese", r"frans\b", r"francuski", r"francouzšt"]
ENGLISH = [r"english", r"英語"]
OSAKA = [r"osaka", r"大阪", r"kansai", r"関西"]
FULL_REMOTE = [r"full[- ]?remote", r"fully remote", r"100\s?% (remote|télétravail|en remoto|remoto)", r"remote[- ]first",
               r"フルリモート", r"完全在宅", r"完全リモート", r"télétravail (complet|total)", r"full[- ]?télétravail",
               r"\bremote\b(?![^.\n]{0,25}(day|jour|día|tag|hybrid))", r"teletrabajo total", r"100% remoto"]
PART_REMOTE = [r"hybrid", r"hybride", r"híbrido", r"\d\s*(jours?|days?|días|tage?)\s*(de )?(télétravail|remote|teletrabajo)",
               r"(télétravail|remote|teletrabajo)[^.\n]{0,20}\d\s*(jours?|days?|días|tage?)", r"télétravail partiel",
               r"一部在宅", r"週\d日.{0,4}(在宅|リモート)"]
TOKYO = [r"tokyo", r"東京"]
FRANCE_CITY = [r"paris", r"lyon", r"marseille", r"toulouse", r"bordeaux", r"lille", r"nantes", r"france"]
NATIONALITY = [r"日本国籍", r"japanese nationals? only", r"japanese citizenship"]
LICENCE = [r"普通(自動車)?免許", r"driver'?s licen[cs]e", r"permis b\b", r"carnet de conducir", r"carta de condução",
           r"führerschein"]
# Work rights: EU/EEA + Switzerland (French national) and Japan (spouse visa). Nowhere else.
NO_RIGHTS = [r"authori[sz]ed to work in the (us|u\.s\.|united states|uk|united kingdom|canada|australia)",
             r"autorisation de travail (au|aux|en) (royaume-uni|états-unis|canada|australie)",
             r"permiso de trabajo (en|para) (ee\.? ?uu|estados unidos|reino unido|canadá)",
             r"right to work in the (uk|united kingdom|us|united states|canada|australia)",
             r"(us|u\.s\.|uk|canada|australia)[- ]based (only|candidates)", r"\b(us|usa|uk|canada) only\b",
             r"must (be located|reside|live) in the (us|united states|uk|united kingdom|canada)",
             r"(us|u\.s\.) citizens?(hip)? (only|required)", r"green card", r"security clearance"]
WORLDWIDE_OK = [r"worldwide", r"anywhere in the world", r"\bglobal(ly)? remote\b", r"employer of record",
                r"\bemea\b", r"\beurope\b", r"\beu\b", r"\bjapan\b", r"日本"]


def _any(patterns, text):
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def _japanese_share(text: str) -> float:
    jp = len(re.findall(r"[぀-ヿ一-鿿]", text))
    return jp / max(len(text), 1)


def rule_flags(text: str, track: Optional[str]) -> list[Flag]:
    t = text.lower()
    flags = []

    if _any(JP_HIGH, text) and not _any(JP_LOW_OK, text):
        flags.append(Flag("blocker", "Asks for Japanese above N4 (N3+, business or native level)."))
    elif _japanese_share(text) > 0.3 and not _any(JP_LOW_OK, text) and track not in ("factory", "hotel", "cs_jp", "teaching_fr"):
        flags.append(Flag("stretch", "Posting is in Japanese and says nothing about the level; expect Japanese at work."))
    elif _any(JP_LOW_OK, text):
        flags.append(Flag("plus", "Basic or daily-conversation Japanese is fine."))

    if _any(FRENCH, t):
        flags.append(Flag("plus", "Mentions French: your native language."))
    if _any(ENGLISH, t):
        flags.append(Flag("plus", "Mentions English: fluent, 4 years working in the UK and Ireland."))

    if _any(NATIONALITY, text):
        flags.append(Flag("blocker", "Requires Japanese nationality."))

    for m in re.finditer(r"(\d{2})\s*歳\s*(まで|以下|迄|未満)", text):
        if int(m.group(1)) < AGE:
            flags.append(Flag("blocker", f"Age limit {m.group(1)} (you are {AGE})."))
    for pat in (r"(under|up to|below|max(?:imum)?)\s*(\d{2})\s*(years old|y\.?o)",
                r"(moins de|maximum|jusqu'à)\s*(\d{2})\s*ans", r"(menos de|máximo|hasta)\s*(\d{2})\s*años",
                r"(menos de|até)\s*(\d{2})\s*anos", r"(unter|bis|höchstens)\s*(\d{2})\s*jahre"):
        for m in re.finditer(pat, t):
            if int(m.group(2)) < AGE:
                flags.append(Flag("blocker", f"Age limit {m.group(2)} (you are {AGE})."))

    partly = _any(PART_REMOTE, t)
    remote = _any(FULL_REMOTE, t) and not partly
    if _any(OSAKA, t):
        flags.append(Flag("plus", "Osaka / Kansai."))
    elif remote:
        flags.append(Flag("plus", "Fully remote (check from which countries)."))
    else:
        if partly:
            flags.append(Flag("note", "Partly remote only: you still need to live near the office."))
        if _any(TOKYO, t):
            flags.append(Flag("stretch", "Tokyo, on site: needs a move."))
        elif _any(FRANCE_CITY, t) and _japanese_share(text) < 0.05:
            flags.append(Flag("stretch", "On site in France: needs a move."))

    if _any(NO_RIGHTS, text):
        if _any(WORLDWIDE_OK, t):
            flags.append(Flag("stretch", "Mentions US/UK work rights but also EU, Japan or worldwide: check which applies."))
        else:
            flags.append(Flag("blocker", "Needs the right to work in the US/UK or similar. You have EU and Japan only."))

    lack = re.search(r"(deutsch|german|allemand|alemán|néerlandais|dutch|nederlands|italien|italian|italiano|"
                     r"polish|polski|polonais|portugais|portuguese|português)[^.\n]{0,40}"
                     r"(c1|c2|fluent|courant|natif|native|muttersprach|zwingend|erforderlich|required|obligatoire|indispensable)|"
                     r"(sehr gute|fließende?|verhandlungssichere?) deutschkenntnisse|deutschkenntnisse[^.\n]{0,20}(c1|c2|zwingend)",
                     t)
    if lack:
        flags.append(Flag("blocker", f"Requires a language you don't have: '{lack.group(0)[:40]}'."))

    if _any(LICENCE, text):
        flags.append(Flag("note", "Asks for a driving licence: check you hold the right one."))

    return flags


def pick_track(text: str, library: dict) -> Optional[str]:
    t = text.lower()
    best, best_hits = None, 0
    for tid, tr in library.get("tracks", {}).items():
        hits = sum(1 for k in tr.get("keywords", []) if k.lower() in t)
        if hits > best_hits:
            best, best_hits = tid, hits
    return best


def verdict_from(flags: list[Flag], track: Optional[str]) -> str:
    if any(f.level == "blocker" for f in flags):
        return "skip"
    if track is None or any(f.level == "stretch" for f in flags):
        return "stretch"
    return "realistic"


# --- Claude -------------------------------------------------------------------

SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["realistic", "stretch", "skip"]},
        "track": {"type": "string"},
        "reasons": {"type": "array", "items": {"type": "string"}},
        "motivation_angle": {"type": "string"},
        "match": {"type": "integer"},
    },
    "required": ["verdict", "track", "reasons", "motivation_angle", "match"],
    "additionalProperties": False,
}

SYSTEM = """You triage job postings for one candidate. Be honest and brief.
"realistic": he meets the hard requirements and has direct evidence for the core of the job.
"stretch": one real gap, or a move, but worth sending.
"skip": a hard requirement he cannot meet, or nothing in his record matches.
Use only facts from the profile. Never assume skills, levels or numbers that are not written there.
Reasons: 2-4 short sentences, each naming the requirement and the evidence (or the gap).
motivation_angle: one sentence on the honest link between his record and this employer, for the cover letter or 志望動機.
match 0-100: how much of the job's core duties his record shows directly. 80+ he has done this job; 50-79 related experience with a gap; under 50 a stretch. Judge the duties, not the wording."""


def claude_triage(text: str, profile_summary: str, library: dict, flags: list[Flag]) -> dict:
    from core.llm import ask_json
    tracks = "\n".join(f"- {k}: {v['label']}" for k, v in library.get("tracks", {}).items())
    found = "\n".join(f"- {f.level}: {f.text}" for f in flags) or "- none"
    return ask_json(
        f"<profile>\n{profile_summary}\n</profile>\n\n<tracks>\n{tracks}\n</tracks>\n\n"
        f"<rule_checks>\n{found}\n</rule_checks>\n\n<posting>\n{text}\n</posting>\n\n"
        "Pick the track id that fits best.",
        system=SYSTEM, schema=SCHEMA,
    )


def profile_summary() -> str:
    from core.profile_manager import ProfileManager
    pm = ProfileManager()
    p = pm.load()
    lines = [f"Name: {p['personal'].get('name')} ({p['personal'].get('name_ja', '')} in Japanese: always "
             f"this katakana, never フローラン)."]
    lines += [f"Location: {p['personal'].get('location')}. Age {AGE}. French national, Japan spouse visa (no work limits)."]
    lines += [f"Language: {l['language']} - {l['level']}" for l in pm.get_languages()]
    lines.append("When you write a reason, note, fit line, gap or explanation for him to read, address him as "
                 "'you' and 'your' (never 'he' or 'his'). CVs, letters and emails stay in his own first person.")
    lines.append("These language levels are exact. Never state a higher level, a language not listed, or a "
                 "certificate he does not hold (for Japanese: never N3 or above, never 'business' or 'fluent').")
    if p.get("facts"):
        lines.append("Facts he confirmed himself (they override anything else here):")
        lines += [f"- {f}" for f in p["facts"]]
    for e in pm.get_experience():
        lines.append(f"{e['role']} at {e['company']} ({e['period']['start']}-{e['period']['end']}): "
                     + "; ".join(e.get("achievements", [])))
    for pr in pm.get_projects():
        if pr.get("status") in ("active", "complete", "published"):
            tag = " (built with AI assistance)" if pr.get("ai_assisted") else ""
            lines.append(f"Project {pr['name']}{tag}: {pr.get('description', '')}")
    lines.append("Certifications: " + ", ".join(p.get("skills", {}).get("certifications", [])))
    return "\n".join(lines)


# --- entry point --------------------------------------------------------------

def triage(text: str, use_claude: bool = True) -> Triage:
    library = load_library()
    track = pick_track(text, library)
    flags = rule_flags(text, track)
    result = Triage(verdict=verdict_from(flags, track), track=track, track_label="", documents=[], flags=flags)

    if use_claude:
        from core.llm import backend
        if backend():
            try:
                ai = claude_triage(text, profile_summary(), library, flags)
                result.reasons = ai["reasons"]
                result.motivation_angle = ai["motivation_angle"]
                result.match = ai["match"]
                if ai["track"] in library.get("tracks", {}):
                    result.track = ai["track"]
                # Rules hold the hard limits: Claude cannot lift a blocker.
                if result.verdict != "skip":
                    result.verdict = ai["verdict"]
                result.by = "rules+claude"
            except Exception as e:  # rules result still stands
                msg = getattr(e, "message", None) or str(e)
                if "credit balance" in msg:
                    msg = "API credit is empty. Rules only."
                result.note = f"Claude not used: {msg[:160]}"
        else:
            result.note = "Claude not used: install Claude Code or add an API key."

    tr = library.get("tracks", {}).get(result.track or "", {})
    result.track_label = tr.get("label", "No matching track")
    result.documents = [d for d in library.get("documents", []) if d["track"] == result.track]
    return result
