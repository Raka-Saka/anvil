"""
Basin Method - 3-Layer Generation System

ORANGE (Ceiling): What we CANNOT say - constraints, fraud prevention
BLACK (Spine): Structure and organization
RED (Flesh): Voice and human touch

This is YOUR methodology, now used to generate YOUR professional content.
"""

from pathlib import Path
from typing import Optional
import re


class OrangeLayer:
    """
    ORANGE - The Ceiling Layer
    
    Defines constraints. What we absolutely cannot say.
    This is the fraud prevention layer.
    """
    
    def __init__(self, profile: dict, voice: dict):
        self.profile = profile
        self.voice = voice
    
    def get_constraints(self) -> dict:
        """Get all constraints for generation."""
        return {
            'forbidden_phrases': self.voice['language']['forbidden'],
            'max_years': self._calculate_max_years(),
            'evidenced_skills': self._get_evidenced_skills(),
            'must_acknowledge_ai': self.profile['working_style']['type'] == 'ai_collaborative_builder',
        }
    
    def validate(self, text: str) -> list[dict]:
        """
        Validate text against constraints.
        Returns list of violations.
        """
        violations = []
        
        # Check forbidden phrases
        for phrase in self.voice['language']['forbidden']:
            if phrase.lower() in text.lower():
                violations.append({
                    'type': 'forbidden_phrase',
                    'found': phrase,
                    'severity': 'medium',
                    'suggestion': self._get_alternative(phrase),
                })
        
        # Check for unsubstantiated expertise claims
        expertise_patterns = [
            r'expert in (\w+)',
            r'extensive experience (?:in |with )?(\w+)',
            r'deep knowledge of (\w+)',
            r'mastery of (\w+)',
        ]
        
        for pattern in expertise_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if not self._has_evidence(match):
                    violations.append({
                        'type': 'unsubstantiated_claim',
                        'found': f"expertise claim about '{match}'",
                        'severity': 'high',
                        'suggestion': f"Replace with evidence: what did you build with {match}?",
                    })
        
        violations += self.language_inflation(text)

        # Check for missing AI acknowledgment in technical claims
        if self._claims_technical_implementation(text) and not self._acknowledges_ai(text):
            violations.append({
                'type': 'missing_ai_acknowledgment',
                'found': 'Technical implementation claims without AI context',
                'severity': 'medium',
                'suggestion': 'Add "AI-assisted" or explain your role (design, debug, ship)',
            })
        
        return violations
    
    # A level claim is fine when the sentence is about what the job asks ("the posting asks for N2").
    _ASKS = re.compile(r"ask|require|request|want|need|demand|exig|requis|demand|求め|必要|以上|条件|pide|requer|verlang",
                       re.IGNORECASE)
    _JP_HIGH = [r"JLPT\s*N[123]\b", r"\bN[123]\b", r"日本語能力試験\s*[123]級", r"business[- ]level japanese",
                r"(fluent|advanced|business) japanese", r"japanese[^.\n]{0,15}(fluent|advanced|business level)",
                r"japonais (courant|professionnel|avancé|bilingue)", r"ビジネスレベル", r"日本語[^。\n]{0,8}(流暢|堪能|ネイティブ|上級)",
                r"japonés (fluido|avanzado)"]
    _OTHER = {"german": r"(german|allemand|deutsch|alemán)", "dutch": r"(dutch|néerlandais|nederlands)",
              "italian": r"(italian|italien|italiano)", "portuguese": r"(portuguese|portugais|português)",
              "chinese": r"(chinese|chinois|中国語)", "korean": r"(korean|coréen|韓国語)"}
    _FLUENT = r"(fluent|courant|native|natif|c1|c2|b2|fließend|bilingual|bilingue|business)"

    def language_inflation(self, text: str) -> list[dict]:
        """Language levels stated higher than the profile (Japanese above N4; languages he does not have)."""
        langs = {l["language"].lower(): l["level"] for l in self.profile.get("personal", {}).get("languages", [])}
        out = []
        sentences = re.split(r"(?<=[.!?。\n])", text)
        jp = langs.get("japanese", "")
        jp_n = re.search(r"N([1-5])", jp)
        if jp_n and int(jp_n.group(1)) >= 4:
            for s in sentences:
                if self._ASKS.search(s):
                    continue
                about_jp = re.search(r"japan|japon|日本語|jlpt", s, re.IGNORECASE)
                for p in self._JP_HIGH:
                    if p == self._JP_HIGH[1] and not about_jp:      # "support N2" is a support level
                        continue
                    m = re.search(p, s, re.IGNORECASE)
                    if m and p == "ビジネスレベル":
                        # "英語はビジネスレベル" is about English: only flag when no other language is named just before
                        before = s[max(0, m.start() - 10):m.start()]
                        if re.search(r"(?<!日本)語", before) and "日本語" not in before:
                            continue
                    if m:
                        out.append({"type": "language_inflation", "severity": "high",
                                    "found": f"Japanese level above N{jp_n.group(1)}: '{m.group(0)}' in \"{s.strip()[:80]}\"",
                                    "suggestion": f"His Japanese is: {jp}. Say that, or leave it out."})
                        break
        for name, pat in self._OTHER.items():
            if name in langs:
                continue
            for s in sentences:
                if self._ASKS.search(s):
                    continue
                if re.search(pat + r"[^.\n]{0,20}" + self._FLUENT, s, re.IGNORECASE) or \
                   re.search(self._FLUENT + r"[^.\n]{0,20}" + pat, s, re.IGNORECASE):
                    out.append({"type": "language_inflation", "severity": "high",
                                "found": f"Claims {name}, which is not in his profile: \"{s.strip()[:80]}\"",
                                "suggestion": "Remove it."})
                    break
        return out

    def _calculate_max_years(self) -> dict:
        """Calculate maximum provable years for each skill area."""
        # Based on work history
        years = {}
        for exp in self.profile.get('experience', []):
            period = exp.get('period', {})
            # Calculate duration and map to keywords
            # Simplified - real implementation would parse dates
        return years
    
    def _get_evidenced_skills(self) -> list[str]:
        """Get list of skills that have evidence."""
        skills = []
        for s in self.profile['skills'].get('direct_experience', []):
            if 'evidence' in s:
                skills.append(s['skill'].lower())
        for s in self.profile['skills'].get('ai_assisted_building', []):
            if 'evidence' in s:
                skills.append(s['skill'].lower())
        return skills
    
    def _has_evidence(self, skill: str) -> bool:
        """Check if we have evidence for a skill."""
        skill_lower = skill.lower()
        return any(skill_lower in s for s in self._get_evidenced_skills())
    
    def _get_alternative(self, forbidden: str) -> str:
        """Get alternative phrasing for forbidden phrase."""
        alternatives = self.voice['language'].get('prefer', {})
        
        for original, replacement in alternatives.items():
            if forbidden.lower() in original.lower():
                return replacement
        
        return f"Remove '{forbidden}' - show evidence instead"
    
    def _claims_technical_implementation(self, text: str) -> bool:
        """Check if text claims technical implementation."""
        implementation_words = [
            'developed', 'built', 'created', 'implemented', 
            'wrote', 'coded', 'programmed', 'engineered'
        ]
        text_lower = text.lower()
        return any(word in text_lower for word in implementation_words)
    
    def _acknowledges_ai(self, text: str) -> bool:
        """Check if text acknowledges AI assistance."""
        ai_phrases = [
            'ai-assisted', 'ai assisted', 'with ai', 'using ai',
            'claude', 'with assistance', 'ai tool'
        ]
        text_lower = text.lower()
        return any(phrase in text_lower for phrase in ai_phrases)


class BlackLayer:
    """
    BLACK - The Spine Layer
    
    Defines structure. The skeleton that holds everything together.
    """
    
    def __init__(self, voice: dict):
        self.voice = voice
    
    def get_structure(self, doc_type: str) -> dict:
        """Get structure for document type."""
        
        structures = {
            'cv': {
                'sections': [
                    {'name': 'header', 'required': True},
                    {'name': 'summary', 'required': True, 'max_sentences': 3},
                    {'name': 'skills', 'required': True, 'split': ['direct', 'ai_assisted']},
                    {'name': 'projects', 'required': True, 'max_items': 4},
                    {'name': 'experience', 'required': True},
                    {'name': 'education', 'required': False},
                ],
                'order': 'projects_before_experience',
            },
            
            'cover_letter': {
                'sections': [
                    {'name': 'opening', 'sentences': [1, 2], 'style': 'direct'},
                    {'name': 'body', 'paragraphs': [2, 3], 'must_have_evidence': True},
                    {'name': 'gaps', 'sentences': [0, 2], 'optional': True},
                    {'name': 'closing', 'sentences': 1, 'style': 'simple'},
                ],
            },
            
            'article': {
                'sections': [
                    {'name': 'hook', 'sentences': [1, 2]},
                    {'name': 'problem', 'paragraphs': 1},
                    {'name': 'approach', 'paragraphs': [1, 2]},
                    {'name': 'result', 'paragraphs': [2, 3]},
                    {'name': 'learning', 'paragraphs': 1},
                ],
                'no_call_to_action': True,
                'word_count': self.voice['articles']['length_words'],
            },
        }
        
        return structures.get(doc_type, {})
    
    def validate_structure(self, text: str, doc_type: str) -> list[str]:
        """Check if text follows required structure."""
        issues = []
        structure = self.get_structure(doc_type)
        
        # Basic validation - real implementation would parse sections
        if doc_type == 'cv':
            if 'summary' in structure:
                # Check summary length
                pass
        
        return issues


class RedLayer:
    """
    RED - The Flesh Layer
    
    Adds voice. Makes it sound like YOU.
    """
    
    def __init__(self, voice: dict):
        self.voice = voice
    
    def apply_voice(self, text: str) -> str:
        """Transform text to match user's voice."""
        
        # Apply preferred phrasings
        for original, replacement in self.voice['language'].get('prefer', {}).items():
            # Simple replacement - real implementation would be smarter
            text = re.sub(
                re.escape(original), 
                replacement, 
                text, 
                flags=re.IGNORECASE
            )
        
        # Remove forbidden phrases that slipped through
        for phrase in self.voice['language']['forbidden']:
            if phrase == '!':
                # Handle exclamation marks specially
                text = text.replace('!', '.')
            else:
                # Just flag these, don't auto-remove
                pass
        
        return text
    
    def get_opening(self, doc_type: str, context: dict = None) -> str:
        """Get appropriate opening for document type."""
        context = context or {}
        
        if doc_type == 'article':
            import random
            openings = self.voice['articles']['openings']
            template = random.choice(openings)
            
            # Fill in template
            return template.format(**context) if context else template
        
        elif doc_type == 'cover_letter':
            role = context.get('role', 'this position')
            return f"I saw your posting for {role}."
        
        return ""
    
    def get_closing(self, doc_type: str) -> str:
        """Get appropriate closing."""
        if doc_type == 'cover_letter':
            return "Happy to talk more about any of this."
        return ""


class BasinMethod:
    """
    Complete Basin Method implementation.
    
    Combines ORANGE (constraints), BLACK (structure), RED (voice).
    """
    
    def __init__(self, profile: dict, voice: dict):
        self.profile = profile
        self.voice = voice
        
        self.orange = OrangeLayer(profile, voice)
        self.black = BlackLayer(voice)
        self.red = RedLayer(voice)
    
    def generate(self, doc_type: str, content: str, context: dict = None) -> dict:
        """
        Generate content using Basin Method.
        
        Returns dict with:
            - content: The generated text
            - violations: Any constraint violations
            - structure_issues: Any structure issues
        """
        context = context or {}
        
        # 1. Check constraints (ORANGE)
        violations = self.orange.validate(content)
        
        # 2. Check structure (BLACK)
        structure_issues = self.black.validate_structure(content, doc_type)
        
        # 3. Apply voice (RED)
        content = self.red.apply_voice(content)
        
        return {
            'content': content,
            'violations': violations,
            'structure_issues': structure_issues,
            'doc_type': doc_type,
        }
    
    def get_generation_prompt(self, doc_type: str, context: dict) -> str:
        """Get prompt for Claude API generation."""
        
        constraints = self.orange.get_constraints()
        structure = self.black.get_structure(doc_type)
        
        forbidden_list = '\n'.join(f"- {p}" for p in constraints['forbidden_phrases'][:10])
        
        prompt = f"""Generate a {doc_type} following these rules:

CONSTRAINTS (NEVER violate):
{forbidden_list}
- Every claim must have evidence
- Acknowledge AI assistance for technical work
- No exclamation marks

STRUCTURE:
{structure}

VOICE:
- Introvert: quiet confidence, not salesy
- Short sentences (max 20 words)
- Active voice
- First person
- Technical accuracy over impression

CONTEXT:
{context}

Generate the {doc_type} now. Be direct, honest, evidence-based."""
        
        return prompt
