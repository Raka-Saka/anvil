# Anvil Diary - Roadmap

## Vision
Transform Anvil Diary into the definitive tool for developer storytelling - turning engineering logs into engaging, cross-platform content with minimal effort.

---

## Phase 1: Foundation Polish (Current)
**Status: In Progress**

### Completed
- [x] Comedy article generator with Basin Method narrative structure
- [x] Japanese translation with localized hashtags
- [x] Chronological diary progression from engineering logs
- [x] Flet desktop UI with dark theme
- [x] Previous articles browser with EN/JA toggle
- [x] Background thread generation (non-blocking UI)
- [x] Auto-save to markdown with frontmatter

### Remaining
- [ ] Fix any remaining UI bugs
- [ ] Add reading time calculation
- [ ] Add copy buttons (title, content, hashtags separately)
- [ ] Export format options (MD, HTML, plain text)

---

## Phase 2: Cross-Platform Publishing
**Target: Enable one-click publishing to multiple platforms**

### M1: Platform Integrations
- [ ] dev.to API integration (REST)
- [ ] Hashnode API integration (GraphQL)
- [ ] LinkedIn API integration
- [ ] Medium API integration (if available, otherwise manual)

### M2: Platform-Specific Formatting
- [ ] Adapt content length per platform
- [ ] Platform-specific hashtag mapping
- [ ] Canonical URL handling (SEO)
- [ ] Cover image requirements per platform

### M3: Publishing UI
- [ ] Platform selection checkboxes
- [ ] Preview per platform
- [ ] Publish button with status feedback
- [ ] Published URLs display

---

## Phase 3: Twitter/X Thread Generator
**Target: Convert long articles to viral thread format**

### M4: Thread Conversion
- [ ] Article → thread algorithm (split by beats/sections)
- [ ] Hook tweet generation (attention-grabbing opener)
- [ ] Code block → screenshot conversion
- [ ] Thread preview UI
- [ ] Character count validation (280 per tweet)

### M5: Thread Publishing
- [ ] Twitter/X API integration
- [ ] Thread scheduling
- [ ] Quote-tweet linking to full article

---

## Phase 4: Visual Content
**Target: Auto-generate cover images and code screenshots**

### M6: Cover Image Generator
- [ ] Template system (ChronOS branding)
- [ ] Title text overlay
- [ ] Dynamic backgrounds based on topic
- [ ] Export sizes for each platform
- [ ] Local generation (Pillow) - no API costs

### M7: Code Screenshots
- [ ] Syntax-highlighted code images
- [ ] Carbon.sh style or local generation
- [ ] Consistent theme matching articles

---

## Phase 5: Audio Content
**Target: Podcast-style audio versions**

### M8: Text-to-Speech
- [ ] Edge-TTS integration (free, high quality)
- [ ] Japanese TTS support
- [ ] Audio file management
- [ ] Embed player in exported HTML

### M9: Podcast Feed
- [ ] RSS feed generation for audio
- [ ] Podcast metadata (title, description, duration)
- [ ] iTunes-compatible feed format

---

## Phase 6: Analytics & Insights
**Target: Track content performance across platforms**

### M10: Data Collection
- [ ] dev.to stats API
- [ ] Hashnode analytics API
- [ ] LinkedIn post metrics
- [ ] Local storage of historical data

### M11: Analytics Dashboard
- [ ] Views/reads per article
- [ ] Engagement (likes, comments, shares)
- [ ] Best performing articles
- [ ] Platform comparison
- [ ] Best time to post analysis

### M12: Readability Metrics
- [ ] Flesch-Kincaid readability score
- [ ] Technical complexity indicator
- [ ] Humor density (beats per 1000 words)
- [ ] Estimated reading time

---

## Phase 7: Content Calendar
**Target: Visual planning and scheduling**

### M13: Calendar UI
- [ ] Month view with articles
- [ ] Drag-and-drop scheduling
- [ ] 3x/week rhythm visualization
- [ ] Gap detection and warnings

### M14: Scheduling System
- [ ] Queue system for future posts
- [ ] Platform-specific optimal times
- [ ] Batch generation for the week

---

## Phase 8: Content Repurposing
**Target: One article → multiple formats**

### M15: Format Conversions
- [ ] Full article → LinkedIn post (300 words)
- [ ] Full article → Newsletter snippet
- [ ] Full article → Slide deck outline
- [ ] Key quotes extraction

### M16: Repurposing UI
- [ ] Side-by-side format preview
- [ ] Edit each format independently
- [ ] Bulk export

---

## Phase 9: Advanced Features
**Target: Polish and differentiation**

### M17: Title A/B Testing
- [ ] Generate 3-5 title variants
- [ ] Track performance per title style
- [ ] Learn preferences over time

### M18: RSS Feed
- [ ] Generate RSS/Atom feed
- [ ] Include all published articles
- [ ] Auto-update on new content

### M19: Voice Learning
- [ ] Analyze user's existing content
- [ ] Refine voice.yaml automatically
- [ ] Style consistency scoring

---

## Priority Matrix

| Phase | Impact | Effort | Priority |
|-------|--------|--------|----------|
| P2: Cross-Platform | High | Medium | 1 |
| P3: Twitter Threads | High | Low | 2 |
| P4: Cover Images | Medium | Low | 3 |
| P5: Audio/TTS | Medium | Low | 4 |
| P6: Analytics | Medium | High | 5 |
| P7: Calendar | Low | Medium | 6 |
| P8: Repurposing | Medium | Medium | 7 |
| P9: Advanced | Low | High | 8 |

---

## Success Metrics

1. **Time to publish**: < 5 minutes from generation to live on 3+ platforms
2. **Consistency**: 3 articles/week maintained for 3+ months
3. **Engagement**: 100+ views average per article within first week
4. **Reach**: Present on 4+ platforms (dev.to, Hashnode, LinkedIn, Twitter)
5. **Cost**: < $20/month total for all external services
