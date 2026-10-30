"""
Application pack - a tailored CV and cover letter for one offer, ready to send.

Claude reads the posting itself (WebFetch), picks the track, and rewrites the matching base CV
from docs/ for this job, using only facts written in his documents and profile. For Japanese
tracks Anvil writes a fresh 履歴書 (dated today, with this job's 志望動機) and 職務経歴書 as PDFs
(generators/rirekisho.py); the fixed facts come from data/rirekisho.yaml.
Files go to output/applications/<pipeline id>-<company>/: cv.md/.docx, letter.md/.docx, posting.md.
The Basin fraud check runs on both texts; violations are listed in the pack.
"""

import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
OUT_DIR = ROOT / "output" / "applications"
BUSY = set()   # pipeline ids being prepared, shared by the Job Finder and Pipeline tabs

SCHEMA = {
    "type": "object",
    "properties": {
        "track": {"type": "string"},
        "language": {"type": "string", "enum": ["en", "fr", "ja"]},
        "posting": {"type": "string"},
        "cv": {"type": "string"},
        "letter_kind": {"type": "string"},
        "letter": {"type": "string"},
        "how_to_apply": {"type": "string"},
        "letter_english": {"type": "string"},
        "gaps": {"type": "array", "items": {"type": "string"}},
        "rireki_jobs": {"type": "array", "items": {
            "type": "object", "properties": {"company": {"type": "string"}, "desc": {"type": "string"}},
            "required": ["company", "desc"], "additionalProperties": False}},
        "rireki_licenses": {"type": "array", "items": {"type": "string"}},
        "hope": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["track", "language", "posting", "cv", "letter_kind", "letter", "how_to_apply", "letter_english", "gaps",
                 "rireki_jobs", "rireki_licenses", "hope"],
    "additionalProperties": False,
}

SYSTEM = """You prepare one job application for the candidate. Open the posting URL with WebFetch first.
Hard rules:
- Use only facts written in his base documents and profile below. Never add a skill, number, tool, date
  or achievement that is not there. If the job wants something he lacks, list it in `gaps`, never claim it.
- Work done with AI assistance (his software projects) is said to be built with AI assistance.
- Voice: quiet, plain, first person, short sentences (max 20 words), active voice. No exclamation marks.
  Never use: {forbidden}.
- Write in the posting's language (`language`).
Output:
- track: the id of the base document track that fits best.
- posting: the posting's text as you read it (title, company, place, duties, requirements, how to apply), plain text.
- cv: for en/fr, the base CV for that track rewritten for this job, in Markdown: same facts, reordered and
  reworded so the duties the posting asks for come first, the posting's own words used where they are
  true. One or two pages.
  For ja: the 職務経歴書 in Markdown (## 職務要約, ## 職務経歴, 【Employer（city）】 date lines, ・ bullets,
  ## 資格・語学, ## 自己PR), rewritten from his base 職務経歴書 for this job: same facts only, the duties this
  posting asks for first. No title, date or name (Anvil adds them). Never copy a staff number or anything
  addressed to another company or agency, and never say short-term (短期) unless this posting is short-term.
- letter_kind: "Cover letter", "Lettre de motivation" or "志望動機".
- letter: en/fr: 180-300 words, problem then evidence, ends plainly (no "I look forward to").
  ja: a 志望動機 of 200-300 characters in polite form, naming this company and why.
- how_to_apply: one line in English (even for a French or Japanese job): where and how to send it
  (form, email, site), and which files to attach. He applies from Japan, and HelloWork.com refuses
  applications from Japanese IPs: never send him there. For ja, the files are 履歴書.pdf and 職務経歴書.pdf
  that Anvil writes for this job, dated today and with this 志望動機 already in: name them, never ask him to
  edit a file or to use an older 履歴書. Use WebSearch to find the employer's or recruiter's own
  careers page or application email for this job; if there is none, say so plainly.
- letter_english: for ja, a faithful English translation of the letter so he can check it; else "".
- For ja, Anvil prints a new 履歴書 from his fixed facts (names, dates, employers come from Anvil, not you):
  rireki_jobs: for each employer in <rirekisho_facts>, the duty wording that best fits this job, in the style
  of his 履歴書 versions (e.g. 越境EC（ASOS）カスタマーサポート業務 for support jobs, 食品工場にて製造・包装
  および業務改善を担当 for factory jobs), only from his documents; company exactly as written in the facts.
  rireki_licenses: which licence lines (exact text from the facts) to show; all of them unless one is irrelevant.
  hope: the 本人希望記入欄 lines, chosen only from hope_facts (pick the ones that fit this job; a shift the posting
  lists may be named). Never add short-term (短期) availability. The visa line is added by Anvil.
  For en/fr: rireki_jobs, rireki_licenses and hope are empty lists.
- gaps: in English.
- gaps: the posting's requirements he does not show, honestly, each in a few words, in English."""


def _base_documents() -> str:
    """Text of every base CV in docs/, tagged with its track."""
    from analyzers.triage import load_library
    from pypdf import PdfReader
    parts = []
    for d in load_library().get("documents", []):
        path = ROOT / d["file"]
        if not path.exists() or path.suffix.lower() != ".pdf":
            continue
        try:
            text = "\n".join(p.extract_text() or "" for p in PdfReader(path).pages)
        except Exception:
            continue
        parts.append(f'<document track="{d["track"]}" lang="{d["lang"]}" kind="{d["kind"]}" file="{path.name}">\n'
                     f"{text.strip()[:6000]}\n</document>")
    return "\n\n".join(parts)


def _forbidden() -> list[str]:
    from core.profile_manager import ProfileManager
    return ProfileManager().load_voice()["language"]["forbidden"]


def _slug(text: str) -> str:
    return re.sub(r"[^\w]+", "-", text.lower()).strip("-")[:40] or "job"


def _docx(markdown: str, path: Path):
    """Plain DOCX from simple Markdown: headings, bullets, paragraphs."""
    from docx import Document
    from docx.shared import Pt
    doc = Document()
    doc.styles["Normal"].font.size = Pt(10.5)
    for line in markdown.splitlines():
        s = line.strip()
        if not s:
            continue
        m = re.match(r"^(#{1,3})\s+(.*)", s)
        clean = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
        if m:
            doc.add_heading(re.sub(r"\*\*(.+?)\*\*", r"\1", m.group(2)), level=len(m.group(1)))
        elif re.match(r"^[-*•]\s+", s):
            doc.add_paragraph(re.sub(r"^[-*•]\s+", "", clean), style="List Bullet")
        else:
            doc.add_paragraph(clean)
    doc.save(path)


def prepare(app_id: int) -> dict:
    """Write the pack for a pipeline entry and record it there. Takes a minute or two."""
    from analyzers.triage import load_library, profile_summary
    from basin.method import OrangeLayer
    from core.llm import run_claude_code, LLMError
    from core.pipeline import Pipeline
    from core.profile_manager import ProfileManager

    pipe = Pipeline()
    app = pipe.get(app_id)
    if not app:
        raise KeyError(app_id)
    lib = load_library()
    tracks = "\n".join(f"- {k}: {v['label']}" for k, v in lib.get("tracks", {}).items())
    known = f"\nWhat the search noted: {app.get('notes', '')}" if app.get("notes") else ""
    if app.get("description"):
        known += ("\n\n<posting_text>\n" + app["description"][:20000] + "\n</posting_text>\n"
                  "(The posting as he copied it. Use this text; the site may refuse to be read.)")
    from generators import rirekisho
    facts = rirekisho.facts()
    if facts:
        import yaml
        known += ("\n\n<rirekisho_facts>\n" + yaml.safe_dump(
            {k: facts.get(k) for k in ("career", "licenses", "hope_facts")}, allow_unicode=True, sort_keys=False)
                  + "</rirekisho_facts>")
    data = run_claude_code(
        f"Posting: {app['url']}\nRole: {app['role']}\nCompany: {app['company']}{known}\n\n"
        f"<profile>\n{profile_summary()}\n</profile>\n\n<tracks>\n{tracks}\n</tracks>\n\n"
        f"<base_documents>\n{_base_documents()}\n</base_documents>\n\nToday: {date.today()}",
        system=SYSTEM.format(forbidden=", ".join(f'"{p}"' for p in _forbidden())),
        schema=SCHEMA, tools=["WebFetch", "WebSearch"], effort="medium",
    )
    pack = data.get("structured_output")
    if not pack:
        raise LLMError(data.get("result") or "No application pack.")

    pm = ProfileManager()
    orange = OrangeLayer(pm.load(), pm.load_voice())
    violations = [v["found"] for v in orange.validate(pack["cv"] + "\n" + pack["letter"])]

    folder = OUT_DIR / f"{app_id}-{_slug(app['company'])}"
    folder.mkdir(parents=True, exist_ok=True)
    files = []
    (folder / "posting.md").write_text(f"# {app['role']} — {app['company']}\n\n{app['url']}\n\n{pack['posting']}\n",
                                       encoding="utf-8")
    (folder / "letter.md").write_text(pack["letter"], encoding="utf-8")
    if pack.get("letter_english", "").strip():
        (folder / "letter_english.md").write_text(pack["letter_english"], encoding="utf-8")
    if pack["language"] == "ja" and facts:
        # a fresh 履歴書 (today's date, this 志望動機) and 職務経歴書, ready to attach
        rirekisho.render_rirekisho(folder / "履歴書.pdf", pack["letter"], pack["hope"],
                                   {j["company"]: j["desc"] for j in pack["rireki_jobs"]},
                                   pack["rireki_licenses"] or None)
        files.append(str(folder / "履歴書.pdf"))
        if pack["cv"].strip():
            (folder / "職務経歴書.md").write_text(pack["cv"], encoding="utf-8")
            rirekisho.render_shokumu(folder / "職務経歴書.pdf", pack["cv"])
            files.append(str(folder / "職務経歴書.pdf"))
        else:
            files += [str(ROOT / d["file"]) for d in lib.get("documents", [])
                      if d["track"] == pack["track"] and d["kind"] == "shokumu"]
    else:
        if pack["cv"].strip():
            (folder / "cv.md").write_text(pack["cv"], encoding="utf-8")
            _docx(pack["cv"], folder / "cv.docx")
            files.append(str(folder / "cv.docx"))
        _docx(pack["letter"], folder / "letter.docx")
        files.append(str(folder / "letter.docx"))
        if not pack["cv"].strip():    # no CV written: send the base one for the track
            files = [str(ROOT / d["file"]) for d in lib.get("documents", []) if d["track"] == pack["track"]] + files

    pipe.update(app_id, documents=files, language=pack["language"], description=pack["posting"][:4000],
                pack={"folder": str(folder), "track": pack["track"], "letter_kind": pack["letter_kind"],
                      "how_to_apply": pack["how_to_apply"], "gaps": pack["gaps"], "violations": violations,
                      "on": date.today().isoformat()})
    pipe.set_next(app_id, "Check the pack and send it", date.today().isoformat())
    return pipe.get(app_id)
