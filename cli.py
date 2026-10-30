"""
Anvil CLI - Command-line interface for generating professional content.
"""

import sys
from pathlib import Path
from datetime import datetime

# Ensure imports work
sys.path.insert(0, str(Path(__file__).parent))

from core.profile_manager import ProfileManager
from core.config import load_api_key, has_api_key
from generators.cv import CVGenerator
from generators.cover_letter import CoverLetterGenerator
from generators.article import ArticleGenerator


def main():
    """Main CLI entry point."""

    print("=" * 50)
    print("  ANVIL - Honest Professional Visibility")
    print("=" * 50)
    print()
    print("Commands:")
    print("  cv       - Generate CV")
    print("  cover    - Generate cover letter")
    print("  article  - Generate article from logs")
    print("  comedy   - Generate comedy article (ChronOS)")
    print("  schedule - Article scheduler (3x/week)")
    print("  triage   - Realistic / stretch / skip for a pasted posting")
    print("  log      - Log an application (any channel)")
    print("  today    - What's due in the pipeline")
    print("  stats    - Reply rate by channel and country")
    print("  review   - Weekly review (saved to output/reviews)")
    print("  check    - Validate profile")
    print("  ui       - Launch desktop UI")
    print("  help     - Show this help")
    print()
    
    while True:
        try:
            cmd = input("anvil> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break
        
        if not cmd:
            continue
        elif cmd in ('quit', 'exit', 'q'):
            print("Bye.")
            break
        elif cmd == 'help':
            show_help()
        elif cmd == 'cv':
            generate_cv()
        elif cmd == 'cover':
            generate_cover_letter()
        elif cmd == 'article':
            generate_article()
        elif cmd == 'check':
            check_profile()
        elif cmd == 'triage':
            run_triage()
        elif cmd == 'log':
            log_application()
        elif cmd == 'today':
            show_today()
        elif cmd == 'stats':
            show_stats()
        elif cmd == 'review':
            from analyzers.review import weekly_review
            md, path = weekly_review()
            print(md)
            print(f"Saved to {path}")
        elif cmd == 'ui':
            launch_ui()
        elif cmd == 'comedy':
            generate_comedy_article()
        elif cmd == 'schedule':
            run_scheduler()
        else:
            print(f"Unknown command: {cmd}")
            print("Type 'help' for available commands.")


def show_help():
    """Show help text."""
    print("""
Anvil Commands:

  cv [role]
      Generate a CV. Optional role type:
      - general (default)
      - technical_pm
      - qa_lead
      - ai_dev
      
  cover
      Generate a cover letter. You'll be prompted to paste
      the job description.
      
  article [log_file]
      Generate an article from an engineering log.
      If no file specified, scans data/projects/ for logs.
      
  check
      Validate your profile for completeness and issues.
      
  quit / exit / q
      Exit Anvil.
""")


def generate_cv():
    """Generate CV interactively."""
    
    print("\n--- CV Generator ---")
    
    # Get role type
    print("\nTarget role type:")
    print("  1. General")
    print("  2. Technical PM")
    print("  3. QA Lead")
    print("  4. AI-Assisted Developer")
    
    choice = input("Choice [1]: ").strip() or "1"
    roles = {
        "1": "general",
        "2": "technical_pm",
        "3": "qa_lead",
        "4": "ai_dev",
    }
    role = roles.get(choice, "general")
    
    # Get emphasis
    print("\nEmphasis:")
    print("  1. Balanced")
    print("  2. Problem Solving")
    print("  3. Project Management")
    print("  4. Technical")
    
    choice = input("Choice [1]: ").strip() or "1"
    emphases = {
        "1": "balanced",
        "2": "problem_solving",
        "3": "project_management",
        "4": "technical",
    }
    emphasis = emphases.get(choice, "balanced")
    
    print("\nGenerating CV...")
    api_key = load_api_key()
    from core.llm import describe
    print(f"(Claude: {describe()})")

    try:
        generator = CVGenerator(api_key=api_key)
        result = generator.generate(target_role=role, emphasis=emphasis)
        
        # Show warnings
        if result['violations']:
            print("\n⚠️  WARNINGS:")
            for v in result['violations']:
                print(f"   [{v['severity'].upper()}] {v['type']}")
                print(f"   Found: {v['found']}")
                print(f"   Suggestion: {v['suggestion']}")
                print()
        
        # Show preview
        print("\n" + "=" * 50)
        print("CV PREVIEW")
        print("=" * 50)
        print(result['content'])
        print("=" * 50)
        
        # Save option
        save = input("\nSave to file? [y/N]: ").strip().lower()
        if save == 'y':
            output_dir = Path(__file__).parent / "output" / "cv"
            output_dir.mkdir(parents=True, exist_ok=True)

            filename = f"cv_{role}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            filepath = output_dir / filename
            
            filepath.write_text(result['content'], encoding='utf-8')
            print(f"Saved to: {filepath}")
        
    except Exception as e:
        print(f"Error: {e}")


def generate_cover_letter():
    """Generate cover letter interactively."""
    
    print("\n--- Cover Letter Generator ---")
    print("\nPaste the job description (press Enter twice when done):")
    
    lines = []
    empty_count = 0
    
    while True:
        try:
            line = input()
            if line == "":
                empty_count += 1
                if empty_count >= 2:
                    break
            else:
                empty_count = 0
            lines.append(line)
        except EOFError:
            break
    
    job_description = '\n'.join(lines).strip()
    
    if not job_description:
        print("No job description provided.")
        return
    
    company = input("Company name (optional): ").strip() or None
    role = input("Role name (optional): ").strip() or None
    
    print("\nAnalyzing job and generating letter...")
    api_key = load_api_key()
    from core.llm import describe
    print(f"(Claude: {describe()})")

    try:
        generator = CoverLetterGenerator(api_key=api_key)
        result = generator.generate(
            job_description=job_description,
            company_name=company,
            role_name=role
        )
        
        # Show analysis
        print(f"\n📊 Match Score: {result['analysis']['match_score']:.0f}%")
        print(f"   Matches: {len(result['analysis']['matches'])}")
        if result['analysis']['gaps']:
            print(f"   Gaps: {', '.join(result['analysis']['gaps'][:3])}")
        
        # Show warnings
        if result['violations']:
            print("\n⚠️  WARNINGS:")
            for v in result['violations']:
                print(f"   [{v['severity'].upper()}] {v['found']}")
        
        # Show letter
        print("\n" + "=" * 50)
        print("COVER LETTER")
        print("=" * 50)
        print(result['content'])
        print("=" * 50)
        
        # Save option
        save = input("\nSave to file? [y/N]: ").strip().lower()
        if save == 'y':
            output_dir = Path(__file__).parent / "output" / "cover_letters"
            output_dir.mkdir(parents=True, exist_ok=True)

            safe_company = (company or "unknown").replace(" ", "_")[:20]
            filename = f"cover_{safe_company}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            filepath = output_dir / filename
            
            filepath.write_text(result['content'], encoding='utf-8')
            print(f"Saved to: {filepath}")
        
    except Exception as e:
        print(f"Error: {e}")


def generate_article():
    """Generate article from engineering log."""
    
    print("\n--- Article Generator ---")
    
    # Find available logs
    data_dir = Path(__file__).parent / "data" / "projects"
    
    logs = list(data_dir.glob("**/logs/*.md"))
    logs += list(data_dir.glob("**/*LOG*.md"))
    logs += list(data_dir.glob("**/*log*.md"))
    
    if not logs:
        print("No log files found in data/projects/")
        manual = input("Enter log file path manually: ").strip()
        if manual:
            logs = [Path(manual)]
        else:
            return
    
    print("\nAvailable logs:")
    for i, log in enumerate(logs, 1):
        print(f"  {i}. {log.relative_to(data_dir) if log.is_relative_to(data_dir) else log}")
    
    choice = input(f"Select [1-{len(logs)}]: ").strip()
    try:
        log_path = logs[int(choice) - 1]
    except (ValueError, IndexError):
        log_path = logs[0]
    
    project_name = input("Project name: ").strip() or log_path.parent.parent.name
    
    print(f"\nScanning {log_path.name}...")
    api_key = load_api_key()

    try:
        generator = ArticleGenerator(api_key=api_key)
        sections = generator.scan_log(log_path)
        
        if not sections:
            print("No publishable sections found.")
            return
        
        print(f"\nFound {len(sections)} potential sections:")
        for i, s in enumerate(sections, 1):
            flags = []
            if s['has_problem']:
                flags.append("problem")
            if s['has_lesson']:
                flags.append("lesson")
            if s['has_code']:
                flags.append("code")
            print(f"  {i}. {s['title'][:50]} ({s['word_count']} words) [{', '.join(flags)}]")
        
        choice = input(f"\nSelect section [1-{len(sections)}]: ").strip()
        try:
            section = sections[int(choice) - 1]
        except (ValueError, IndexError):
            section = sections[0]
        
        print(f"\nGenerating article from: {section['title'][:50]}...")
        
        result = generator.generate(
            source=section['content'],
            project_name=project_name
        )
        
        # Show article
        print("\n" + "=" * 50)
        print(f"TITLE: {result['title']}")
        print(f"WORDS: {result['word_count']}")
        print("=" * 50)
        print(result['content'])
        print("=" * 50)
        
        # Show warnings
        if result['violations']:
            print("\n⚠️  WARNINGS:")
            for v in result['violations']:
                print(f"   [{v['severity'].upper()}] {v['found']}")
        
        # Save option
        save = input("\nSave to file? [y/N]: ").strip().lower()
        if save == 'y':
            output_dir = Path(__file__).parent / "output" / "articles"
            output_dir.mkdir(parents=True, exist_ok=True)

            safe_title = result['title'].replace(" ", "_").replace(":", "")[:30]
            filename = f"article_{safe_title}_{datetime.now().strftime('%Y%m%d')}.md"
            filepath = output_dir / filename
            
            content = f"# {result['title']}\n\n{result['content']}"
            filepath.write_text(content, encoding='utf-8')
            print(f"Saved to: {filepath}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


def launch_ui():
    """Launch the desktop UI."""
    print("\nLaunching Anvil UI...")
    try:
        from ui import run
        run()
    except ImportError as e:
        print(f"Error: Could not import UI. Make sure flet is installed: pip install flet")
        print(f"Details: {e}")


def generate_comedy_article():
    """Generate a comedy article about ChronOS development."""
    print("\n--- Comedy Article Generator ---")
    print("Generates self-deprecating dev blog posts from ChronOS logs")
    print()

    api_key = load_api_key()
    from core.llm import backend
    if not backend():
        print("Error: Claude needed for comedy articles (install Claude Code, or add an API key)")
        return

    # ChronOS paths
    log_path = Path("F:/chronos/ENGINEERING_LOG_V4.md")
    roadmap_path = Path("F:/chronos/ROADMAP_V4.md")

    if not log_path.exists():
        print(f"ChronOS log not found: {log_path}")
        manual = input("Enter path to engineering log: ").strip()
        if manual:
            log_path = Path(manual)
        else:
            return

    try:
        from generators.comedy_article import ComedyArticleGenerator
        import json

        generator = ComedyArticleGenerator(api_key=api_key)

        # History tracking
        output_dir = Path(__file__).parent / "output" / "articles" / "comedy"
        output_dir.mkdir(parents=True, exist_ok=True)
        history_file = output_dir / ".history.json"

        if history_file.exists():
            history = json.loads(history_file.read_text())
        else:
            history = {'used_sections': []}

        # Scan for sections
        print(f"Scanning {log_path.name}...")
        sections = generator.scan_sources(log_path, roadmap_path if roadmap_path.exists() else None)

        if not sections:
            print("No sections found in log.")
            return

        # Filter out used sections
        available = [s for s in sections if s['title'] not in history['used_sections']]

        print(f"\nFound {len(sections)} sections ({len(available)} unused)")
        print()

        if not available:
            print("All sections have been used.")
            reset = input("Reset history and start over? [y/N]: ").strip().lower()
            if reset == 'y':
                history = {'used_sections': []}
                available = sections
            else:
                return

        # Show next section (chronological - it's a diary)
        next_section = available[0]
        print(f"Next entry: {next_section['title']}")
        print(f"            ({next_section['word_count']} words of source material)")
        print()

        # Option to skip or pick different
        print("Options:")
        print("  Enter  - Generate from this section")
        print("  s      - Skip to next section")
        print("  l      - List all available sections")
        print("  q      - Quit")

        choice = input("\nChoice: ").strip().lower()

        if choice == 'q':
            return
        elif choice == 's':
            # Skip this section (mark as used but don't generate)
            history['used_sections'].append(next_section['title'])
            history_file.write_text(json.dumps(history, indent=2))
            print(f"Skipped: {next_section['title']}")
            print(f"{len(available) - 1} sections remaining.")
            return
        elif choice == 'l':
            print("\nAll available sections (chronological):")
            for i, s in enumerate(available[:15], 1):
                print(f"  {i}. {s['title'][:60]} ({s['word_count']}w)")
            if len(available) > 15:
                print(f"  ... and {len(available) - 15} more")
            print()
            pick = input(f"Pick section [1-{min(len(available), 15)}] or Enter for first: ").strip()
            try:
                section = available[int(pick) - 1]
            except (ValueError, IndexError):
                section = next_section
        else:
            section = next_section

        print(f"\nGenerating from: {section['title']}")
        print("This may take a moment...")

        result = generator.generate(
            source=section['content'],
            project_name="ChronOS",
            section_title=section['title']
        )

        # Mark as used
        history['used_sections'].append(section['title'])
        history_file.write_text(json.dumps(history, indent=2))

        print("\n" + "=" * 60)
        print(f"TITLE: {result['title']}")
        print(f"WORDS: {result['word_count']}")
        print(f"HASHTAGS: {' '.join(result.get('hashtags', []))}")
        print("=" * 60)
        print(result['content'])
        print("=" * 60)

        if result.get('violations'):
            print("\nWarnings:")
            for v in result['violations']:
                print(f"  [{v['severity']}] {v['found']}")

        # Auto-save (English and Japanese)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_title = result['title'].replace(' ', '_').replace(':', '').replace("'", '').replace('"', '')[:40]

        # English version
        filename_en = f"comedy_{timestamp}_{safe_title}_EN.md"
        filepath_en = output_dir / filename_en

        md_content_en = f"""---
title: "{result['title']}"
generated: {result.get('generated_at', datetime.now().isoformat())}
source_section: "{section['title']}"
style: comedy
word_count: {result['word_count']}
hashtags: {' '.join(result.get('hashtags', []))}
language: en
---

# {result['title']}

{result['content']}
"""
        filepath_en.write_text(md_content_en, encoding='utf-8')

        # Japanese version
        filename_ja = f"comedy_{timestamp}_{safe_title}_JA.md"
        filepath_ja = output_dir / filename_ja

        hashtags_ja = result.get('hashtags_ja', [])
        hashtags_ja_str = ' '.join(hashtags_ja)

        md_content_ja = f"""---
title: "{result.get('title_ja', result['title'])}"
generated: {result.get('generated_at', datetime.now().isoformat())}
source_section: "{section['title']}"
style: comedy
language: ja
hashtags: {hashtags_ja_str}
---

# {result.get('title_ja', result['title'])}

{result.get('content_ja', '')}

---

{hashtags_ja_str}
"""
        filepath_ja.write_text(md_content_ja, encoding='utf-8')

        print(f"\nSaved to:")
        print(f"  EN: {filepath_en}")
        print(f"  JA: {filepath_ja}")

        # Show remaining
        remaining = len(available) - 1
        print(f"\n{remaining} sections remaining for future articles.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


def run_scheduler():
    """Run the article scheduler."""
    print("\n--- Article Scheduler ---")
    print("Schedules comedy articles 3x/week from ChronOS logs")
    print()

    try:
        from scheduler.article_scheduler import main as scheduler_main
        scheduler_main()
    except ImportError as e:
        print(f"Error importing scheduler: {e}")
        print("Make sure the scheduler module is set up correctly.")


def run_triage():
    """Triage a pasted posting. End the paste with a line containing only END."""
    from analyzers.triage import triage

    print("Paste the posting, then a line with END:")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "END":
            break
        lines.append(line)
    text = "\n".join(lines).strip()
    if not text:
        return
    r = triage(text)
    print(f"\n{r.verdict.upper()}  -  {r.track_label}  ({r.by})")
    for f in r.flags:
        print(f"  [{f.level}] {f.text}")
    for reason in r.reasons:
        print(f"  - {reason}")
    if r.motivation_angle:
        print(f"  Angle: {r.motivation_angle}")
    for d in r.documents:
        print(f"  Send: {d['file']}")
    if r.note:
        print(f"  ({r.note})")


def log_application():
    """Log an application sent on any channel."""
    from core.pipeline import Pipeline, load_channels, today

    company = input("Company: ").strip()
    role = input("Role: ").strip()
    if not (company and role):
        print("Company and role are needed.")
        return
    country = (input("Country [JP/FR/ANY] (JP): ").strip().upper() or "JP")
    channels = [c for c in load_channels() if c["country"] in (country, "ANY")]
    for i, c in enumerate(channels, 1):
        print(f"  {i:2}. {c['name']}")
    pick = input("Channel number: ").strip()
    channel = channels[int(pick) - 1]["id"] if pick.isdigit() and 0 < int(pick) <= len(channels) else "other"
    on = input(f"Date applied ({today()}): ").strip() or today()
    url = input("Link (optional): ").strip()

    app = Pipeline().add(company=company, role=role, channel=channel, country=country, on=on, url=url)
    print(f"Logged #{app['id']}. Follow-up due {app['next_due']}.")


def show_today():
    """Show what's due and what has gone quiet."""
    from core.pipeline import Pipeline, channel_name

    p = Pipeline()
    ghosts = p.mark_ghosted()
    due = p.due()
    print(f"\n--- Due ({len(due)}) ---")
    for a in due:
        print(f"  #{a['id']} {a['next_due']}  {a['next_action']}: {a['role']} @ {a['company']} ({channel_name(a['channel'])})")
    if not due:
        print("  Nothing due.")
    if ghosts:
        print(f"\nMarked ghosted (no reply in 30 days): {', '.join(a['company'] for a in ghosts)}")


def show_stats():
    """Funnel overall, by country, by channel."""
    from core.pipeline import Pipeline, channel_name

    p = Pipeline()

    def row(label, f):
        print(f"  {label:<32} {f.applied:>3} sent  {f.responded:>3} replies  "
              f"{f.interviews:>2} interviews  {f.response_rate:>4.0%}")

    print("\n--- Overall ---")
    row("All", p.funnel())
    print("\n--- By country ---")
    for k, f in p.funnel_by("country").items():
        row(k, f)
    print("\n--- By channel ---")
    for k, f in sorted(p.funnel_by("channel").items(), key=lambda kv: -kv[1].applied):
        row(channel_name(k), f)


def check_profile():
    """Validate profile."""

    print("\n--- Profile Check ---\n")
    
    try:
        pm = ProfileManager()
        issues = pm.validate()
        
        if issues:
            print("⚠️  Issues found:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("✅ Profile looks good!")
        
        # Show summary
        print(f"\nProfile Summary:")
        print(f"   Name: {pm.get_name()}")
        print(f"   Email: {pm.get_email()}")
        print(f"   Direct skills: {len(pm.get_skills_direct())}")
        print(f"   AI-assisted skills: {len(pm.get_skills_ai_assisted())}")
        print(f"   Projects: {len(pm.get_projects())}")
        print(f"   Experience entries: {len(pm.get_experience())}")

        # API key status
        from core.llm import describe
        print(f"\n   Claude: {describe()}")
        
    except Exception as e:
        print(f"Error loading profile: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == "cv":
            generate_cv()
        elif cmd == "cover":
            generate_cover_letter()
        elif cmd == "article":
            generate_article()
        elif cmd == "comedy":
            generate_comedy_article()
        elif cmd == "schedule":
            run_scheduler()
        elif cmd == "check":
            check_profile()
        elif cmd == "ui":
            launch_ui()
        else:
            main()
    else:
        main()
