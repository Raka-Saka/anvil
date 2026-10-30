# Anvil Diary - External Services & Costs

## Overview
Total estimated monthly cost: **$5-15/month** for full functionality

---

## Currently Used

### 1. Claude API (Anthropic)
**Purpose**: Article generation + Japanese translation
**Status**: Active

| Model | Input | Output | Use Case |
|-------|-------|--------|----------|
| Claude Sonnet | $3/M tokens | $15/M tokens | Article generation |

**Monthly Estimate** (12 articles):
- Input: 24,000 tokens × $3/M = $0.07
- Output: 108,000 tokens × $15/M = $1.62
- **Total: ~$1.70/month**

**Setup**: Add API key to `config/api_keys.yaml`
```yaml
anthropic:
  api_key: "sk-ant-..."
```

---

## Phase 2: Cross-Platform Publishing

### 2. dev.to API
**Purpose**: Publish articles to dev.to
**Cost**: FREE
**Rate Limit**: 30 requests/minute

**Setup**:
1. Go to https://dev.to/settings/extensions
2. Generate API key
3. Add to config:
```yaml
devto:
  api_key: "your-key"
```

**Endpoint**: `POST https://dev.to/api/articles`

---

### 3. Hashnode API
**Purpose**: Publish articles to Hashnode blog
**Cost**: FREE
**Type**: GraphQL

**Setup**:
1. Go to https://hashnode.com/settings/developer
2. Generate Personal Access Token
3. Add to config:
```yaml
hashnode:
  token: "your-token"
  publication_id: "your-pub-id"
```

**Endpoint**: `https://gql.hashnode.com`

---

### 4. LinkedIn API
**Purpose**: Publish articles/posts to LinkedIn
**Cost**: FREE (with limitations)
**Complexity**: HIGH (OAuth2 required)

**Options**:

**Option A: Official API (Complex)**
- Requires LinkedIn app approval
- OAuth2 flow
- Limited to text posts (no native articles)

**Option B: Manual + Clipboard**
- Generate LinkedIn-formatted content
- One-click copy
- User pastes manually
- **Recommended for simplicity**

**Option C: Third-party service**
- Buffer/Hootsuite ($15-75/month)
- Not recommended (expensive)

---

### 5. Medium API
**Purpose**: Publish to Medium
**Cost**: FREE
**Status**: Limited functionality

**Note**: Medium's API is deprecated/limited. Recommend:
- Manual posting with one-click copy
- Or use their import from URL feature

---

## Phase 3: Twitter/X

### 6. Twitter/X API
**Purpose**: Post threads
**Cost**: $100/month (Basic) or FREE (limited)

**Pricing Tiers**:
| Tier | Cost | Tweets/month | Read |
|------|------|--------------|------|
| Free | $0 | 1,500 | 0 |
| Basic | $100/mo | 3,000 | 10,000 |
| Pro | $5,000/mo | 300,000 | 1,000,000 |

**Recommendation**:
- Start with **manual posting** (copy thread to clipboard)
- Consider Basic only if volume justifies cost
- **Alternative**: Use Typefully ($12/mo) for thread scheduling

**Budget Option - Typefully**:
- $12/month
- Thread composer
- Scheduling
- Analytics
- Much cheaper than Twitter API direct

---

## Phase 4: Visual Content

### 7. Cover Image Generation
**Purpose**: Article cover images
**Cost**: FREE (local generation)

**Approach**: Use Pillow (Python)
- No API needed
- Template-based generation
- Text overlay on backgrounds
- Consistent branding

**Dependencies**:
```bash
pip install Pillow
```

**Alternative (if quality needed)**:
- DALL-E API: $0.04-0.08 per image
- 12 images/month = ~$0.50-1.00

---

### 8. Code Screenshots
**Purpose**: Pretty code images for threads
**Cost**: FREE

**Options**:
- **carbon.now.sh** - Free, manual
- **Local generation** with Pygments + Pillow - Free, automated
- **ray.so** - Free, manual

**Recommendation**: Local generation with Pygments

---

## Phase 5: Audio/TTS

### 9. Edge-TTS
**Purpose**: Text-to-speech for articles
**Cost**: FREE
**Quality**: High (Microsoft voices)

**Voices**:
- English: `en-US-GuyNeural`, `en-GB-RyanNeural`
- Japanese: `ja-JP-NanamiNeural`, `ja-JP-KeitaNeural`

**Setup**:
```bash
pip install edge-tts
```

**Usage**:
```python
import edge_tts
communicate = edge_tts.Communicate(text, voice)
await communicate.save("output.mp3")
```

**Alternative (higher quality)**:
- ElevenLabs: $5/month for 30,000 characters
- ~10 articles worth
- Better voice quality but not necessary

---

## Phase 6: Analytics

### 10. Analytics APIs
**Purpose**: Track article performance
**Cost**: FREE (platform APIs)

| Platform | API | Cost |
|----------|-----|------|
| dev.to | REST | Free |
| Hashnode | GraphQL | Free |
| LinkedIn | Limited | Free |

**Local Storage**: SQLite database for historical data

---

## Cost Summary

### Minimal Setup (Current)
| Service | Monthly Cost |
|---------|--------------|
| Claude API | $1.70 |
| **Total** | **$1.70** |

### Full Setup (All Phases)
| Service | Monthly Cost |
|---------|--------------|
| Claude API | $1.70 |
| dev.to | Free |
| Hashnode | Free |
| LinkedIn | Free (manual) |
| Twitter threads | Free (manual) or $12 (Typefully) |
| Cover images | Free (Pillow) |
| TTS | Free (Edge-TTS) |
| Analytics | Free |
| **Total (minimal)** | **$1.70** |
| **Total (with Typefully)** | **$13.70** |

### Optional Quality Upgrades
| Service | Cost | Benefit |
|---------|------|---------|
| DALL-E images | +$1/mo | Better cover art |
| ElevenLabs TTS | +$5/mo | Premium voice quality |
| Twitter Basic API | +$100/mo | Direct posting (skip) |

---

## Recommended Stack

### Budget Tier ($2/month)
- Claude API (required)
- Manual posting to all platforms
- Local image generation
- Edge-TTS for audio
- Copy-paste workflow

### Comfort Tier ($15/month)
- Claude API
- Typefully for Twitter threads
- Everything else same as budget
- Semi-automated workflow

### Premium Tier ($25/month)
- Claude API
- Typefully
- ElevenLabs TTS
- DALL-E for special images
- High quality output

---

## API Keys Needed

```yaml
# config/api_keys.yaml

# Required
anthropic:
  api_key: "sk-ant-..."

# Phase 2 (free)
devto:
  api_key: "..."

hashnode:
  token: "..."
  publication_id: "..."

# Phase 3 (optional, if using Typefully)
typefully:
  api_key: "..."

# Phase 4 (optional, if using DALL-E)
openai:
  api_key: "sk-..."

# Phase 5 (optional, if using ElevenLabs)
elevenlabs:
  api_key: "..."
```

---

## Setup Checklist

### Now
- [x] Claude API key

### Phase 2
- [ ] dev.to API key
- [ ] Hashnode token + publication ID
- [ ] LinkedIn: decide manual vs API

### Phase 3
- [ ] Decide: manual threads vs Typefully
- [ ] If Typefully: subscribe + get API key

### Phase 4
- [ ] Install Pillow: `pip install Pillow`
- [ ] Create cover image templates

### Phase 5
- [ ] Install edge-tts: `pip install edge-tts`
- [ ] Test voice options

### Phase 6
- [ ] Set up SQLite for analytics storage
- [ ] Implement API polling for stats

---

## Risk Assessment

| Service | Risk | Mitigation |
|---------|------|------------|
| Claude API | Price increase | Budget buffer, could switch to local LLM |
| dev.to | API changes | Simple REST, easy to update |
| Twitter | API restrictions | Manual posting fallback |
| Edge-TTS | Service discontinuation | Multiple TTS fallbacks exist |

---

## Vendor Lock-in Analysis

**Low lock-in**:
- All content stored locally as Markdown
- Platform APIs are standard REST/GraphQL
- Can switch LLM providers (prompts are portable)
- Audio/images generated locally

**Recommendation**: Keep all content in local Markdown as source of truth. Platform publishing is just distribution.
