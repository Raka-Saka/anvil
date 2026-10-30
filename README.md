# Anvil

**Honest professional visibility tool for introverts who build things.**

No overselling. No buzzwords. Just evidence.

## What It Does

1. **CV Generator** - Creates honest, evidence-based CVs with proper categorization of "direct experience" vs "AI-assisted building"

2. **Cover Letter Generator** - Matches your experience to job requirements, acknowledges gaps honestly, uses your voice (not salesy)

3. **Article Generator** - Transforms engineering logs into quiet technical articles. No "follow me!" No self-promotion. Just sharing what you learned.

4. **Fraud Detection** - Catches overselling before it happens. Flags unsubstantiated claims, forbidden phrases, missing AI acknowledgment.

## Your Voice

Anvil knows you're an introvert. It writes like you:
- Quiet confidence, not bravado
- Evidence before assertions
- Short sentences (max 20 words)
- No exclamation marks
- No "passionate about" or "excited to"
- Technical accuracy over impression

## Launch

Double-click **Anvil** on the desktop, or `Anvil.cmd` in this folder. No console window.
Claude runs through Claude Code (your subscription); no API key needed.

## Quick Start

```bash
# Install dependencies
pip install anthropic pyyaml python-docx

# Run CLI
python cli.py

# Or run specific generators
python cli.py cv
python cli.py cover
python cli.py article
python cli.py check
```

## For Claude Code

This project is ready for Claude Code to extend. Key files:

- `data/profile.yaml` - Your complete professional data (edit this!)
- `data/voice.yaml` - How Anvil writes (your voice settings)
- `basin/method.py` - The Basin Method (ORANGE/BLACK/RED layers)
- `generators/cv.py` - CV generation
- `generators/cover_letter.py` - Cover letter generation
- `generators/article.py` - Article from logs

### Next Steps to Build

1. **Add Claude API key**
   ```bash
   # Create config/api_keys.yaml
   echo "api_key: 'your-anthropic-key'" > config/api_keys.yaml
   ```

2. **Copy your engineering logs**
   ```bash
   cp /path/to/ENGINEERING_LOG_V4.md data/projects/chronos/logs/
   ```

3. **Test CV generation**
   ```bash
   python -c "from generators.cv import generate_cv; print(generate_cv())"
   ```

4. **Build GUI (optional)**
   - Install PyQt6: `pip install PyQt6`
   - Create `ui/main_window.py` with desktop interface

### Project Structure

```
anvil/
├── anvil.py              # Main entry point
├── cli.py                # Command-line interface
├── requirements.txt
│
├── data/
│   ├── profile.yaml      # YOUR data - edit this
│   ├── voice.yaml        # YOUR voice - edit this
│   └── projects/         # Project logs
│       └── chronos/
│           └── logs/     # Engineering logs go here
│
├── core/
│   └── profile_manager.py
│
├── basin/
│   └── method.py         # ORANGE/BLACK/RED layers
│
├── generators/
│   ├── cv.py
│   ├── cover_letter.py
│   └── article.py
│
├── checks/               # Fraud detection (to build)
├── ui/                   # Desktop GUI (to build)
├── export/               # Document export (to build)
│
└── output/               # Generated files
    ├── cv/
    ├── cover_letters/
    └── articles/
```

## The Basin Method

Your methodology, applied to professional content:

- **ORANGE (Ceiling)**: Constraints. What we cannot say. Fraud prevention.
- **BLACK (Spine)**: Structure. The skeleton.
- **RED (Flesh)**: Voice. Makes it sound like you.

## Philosophy

"Show work, don't claim expertise."

Every claim in your CV, cover letter, or article should have evidence.
If you can't prove it, don't say it.

## License

All rights reserved. You need written permission to use, copy or modify Anvil; see [LICENSE](LICENSE).
Personal data (profile, applications, CVs) is gitignored and never published.
