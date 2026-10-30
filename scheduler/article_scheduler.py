"""
Article Scheduler - Generate comedy articles 3x/week from ChronOS logs.

Uses the Basin Method with comedy voice settings.
Reads from engineering logs and roadmap.
Outputs to a drafts folder for review before publishing.

Schedule: Monday, Wednesday, Friday (configurable)
"""

from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
import json
import logging

try:
    import schedule
    HAS_SCHEDULE = True
except ImportError:
    HAS_SCHEDULE = False

from generators.comedy_article import ComedyArticleGenerator
from core.config import load_api_key

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ArticleScheduler:
    """Schedule and manage comedy article generation."""

    def __init__(self,
                 log_path: Path,
                 roadmap_path: Optional[Path] = None,
                 output_dir: Optional[Path] = None):
        """
        Initialize the scheduler.

        Args:
            log_path: Path to ChronOS engineering log
            roadmap_path: Optional path to roadmap file
            output_dir: Where to save generated articles (default: output/articles/scheduled)
        """
        self.log_path = Path(log_path)
        self.roadmap_path = Path(roadmap_path) if roadmap_path else None
        self.output_dir = output_dir or Path(__file__).parent.parent / "output" / "articles" / "scheduled"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Track what we've already generated
        self.history_file = self.output_dir / ".generation_history.json"
        self.history = self._load_history()

        # API key
        self.api_key = load_api_key()
        if not self.api_key:
            raise ValueError("Claude API key required. Add to config/api_keys.yaml")

        self.generator = ComedyArticleGenerator(api_key=self.api_key)

    def _load_history(self) -> dict:
        """Load generation history."""
        if self.history_file.exists():
            return json.loads(self.history_file.read_text())
        return {'generated_sections': [], 'last_generation': None}

    def _save_history(self):
        """Save generation history."""
        self.history_file.write_text(json.dumps(self.history, indent=2))

    def get_next_section(self) -> Optional[dict]:
        """
        Get the next section to generate an article from.
        Avoids sections we've already used.
        """
        sections = self.generator.scan_sources(self.log_path, self.roadmap_path)

        # Filter out already-used sections
        used_titles = set(self.history['generated_sections'])
        available = [s for s in sections if s['title'] not in used_titles]

        if not available:
            logger.warning("No new sections available. Consider clearing history or updating logs.")
            return None

        # Return highest comedy score section
        return available[0] if available else None

    def generate_article(self) -> Optional[dict]:
        """Generate a single comedy article."""
        section = self.get_next_section()
        if not section:
            return None

        logger.info(f"Generating article from: {section['title']}")

        try:
            article = self.generator.generate(
                source=section['content'],
                project_name="ChronOS",
                section_title=section['title']
            )

            # Save to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_title = article['title'].replace(' ', '_').replace(':', '').replace("'", '')[:40]
            filename = f"{timestamp}_{safe_title}.md"
            filepath = self.output_dir / filename

            # Build markdown content
            md_content = f"""---
title: "{article['title']}"
generated: {article['generated_at']}
source_section: "{section['title']}"
style: comedy
word_count: {article['word_count']}
status: draft
---

# {article['title']}

{article['content']}
"""
            filepath.write_text(md_content, encoding='utf-8')
            logger.info(f"Saved article to: {filepath}")

            # Update history
            self.history['generated_sections'].append(section['title'])
            self.history['last_generation'] = datetime.now().isoformat()
            self._save_history()

            article['filepath'] = str(filepath)
            return article

        except Exception as e:
            logger.error(f"Failed to generate article: {e}")
            return None

    def generate_batch(self, count: int = 3) -> list[dict]:
        """Generate multiple articles at once."""
        articles = []
        for i in range(count):
            article = self.generate_article()
            if article:
                articles.append(article)
            else:
                break
        return articles

    def run_scheduled(self, days: list[str] = None):
        """
        Run on a schedule.

        Args:
            days: Days to run (default: ['monday', 'wednesday', 'friday'])
        """
        if not HAS_SCHEDULE:
            raise ImportError("Install 'schedule' package: pip install schedule")

        days = days or ['monday', 'wednesday', 'friday']
        time_of_day = "09:00"  # Generate in the morning

        for day in days:
            getattr(schedule.every(), day).at(time_of_day).do(self.generate_article)

        logger.info(f"Scheduled article generation for {days} at {time_of_day}")
        logger.info("Press Ctrl+C to stop")

        import time
        while True:
            schedule.run_pending()
            time.sleep(60)

    def clear_history(self):
        """Clear generation history to allow re-using sections."""
        self.history = {'generated_sections': [], 'last_generation': None}
        self._save_history()
        logger.info("Generation history cleared")

    def status(self) -> dict:
        """Get scheduler status."""
        sections = self.generator.scan_sources(self.log_path, self.roadmap_path)
        used = len(self.history['generated_sections'])
        available = len([s for s in sections if s['title'] not in set(self.history['generated_sections'])])

        return {
            'total_sections': len(sections),
            'used_sections': used,
            'available_sections': available,
            'last_generation': self.history['last_generation'],
            'output_dir': str(self.output_dir),
        }


def main():
    """CLI for the article scheduler."""
    import sys

    # Default paths - ChronOS location
    default_log = Path("F:/chronos/ENGINEERING_LOG_V4.md")
    default_roadmap = Path("F:/chronos/ROADMAP_V4.md")

    print("=" * 50)
    print("  ChronOS Comedy Article Scheduler")
    print("=" * 50)
    print()

    # Check for log files
    log_path = default_log
    roadmap_path = default_roadmap

    if not log_path.exists():
        print(f"Log file not found: {log_path}")
        manual = input("Enter path to engineering log: ").strip()
        if manual:
            log_path = Path(manual)
        else:
            print("No log file provided. Exiting.")
            return

    print(f"Log file: {log_path}")
    if roadmap_path.exists():
        print(f"Roadmap: {roadmap_path}")
    else:
        print("Roadmap: Not found (will use log only)")
        roadmap_path = None

    print()

    try:
        scheduler = ArticleScheduler(log_path, roadmap_path)
    except ValueError as e:
        print(f"Error: {e}")
        return

    # Show status
    status = scheduler.status()
    print(f"Available sections: {status['available_sections']} / {status['total_sections']}")
    print(f"Last generation: {status['last_generation'] or 'Never'}")
    print()

    print("Commands:")
    print("  1. Generate one article now")
    print("  2. Generate 3 articles (one week's worth)")
    print("  3. Start scheduled generation (Mon/Wed/Fri)")
    print("  4. Clear history (allow re-using sections)")
    print("  5. Exit")
    print()

    while True:
        choice = input("Choice: ").strip()

        if choice == '1':
            print("\nGenerating article...")
            article = scheduler.generate_article()
            if article:
                print(f"\nTitle: {article['title']}")
                print(f"Words: {article['word_count']}")
                print(f"Saved: {article['filepath']}")
            else:
                print("No article generated (no new sections available)")

        elif choice == '2':
            print("\nGenerating 3 articles...")
            articles = scheduler.generate_batch(3)
            print(f"\nGenerated {len(articles)} articles:")
            for a in articles:
                print(f"  - {a['title']}")

        elif choice == '3':
            print("\nStarting scheduled generation...")
            print("Articles will be generated Mon/Wed/Fri at 9:00 AM")
            try:
                scheduler.run_scheduled()
            except KeyboardInterrupt:
                print("\nScheduler stopped.")

        elif choice == '4':
            scheduler.clear_history()
            status = scheduler.status()
            print(f"Available sections: {status['available_sections']}")

        elif choice == '5':
            print("Bye.")
            break

        else:
            print("Invalid choice")

        print()


if __name__ == "__main__":
    main()
