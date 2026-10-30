# CLAUDE.md - Instructions for Claude Code

## Project Overview

Anvil is a desktop tool that generates honest professional content (CVs, cover letters, articles) for an introvert who builds technical projects with AI assistance.

**The user is NOT a traditional developer.** He uses Claude to implement what he designs. He's good at:
- Problem definition
- Project management
- Debugging
- Shipping

He is NOT good at:
- Memorizing syntax
- Self-promotion
- Networking
- Sounding "professional" in the LinkedIn sense

## Core Philosophy

**"Show work, don't claim expertise."**

Every output from Anvil must:
1. Be evidence-based (every claim has proof)
2. Sound like an introvert (quiet confidence, no hype)
3. Acknowledge AI assistance honestly
4. Never oversell

## Key Files

```
anvil/
├── data/
│   ├── profile.yaml      # User's complete data - THE SOURCE OF TRUTH
│   └── voice.yaml        # How to write - THE VOICE RULES
├── basin/
│   └── method.py         # Basin Method (ORANGE/BLACK/RED layers)
├── generators/
│   ├── cv.py             # CV generation
│   ├── cover_letter.py   # Cover letter generation
│   └── article.py        # Article from engineering logs
└── cli.py                # Command-line interface
```

## The Basin Method

This is the user's own methodology. Use it for all generation:

- **ORANGE (Ceiling)**: Constraints. What we CANNOT say. Fraud prevention.
- **BLACK (Spine)**: Structure. The skeleton that holds content together.
- **RED (Flesh)**: Voice. Makes it sound like the user, not a template.

## Voice Rules - CRITICAL

When generating ANY content, follow these rules from `data/voice.yaml`:

### NEVER use these phrases:
- "passionate about"
- "excited to"
- "thrilled"
- "proven track record"
- "extensive experience"
- "expert in"
- "guru", "ninja", "rockstar", "wizard"
- "synergy", "leverage", "disrupt"
- "!" (exclamation marks in professional docs)

### ALWAYS prefer:
- "I build X" instead of "passionate about X"
- "[specific achievement]" instead of "proven track record"
- "I've built [thing]" instead of "expert in"
- Short sentences (max 20 words)
- Active voice
- First person

### Skill Categories

The user has two types of skills - keep them separate:

1. **Direct Experience** - Skills used professionally (QA, team leadership, process improvement)
2. **AI-Assisted Building** - What he builds with Claude's help (OS kernel, ML models, games)

Never claim "expert" in AI-assisted skills. Say "Built X with AI assistance" instead.

## When Modifying Code

### Adding New Generators

1. Follow the pattern in `generators/cv.py`
2. Use `ProfileManager` to load data
3. Use `BasinMethod` for generation
4. Return dict with `content`, `violations`, and metadata
5. Make `anthropic` import optional (some users won't have API key)

```python
try:
    import anthropic
except ImportError:
    anthropic = None
```

### Adding Fraud Detection

Check for:
- Unsubstantiated expertise claims
- Forbidden phrases from voice.yaml
- Missing AI acknowledgment for technical work
- Inflated years of experience
- Extrovert language patterns

### Adding UI Components

- Keep it simple and clean
- Dark theme preferred
- No overwhelming options
- User reviews everything before export
- Show warnings prominently

## Testing

Test CV generation without API:
```bash
python -c "from generators.cv import CVGenerator; g = CVGenerator(); print(g.generate()['content'][:500])"
```

Test profile validation:
```bash
python cli.py check
```

## Common Tasks

### "Add a new project to the profile"

Edit `data/profile.yaml` under the `projects:` section. Include:
- name, status, description
- evidence (list of concrete achievements)
- ai_assisted: true/false
- technical stack
- cv_angle (how to frame it for jobs)

### "Generate content for a specific job"

```python
from generators.cover_letter import CoverLetterGenerator
g = CoverLetterGenerator(api_key="...")
result = g.generate(job_description="...", company_name="...")
```

### "Add article scheduling"

Use the `schedule` library. Articles should:
- Generate from engineering logs automatically
- Post every 2-3 days
- Never include call-to-action
- Focus on what was learned, not self-promotion

### "Export to DOCX"

Use `python-docx`. Keep formatting minimal:
- No fancy headers
- Simple bullet points
- Professional but not corporate
- Match the plain text output style

## User Context

The user:
- Lives in Osaka, Japan
- Works a factory day job (wants to change this)
- Is 48 years old
- Has a spouse visa (no sponsorship needed)
- Prefers remote work
- Is building an OS kernel (ChronOS) for fun
- Has trained 60+ LoRA models
- Published a grunge album
- Worked at EA and Zenimax (QA)
- Is an introvert who struggles with self-promotion

## What Success Looks Like

The user should be able to:
1. Generate a CV in 30 seconds that he's not embarrassed by
2. Create cover letters that match him to jobs honestly
3. Share his project progress without feeling like a fraud
4. Get interviews for roles that actually fit (Technical PM, QA Lead, etc.)

## Do NOT

- Add "engagement optimization" features
- Suggest LinkedIn growth hacks
- Use buzzwords even ironically
- Make the user sound like someone he's not
- Claim expertise he doesn't have
- Ignore the fraud detection system
- Add features that require constant attention (he's busy)

## Do

- Keep it simple
- Keep it honest
- Keep it quiet (introvert-friendly)
- Show evidence for every claim
- Respect the Basin Method
- Test with `python cli.py` before committing
