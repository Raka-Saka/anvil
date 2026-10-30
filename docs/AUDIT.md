# Anvil audit — 2026-10-19

Last code change: 2026-01-11. Dormant ~9 months. Not a git repo.

## What works (tested today)

| Piece | State |
|---|---|
| `cli.py check` | Passes. Claude key configured. |
| CV generator (`generators/cv.py`) | Generates. Exports MD/TXT/HTML/DOCX/PDF. |
| Cover letter generator | Works (Claude + template fallback). Used Jan 2026 for DISHER, Tardus. |
| Job analyzer (URL/text → match score, gaps) | Code present; keyword-based scoring. |
| Job searcher | Runs. Jobicy, Remotive, Arbeitnow respond. |
| Flet desktop UI (8 tabs) | Present, Flet 0.80.1. |
| Application tracker (`ui/storage.py` → `data/jobs.yaml`) | Code present. **File never created — zero applications ever tracked.** |

## Why it isn't finding you jobs

1. **Wrong markets.** All live sources are US/global remote boards. Today's "project manager"
   search returned Canada/USA-only roles and German Google-Ads jobs. Nothing for Japan or France.
   Missing: Daijob, CareerCross, GaijinPot, Indeed JP, LinkedIn JP; France Travail, APEC,
   Welcome to the Jungle, Indeed FR, HelloWork.
2. **No pipeline.** Tracker has one status field. No follow-up dates, no contacts, no reminders,
   no record of where the 3 months of applications went. Can't learn what isn't working.
3. **One language.** CV and letters are English only. France needs a French CV and lettre de
   motivation; Japan often needs 履歴書 / 職務経歴書 (or at least a JP-market English CV).
4. **Drift.** About 40% of the code is the comedy diary, YouTube, TTS, Bluesky/dev.to publishing.
   `ROADMAP.md` is entirely about content, not jobs.
5. **Matching is keyword-only.** The analyzer counts words; no Claude read of fit, no
   "is this realistic for a 48-year-old career-changer in Osaka" filter.
6. **No outreach.** Nothing for recruiters (Japan runs on agencies: Robert Walters, Hays,
   Michael Page, en world, JAC) or direct company contact.

## Honesty bugs (against Anvil's own rules)

- `generators/cover_letter.py:482,616,758` say "conversational Japanese". Profile says N4.
- `generators/cv.py:187` hard-codes a quirky line ("Problems don't care what language you speak").
- Profile: Ribbon (current job, 2022–present) is hidden from the CV, leaving a 2022 gap
  that recruiters will ask about.

## Hygiene

- Secrets in `config/` (`api_keys.yaml`, `client_secrets.json`, `youtube_token.json`). Only
  `api_keys.yaml` is in `.gitignore`.
- Stray files: `nul`, `test2.pdf`, `test3.pdf`, `test_simple.pdf`, `master_profile_starter.yaml`.
- `README.md` is outdated (says UI "to build", lists PyQt6). `requirements.txt` misses
  flet, requests, beautifulsoup4, reportlab/fpdf.
- No tests. No git.

## Proposed expansion (job-search first)

| # | Feature | Why |
|---|---|---|
| 1 | Pipeline: applications with stage, dates, contact, next action, source; import past 3 months | Know what's happening; see the funnel |
| 2 | Japan + France sources (APIs where they exist, saved-search/RSS/manual paste otherwise) | Search where the jobs are |
| 3 | Claude fit triage: realistic / stretch / skip, with reasons | Spend effort on jobs you can get |
| 4 | French CV + lettre de motivation; JP-market CV and 職務経歴書 | Match each country's format |
| 5 | Recruiter/agency outreach drafts + follow-up reminders | Japan hiring runs on agencies |
| 6 | Weekly review: funnel stats, what got replies, what to change | Learn from results |
| 7 | Park the content/YouTube side under its own tab or project | Keep the job tool focused |

## Update — same day, after the CVs in docs/ arrived

- Real tracks in 2026: FR/EN support, developer, CS in Japan, French teaching, hotel, factory.
  Mapped in `data/documents.yaml`; profile.yaml updated from the CVs (Ribbon Foods to 2026-07,
  OsakaWire, nagare-dsp, Google Data Analytics).
- Generators invented numbers (`_quantify_text`, hooks: "10x output", "8-member team",
  "500K+ players", "100+ test cases"). None appear in your CVs. Removed from code; kept in
  profile.yaml under `unconfirmed:` until you confirm or drop them.
- Anthropic API key has no credit. All Claude calls now go through Claude Code (`core/llm.py`,
  your Max subscription); the API is only a fallback (`llm: api` in config/api_keys.yaml).

## Pipeline audit (2026-10-20)

End-to-end run on a copy of the real data: two offers selected at once (English and Japanese), packs,
applied, follow-up draft, reply, interview brief, ghosting, outreach reply, turn-down reason, weekly
review, gaps, CV and Cover Letter tabs, DOCX/PDF exports. 37/37 checks pass after the fixes below.
Every number in the generated CVs and letters was found in his documents.

Fixed:
- Lost writes: long Claude jobs saved files loaded minutes earlier (a selected offer vanished). All
  stores now reload and save under one lock (core/store.py).
- A reply left "Follow up if no reply" as the next action.
- Notices in the CV, Cover Letter, Article and Diary tabs never showed (page.snack_bar is gone in Flet 0.80).
- CV and Cover Letter generation froze the window; now off the UI thread.
- Ghosting ignored follow-ups sent; deleted pipeline ids were reused; same job title in two cities merged;
  closing dates read as posting dates; offline exchange rates retried on every card; long mailto links
  failed (body now goes to the clipboard); remote jobs with no city; empty place list.
- Wording that went beyond the profile ("shipped" OS kernel, "results-driven", "track record").
- Japan sources in his order: Indeed, Recruit, GaijinPot, YOLO WORK, Hello Work.

## Languages (2026-10-20)

Tested with postings in Japanese, French, Spanish, Portuguese, German and English. Claude's triage read
all of them correctly (reasons always in English). Fixed in the no-Claude rules: "support N2" read as
Japanese N2; part-time télétravail counted as remote; age limits and work-rights phrases in French,
Spanish, Portuguese, German; French spotted in other languages (francés, francês, Französisch); a
required language he lacks (e.g. German C1). Same job in two languages is now caught by a Claude check
after each search (Medtronic EN/FR, ZenGroup JA/EN, Central Crew JA/EN). Japanese letters, emails and
interview answers come with an English translation. Contract terms come in local vocabulary (派遣, intérim).
