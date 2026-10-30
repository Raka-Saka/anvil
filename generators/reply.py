"""
Answer kit - what to do when an employer writes back between the application and the interview.

Claude reads their e-mail (from core/mail_watch.py) with the application card and what was sent,
and says what they ask for (a 履歴書 by post, a detailed CV, a form, a date), how and by when.
Anvil then writes what is needed into the application folder: a fresh 履歴書 / 職務経歴書 (the
志望動機 already sent is kept), a 送付状 when it goes by post, the CV for en/fr, the reply in their
language with an English gloss, and answer_<date>.md with the steps and the envelope text.
Nothing is sent: the reply can be saved as a Gmail draft in their thread, for him to check and send.
"""

import re
from datetime import date
from pathlib import Path

from generators.application import OUT_DIR, _slug, _docx, _base_documents, _forbidden

ANSWERABLE = ("reply", "interview", "offer")

SCHEMA = {
    "type": "object",
    "properties": {
        "asks": {"type": "array", "items": {"type": "string"}},
        "deliver": {"type": "string", "enum": ["email", "post", "upload", "form", "phone", "in_person", "none"]},
        "deadline": {"type": "string"},
        "postal_address": {"type": "string"},
        "addressee": {"type": "string"},
        "documents": {"type": "array", "items": {"type": "string", "enum": [
            "rirekisho", "shokumu", "cv", "letter", "other"]}},
        "other_documents": {"type": "array", "items": {"type": "string"}},
        "reply_needed": {"type": "boolean"},
        "reply_subject": {"type": "string"},
        "reply": {"type": "string"},
        "reply_english": {"type": "string"},
        "cover_note": {"type": "string"},
        "cv": {"type": "string"},
        "rireki_jobs": {"type": "array", "items": {
            "type": "object", "properties": {"company": {"type": "string"}, "desc": {"type": "string"}},
            "required": ["company", "desc"], "additionalProperties": False}},
        "rireki_licenses": {"type": "array", "items": {"type": "string"}},
        "hope": {"type": "array", "items": {"type": "string"}},
        "steps": {"type": "array", "items": {"type": "string"}},
        "next_action": {"type": "string"},
        "next_due": {"type": "string"},
    },
    "required": ["asks", "deliver", "deadline", "postal_address", "addressee", "documents", "other_documents",
                 "reply_needed", "reply_subject", "reply", "reply_english", "cover_note", "cv", "rireki_jobs",
                 "rireki_licenses", "hope", "steps", "next_action", "next_due"],
    "additionalProperties": False,
}

SYSTEM = """An employer wrote back to the candidate after his application. Work out what they ask and
prepare his answer. Hard rules:
- Use only facts in his profile, base documents and the application already sent. Never invent a skill,
  number, date or achievement. Keep what he already told them (the letter / 志望動機 sent) consistent.
- Voice: quiet, plain, polite, short sentences. No exclamation marks. Never use: {forbidden}.
- Never promise a date he did not give; say "within the next few days" (近日中) style wording instead.
Output:
- asks: each thing they ask for, one short English line each (documents, questions to answer). How and by
  when go in deliver and deadline, not here.
- deliver: how the documents go: email, post (郵送), upload (their site), form, phone, in_person, none.
- deadline: their deadline as YYYY-MM-DD if they give one, else "".
- postal_address: for post, the street address only (〒 code first, no company name), from their e-mail or the posting;
  if neither has it, look up the company's own site with WebSearch; "" if not found or not post.
- addressee: who to write to, e.g. "株式会社ツルミ製麺所 採用ご担当者様" (a named person: "… 様"). Empty if not needed.
- documents: which of his documents they want: rirekisho (履歴書), shokumu (職務経歴書), cv (an en/fr CV),
  letter (cover letter). A Japanese employer asking for 履歴書 only: rirekisho, plus shokumu when it helps
  his case (it shows his line and inspection work in detail) - say in steps that it is optional.
  other_documents: anything else (diploma copy, residence card copy, portfolio), in English.
- reply_needed: true when a short e-mail answer is polite or needed (in Japan, a short 承知しました mail
  before posting documents is good manners).
  reply_subject: "Re: <their subject>". reply: the e-mail in their language, ready to send: Japanese in
  business form (宛名, 名乗り, お礼, what he will do, 結び, 署名 with name, phone, e-mail from his facts).
  reply_english: a faithful English translation, so he can check it. Both "" when no reply is needed.
- cover_note: for post, the body of the 送付状 in Japanese (拝啓 + 時候の挨拶 for this month … お礼,
  what is enclosed, a request for consideration … 敬具), without the 記/同封書類 list (Anvil adds it). Else "".
- cv: only when documents has shokumu (Japanese) or cv (en/fr), in Markdown, rewritten from his base documents
  for this job, same rules as an application pack: ja = ## 職務要約, ## 職務経歴, 【Employer（city）】 date lines,
  ・ bullets, ## 資格・語学, ## 自己PR; no title, date or name; never a staff number or short-term (短期)
  unless the job is short-term. "" otherwise. A request for a "detailed CV" means a full one, two pages.
- rireki_jobs, rireki_licenses, hope: only when documents has rirekisho, as for the application pack: for each
  employer in <rirekisho_facts> the duty wording that fits this job (company exactly as written there), the
  licence lines to show, and the 本人希望記入欄 lines chosen only from hope_facts (never 短期). Else empty.
- steps: the checklist in English, in order, concrete. Anvil prints the documents (履歴書 dated today with the
  志望動機 already sent, 職務経歴書, 送付状 with its 記 list): never tell him to write, fill or edit them; only to
  check, print and send them. For post in Japan: print single-sided on A4 (or A3
  folded for the 履歴書), sign nothing extra, a real ID photo glued on the 履歴書 is the norm (the printed one
  is acceptable; write his name on the back of a glued photo), documents in a clear file in the order
  送付状, 履歴書, 職務経歴書, a white 角形2号 envelope, 応募書類在中 in red boxed on the front, send by
  普通郵便 or 特定記録 (to have proof), post within 2-3 days. For email: which files to attach.
- next_action: the next step for his card, a few English words (e.g. "Post the 履歴書"). next_due: YYYY-MM-DD."""


def messages(app_id) -> list:
    """The employer's mails on this card that may need an answer, newest first."""
    from core import mail_watch
    return sorted([m for m in mail_watch.load()["found"]
                   if m["for"] == "app" and str(m["item_id"]) == str(app_id) and m["kind"] in ANSWERABLE],
                  key=lambda m: m["date"], reverse=True)


def _mail_text(m: dict) -> str:
    from core import mail_watch
    full = mail_watch._service().users().messages().get(userId="me", id=m["id"], format="full").execute()
    return mail_watch._body(full["payload"])[:8000]


def prepare_answer(app_id, msg_id: str = None) -> dict:
    """Write the answer kit for the employer's last (or a given) e-mail. Takes one to two minutes."""
    from analyzers.triage import profile_summary
    from core.llm import run_claude_code, LLMError
    from core.pipeline import Pipeline
    from generators import rirekisho

    pipe = Pipeline()
    app = pipe.get(app_id)
    if not app:
        raise KeyError(app_id)
    found = messages(app_id)
    m = next((x for x in found if x["id"] == msg_id), None) if msg_id else (found[0] if found else None)
    if not m:
        raise LLMError("No e-mail from them on this card yet.")
    body = _mail_text(m)

    pack = app.get("pack") or {}
    folder = Path(pack["folder"]) if pack.get("folder") else OUT_DIR / f"{app_id}-{_slug(app['company'])}"
    folder.mkdir(parents=True, exist_ok=True)
    sent = ""
    for name in ("letter.md", "cv.md", "職務経歴書.md"):
        if (folder / name).exists():
            sent += f"<{name}>\n{(folder / name).read_text(encoding='utf-8')}\n</{name}>\n"
    facts = rirekisho.facts()
    me = ""
    if facts:
        import yaml
        me = ("<rirekisho_facts>\n" + yaml.safe_dump(
            {k: facts.get(k) for k in ("name", "name_kana", "postcode", "address", "phone", "email", "career",
                                       "licenses", "hope_facts")}, allow_unicode=True, sort_keys=False)
              + "</rirekisho_facts>\n\n")

    data = run_claude_code(
        f"<their_email>\nFrom: {m['from']}\nSubject: {m['subject']}\nDate: {m['date']}\n\n{body}\n</their_email>\n\n"
        f"Role: {app['role']}\nCompany: {app['company']}\nCountry: {app.get('country', '')}\n"
        f"Language of the application: {app.get('language', '')}\nPosting: {app.get('url', '')}\n\n"
        f"<posting>\n{app.get('description', '')[:6000]}\n</posting>\n\n"
        f"<application_sent>\n{sent or 'not recorded'}\n</application_sent>\n\n{me}"
        f"<profile>\n{profile_summary()}\n</profile>\n\n<base_documents>\n{_base_documents()}\n</base_documents>\n\n"
        f"Today: {date.today()}",
        system=SYSTEM.format(forbidden=", ".join(f'"{p}"' for p in _forbidden())),
        schema=SCHEMA, tools=["WebSearch", "WebFetch"], effort="medium",
    )
    k = data.get("structured_output")
    if not k:
        raise LLMError(data.get("result") or "No answer kit.")

    from basin.method import OrangeLayer
    from core.profile_manager import ProfileManager
    pm = ProfileManager()
    violations = [v["found"] for v in OrangeLayer(pm.load(), pm.load_voice()).validate(
        k["cv"] + "\n" + k["reply"] + "\n" + k["cover_note"])]

    files = []
    ja = app.get("language") == "ja" or bool(re.search(r"[぀-ヿ]", body))
    if "rirekisho" in k["documents"] and facts:
        motive = (folder / "letter.md").read_text(encoding="utf-8") if (folder / "letter.md").exists() else ""
        files.append(rirekisho.render_rirekisho(folder / "履歴書.pdf", motive, k["hope"],
                                                {j["company"]: j["desc"] for j in k["rireki_jobs"]},
                                                k["rireki_licenses"] or None))
    if k["cv"].strip():
        if ja and facts:
            (folder / "職務経歴書.md").write_text(k["cv"], encoding="utf-8")
            files.append(rirekisho.render_shokumu(folder / "職務経歴書.pdf", k["cv"]))
        else:
            (folder / "cv.md").write_text(k["cv"], encoding="utf-8")
            _docx(k["cv"], folder / "cv.docx")
            files.append(folder / "cv.docx")
    if k["deliver"] == "post" and k["cover_note"].strip() and facts:
        names = {"rirekisho": "履歴書", "shokumu": "職務経歴書", "cv": "CV"}
        enclosed = list(dict.fromkeys(names[d] for d in k["documents"] if d in names))
        files.insert(0, rirekisho.render_cover(folder / "送付状.pdf", k["addressee"] or app["company"],
                                               k["cover_note"], enclosed + k["other_documents"]))
    if "letter" in k["documents"] and (folder / "letter.docx").exists():
        files.append(folder / "letter.docx")

    today = date.today().isoformat()
    md = _markdown(app, m, k, files, violations)
    path = folder / f"answer_{today}.md"
    path.write_text(md, encoding="utf-8")

    old = next((x for x in app.get("answers") or [] if x.get("msg") == m["id"]), {})
    answers = [x for x in (app.get("answers") or []) if x.get("msg") != m["id"]]
    answers.append({"draft": old.get("draft", ""), "attach": old.get("attach", False), "msg": m["id"], "thread": m["thread"], "to": m["from"], "on": today, "file": str(path),
                    "files": [str(f) for f in files], "deliver": k["deliver"], "deadline": k["deadline"],
                    "subject": k["reply_subject"], "reply": k["reply"] if k["reply_needed"] else "",
                    "violations": violations})
    docs = list(dict.fromkeys([str(f) for f in files] + [d for d in app.get("documents", []) if Path(d).exists()]))
    pipe.update(app_id, answers=answers, documents=docs)
    due = k["deadline"] or k["next_due"]
    try:
        date.fromisoformat(due)
    except ValueError:
        due = today
    pipe.set_next(app_id, k["next_action"], due)
    return pipe.get(app_id)


def _markdown(app, m, k, files, violations) -> str:
    how = {"email": "by e-mail", "post": "by post (郵送)", "upload": "on their site", "form": "through their form",
           "phone": "by phone", "in_person": "in person", "none": "nothing to send"}[k["deliver"]]
    out = [f"# Answer to {app['company']}", f"_Their e-mail of {m['date']}: {m['subject']}_", ""]
    if violations:
        out += [f"> Check before sending: {'; '.join(violations)}", ""]
    out += ["## What they ask"] + [f"- {a}" for a in k["asks"]]
    out += [f"- Send it {how}" + (f", by **{k['deadline']}**" if k["deadline"] else ""), ""]
    if files:
        out += ["## Ready in this folder"] + [f"- {Path(f).name}" for f in files] + [""]
    if k["other_documents"]:
        out += ["## You add yourself"] + [f"- {d}" for d in k["other_documents"]] + [""]
    out += ["## Steps"] + [f"{n}. {s}" for n, s in enumerate(k["steps"], 1)] + [""]
    if k["deliver"] == "post" and k["postal_address"]:
        out += ["## Envelope (角形2号, white)",
                "**Front**, written vertically, large and centred:", "",
                f"    {k['postal_address']}", f"    {k['addressee']}", "",
                "Bottom left, in red, in a box: **応募書類在中**", "",
                "**Back**, left side: your 〒, address and name, and the posting date at top left (e.g. 10月25日).", ""]
    if k["reply_needed"] and k["reply"].strip():
        out += [f"## Your reply e-mail", f"**Subject:** {k['reply_subject']}", "", k["reply"], ""]
        if k["reply_english"].strip():
            out += ["### In English", k["reply_english"], ""]
    return "\n".join(out) + "\n"


def save_draft(app_id, msg_id: str) -> str:
    """Put the reply in Gmail drafts, in their thread, with the files when it goes by e-mail. Never sends."""
    import base64
    import mimetypes
    from email.message import EmailMessage
    from core import mail_watch
    from core.pipeline import Pipeline

    a = Pipeline().get(app_id)
    ans = next(x for x in a.get("answers") or [] if x["msg"] == msg_id)
    svc = mail_watch._service()
    orig = svc.users().messages().get(userId="me", id=msg_id, format="metadata",
                                      metadataHeaders=["Message-ID", "Reply-To", "From"]).execute()
    msg = EmailMessage()
    msg["To"] = mail_watch._header(orig, "reply-to") or mail_watch._header(orig, "from")
    msg["Subject"] = ans["subject"]
    ref = mail_watch._header(orig, "message-id")
    if ref:
        msg["In-Reply-To"] = ref
        msg["References"] = ref
    msg.set_content(ans["reply"])
    if ans["deliver"] == "email" or ans.get("attach"):       # attach: post + a PDF copy by e-mail
        for f in ans["files"]:
            p = Path(f)
            kind = (mimetypes.guess_type(p.name)[0] or "application/octet-stream").split("/")
            msg.add_attachment(p.read_bytes(), maintype=kind[0], subtype=kind[1], filename=p.name)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    body = {"message": {"raw": raw, "threadId": ans["thread"]}}
    try:                              # the same draft is replaced, not doubled
        d = svc.users().drafts().update(userId="me", id=ans["draft"], body=body).execute()
    except Exception:
        d = svc.users().drafts().create(userId="me", body=body).execute()
    answers = a["answers"]
    for x in answers:
        if x["msg"] == msg_id:
            x["draft"] = d["id"]
    Pipeline().update(app_id, answers=answers)
    return d["id"]
