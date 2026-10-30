# Anvil Diary - Engineering Log

## Session 1: Initial Comedy Article System
**Date**: 2026-01-08

### Goal
Create a comedy article generator that transforms ChronOS engineering logs into "Dear Diary" style dev blog posts.

### What Was Built
1. **ComedyArticleGenerator** (`generators/comedy_article.py`)
   - Scans engineering logs for sections
   - Calculates "comedy potential" score (bugs, frustration, late nights)
   - Uses Basin Method beat structure (12-24 beats across 4 acts)
   - Generates ~2000 word narrative articles
   - Auto-generates relevant hashtags

2. **Japanese Translation**
   - Added `_translate_to_japanese()` method
   - Preserves humor and narrative style
   - Generates Japanese hashtags (#OS開発, #プログラミング, etc.)
   - Saves both EN and JA versions

3. **Article Scheduler** (`scheduler/article_scheduler.py`)
   - Scans ChronOS logs at F:\chronos
   - Tracks used sections in history file
   - Supports 3x/week scheduled generation

4. **CLI Integration** (`cli.py`)
   - `comedy` command for manual generation
   - Shows next chronological section
   - Skip/list options
   - Auto-saves both language versions

### Technical Decisions
- **Claude Sonnet** for generation (balance of quality/cost)
- **4000 max_tokens** for ~2000 word articles + Japanese
- **Chronological order** preserved (it's a diary, not random posts)
- **Background threading** in UI to prevent freezing

### Challenges
1. Flet 0.80 API changes - many constructor args moved to attributes
2. UI freezing during long API calls - solved with threading
3. Set serialization error - changed SegmentedButton to RadioGroup

---

## Session 2: UI Integration
**Date**: 2026-01-08

### Goal
Add Comedy/Diary tab to Flet UI with simple one-button generation.

### What Was Built
1. **ComedyView** (`ui/views/comedy_view.py`)
   - Status display (remaining sections)
   - "Generate Next Diary Entry" button
   - Skip and Reset buttons
   - Previous articles dropdown
   - View EN / View JA buttons
   - Copyable title and hashtags (TextField instead of Text)

2. **Navigation**
   - Added "Diary" tab to nav rail
   - Book/stories icon

### Technical Decisions
- **No on_change for Dropdown** - Flet 0.80 doesn't support it well, used separate View buttons
- **TextField for copyable content** - read_only=True, border=None
- **Background thread for generation** - prevents UI freeze

### API Calls Per Article
- 1x Claude Sonnet for English article (~4000 tokens output)
- 1x Claude Sonnet for Japanese translation (~5000 tokens output)
- Total: ~9000 output tokens + ~2000 input tokens per article

### Files Changed
- `ui/views/comedy_view.py` (new)
- `ui/views/__init__.py` (added ComedyView)
- `ui/app.py` (added to nav and views)
- `ui/components.py` (PreviewBox.set_content update)
- `generators/comedy_article.py` (Japanese translation)
- `cli.py` (comedy command updates)
- `data/voice.yaml` (comedy settings, 1800-2200 words)

---

## Session 3: [Next Session]
**Date**: TBD

### Planned
- Phase 2: Cross-platform publishing
- dev.to API integration
- Hashnode API integration

---

## Architecture Notes

### Data Flow
```
F:\chronos\ENGINEERING_LOG_V4.md
         ↓
    scan_sources()
         ↓
    sections[] (chronological)
         ↓
    generate() → Claude API
         ↓
    EN article + hashtags
         ↓
    _translate_to_japanese() → Claude API
         ↓
    JA article + JA hashtags
         ↓
    Save to output/articles/comedy/
         ↓
    [Future: publish to platforms]
```

### File Structure
```
anvil/
├── generators/
│   └── comedy_article.py    # Main generation logic
├── scheduler/
│   └── article_scheduler.py # 3x/week automation
├── ui/
│   └── views/
│       └── comedy_view.py   # Diary tab UI
├── output/
│   └── articles/
│       └── comedy/
│           ├── *_EN.md      # English versions
│           ├── *_JA.md      # Japanese versions
│           └── .history.json # Used sections
├── data/
│   └── voice.yaml           # Comedy settings + beats
└── config/
    └── api_keys.yaml        # Claude API key
```

### API Usage Estimates
Per article:
- Input: ~2000 tokens (prompt + source)
- Output EN: ~3000 tokens
- Output JA: ~4000 tokens
- Total: ~9000 tokens

Per week (3 articles):
- ~27,000 tokens
- Cost: ~$0.30 (Sonnet pricing)

Per month:
- ~108,000 tokens
- Cost: ~$1.20

---

## Known Issues

1. **First article has no JA version** - Generated before translation was added
2. **Dropdown on_change not working** - Flet 0.80 limitation, using buttons instead
3. **Long generation time** - 30-60 seconds for EN+JA, acceptable but could optimize

---

## Future Optimization Ideas

1. **Parallel translation** - Generate EN and JA simultaneously (2 API calls in parallel)
2. **Streaming response** - Show content as it generates
3. **Caching** - Cache translated hashtags for common terms
4. **Local preview** - Show section content before generating
