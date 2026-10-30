"""
Interview prep - a brief for one pipeline entry, written when it reaches screening or interview.

Claude researches the company (web search) and writes likely questions with answers taken only
from his record, the awkward questions (age, the years since 2017, Japanese level, salary) with
honest answers, questions to ask them, and the local interview customs (Japan or France).
Saved as interview.md in the application's folder and recorded on the pipeline entry.
"""

from datetime import date

from generators.application import OUT_DIR, _slug

QA = {"type": "object", "properties": {"q": {"type": "string"}, "answer": {"type": "string"}},
      "required": ["q", "answer"], "additionalProperties": False}

FACT = {"type": "object", "properties": {"label": {"type": "string"}, "value": {"type": "string"}},
        "required": ["label", "value"], "additionalProperties": False}

SCHEMA = {
    "type": "object",
    "properties": {
        "company_brief": {"type": "string"},
        "key_facts": {"type": "array", "items": FACT},
        "products": {"type": "array", "items": {"type": "string"}},
        "customers": {"type": "array", "items": {"type": "string"}},
        "competitors": {"type": "array", "items": {"type": "string"}},
        "leadership": {"type": "array", "items": {"type": "string"}},
        "culture": {"type": "array", "items": {"type": "string"}},
        "team_and_tools": {"type": "array", "items": {"type": "string"}},
        "their_words": {"type": "array", "items": {"type": "string"}},
        "links_to_you": {"type": "array", "items": {"type": "string"}},
        "recent_news": {"type": "array", "items": {"type": "string"}},
        "they_look_for": {"type": "array", "items": {"type": "string"}},
        "questions": {"type": "array", "items": QA},
        "awkward": {"type": "array", "items": QA},
        "ask_them": {"type": "array", "items": {"type": "string"}},
        "customs": {"type": "array", "items": {"type": "string"}},
        "salary": {"type": "string"},
        "sources": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["company_brief", "key_facts", "products", "customers", "competitors", "leadership", "culture",
                 "team_and_tools", "their_words", "links_to_you", "recent_news", "they_look_for", "questions", "awkward", "ask_them",
                 "customs", "salary", "sources"],
    "additionalProperties": False,
}

SYSTEM = """You prepare the candidate for a job interview. Use web search for the company.
Rules:
- Answers use only facts in his profile and in the application sent. Never invent a skill, number or story.
  Where he lacks something, the answer says so plainly and names the nearest real evidence.
- Voice: quiet, plain, first person, short sentences. Answers he can say in 30-60 seconds.
- Write the questions and answers in the language of the interview (the posting's language).
  Japanese interview: answers in short, simple polite Japanese (です/ます) he can say at his real level (JLPT N4),
  each followed by the English meaning in parentheses; questions likewise. Everything else
  (company brief, news, customs, salary) in English.
  French or other interviews: questions and answers in that language; the rest in English.
Output:
- company_brief: 3-4 sentences: what they do, size, where, how the team he would join works.
- key_facts: the numbers to know, each {label, value}: founded, HQ and offices, employees, revenue or ARR,
  funding / owner (investors, acquisitions, private equity), growth or cuts, ratings (Glassdoor, Trustpilot,
  G2). Say "not public" rather than guess; give the year of each figure.
- products: what they sell, in plain words, the main products or modules and what each is for (3-6 items).
- customers: who buys it (sectors, size) and named reference customers they publish.
- competitors: the main competitors and how this company says it is different.
- leadership: CEO and founders, and the heads of the department he would join (support, customer success),
  name and title only, from the company site or press. Nothing about private lives.
- culture: how employees describe working there (reviews: pros, cons, recurring complaints), values the company
  states, remote policy, languages used.
- team_and_tools: what is known about the team he would join: size, locations, shifts, the tools in the posting
  or their engineering/support pages (ticketing, CRM, knowledge base), and how support is sold (tiers, SLAs).
- their_words: 4-6 phrases or terms the company uses about itself (mission, product names) that he should
  recognise and can use naturally.
- links_to_you: 3-5 honest links between his real record and this company's situation, each one line.
- recent_news: up to 4 dated items worth knowing (results, launches, layoffs, acquisitions).
- they_look_for: the 3-5 things this interview will test, from the posting.
- questions: 8-10 likely questions for this role, each with his answer.
- awkward: the hard questions for him with honest answers: his age (49), why support work ended in 2017
  and what he did since (factory work in Japan, process improvement, building software with AI assistance),
  his Japanese level (N4), why he would leave Japan or move, and salary. Include only those that apply.
- ask_them: 4-5 good questions for him to ask, including ones that check the red flags known about this employer.
- customs: interview customs for that country and company type (e.g. Japan: 面接 manners, entering the room,
  self-introduction 自己紹介, 逆質問; France: tutoiement or not, the CDI trial period question). 4-6 items.
- salary: the range to ask for and why, from the market data you found, in local currency and EUR.
- sources: the URLs you used."""


def _markdown(app: dict, p: dict) -> str:
    out = [f"# Interview: {app['role']} — {app['company']}", f"_Prepared {date.today()}_", "",
           "## The company", p["company_brief"], ""]
    if p.get("key_facts"):
        out += ["| | |", "|---|---|"] + [f"| {f['label']} | {f['value']} |" for f in p["key_facts"]] + [""]
    for key, title in (("products", "What they sell"), ("customers", "Their customers"),
                       ("competitors", "Competitors"), ("leadership", "Leadership"),
                       ("culture", "Working there"), ("team_and_tools", "The team and its tools"),
                       ("their_words", "Their own words"), ("links_to_you", "Where your record meets theirs")):
        if p.get(key):
            out += [f"## {title}"] + [f"- {n}" for n in p[key]] + [""]
    if p["recent_news"]:
        out += ["## Recent news"] + [f"- {n}" for n in p["recent_news"]] + [""]
    out += ["## What they will test"] + [f"- {n}" for n in p["they_look_for"]] + [""]
    out += ["## Likely questions"]
    for qa in p["questions"]:
        out += [f"**{qa['q']}**", qa["answer"], ""]
    out += ["## Hard questions"]
    for qa in p["awkward"]:
        out += [f"**{qa['q']}**", qa["answer"], ""]
    out += ["## Ask them"] + [f"- {n}" for n in p["ask_them"]] + [""]
    out += ["## Customs"] + [f"- {n}" for n in p["customs"]] + [""]
    out += ["## Salary", p["salary"], "", "## Sources"] + [f"- {s}" for s in p["sources"]]
    return "\n".join(out) + "\n"


def prepare_interview(app_id: int) -> dict:
    """Write interview.md for a pipeline entry. Takes one to three minutes."""
    from pathlib import Path
    from analyzers.triage import profile_summary
    from core.llm import run_claude_code, LLMError
    from core.offers import OfferLibrary
    from core.pipeline import Pipeline

    pipe = Pipeline()
    app = pipe.get(app_id)
    if not app:
        raise KeyError(app_id)
    pack = app.get("pack") or {}
    folder = Path(pack["folder"]) if pack.get("folder") else OUT_DIR / f"{app_id}-{_slug(app['company'])}"
    sent = ""
    for name in ("cv.md", "letter.md"):
        if (folder / name).exists():
            sent += f"<{name}>\n{(folder / name).read_text(encoding='utf-8')}\n</{name}>\n"
    known = ""
    offer_id = (app.get("fit") or {}).get("offer_id")
    info = (OfferLibrary().get(offer_id) or {}).get("company_info") if offer_id else None
    if info:
        known = (f"Known about the employer: rating {info['rating']}; cons: {'; '.join(info['cons'])}; "
                 f"red flags: {'; '.join(info['red_flags']) or 'none'}.\n")

    data = run_claude_code(
        f"Role: {app['role']}\nCompany: {app['company']}\nCountry: {app.get('country', '')}\n"
        f"Posting: {app.get('url', '')}\nStage: {app['stage']}\n{known}\n"
        f"<posting>\n{app.get('description', '')}\n</posting>\n\n<profile>\n{profile_summary()}\n</profile>\n\n"
        f"<application_sent>\n{sent or 'not recorded'}\n</application_sent>\n\nToday: {date.today()}",
        system=SYSTEM, schema=SCHEMA, tools=["WebSearch", "WebFetch"], effort="medium",
    )
    prep = data.get("structured_output")
    if not prep:
        raise LLMError(data.get("result") or "No interview prep.")

    from core.outreach import check
    md = _markdown(app, prep)
    answers = "\n".join(qa["answer"] for qa in prep["questions"] + prep["awkward"])
    issues = check(answers)
    if issues:
        md = md.replace("\n\n## The company", "\n\n> Check these answers: " + "; ".join(issues) + "\n\n## The company", 1)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "interview.md"
    path.write_text(md, encoding="utf-8")
    pipe.update(app_id, interview_prep={"file": str(path), "on": date.today().isoformat()})
    return pipe.get(app_id)
