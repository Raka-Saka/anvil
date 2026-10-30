"""
Article Generator - Transform engineering logs into quiet, technical articles.
No self-promotion. No call to action. Just sharing what you learned.
"""

from pathlib import Path
from typing import Optional
from datetime import datetime
import re
import random

try:
    import anthropic
except ImportError:
    anthropic = None

from core.profile_manager import ProfileManager
from core.llm import get_client
from basin.method import BasinMethod


class ArticleGenerator:
    """Generate articles from project logs and notes."""
    
    def __init__(self,
                 profile_path: Optional[Path] = None,
                 voice_path: Optional[Path] = None,
                 api_key: Optional[str] = None):
        
        self.pm = ProfileManager(profile_path, voice_path)
        self.profile = self.pm.load()
        self.voice = self.pm.load_voice()
        self.basin = BasinMethod(self.profile, self.voice)
        
        self.client = get_client(api_key)  # Claude Code subscription, or API key
    
    def scan_log(self, log_path: Path) -> list[dict]:
        """
        Scan engineering log for publishable sections.
        
        Returns list of sections with enough content to be articles.
        """
        
        content = log_path.read_text(encoding='utf-8')
        sections = []
        
        # Find session or milestone sections
        # Pattern: ## Session N or ### MN: Title
        patterns = [
            (r'## Session \d+:([^\n]+)\n(.*?)(?=## Session|\Z)', 'session'),
            (r'### (M\d+[^\n]+)\n(.*?)(?=### M\d+|\Z)', 'milestone'),
        ]
        
        for pattern, section_type in patterns:
            for match in re.finditer(pattern, content, re.DOTALL):
                title = match.group(1).strip()
                body = match.group(2).strip()
                
                # Check if section has enough content
                word_count = len(body.split())
                
                if word_count >= 200:  # Minimum for article
                    sections.append({
                        'title': title,
                        'content': body,
                        'type': section_type,
                        'word_count': word_count,
                        'has_code': '```' in body,
                        'has_problem': any(w in body.lower() for w in ['problem', 'bug', 'issue', 'fix']),
                        'has_lesson': any(w in body.lower() for w in ['learned', 'lesson', 'realized', 'key']),
                    })
        
        return sections
    
    def generate(self,
                 source: str,
                 project_name: str,
                 context: dict = None) -> dict:
        """
        Generate article from source content.
        
        Args:
            source: The raw content (log section, notes, etc.)
            project_name: Name of the project
            context: Additional context (optional)
        
        Returns:
            dict with title, content, warnings, word_count
        """
        
        context = context or {}
        
        if self.client:
            return self._generate_with_ai(source, project_name, context)
        else:
            return self._generate_template(source, project_name, context)
    
    def _generate_with_ai(self, source: str, project_name: str, context: dict) -> dict:
        """Generate with Claude AI."""
        
        # Get opening style
        openings = self.voice['articles']['openings']
        
        prompt = f"""Transform this engineering log into a blog article.

PROJECT: {project_name}

SOURCE CONTENT:
{source}

RULES:
1. Structure: problem → approach → what happened → what I learned
2. Tone: engineer's notebook made public
3. Length: 800-1200 words
4. NO call to action (no "follow me", "like this", etc.)
5. NO exclamation marks
6. Acknowledge AI assistance where relevant
7. Focus on the LEARNING, not self-promotion
8. Introvert voice: quiet, technical, factual
9. Short paragraphs (3-4 sentences max)
10. Include code snippets if they illustrate the point

OPENING STYLE OPTIONS (pick one naturally):
{chr(10).join(f'- {o}' for o in openings)}

FORBIDDEN:
- "Follow me"
- "Like and subscribe"
- "What do you think?"
- "Share this"
- Exclamation marks
- Self-congratulation
- Buzzwords

The reader should learn something technical. That's the only goal.

Write the article now."""

        response = self.client.messages.create(
            model="claude-opus-5-5",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        content = response.content[0].text
        
        # Apply Basin Method
        result = self.basin.generate('article', content)
        
        # Generate title
        result['title'] = self._generate_title(source, project_name)
        result['word_count'] = len(content.split())
        result['generated_at'] = datetime.now().isoformat()
        result['source_preview'] = source[:200] + '...' if len(source) > 200 else source
        
        return result
    
    def _generate_template(self, source: str, project_name: str, context: dict) -> dict:
        """Generate from template (no AI)."""
        
        # Extract key information
        problem = self._extract_problem(source)
        solution = self._extract_solution(source)
        learning = self._extract_learning(source)
        
        # Pick opening
        opening = random.choice(self.voice['articles']['openings'])
        opening = opening.format(
            project=project_name,
            event="something interesting happened",
            problem=problem or "a tricky issue",
            topic=project_name,
            achievement="made progress",
            time="a while"
        )
        
        lines = []
        
        # Opening
        lines.append(opening)
        lines.append("")
        
        # Problem
        if problem:
            lines.append(f"The problem: {problem}")
            lines.append("")
        
        # What I tried / approach
        lines.append("Here's what was going on:")
        lines.append("")
        lines.append(self._summarize(source, max_paragraphs=3))
        lines.append("")
        
        # Learning
        if learning:
            lines.append(f"What I learned: {learning}")
        else:
            lines.append("Still working through it. More updates to come.")
        
        content = '\n'.join(lines)
        
        result = self.basin.generate('article', content)
        result['title'] = self._generate_title(source, project_name)
        result['word_count'] = len(content.split())
        result['generated_at'] = datetime.now().isoformat()
        
        return result
    
    def _generate_title(self, source: str, project_name: str) -> str:
        """Generate honest, non-clickbait title."""
        
        source_lower = source.lower()
        
        # Look for specific topics
        if 'user mode' in source_lower or 'ring 3' in source_lower:
            return "Getting User Mode Working in a Homebrew OS"
        elif 'context switch' in source_lower:
            return "Why Context Switching Is Harder Than It Looks"
        elif 'interrupt' in source_lower:
            return "Setting Up Interrupts on Bare Metal"
        elif 'page table' in source_lower or 'pte' in source_lower:
            return "Page Tables: The Thing That Took Me 2 Days to Debug"
        elif 'preempt' in source_lower:
            return "Adding Preemptive Multitasking to a Custom OS"
        elif 'boot' in source_lower:
            return f"Getting {project_name} to Boot"
        elif 'bug' in source_lower or 'debug' in source_lower:
            return f"A Bug That Took Too Long to Find"
        
        # Default: simple project update
        return f"Progress on {project_name}"
    
    def _extract_problem(self, source: str) -> Optional[str]:
        """Try to extract the problem statement."""
        
        patterns = [
            r'problem[:\s]+([^\n.]+)',
            r'issue[:\s]+([^\n.]+)',
            r'bug[:\s]+([^\n.]+)',
            r'the problem was[:\s]+([^\n.]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, source, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_solution(self, source: str) -> Optional[str]:
        """Try to extract the solution."""
        
        patterns = [
            r'fix[:\s]+([^\n.]+)',
            r'solution[:\s]+([^\n.]+)',
            r'solved by[:\s]+([^\n.]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, source, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_learning(self, source: str) -> Optional[str]:
        """Try to extract what was learned."""
        
        patterns = [
            r'learned[:\s]+([^\n.]+)',
            r'lesson[:\s]+([^\n.]+)',
            r'key (?:insight|takeaway)[:\s]+([^\n.]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, source, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _summarize(self, text: str, max_paragraphs: int = 3) -> str:
        """Basic summarization - take first few meaningful paragraphs."""
        
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        # Filter out code blocks and very short paragraphs
        meaningful = []
        for p in paragraphs:
            if p.startswith('```'):
                continue
            if len(p) < 50:
                continue
            meaningful.append(p)
        
        return '\n\n'.join(meaningful[:max_paragraphs])
    
    def generate_from_log(self, log_path: Path, project_name: str) -> list[dict]:
        """
        Generate multiple articles from an engineering log.
        
        Returns list of generated articles.
        """
        
        sections = self.scan_log(log_path)
        articles = []
        
        for section in sections:
            if section['has_problem'] or section['has_lesson']:
                article = self.generate(
                    source=section['content'],
                    project_name=project_name,
                    context={'section_title': section['title']}
                )
                article['source_section'] = section['title']
                articles.append(article)
        
        return articles


if __name__ == "__main__":
    # Test with sample content
    generator = ArticleGenerator()
    
    sample_log = """
    ### M19: User Mode Basics
    
    **Goal:** Run code in ring 3 with separate address space
    
    **The Bug:** Reserved Bit Set in Page Table
    
    **Symptom:** Page fault with error "Reserved bit set in page table" at address 0x4FFFF8
    
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
    
    **Key Lesson:** USER bit must be at ALL page table levels, not just final PTE.
    """
    
    result = generator.generate(sample_log, "Chrono OS")
    
    print(f"TITLE: {result['title']}")
    print(f"WORDS: {result['word_count']}")
    print()
    print("ARTICLE:")
    print(result['content'])
    
    if result['violations']:
        print("\nWARNINGS:")
        for v in result['violations']:
            print(f"  [{v['severity']}] {v['found']}")
