# Anvil - Honest Professional Visibility Tool

## Project Overview

Anvil is a desktop application for people who build things but struggle to talk about themselves. It generates CVs, cover letters, and project articles that are honest, evidence-based, and written in the user's authentic voice.

**Core Philosophy:** Show work, don't claim expertise. Every assertion has proof.

**Target User:** Introverted builders who use AI as a tool, have real accomplishments, but undersell themselves.

---

## The Problem This Solves

| Without Anvil | With Anvil |
|---------------|------------|
| Stare at blank page for hours | Structured generation from real data |
| Undersell: "Python beginner" | Honest: "AI-assisted Python development" |
| Oversell: Copy LinkedIn buzzwords | Flagged: "Evidence required" |
| Sound like everyone else | Sound like yourself |
| Forget to document projects | Scheduled articles from logs |
| Applications take 2+ hours | 10 minutes, tailored output |

---

## Core Principles

### 1. Evidence-Based Everything
```
WRONG: "Expert in systems programming"
RIGHT: "Built custom OS kernel - 19 milestones, boots on hardware"
       Link: github.com/user/chronos
```

### 2. Introvert Voice
```
WRONG: "I'm passionate about connecting with teams and driving synergy!"
RIGHT: "I build things. Here's proof."
```

### 3. AI Honesty
```
WRONG: "Extensive C programming experience"
RIGHT: "AI-assisted systems development - I design, debug, and ship"
```

### 4. No Fraud
- Every claim checked against profile
- Inflation detected and flagged
- User reviews everything before export

---

## Architecture

```
anvil/
├── anvil.py                    # Main entry point
├── config/
│   ├── settings.yaml           # App settings
│   └── api_keys.yaml           # Claude API key (gitignored)
│
├── data/
│   ├── profile.yaml            # User's master profile
│   ├── voice.yaml              # Writing voice configuration
│   ├── projects/               # Project folders
│   │   ├── chronos/
│   │   │   ├── meta.yaml       # Project metadata
│   │   │   └── logs/           # Engineering logs
│   │   ├── basin/
│   │   └── ...
│   └── history/
│       ├── applications.json   # Application tracking
│       └── articles.json       # Published articles
│
├── core/
│   ├── __init__.py
│   ├── profile_manager.py      # Load/validate profile
│   ├── project_scanner.py      # Scan project folders for content
│   └── evidence_linker.py      # Match claims to proof
│
├── basin/
│   ├── __init__.py
│   ├── method.py               # Basin 3-layer implementation
│   ├── orange.py               # Ceiling layer (constraints)
│   ├── black.py                # Spine layer (structure)
│   └── red.py                  # Flesh layer (voice)
│
├── generators/
│   ├── __init__.py
│   ├── cv.py                   # CV generation
│   ├── cover_letter.py         # Cover letter generation
│   └── article.py              # Project article generation
│
├── checks/
│   ├── __init__.py
│   ├── fraud_detector.py       # Catch overselling
│   ├── undersell_detector.py   # Catch underselling
│   └── voice_checker.py        # Ensure introvert voice
│
├── ui/
│   ├── __init__.py
│   ├── main_window.py          # Main application window
│   ├── cv_tab.py               # CV generator tab
│   ├── cover_letter_tab.py     # Cover letter tab
│   ├── article_tab.py          # Article generator tab
│   └── components/
│       ├── editor.py           # Text editor with preview
│       ├── job_parser.py       # Job description analyzer
│       └── project_picker.py   # Project selection widget
│
├── export/
│   ├── __init__.py
│   ├── docx_export.py          # Word document export
│   ├── pdf_export.py           # PDF export
│   ├── markdown_export.py      # Markdown export
│   └── clipboard.py            # Copy to clipboard
│
├── templates/
│   ├── cv/
│   │   ├── standard.yaml       # Standard CV template
│   │   └── technical_pm.yaml   # Technical PM focused
│   ├── cover_letter/
│   │   ├── standard.yaml
│   │   └── startup.yaml
│   └── article/
│       ├── engineering_log.yaml
│       └── project_update.yaml
│
└── output/                     # Generated files (gitignored)
    ├── cv/
    ├── cover_letters/
    └── articles/
```

---

## Data Structures

### profile.yaml (Master Profile)

```yaml
# User's complete professional data
# This is the source of truth - everything generates from here

personal:
  name: "Florent Herisson"
  name_ja: "フローラン・ヘリソン"
  email: "you@example.com"
  phone: "+81 00-0000-0000"
  location: "Osaka, Japan"
  website: "https://florentherisson.com"
  github: "https://github.com/Raka-Saka"
  
  # Honest positioning
  title: "Technical Project Manager / AI-Assisted Builder"
  tagline: "I build things. I use AI as a tool. Here's proof."

working_style:
  type: "ai_collaborative_builder"
  description: |
    I don't memorize syntax. I define problems clearly, manage complexity,
    debug when things break, and ship. AI is my implementation tool.
  
  strengths:
    - "Problem definition and decomposition"
    - "Project roadmapping and milestone tracking"
    - "Debugging and root cause analysis"
    - "Shipping complete projects"
    - "Process improvement"
  
  honest_limitations:
    - "Not a traditional developer - I use AI assistance"
    - "Can't write C from memory - but can debug it"
    - "Introvert - not a networking person"

skills:
  # Split into honest categories
  direct_experience:
    - skill: "QA Testing"
      years: 3
      evidence: "EA, Zenimax - shipped AAA titles"
    - skill: "Team Leadership"
      years: 2
      evidence: "EA Team Captain - 30+ international reports"
    - skill: "Process Improvement"
      evidence: "10x production increase at Eishin Techno"
    - skill: "Project Management"
      evidence: "34-milestone OS roadmap, 19 completed"
  
  ai_assisted_building:
    - skill: "OS Kernel Development"
      evidence: "ChronOS - boots on real hardware"
    - skill: "ML Model Training"
      evidence: "60+ LoRA models trained"
    - skill: "Game Development (Unity)"
      evidence: "Space game with orbital mechanics"
    - skill: "Backend Development (Rust, Python)"
      evidence: "GlobalChat, GRIP, various tools"
  
  tools:
    - "JIRA, Confluence (professional)"
    - "Claude AI (daily driver)"
    - "Unity, VS Code, Git"
    - "Python, C#, C (with AI assistance)"

languages:
  - language: "French"
    level: "Native"
  - language: "English"
    level: "Fluent"
  - language: "Japanese"
    level: "N4 (conversational)"

experience:
  # Professional experience with evidence
  - company: "Electronic Arts"
    role: "Tier 3 Team Captain / CE Advisor"
    location: "Galway, Ireland"
    period: "2015-01 to 2017-04"
    evidence:
      - "Managed 30+ advisors across England, Germany, France"
      - "SWTOR specialist - Tier 3 escalations"
      - "100% CSAT maintained"
    keywords: ["QA", "Team Lead", "Gaming", "JIRA"]
  
  # ... rest of experience

projects:
  # Personal projects with proof
  - name: "Chrono OS"
    status: "active"
    repo: "https://github.com/Raka-Saka/chronos"
    description: "Custom operating system with time-native philosophy"
    evidence:
      - "19/34 milestones completed"
      - "Boots on real hardware (Aorus X3)"
      - "Preemptive multitasking working"
      - "User mode (Ring 3) implemented"
    log_file: "projects/chronos/logs/ENGINEERING_LOG_V4.md"
    ai_assisted: true
    
  # ... rest of projects
```

### voice.yaml (Writing Voice Configuration)

```yaml
# How Anvil writes - this is YOUR voice, not generic professional

voice_type: "introvert_builder"

# Core identity
identity:
  - "I build things"
  - "I use AI as a tool"
  - "I show work, not claims"
  - "I'm not a salesperson"

# Writing principles
principles:
  evidence_first: true          # Every claim needs proof
  quiet_confidence: true        # State facts, don't boast
  technical_accuracy: true      # Precision over impression
  acknowledge_ai: true          # Honest about AI assistance
  show_process: true            # How you solved it, not just that you did

# Language rules
language:
  # Words/phrases to NEVER use
  forbidden:
    - "passionate about"
    - "excited to"
    - "proven track record"
    - "extensive experience"
    - "expert in"
    - "guru"
    - "ninja"
    - "rockstar"
    - "synergy"
    - "leverage"
    - "disrupt"
    - "game-changer"
    - "think outside the box"
    - "hit the ground running"
    - "!"  # Exclamation marks in professional docs
    
  # Preferred alternatives
  prefer:
    "passionate about X": "I build X"
    "extensive experience": "N years doing X, evidence: Y"
    "expert in": "I've built [specific thing]"
    "excited to join": "This role fits because"
    "proven track record": "[specific achievement with numbers]"
    
  # Sentence style
  style:
    max_sentence_length: 20      # Words - keep it tight
    active_voice: true           # "I built" not "was built by me"
    first_person: true           # "I" not "the candidate"
    contractions: true           # "I'm" not "I am" - sounds human

# Article specific
articles:
  structure: "problem → approach → what happened → what I learned"
  tone: "engineer's notebook"
  length_words: [800, 1200]     # Min, max
  call_to_action: false         # No "follow me!" nonsense
  self_promotion: minimal       # Let the work speak
  
  # Opening styles (rotate)
  openings:
    - "I've been building [X]. This week, [specific thing happened]."
    - "Here's a problem I hit: [problem]. Here's how I solved it."
    - "[Technical thing] isn't as hard as it sounds. Here's what's actually involved."
    - "I don't have a CS degree. Last week I [technical achievement]."

# CV specific  
cv:
  format: "evidence_based"
  summary_length: 3             # Sentences max
  bullets_per_job: [3, 5]       # Min, max
  quantify_everything: true     # Numbers where possible
  
# Cover letter specific
cover_letter:
  length_paragraphs: [3, 5]     # Short and direct
  opening: "direct"             # No "I am writing to apply..."
  closing: "simple"             # No "I look forward to..."
  
  # Structure
  structure:
    - "Why this caught my attention (1-2 sentences)"
    - "What I bring - with evidence (2-3 short paragraphs)"
    - "Honest acknowledgment of gaps if any (1 sentence)"
    - "Simple close (1 sentence)"
```

---

## Basin Method Integration

The Basin Method is used for all generation:

### ORANGE Layer (Ceiling/Constraints)

```python
# basin/orange.py
"""
ORANGE layer defines what we CANNOT say.
This is the fraud prevention layer.
"""

class OrangeLayer:
    def __init__(self, profile: dict, voice: dict):
        self.profile = profile
        self.voice = voice
    
    def get_constraints(self) -> dict:
        return {
            # Hard constraints from profile
            "max_years_experience": self._calculate_max_years(),
            "proven_skills_only": self._get_evidenced_skills(),
            "forbidden_claims": self._get_forbidden_claims(),
            "forbidden_language": self.voice['language']['forbidden'],
            
            # Honesty constraints
            "must_acknowledge_ai": self.profile['working_style']['type'] == 'ai_collaborative_builder',
            "cannot_claim_traditional_dev": True,
        }
    
    def validate(self, text: str) -> list[str]:
        """Return list of constraint violations."""
        violations = []
        
        # Check forbidden language
        for phrase in self.voice['language']['forbidden']:
            if phrase.lower() in text.lower():
                violations.append(f"Forbidden phrase: '{phrase}'")
        
        # Check unsubstantiated claims
        claims = self._extract_claims(text)
        for claim in claims:
            if not self._has_evidence(claim):
                violations.append(f"Unsubstantiated claim: '{claim}'")
        
        return violations
```

### BLACK Layer (Spine/Structure)

```python
# basin/black.py
"""
BLACK layer defines the structure.
This is the skeleton that holds everything together.
"""

class BlackLayer:
    def __init__(self, template: dict):
        self.template = template
    
    def get_structure(self, doc_type: str) -> dict:
        structures = {
            "cv": {
                "sections": [
                    {"name": "header", "required": True},
                    {"name": "summary", "required": True, "max_sentences": 3},
                    {"name": "skills", "required": True, "split": ["direct", "ai_assisted"]},
                    {"name": "projects", "required": True, "max_items": 4},
                    {"name": "experience", "required": True},
                    {"name": "education", "required": False},
                ],
                "order": "projects_before_experience",  # Show what you build first
            },
            
            "cover_letter": {
                "sections": [
                    {"name": "opening", "sentences": [1, 2], "style": "direct"},
                    {"name": "relevance", "paragraphs": [2, 3], "must_have_evidence": True},
                    {"name": "honesty", "sentences": [0, 2], "optional_gaps": True},
                    {"name": "close", "sentences": 1, "style": "simple"},
                ],
            },
            
            "article": {
                "sections": [
                    {"name": "hook", "sentences": [1, 2]},
                    {"name": "problem", "paragraphs": 1},
                    {"name": "approach", "paragraphs": [1, 2]},
                    {"name": "what_happened", "paragraphs": [2, 3]},
                    {"name": "learning", "paragraphs": 1},
                ],
                "no_call_to_action": True,
            },
        }
        return structures.get(doc_type, {})
```

### RED Layer (Flesh/Voice)

```python
# basin/red.py
"""
RED layer adds the human voice.
This makes it sound like YOU, not a template.
"""

class RedLayer:
    def __init__(self, voice: dict):
        self.voice = voice
    
    def apply_voice(self, text: str) -> str:
        """Transform text to match user's voice."""
        
        # Apply preferred phrasings
        for original, replacement in self.voice['language']['prefer'].items():
            text = self._smart_replace(text, original, replacement)
        
        # Enforce sentence length
        text = self._shorten_sentences(text, self.voice['language']['style']['max_sentence_length'])
        
        # Convert to active voice
        if self.voice['language']['style']['active_voice']:
            text = self._to_active_voice(text)
        
        # Add contractions for natural feel
        if self.voice['language']['style']['contractions']:
            text = self._add_contractions(text)
        
        return text
    
    def get_opening(self, doc_type: str, context: dict) -> str:
        """Generate appropriate opening based on voice."""
        if doc_type == "article":
            # Rotate through opening styles
            openings = self.voice['articles']['openings']
            return self._fill_template(random.choice(openings), context)
        
        elif doc_type == "cover_letter":
            # Direct opening, no fluff
            return f"I saw your posting for {context['role']}."
        
        return ""
```

---

## Generator Implementations

### CV Generator

```python
# generators/cv.py
"""
Generate honest, evidence-based CVs.
"""

from pathlib import Path
from core.profile_manager import ProfileManager
from core.evidence_linker import EvidenceLinker
from basin.method import BasinMethod
from checks.fraud_detector import FraudDetector

class CVGenerator:
    def __init__(self, profile_path: Path, voice_path: Path):
        self.profile = ProfileManager(profile_path).load()
        self.basin = BasinMethod(self.profile, voice_path)
        self.fraud_check = FraudDetector(self.profile)
        self.evidence = EvidenceLinker(self.profile)
    
    def generate(self, 
                 target_role: str = "general",
                 include_projects: list[str] = None,
                 emphasis: str = "balanced") -> dict:
        """
        Generate a CV tailored to target role.
        
        Args:
            target_role: Type of role (technical_pm, qa_lead, general)
            include_projects: List of project names to include
            emphasis: problem_solving, project_management, technical
        
        Returns:
            dict with 'content', 'warnings', 'evidence_links'
        """
        
        # 1. ORANGE: Get constraints
        constraints = self.basin.orange.get_constraints()
        
        # 2. BLACK: Get structure
        structure = self.basin.black.get_structure("cv")
        
        # 3. Build sections
        sections = {}
        
        # Header
        sections['header'] = self._build_header()
        
        # Summary - 3 sentences max, evidence-based
        sections['summary'] = self._build_summary(target_role, emphasis)
        
        # Skills - split into direct and AI-assisted
        sections['skills'] = self._build_skills(target_role)
        
        # Projects - with evidence links
        sections['projects'] = self._build_projects(include_projects)
        
        # Experience - quantified achievements
        sections['experience'] = self._build_experience(target_role)
        
        # 4. RED: Apply voice
        content = self.basin.red.apply_voice(
            self._render_sections(sections, structure)
        )
        
        # 5. Fraud check
        warnings = self.fraud_check.check(content)
        
        # 6. Link evidence
        evidence_links = self.evidence.get_links(content)
        
        return {
            'content': content,
            'sections': sections,
            'warnings': warnings,
            'evidence_links': evidence_links,
        }
    
    def _build_summary(self, target_role: str, emphasis: str) -> str:
        """Build 3-sentence summary based on role and emphasis."""
        
        # Base identity
        identity = "I build things. I use AI as a tool to implement what I design."
        
        # Evidence based on emphasis
        if emphasis == "project_management":
            evidence = f"I've managed a 34-milestone OS project, completing 19 milestones in 5 days on real hardware."
        elif emphasis == "problem_solving":
            evidence = f"Recent example: debugged x86-64 page table hierarchy issue over 2 days, found root cause in USER bit propagation."
        else:
            evidence = f"I ship: custom OS that boots, 60+ trained ML models, published album on Spotify."
        
        # What I'm looking for
        looking_for = "I want to do work that matches what I'm capable of."
        
        return f"{identity} {evidence} {looking_for}"
    
    def _build_skills(self, target_role: str) -> dict:
        """Build skills section with honest categorization."""
        
        return {
            'direct_experience': [
                self._format_skill(s) 
                for s in self.profile['skills']['direct_experience']
            ],
            'ai_assisted_building': [
                self._format_skill(s)
                for s in self.profile['skills']['ai_assisted_building']
            ],
            'tools': self.profile['skills']['tools'],
        }
    
    def _format_skill(self, skill: dict) -> str:
        """Format skill with evidence."""
        if 'years' in skill:
            return f"{skill['skill']} ({skill['years']}y) - {skill['evidence']}"
        return f"{skill['skill']} - {skill['evidence']}"
```

### Cover Letter Generator

```python
# generators/cover_letter.py
"""
Generate cover letters using Basin Method.
Matches user to job, acknowledges gaps honestly.
"""

import anthropic
from core.profile_manager import ProfileManager
from basin.method import BasinMethod

class CoverLetterGenerator:
    def __init__(self, profile_path: Path, voice_path: Path, api_key: str):
        self.profile = ProfileManager(profile_path).load()
        self.basin = BasinMethod(self.profile, voice_path)
        self.client = anthropic.Anthropic(api_key=api_key)
    
    def analyze_job(self, job_description: str) -> dict:
        """Extract requirements and match against profile."""
        
        prompt = f"""Analyze this job description and extract:
1. Required skills (list)
2. Nice-to-have skills (list)
3. Years of experience mentioned
4. Key responsibilities
5. Company values/culture hints

Job Description:
{job_description}

Return as YAML."""

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        requirements = self._parse_yaml(response.content[0].text)
        
        # Match against profile
        matches = self._match_requirements(requirements)
        gaps = self._identify_gaps(requirements)
        
        return {
            'requirements': requirements,
            'matches': matches,
            'gaps': gaps,
            'match_score': len(matches) / (len(matches) + len(gaps)) * 100
        }
    
    def generate(self, job_description: str, company_name: str = None) -> dict:
        """Generate cover letter."""
        
        # Analyze job
        analysis = self.analyze_job(job_description)
        
        # Get constraints (ORANGE)
        constraints = self.basin.orange.get_constraints()
        constraints['job_requirements'] = analysis['requirements']
        
        # Build structure (BLACK)
        structure = self.basin.black.get_structure("cover_letter")
        
        # Generate with Claude
        prompt = self._build_generation_prompt(analysis, constraints, structure)
        
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=self._get_system_prompt(),
            messages=[{"role": "user", "content": prompt}]
        )
        
        content = response.content[0].text
        
        # Apply voice (RED)
        content = self.basin.red.apply_voice(content)
        
        # Check for issues
        warnings = self.basin.orange.validate(content)
        
        return {
            'content': content,
            'analysis': analysis,
            'warnings': warnings,
        }
    
    def _get_system_prompt(self) -> str:
        return f"""You are writing a cover letter for someone with this profile:

{self._summarize_profile()}

VOICE RULES:
- Introvert voice: quiet confidence, no exclamation marks
- Evidence-based: every claim has proof
- Honest about AI assistance
- No buzzwords: "passionate", "excited", "synergy" are forbidden
- Short sentences, active voice
- Direct opening, no "I am writing to apply..."

STRUCTURE:
1. Opening (1-2 sentences): Why this caught attention
2. Relevance (2-3 paragraphs): What I bring, with evidence
3. Honesty (0-2 sentences): Acknowledge gaps if significant
4. Close (1 sentence): Simple, no "I look forward to..."

The letter should sound like a competent introvert wrote it, not a salesperson."""

    def _build_generation_prompt(self, analysis: dict, constraints: dict, structure: dict) -> str:
        return f"""Write a cover letter for this job.

JOB REQUIREMENTS:
{analysis['requirements']}

MY MATCHES:
{analysis['matches']}

GAPS TO ACKNOWLEDGE:
{analysis['gaps']}

EVIDENCE I CAN USE:
{self._get_relevant_evidence(analysis['requirements'])}

Write the cover letter now. Be direct, honest, and evidence-based."""
```

### Article Generator

```python
# generators/article.py
"""
Generate articles from engineering logs and project updates.
For introverts: no self-promotion, just sharing what you learned.
"""

from pathlib import Path
from datetime import datetime
import re

class ArticleGenerator:
    def __init__(self, profile_path: Path, voice_path: Path, api_key: str):
        self.profile = ProfileManager(profile_path).load()
        self.basin = BasinMethod(self.profile, voice_path)
        self.client = anthropic.Anthropic(api_key=api_key)
    
    def extract_sections(self, log_path: Path) -> list[dict]:
        """Extract publishable sections from engineering log."""
        
        content = log_path.read_text(encoding='utf-8')
        
        # Find milestone sections
        sections = []
        pattern = r'### (M\d+.*?)\n(.*?)(?=### M|\Z)'
        
        for match in re.finditer(pattern, content, re.DOTALL):
            title = match.group(1).strip()
            body = match.group(2).strip()
            
            # Check if this section has enough content
            if len(body) > 500:
                sections.append({
                    'title': title,
                    'content': body,
                    'has_code': '```' in body,
                    'has_lesson': 'lesson' in body.lower() or 'learned' in body.lower(),
                })
        
        return sections
    
    def generate_from_section(self, section: dict, project_name: str) -> dict:
        """Generate article from a log section."""
        
        # Get structure (BLACK)
        structure = self.basin.black.get_structure("article")
        
        prompt = f"""Transform this engineering log section into a blog article.

PROJECT: {project_name}
SECTION: {section['title']}

LOG CONTENT:
{section['content']}

RULES:
1. Structure: problem → approach → what happened → what I learned
2. Tone: engineer's notebook made public
3. Length: 800-1200 words
4. NO call to action ("follow me", "like this", etc.)
5. Acknowledge AI assistance honestly where relevant
6. Focus on the LEARNING, not self-promotion
7. Introvert voice: quiet, technical, factual

OPENING STYLE (pick one naturally):
- "I've been building [X]. This week, [specific thing happened]."
- "Here's a problem I hit: [problem]. Here's how I solved it."
- "I don't have a CS degree. Last week I [technical achievement]."

Write the article now."""

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=self._get_system_prompt(),
            messages=[{"role": "user", "content": prompt}]
        )
        
        content = response.content[0].text
        
        # Apply voice (RED)
        content = self.basin.red.apply_voice(content)
        
        # Generate title
        title = self._generate_title(section, content)
        
        return {
            'title': title,
            'content': content,
            'source_section': section['title'],
            'word_count': len(content.split()),
            'generated_at': datetime.now().isoformat(),
        }
    
    def _get_system_prompt(self) -> str:
        return """You are helping an introvert write about their technical projects.

VOICE:
- Engineer's notebook style
- Quiet confidence, no hype
- "I built this" not "I'm amazing"
- Technical accuracy matters
- Acknowledge AI assistance honestly
- Short paragraphs, clear structure

FORBIDDEN:
- "Passionate about..."
- Exclamation marks
- Call to action
- Self-promotion beyond stating facts
- Buzzwords

The reader should learn something. That's it."""

    def _generate_title(self, section: dict, content: str) -> str:
        """Generate honest, non-clickbait title."""
        
        # Extract the core topic
        if "User Mode" in section['title']:
            return "Getting Ring 3 Working in a Homebrew OS"
        elif "Context" in section['title']:
            return "Why Context Switching Is Harder Than It Looks"
        elif "Interrupt" in section['title']:
            return "Setting Up Interrupts on Bare Metal"
        
        # Fallback: simple description
        return section['title'].replace("M", "Milestone ").replace(":", " -")
```

---

## Fraud Detection System

```python
# checks/fraud_detector.py
"""
Catch overselling before it happens.
Every claim must have evidence.
"""

import re
from typing import list

class FraudDetector:
    def __init__(self, profile: dict):
        self.profile = profile
        self.evidence_map = self._build_evidence_map()
    
    def check(self, text: str) -> list[dict]:
        """Check text for fraud indicators."""
        
        warnings = []
        
        # Check for unsubstantiated expertise claims
        expertise_claims = self._find_expertise_claims(text)
        for claim in expertise_claims:
            if not self._has_evidence(claim):
                warnings.append({
                    'type': 'unsubstantiated_claim',
                    'text': claim,
                    'suggestion': self._suggest_alternative(claim),
                    'severity': 'high',
                })
        
        # Check for inflated experience
        years_claims = self._find_years_claims(text)
        for claim in years_claims:
            actual = self._get_actual_years(claim['skill'])
            if claim['years'] > actual:
                warnings.append({
                    'type': 'inflated_experience',
                    'text': f"{claim['years']} years of {claim['skill']}",
                    'actual': f"{actual} years",
                    'severity': 'high',
                })
        
        # Check for forbidden phrases
        forbidden = [
            "expert in", "extensive experience", "proven track record",
            "passionate about", "guru", "ninja", "rockstar",
        ]
        for phrase in forbidden:
            if phrase in text.lower():
                warnings.append({
                    'type': 'forbidden_phrase',
                    'text': phrase,
                    'suggestion': self._get_alternative(phrase),
                    'severity': 'medium',
                })
        
        # Check for missing AI acknowledgment
        if self._claims_technical_work(text) and not self._acknowledges_ai(text):
            warnings.append({
                'type': 'missing_ai_acknowledgment',
                'text': 'Technical implementation claims without AI context',
                'suggestion': 'Add "AI-assisted" or similar honest framing',
                'severity': 'medium',
            })
        
        return warnings
    
    def _find_expertise_claims(self, text: str) -> list[str]:
        """Find phrases that claim expertise."""
        patterns = [
            r"expert in (\w+)",
            r"mastery of (\w+)",
            r"deep knowledge of (\w+)",
            r"extensive experience (?:in |with )?(\w+)",
        ]
        claims = []
        for pattern in patterns:
            claims.extend(re.findall(pattern, text, re.IGNORECASE))
        return claims
    
    def _suggest_alternative(self, claim: str) -> str:
        """Suggest evidence-based alternative."""
        skill = claim.lower()
        
        # Check if we have evidence for this skill
        for s in self.profile['skills']['direct_experience']:
            if skill in s['skill'].lower():
                return f"'{s['skill']}' - {s['evidence']}"
        
        for s in self.profile['skills']['ai_assisted_building']:
            if skill in s['skill'].lower():
                return f"'AI-assisted {s['skill']}' - {s['evidence']}"
        
        return f"Remove or provide specific evidence for '{claim}'"
```

---

## Simple Desktop UI

```python
# ui/main_window.py
"""
Simple, clean desktop interface.
No overwhelming options. Just get the job done.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QPushButton, QTextEdit,
    QComboBox, QCheckBox, QListWidget, QSplitter,
    QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class AnvilWindow(QMainWindow):
    def __init__(self, config_path: Path):
        super().__init__()
        self.config_path = config_path
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("Anvil - Honest Professional Visibility")
        self.setMinimumSize(1000, 700)
        
        # Simple dark theme - easy on the eyes
        self.setStyleSheet("""
            QMainWindow { background-color: #1a1a2e; }
            QWidget { background-color: #1a1a2e; color: #eee; }
            QTabWidget::pane { border: 1px solid #333; }
            QTabBar::tab { 
                background: #16213e; 
                color: #888;
                padding: 10px 20px;
                border: none;
            }
            QTabBar::tab:selected { 
                background: #0f3460; 
                color: #fff;
            }
            QTextEdit {
                background: #0f0f1a;
                border: 1px solid #333;
                padding: 10px;
                font-family: 'Consolas', monospace;
                font-size: 13px;
            }
            QPushButton {
                background: #0f3460;
                border: none;
                padding: 10px 20px;
                color: #fff;
            }
            QPushButton:hover { background: #1a508b; }
            QComboBox {
                background: #16213e;
                border: 1px solid #333;
                padding: 8px;
            }
        """)
        
        # Central widget with tabs
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Header
        header = QLabel("ANVIL")
        header.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        header.setStyleSheet("color: #e94560; margin: 10px;")
        layout.addWidget(header)
        
        subtitle = QLabel("Honest professional visibility. No fraud. No overselling.")
        subtitle.setStyleSheet("color: #666; margin-bottom: 20px;")
        layout.addWidget(subtitle)
        
        # Tab widget
        tabs = QTabWidget()
        tabs.addTab(CVTab(self.config_path), "CV")
        tabs.addTab(CoverLetterTab(self.config_path), "Cover Letter")
        tabs.addTab(ArticleTab(self.config_path), "Articles")
        tabs.addTab(SettingsTab(self.config_path), "Settings")
        layout.addWidget(tabs)


class CVTab(QWidget):
    """CV generation tab."""
    
    def __init__(self, config_path: Path):
        super().__init__()
        self.config_path = config_path
        self.setup_ui()
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        
        # Left panel - options
        left = QWidget()
        left_layout = QVBoxLayout(left)
        
        # Role type
        left_layout.addWidget(QLabel("Target Role:"))
        self.role_combo = QComboBox()
        self.role_combo.addItems([
            "General",
            "Technical PM",
            "QA Lead",
            "AI-Assisted Developer",
            "Startup Generalist"
        ])
        left_layout.addWidget(self.role_combo)
        
        # Projects to include
        left_layout.addWidget(QLabel("Include Projects:"))
        self.project_list = QListWidget()
        self.project_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        # Populate from profile
        self._load_projects()
        left_layout.addWidget(self.project_list)
        
        # Emphasis
        left_layout.addWidget(QLabel("Emphasis:"))
        self.emphasis_combo = QComboBox()
        self.emphasis_combo.addItems([
            "Balanced",
            "Problem Solving",
            "Project Management",
            "Technical"
        ])
        left_layout.addWidget(self.emphasis_combo)
        
        # Generate button
        generate_btn = QPushButton("Generate CV")
        generate_btn.clicked.connect(self.generate)
        left_layout.addWidget(generate_btn)
        
        left_layout.addStretch()
        
        # Right panel - preview and warnings
        right = QWidget()
        right_layout = QVBoxLayout(right)
        
        right_layout.addWidget(QLabel("Preview:"))
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        right_layout.addWidget(self.preview)
        
        # Warnings panel
        self.warnings = QTextEdit()
        self.warnings.setMaximumHeight(100)
        self.warnings.setStyleSheet("background: #2a1a1a; color: #e94560;")
        self.warnings.setPlaceholderText("Fraud check warnings will appear here...")
        right_layout.addWidget(self.warnings)
        
        # Export buttons
        export_layout = QHBoxLayout()
        
        docx_btn = QPushButton("Export .docx")
        docx_btn.clicked.connect(lambda: self.export('docx'))
        export_layout.addWidget(docx_btn)
        
        pdf_btn = QPushButton("Export .pdf")
        pdf_btn.clicked.connect(lambda: self.export('pdf'))
        export_layout.addWidget(pdf_btn)
        
        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.clicked.connect(self.copy_to_clipboard)
        export_layout.addWidget(copy_btn)
        
        right_layout.addLayout(export_layout)
        
        # Add to splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([300, 700])
        
        layout.addWidget(splitter)
    
    def generate(self):
        """Generate CV with current settings."""
        # Implementation calls CVGenerator
        pass
    
    def export(self, format: str):
        """Export to file."""
        pass
    
    def copy_to_clipboard(self):
        """Copy to clipboard."""
        pass


class CoverLetterTab(QWidget):
    """Cover letter generation tab."""
    
    def __init__(self, config_path: Path):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Job description input
        layout.addWidget(QLabel("Paste Job Description:"))
        self.job_input = QTextEdit()
        self.job_input.setPlaceholderText("Paste the job description here...")
        self.job_input.setMaximumHeight(200)
        layout.addWidget(self.job_input)
        
        # Analyze button
        analyze_btn = QPushButton("Analyze Job")
        analyze_btn.clicked.connect(self.analyze)
        layout.addWidget(analyze_btn)
        
        # Analysis results
        self.analysis = QTextEdit()
        self.analysis.setReadOnly(True)
        self.analysis.setMaximumHeight(150)
        self.analysis.setPlaceholderText("Match analysis will appear here...")
        layout.addWidget(self.analysis)
        
        # Generate button
        generate_btn = QPushButton("Generate Cover Letter")
        generate_btn.clicked.connect(self.generate)
        layout.addWidget(generate_btn)
        
        # Preview
        layout.addWidget(QLabel("Preview:"))
        self.preview = QTextEdit()
        layout.addWidget(self.preview)
        
        # Warnings
        self.warnings = QTextEdit()
        self.warnings.setMaximumHeight(80)
        self.warnings.setStyleSheet("background: #2a1a1a; color: #e94560;")
        layout.addWidget(self.warnings)
        
        # Export
        export_layout = QHBoxLayout()
        export_layout.addWidget(QPushButton("Export .docx"))
        export_layout.addWidget(QPushButton("Copy"))
        layout.addLayout(export_layout)
    
    def analyze(self):
        """Analyze job description."""
        pass
    
    def generate(self):
        """Generate cover letter."""
        pass


class ArticleTab(QWidget):
    """Article generation from project logs."""
    
    def __init__(self, config_path: Path):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        
        # Left - source selection
        left = QWidget()
        left_layout = QVBoxLayout(left)
        
        left_layout.addWidget(QLabel("Project:"))
        self.project_combo = QComboBox()
        # Populate from profile
        left_layout.addWidget(self.project_combo)
        
        left_layout.addWidget(QLabel("Log Sections:"))
        self.section_list = QListWidget()
        left_layout.addWidget(self.section_list)
        
        generate_btn = QPushButton("Generate Article")
        generate_btn.clicked.connect(self.generate)
        left_layout.addWidget(generate_btn)
        
        # Schedule
        left_layout.addWidget(QLabel("Auto-Schedule:"))
        self.schedule_combo = QComboBox()
        self.schedule_combo.addItems(["Off", "Every 2 days", "Every 3 days", "Weekly"])
        left_layout.addWidget(self.schedule_combo)
        
        left_layout.addStretch()
        
        # Right - preview
        right = QWidget()
        right_layout = QVBoxLayout(right)
        
        right_layout.addWidget(QLabel("Preview:"))
        self.preview = QTextEdit()
        right_layout.addWidget(self.preview)
        
        # Word count
        self.word_count = QLabel("Words: 0")
        right_layout.addWidget(self.word_count)
        
        # Export
        export_layout = QHBoxLayout()
        export_layout.addWidget(QPushButton("Copy for LinkedIn"))
        export_layout.addWidget(QPushButton("Export .md"))
        right_layout.addLayout(export_layout)
        
        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([300, 700])
        layout.addWidget(splitter)
    
    def generate(self):
        """Generate article from selected section."""
        pass
```

---

## Dependencies

```
# requirements.txt

# Core
anthropic>=0.18.0      # Claude API
pyyaml>=6.0            # Config files
pydantic>=2.0          # Data validation

# Document export
python-docx>=0.8.11    # Word documents
reportlab>=4.0         # PDF generation
markdown>=3.5          # Markdown processing

# Desktop UI
PyQt6>=6.6.0           # Desktop GUI

# Utilities
click>=8.1.0           # CLI interface (optional)
schedule>=1.2.0        # Article scheduling
pyperclip>=1.8.0       # Clipboard
```

---

## Getting Started (For Claude Code)

```bash
# Clone/create project
mkdir anvil && cd anvil

# Create structure
mkdir -p config data/projects core basin generators checks ui export templates output

# Install dependencies
pip install anthropic pyyaml pydantic python-docx PyQt6 click

# Set up API key
echo "api_key: 'your-key-here'" > config/api_keys.yaml

# Copy your profile
cp /path/to/master_profile_starter.yaml data/profile.yaml

# Run
python anvil.py
```

---

## What Makes This Different

| Other Tools | Anvil |
|-------------|-------|
| "Optimize for ATS" | Write honest content |
| "Use these power words" | Use YOUR words |
| "10x your reach" | Share what you learned |
| Generic templates | Basin Method (your system) |
| Fake confidence | Quiet, evidence-based |
| Oversell everything | Fraud detection built in |

---

## Success Metrics

Not vanity metrics. Real outcomes:

- [ ] CV generates in under 30 seconds
- [ ] Cover letter matches job requirements to evidence
- [ ] Fraud detector catches overselling
- [ ] Articles sound like engineer's notebook
- [ ] You're not embarrassed by anything it outputs
- [ ] You get interviews for roles that actually fit

---

*"Show work, don't claim expertise."*
