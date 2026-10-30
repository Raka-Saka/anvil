"""
Comedy Article Generator - Transform engineering logs into funny dev blog posts.
Self-deprecating humor, technical accuracy, dry wit.
Uses Basin Method with comedy voice settings.
"""

from pathlib import Path
from typing import Optional
from datetime import datetime
import re
import random
import logging

try:
    import anthropic
except ImportError:
    anthropic = None

from core.profile_manager import ProfileManager
from core.llm import get_client
from basin.method import BasinMethod

logger = logging.getLogger(__name__)


class ComedyArticleGenerator:
    """Generate comedy-style articles from ChronOS development logs."""

    def __init__(self,
                 profile_path: Optional[Path] = None,
                 voice_path: Optional[Path] = None,
                 api_key: Optional[str] = None):

        self.pm = ProfileManager(profile_path, voice_path)
        self.profile = self.pm.load()
        self.voice = self.pm.load_voice()
        self.basin = BasinMethod(self.profile, self.voice)

        self.client = get_client(api_key)  # Claude Code subscription, or API key

        # Load comedy-specific voice settings
        self.comedy_voice = self.voice.get('articles_comedy', {})

    def scan_sources(self, log_path: Path, roadmap_path: Optional[Path] = None) -> list[dict]:
        """
        Scan engineering log and roadmap for article-worthy content.

        Returns list of sections with comedy potential.
        """
        sections = []

        # Scan engineering log
        if log_path.exists():
            content = log_path.read_text(encoding='utf-8')
            sections.extend(self._parse_log(content))

        # Scan roadmap if provided
        if roadmap_path and roadmap_path.exists():
            roadmap = roadmap_path.read_text(encoding='utf-8')
            sections.extend(self._parse_roadmap(roadmap))

        # Keep chronological order (it's a diary - start from the beginning)
        # Don't sort - preserve order from the log file

        return sections

    def _parse_log(self, content: str) -> list[dict]:
        """Parse engineering log for sections."""
        sections = []

        # Session pattern
        session_pattern = r'## Session \d+:([^\n]+)\n(.*?)(?=## Session|\Z)'
        for match in re.finditer(session_pattern, content, re.DOTALL):
            title = match.group(1).strip()
            body = match.group(2).strip()
            sections.append(self._analyze_section(title, body, 'session'))

        # Milestone pattern
        milestone_pattern = r'### (M\d+[^\n]+)\n(.*?)(?=### M\d+|\Z)'
        for match in re.finditer(milestone_pattern, content, re.DOTALL):
            title = match.group(1).strip()
            body = match.group(2).strip()
            sections.append(self._analyze_section(title, body, 'milestone'))

        return [s for s in sections if s['word_count'] >= 150]

    def _parse_roadmap(self, content: str) -> list[dict]:
        """Parse roadmap for completed milestones."""
        sections = []

        # Look for completed milestones with notes
        milestone_pattern = r'\[x\]\s*(M\d+[^\n]+)\n(.*?)(?=\[.\]|\Z)'
        for match in re.finditer(milestone_pattern, content, re.DOTALL | re.IGNORECASE):
            title = match.group(1).strip()
            body = match.group(2).strip()
            if len(body) > 100:
                sections.append(self._analyze_section(title, body, 'roadmap'))

        return sections

    def _analyze_section(self, title: str, body: str, source_type: str) -> dict:
        """Analyze a section for comedy potential."""
        body_lower = body.lower()

        # Comedy gold indicators
        has_bug = any(w in body_lower for w in ['bug', 'fix', 'broken', 'crash', 'fail'])
        has_frustration = any(w in body_lower for w in ['hours', 'days', 'finally', 'turns out', 'stupid'])
        has_revelation = any(w in body_lower for w in ['realized', 'discovered', 'the problem was', 'root cause'])
        has_late_night = any(w in body_lower for w in ['3am', '2am', 'midnight', 'all night'])

        # Calculate comedy score
        comedy_score = sum([
            has_bug * 3,
            has_frustration * 2,
            has_revelation * 2,
            has_late_night * 1,
            ('page table' in body_lower) * 2,  # Page tables are inherently funny
            ('triple fault' in body_lower) * 3,  # Triple faults are hilarious
        ])

        return {
            'title': title,
            'content': body,
            'source_type': source_type,
            'word_count': len(body.split()),
            'has_bug': has_bug,
            'has_frustration': has_frustration,
            'has_revelation': has_revelation,
            'comedy_score': comedy_score,
        }

    def generate(self,
                 source: str,
                 project_name: str = "ChronOS",
                 section_title: str = None) -> dict:
        """
        Generate a comedy article from source content.

        Args:
            source: The raw content (log section, roadmap notes, etc.)
            project_name: Name of the project
            section_title: Optional title of the source section

        Returns:
            dict with title, content, violations, word_count
        """
        if not self.client:
            raise ValueError("Claude API key required for comedy article generation")

        return self._generate_with_claude(source, project_name, section_title)

    def _generate_hashtags(self, source: str, title: str) -> list[str]:
        """Generate relevant hashtags based on content."""
        source_lower = source.lower()
        title_lower = title.lower()
        combined = source_lower + ' ' + title_lower

        hashtags = ['#osdev', '#programming']  # Always include these

        # Technical topics
        if any(w in combined for w in ['page table', 'paging', 'pte', 'virtual memory']):
            hashtags.extend(['#virtualmemory', '#x86'])
        if any(w in combined for w in ['interrupt', 'irq', 'idt', 'exception']):
            hashtags.extend(['#interrupts', '#lowlevel'])
        if any(w in combined for w in ['user mode', 'ring 3', 'ring3', 'privilege']):
            hashtags.extend(['#userspace', '#kerneldev'])
        if any(w in combined for w in ['context switch', 'scheduler', 'preempt', 'multitask']):
            hashtags.extend(['#scheduler', '#multitasking'])
        if any(w in combined for w in ['boot', 'uefi', 'bios', 'bootloader']):
            hashtags.extend(['#bootloader', '#uefi'])
        if any(w in combined for w in ['memory', 'malloc', 'heap', 'allocator']):
            hashtags.extend(['#memorymanagement'])
        if any(w in combined for w in ['assembly', 'asm', 'x86', 'x64', 'register']):
            hashtags.extend(['#assembly', '#x86_64'])
        if any(w in combined for w in ['debug', 'bug', 'fix', 'crash']):
            hashtags.extend(['#debugging', '#bugfix'])
        if any(w in combined for w in ['gdt', 'segment', 'descriptor']):
            hashtags.extend(['#x86', '#segmentation'])

        # Meta/humor tags
        hashtags.extend(['#devlife', '#coding'])

        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for tag in hashtags:
            if tag not in seen:
                seen.add(tag)
                unique.append(tag)

        return unique[:10]  # Max 10 hashtags

    def _generate_with_claude(self, source: str, project_name: str, section_title: str) -> dict:
        """Generate comedy article using Claude."""

        openings = self.comedy_voice.get('openings', [
            "So there I was, wondering why I do this to myself."
        ])
        humor_rules = self.comedy_voice.get('humor_rules', [])

        # Get beat structure from voice config
        beats = self.comedy_voice.get('beats', {})
        beat_structure = beats.get('structure', [])
        beat_descriptions = '\n'.join([f"  - {b['beat']}: {b['description']}" for b in beat_structure])

        prompt = f"""Transform this engineering log into a NARRATIVE "Dear Diary" style dev blog post about building an OS kernel.

PROJECT: {project_name}
{f"SECTION: {section_title}" if section_title else ""}

SOURCE CONTENT:
{source}

THIS IS A STORY, NOT A LIST OF EVENTS.

Write this as an actual narrative - a story with scenes, internal monologue, descriptive moments, and emotional beats. The reader should feel like they're living through the debugging session with the narrator.

FORMAT: "Dear Diary" entries with NARRATIVE PROSE
- Paint scenes: describe the environment, the time of day, the state of mind
- Show internal thoughts: "Maybe if I just..." "What if the problem was..."
- Build tension: the mounting frustration, the false hopes, the despair
- Create moments: the revelation, the facepalm, the bittersweet victory
- Include dialogue with yourself: talking to the computer, cursing at the debugger

NARRATIVE STRUCTURE (use beats as guideposts, not checkboxes):

ACT 1 - THE SETUP (set the scene, establish stakes)
Paint the picture: Where are you? What time? What's the mood? What innocent goal started this nightmare?
Show the confidence before the fall. Let the reader know this is going to go wrong.

ACT 2 - THE DESCENT (the bulk of the story - this is where the comedy lives)
This should be the longest section. Build the frustration through:
- Specific debugging attempts (show the code, show the output, show your confusion)
- Time passing (morning becomes afternoon becomes night becomes 3am)
- The rabbit holes (you were SO sure the problem was X... narrator: it was not X)
- The false hopes (IT WORKS! wait... no, now something else is broken)
- The desperation (maybe I should just delete everything and become a farmer)
- The rock bottom moment (the comedic peak - the most absurd, relatable moment)

ACT 3 - THE REVELATION (the turn)
The moment of clarity. Maybe you stepped away. Maybe you said it out loud. Maybe you read the error message for the first time.
The fix - and why it's either embarrassingly simple or hilariously obscure.
The moment it works (or the suspicious silence that makes you wait for the other shoe to drop).

ACT 4 - THE AFTERMATH (reflection with earned wisdom)
What you actually learned (technical insight that's genuinely useful)
Self-aware commentary on the absurdity of hobby OS development
What's next (hint: more suffering, but you'll do it anyway)

COMEDY STYLE:
- MUST start with "Dear diary," - this is the signature format
- Self-deprecating humor (the joke is always on me, not others)
- Dry, British-style wit - understated, deadpan delivery
- The suffering is REAL, the delivery is deadpan
- Technical accuracy is non-negotiable - the humor comes from HOW you explain it
- Show, don't tell - don't say "I was frustrated", show the third cup of cold coffee
- NO memes, NO "LOL", NO "LMAO", NO cringe humor

OPENING EXAMPLES:
{chr(10).join(f'- {o}' for o in openings)}

VOICE:
- 48-year-old introvert building an OS as a hobby
- Uses AI (Claude) to help implement, designs and debugs himself
- Self-aware about the absurdity of the project
- Genuinely loves the technical challenge despite the suffering
- Dry humor, not loud or attention-seeking
- Writes like someone telling a story to a friend at a bar, not like a LinkedIn post

LENGTH: 1800-2200 words
This is a proper narrative. Take your time. Set scenes. Build tension. Let jokes breathe.

ABSOLUTELY FORBIDDEN:
- "Follow me", "Like", "Subscribe", "Comment below", "Share this"
- Generic tech bro humor
- Explaining jokes
- Being mean to others
- Fake enthusiasm
- Bullet point lists in the story itself
- Rushed pacing - this is a story, not a summary

The goal: Make developers laugh while actually teaching them something about OS development. They should feel like they lived through this debugging nightmare with you.

Write the article now. Just the article text, no meta commentary."""

        response = self.client.messages.create(
            model="claude-opus-5-5",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.content[0].text

        # Generate title first (needed for hashtags)
        title = self._generate_comedy_title(source, project_name, section_title)

        # Generate hashtags
        hashtags = self._generate_hashtags(source, title)
        hashtag_line = '\n\n---\n\n' + ' '.join(hashtags)

        # Append hashtags to content
        content_with_tags = content + hashtag_line

        # Apply Basin Method for violation checking
        result = self.basin.generate('article', content_with_tags)

        result['title'] = title
        result['hashtags'] = hashtags
        result['word_count'] = len(content.split())  # Don't count hashtags
        result['generated_at'] = datetime.now().isoformat()
        result['style'] = 'comedy'
        result['source_preview'] = source[:200] + '...' if len(source) > 200 else source

        # Generate Japanese version
        jp_result = self._translate_to_japanese(content, title, hashtags)
        result['content_ja'] = jp_result['content']
        result['title_ja'] = jp_result['title']
        result['hashtags_ja'] = jp_result['hashtags']

        return result

    def _translate_to_japanese(self, content: str, title: str, hashtags: list) -> dict:
        """Translate the article to Japanese while preserving humor and style."""

        hashtags_str = ' '.join(hashtags)

        prompt = f"""Translate this comedy dev blog article to Japanese.

ORIGINAL TITLE:
{title}

ORIGINAL HASHTAGS:
{hashtags_str}

ORIGINAL ARTICLE:
{content}

TRANSLATION REQUIREMENTS:
- Keep the "Dear diary" format as "親愛なる日記" or similar natural Japanese diary opening
- Preserve the self-deprecating humor and dry wit
- Keep technical terms in English where natural (e.g., page table, CPU, kernel)
- Maintain the narrative flow and comedic timing
- Use casual/informal Japanese appropriate for a personal blog
- Keep code snippets and technical output as-is

HASHTAG REQUIREMENTS:
- Translate hashtags to Japanese equivalents
- Use Japanese hashtags that are actually used on Japanese tech Twitter/blogs
- Examples: #osdev -> #OS開発, #debugging -> #デバッグ, #programming -> #プログラミング
- Keep some English hashtags if they're commonly used in Japanese tech community (e.g., #x86 stays #x86)
- Provide 8-10 hashtags

The translation should feel natural to Japanese readers while keeping the same comedic voice.

Output format:
TITLE_JA: [translated title]
HASHTAGS_JA: [Japanese hashtags separated by spaces]
---
[translated article content WITHOUT hashtags at the end]"""

        response = self.client.messages.create(
            model="claude-opus-5-5",
            max_tokens=5000,
            messages=[{"role": "user", "content": prompt}]
        )

        text = response.content[0].text

        # Parse title, hashtags, and content
        title_ja = title
        hashtags_ja = []
        content_ja = text

        lines = text.split('\n')
        content_start = 0

        for i, line in enumerate(lines):
            if line.startswith("TITLE_JA:"):
                title_ja = line.replace("TITLE_JA:", "").strip()
            elif line.startswith("HASHTAGS_JA:"):
                hashtags_str = line.replace("HASHTAGS_JA:", "").strip()
                hashtags_ja = [h.strip() for h in hashtags_str.split() if h.startswith('#')]
            elif line.strip() == "---":
                content_start = i + 1
                break

        if content_start > 0:
            content_ja = '\n'.join(lines[content_start:]).strip()

        return {
            'title': title_ja,
            'content': content_ja,
            'hashtags': hashtags_ja if hashtags_ja else hashtags  # fallback to English
        }

    def _generate_comedy_title(self, source: str, project_name: str, section_title: str) -> str:
        """Generate a funny but honest title."""

        source_lower = source.lower()

        # Match content to funny titles
        if 'page table' in source_lower or 'pte' in source_lower:
            options = [
                "Page Tables: A Love Story (It's Not)",
                "I Mass Page Tables Now. This Is My Life.",
                "The Page Table Incident",
                "Why Page Tables Want Me Dead",
            ]
        elif 'triple fault' in source_lower:
            options = [
                "Triple Fault: When Your OS Says 'I Quit'",
                "My OS Rage-Quit and All I Got Was This Blog Post",
                "Triple Faults: Nature's Way of Saying 'Go to Bed'",
            ]
        elif 'user mode' in source_lower or 'ring 3' in source_lower:
            options = [
                "Ring 3: Where Dreams Go to Die",
                "User Mode: Because Kernel Mode Wasn't Hard Enough",
                "Getting to Ring 3 (The Hard Way)",
            ]
        elif 'interrupt' in source_lower:
            options = [
                "Interrupts: Please Stop Interrupting Me",
                "The Care and Feeding of Interrupt Handlers",
                "IRQs and the Art of Not Crashing",
            ]
        elif 'boot' in source_lower:
            options = [
                "It Boots. I'm Suspicious.",
                "From Power-On to 'Oh No'",
                f"How to Make {project_name} Boot (Eventually)",
            ]
        elif 'debug' in source_lower or 'bug' in source_lower:
            options = [
                "A Bug That Cost Me My Weekend",
                "The Bug Was Inside Me All Along",
                "Debugging: A Horror Story",
                "Plot Twist: I Was the Bug",
            ]
        elif section_title:
            options = [
                f"{section_title}: A Tragedy in Three Acts",
                f"The {section_title} Incident",
                f"How {section_title} Almost Broke Me",
            ]
        else:
            options = [
                f"Another Day in {project_name} Development",
                "I Made Progress (I Think)",
                "OS Development: A Series of Unfortunate Events",
                f"What I Learned Building {project_name} (The Hard Way)",
            ]

        return random.choice(options)

    def generate_batch(self,
                       log_path: Path,
                       roadmap_path: Optional[Path] = None,
                       max_articles: int = 3) -> list[dict]:
        """
        Generate multiple comedy articles from logs.

        Returns list of generated articles, sorted by comedy potential.
        """
        sections = self.scan_sources(log_path, roadmap_path)

        articles = []
        for section in sections[:max_articles]:
            try:
                article = self.generate(
                    source=section['content'],
                    project_name="ChronOS",
                    section_title=section['title']
                )
                article['source_section'] = section['title']
                article['comedy_score'] = section['comedy_score']
                articles.append(article)
            except Exception as e:
                logger.warning(f"Failed to generate article for '{section['title']}': {e}")

        return articles


if __name__ == "__main__":
    from core.config import load_api_key

    api_key = load_api_key()

    generator = ComedyArticleGenerator(api_key=api_key)

    # Test with sample content
    sample_log = """
    ### M19: User Mode Basics

    **Goal:** Run code in ring 3 with separate address space

    **The Bug:** Reserved Bit Set in Page Table

    Spent 2 days on this. TWO DAYS.

    **Symptom:** Page fault with error "Reserved bit set in page table" at address 0x4FFFF8

    I tried everything. Checked the GDT. Checked the IDT. Rebuilt the page tables three times.
    At 3am I started questioning my life choices.

    **Root Cause Analysis:**

    When debug output was added to vmm.c, the page table entry values revealed:
    ```
    PML4E: 0x00000000B92CB023  <- flags 0x023 (NO USER bit)
    PDPTE: 0x00000000B92C7023  <- flags 0x023 (NO USER bit)
    PDE:   0x0000000000402023  <- flags 0x023 (NO USER bit)
    PTE:   0x0000000000400067  <- flags 0x067 (HAS USER bit)
    ```

    **Critical Discovery:**
    For user-mode (ring 3) access, the USER bit (bit 2) must be set at ALL page table levels,
    not just the final PTE. The CPU walks through PML4E → PDPTE → PDE → PTE, and if ANY
    level lacks the USER bit, access is denied.

    Two days. For one bit. In four places.

    **Key Lesson:** USER bit must be at ALL page table levels, not just final PTE.
    """

    result = generator.generate(sample_log, "ChronOS", "M19: User Mode Basics")

    print(f"TITLE: {result['title']}")
    print(f"WORDS: {result['word_count']}")
    print(f"VIOLATIONS: {len(result['violations'])}")
    print()
    print("ARTICLE:")
    print(result['content'])
