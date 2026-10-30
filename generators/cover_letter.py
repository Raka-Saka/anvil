"""
Cover Letter Generator - Research-based, honest cover letters that get interviews.

Based on research synthesis:
- 94% of hiring managers say cover letters influence decisions
- 36% decide in first 30 seconds - hook is critical
- Problem-Solution format dominates
- 250-400 words max (66% prefer half-page or less)
- Quantified achievements get attention
- Basin Method fraud prevention
"""

from pathlib import Path
from typing import Optional
import json
import logging
import re
from collections import Counter

try:
    import anthropic
except ImportError:
    anthropic = None

logger = logging.getLogger(__name__)

from core.profile_manager import ProfileManager
from core.llm import get_client
from basin.method import BasinMethod


# Job category definitions with role-specific hooks
JOB_CATEGORIES = {
    'technical': {
        'keywords': ['developer', 'engineer', 'programming', 'software', 'code', 'api',
                     'backend', 'frontend', 'devops', 'infrastructure', 'architect'],
        'use_ai_framing': True,
        'highlight': ['ai_assisted_building', 'technical_projects'],
        'hook': "I built a custom OS kernel with AI assistance; it boots on real hardware.",
    },
    'management': {
        'keywords': ['manager', 'director', 'lead', 'head of', 'vp', 'chief',
                     'supervisor', 'team lead', 'coordinator'],
        'use_ai_framing': False,
        'highlight': ['leadership', 'team_management', 'process_improvement'],
        'hook': "At EA, I led a Tier 3 escalation team based in England, Germany and France, and owned its SLA and KPI targets.",
    },
    'research': {
        'keywords': ['analyst', 'research', 'insights', 'data', 'market', 'strategy',
                     'intelligence', 'survey', 'study', 'analysis'],
        'use_ai_framing': False,
        'highlight': ['analytical', 'research', 'data_analysis', 'economics'],
        'hook': "I cut production losses from 35% to 5% at a food factory with Lean 6 Sigma, and built the reporting app that made it measurable.",
    },
    'qa': {
        'keywords': ['qa', 'quality', 'testing', 'test', 'assurance', 'validation'],
        'use_ai_framing': False,
        'highlight': ['qa_experience', 'methodology', 'process'],
        'hook': "I QA tested The Elder Scrolls Online through alpha and beta: functionality, regression and smoke testing.",
    },
    'operations': {
        'keywords': ['operations', 'process', 'logistics', 'supply chain', 'production',
                     'manufacturing', 'optimization', 'efficiency'],
        'use_ai_framing': False,
        'highlight': ['process_improvement', 'operations', 'efficiency'],
        'hook': "I cut production losses from 35% to 5% at a food factory with Lean 6 Sigma.",
    },
    'customer': {
        'keywords': ['customer', 'client', 'support', 'success', 'service', 'relations',
                     'account', 'stakeholder'],
        'use_ai_framing': False,
        'highlight': ['customer_service', 'communication', 'international'],
        'hook': "I had 100% customer satisfaction as a Tier 1 advisor at EA, then led its Tier 3 escalation team.",
    },
}

# Shape of the Claude job analysis
ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "required_skills": {"type": "array", "items": {"type": "string"}},
        "matches": {"type": "array", "items": {
            "type": "object",
            "properties": {"requirement": {"type": "string"}, "skill": {"type": "string"},
                           "evidence": {"type": "string"}},
            "required": ["requirement", "skill", "evidence"], "additionalProperties": False}},
        "gaps": {"type": "array", "items": {"type": "string"}},
        "match_score": {"type": "integer"},
        "challenge": {"type": "string"},
    },
    "required": ["required_skills", "matches", "gaps", "match_score", "challenge"],
    "additionalProperties": False,
}

# Expanded skill keywords for matching
SKILL_KEYWORDS = {
    'market research': ['market research', 'research', 'insights', 'analysis', 'survey', 'study'],
    'data analysis': ['data analysis', 'analytics', 'data', 'quantitative', 'qualitative'],
    'economics': ['economics', 'economic', 'financial', 'business analysis'],
    'strategy': ['strategy', 'strategic', 'planning', 'business development'],
    'project management': ['project management', 'pm', 'roadmap', 'milestone', 'planning', 'coordination'],
    'team leadership': ['leadership', 'lead', 'manage', 'team', 'supervise', 'mentor'],
    'stakeholder management': ['stakeholder', 'cross-functional', 'collaboration', 'partner'],
    'process improvement': ['process', 'optimization', 'efficiency', 'lean', 'improvement'],
    'operations': ['operations', 'operational', 'production', 'manufacturing'],
    'qa': ['qa', 'quality assurance', 'testing', 'test', 'bug', 'validation'],
    'customer service': ['customer', 'client', 'support', 'service', 'account'],
    'international': ['international', 'global', 'multilingual', 'cross-cultural', 'european'],
    'languages': ['language', 'bilingual', 'french', 'english', 'japanese', 'multilingual'],
    'technical': ['technical', 'engineering', 'developer', 'software'],
    'python': ['python', 'scripting'],
}


class CoverLetterGenerator:
    """Generate cover letters using Problem-Solution format with Basin Method."""

    # Word count limits based on research
    MIN_WORDS = 200
    MAX_WORDS = 350
    OPTIMAL_WORDS = 275

    def __init__(self,
                 profile_path: Optional[Path] = None,
                 voice_path: Optional[Path] = None,
                 api_key: Optional[str] = None):

        self.pm = ProfileManager(profile_path, voice_path)
        self.profile = self.pm.load()
        self.voice = self.pm.load_voice()
        self.basin = BasinMethod(self.profile, self.voice)

        self.client = get_client(api_key)  # Claude Code subscription, or API key

    def detect_job_category(self, job_description: str) -> str:
        """Detect the category of job from description."""
        jd_lower = job_description.lower()

        scores = {}
        for category, config in JOB_CATEGORIES.items():
            score = sum(1 for kw in config['keywords'] if kw in jd_lower)
            scores[category] = score

        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else 'management'

    def extract_keywords(self, job_description: str, top_n: int = 10) -> list[str]:
        """
        Extract key phrases from job description.

        Research says: Find words that repeat 3+ times, weave in naturally.
        """
        # Clean and tokenize
        jd_lower = job_description.lower()
        # Remove common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                      'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be',
                      'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                      'would', 'could', 'should', 'may', 'might', 'must', 'shall', 'can',
                      'this', 'that', 'these', 'those', 'it', 'its', 'they', 'them',
                      'their', 'we', 'our', 'you', 'your', 'who', 'which', 'what',
                      'where', 'when', 'why', 'how', 'all', 'each', 'every', 'both',
                      'few', 'more', 'most', 'other', 'some', 'such', 'no', 'not',
                      'only', 'same', 'so', 'than', 'too', 'very', 'just', 'also',
                      'now', 'here', 'there', 'then', 'if', 'else', 'about', 'into',
                      'through', 'during', 'before', 'after', 'above', 'below', 'between',
                      'under', 'again', 'further', 'once', 'any', 'up', 'down', 'out',
                      'off', 'over', 'own', 'work', 'working', 'ability', 'strong'}

        # Extract words
        words = re.findall(r'\b[a-z]{3,}\b', jd_lower)
        words = [w for w in words if w not in stop_words]

        # Count frequency
        counter = Counter(words)

        # Get top keywords (appearing 2+ times)
        keywords = [word for word, count in counter.most_common(top_n * 2) if count >= 2]

        return keywords[:top_n]

    def analyze_job(self, job_description: str) -> dict:
        """
        Analyze job description and match against profile.

        Returns:
            dict with requirements, matches, gaps, match_score, job_category, keywords
        """
        job_category = self.detect_job_category(job_description)
        keywords = self.extract_keywords(job_description)

        if self.client:
            try:
                result = self._ai_analysis(job_description, job_category)
                result['keywords'] = keywords
                return result
            except Exception as e:
                logger.warning(f"AI analysis failed, using basic: {e}")

        result = self._basic_analysis(job_description, job_category)
        result['keywords'] = keywords
        return result

    def _ai_analysis(self, job_description: str, job_category: str) -> dict:
        """Use Claude to analyze job requirements and match profile."""

        profile_summary = self._build_profile_summary()

        prompt = f"""Analyze this job posting and match it against the candidate profile.

JOB POSTING:
{job_description}

CANDIDATE PROFILE:
{profile_summary}

Return a JSON object with:
1. "required_skills": list of key skills/requirements from the job
2. "matches": list of {{"requirement": "...", "skill": "...", "evidence": "..."}} for skills the candidate has
3. "gaps": list of requirements the candidate doesn't clearly meet
4. "match_score": percentage 0-100 based on how well candidate fits
5. "challenge": one sentence describing what the hiring company needs (their problem)

Be honest - only include matches where there's real evidence. Don't stretch the truth.
Return ONLY valid JSON, no commentary."""

        try:
            from core.llm import ask_json
            result = ask_json(prompt, system="You compare job postings with a candidate profile. Be honest.",
                              schema=ANALYSIS_SCHEMA)
            result['job_category'] = job_category
            result['requirements'] = {'required': result.get('required_skills', []), 'nice_to_have': []}
            return result
        except Exception as e:
            logger.warning(f"AI analysis failed, using keyword analysis: {e}")
            return self._basic_analysis(job_description, job_category)

    def _build_profile_summary(self) -> str:
        """Build profile summary for AI analysis."""
        lines = []

        lines.append("DIRECT EXPERIENCE:")
        for skill in self.pm.get_skills_direct():
            evidence = skill.get('evidence', '')
            lines.append(f"- {skill['skill']}: {evidence}")

        # Full record: every role and achievement, languages, location, visa, projects
        from analyzers.triage import profile_summary
        lines.append("\nPROFILE:")
        lines.append(profile_summary())

        lines.append("\nEDUCATION:")
        for edu in self.pm.get_education():
            lines.append(f"- {edu.get('english', edu.get('degree', ''))} - {edu.get('institution', '')}")

        return '\n'.join(lines)

    def generate(self,
                 job_description: str,
                 company_name: str = None,
                 role_name: str = None,
                 hiring_manager: str = None,
                 use_ai: bool = True) -> dict:
        """
        Generate cover letter using Problem-Solution format.

        Args:
            job_description: The job posting text
            company_name: Company name (optional)
            role_name: Role title (optional)
            hiring_manager: Hiring manager name for personalization (optional)
            use_ai: Use Claude for enhanced generation

        Returns:
            dict with content, analysis, word_count, violations
        """
        analysis = self.analyze_job(job_description)

        # Warn if low match score
        match_score = analysis.get('match_score', 0)
        if match_score < 50:
            analysis['low_match_warning'] = True
            logger.warning(f"Low match score ({match_score}%) - consider if this role is a good fit")

        if use_ai and self.client:
            try:
                return self._generate_with_claude(analysis, company_name, role_name,
                                                   hiring_manager, job_description)
            except Exception as e:
                logger.warning(f"Claude generation failed, using template: {e}")

        return self._generate_template(analysis, company_name, role_name,
                                        hiring_manager, job_description)

    def _get_hook(self, job_category: str, analysis: dict) -> str:
        """
        Generate attention-grabbing opening hook.

        Research: 36% of managers decide in 30 seconds. Lead with achievement.
        Always use category-specific hooks which are complete, polished sentences.
        """
        # Use category-specific hook (these are complete sentences with quantified achievements)
        return JOB_CATEGORIES.get(job_category, {}).get(
            'hook',
            "I have worked in five countries, and I finish what I start."
        )

    def _generate_with_claude(self, analysis: dict, company_name: str, role_name: str,
                               hiring_manager: str, job_description: str) -> dict:
        """Generate cover letter using Claude with Problem-Solution format."""

        role = role_name or "this position"
        company = company_name or "your company"
        job_category = analysis.get('job_category', 'management')
        use_ai_framing = JOB_CATEGORIES.get(job_category, {}).get('use_ai_framing', False)
        hook = self._get_hook(job_category, analysis)

        # Build greeting
        if hiring_manager:
            greeting = f"Dear {hiring_manager},"
        else:
            greeting = ""  # Skip generic greetings per research

        profile_summary = self._build_profile_summary()
        matches_text = '\n'.join([f"- {m['skill']}: {m.get('evidence', '')}" for m in analysis.get('matches', [])[:5]])
        gaps_text = ', '.join(analysis.get('gaps', [])[:3]) if analysis.get('gaps') else 'None identified'
        keywords = ', '.join(analysis.get('keywords', [])[:8])
        challenge = analysis.get('challenge', f"finding someone who can deliver results in {role}")

        prompt = f"""Write a cover letter using the PROBLEM-SOLUTION format. The candidate is an introvert who prefers honest, direct communication.

JOB: {role} at {company}
JOB CATEGORY: {job_category}
THEIR CHALLENGE: {challenge}

JOB DESCRIPTION:
{job_description[:1500]}

CANDIDATE PROFILE:
{profile_summary}

MATCHED SKILLS:
{matches_text}

GAPS:
{gaps_text}

KEY PHRASES TO WEAVE IN (naturally, 2-3 times): {keywords}

STRUCTURE TO FOLLOW:
1. {"GREETING: " + greeting if greeting else "NO GREETING - start directly with hook"}
2. HOOK (1-2 sentences): Start with this achievement: "{hook}"
3. THEIR CHALLENGE (2-3 sentences): Show you understand what they need
4. YOUR SOLUTION (3-4 sentences): 2-3 evidence points that directly address the challenge
5. FIT (1-2 sentences): Why this role/company specifically
6. CLOSE: "I welcome the opportunity to discuss how my experience can contribute to [specific goal]." then sign with "Florent Herisson"

CRITICAL RULES - FOLLOW EXACTLY:
- WORD COUNT: 250-300 words MAXIMUM. Count carefully.
- Sound like an introvert: quiet confidence, no enthusiasm, no excitement
- NEVER use: "passionate", "excited", "thrilled", "proven track record", "extensive experience", "expert", "I am writing to apply"
- No exclamation marks
- Use first person, active voice
- Every claim must have evidence from the profile
- Be honest about gaps - acknowledge briefly if significant
{"- Mention that you use AI tools for implementation, but bring problem definition and project management skills" if use_ai_framing else "- Do NOT mention AI, OS projects, or technical hobbies - focus on business/management experience"}
- Include 2-3 of the key phrases naturally

Return ONLY the cover letter text, no commentary or word count."""

        response = self.client.messages.create(
            model="claude-opus-5-5",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.content[0].text.strip()

        # Count words
        word_count = len(content.split())

        # Run through Basin Method for violation checking
        result = self.basin.generate('cover_letter', content)
        result['analysis'] = analysis
        result['word_count'] = word_count
        result['within_limit'] = self.MIN_WORDS <= word_count <= self.MAX_WORDS

        # Add warning if over limit
        if word_count > self.MAX_WORDS:
            result['violations'].append({
                'type': 'word_count',
                'severity': 'warning',
                'found': f'{word_count} words',
                'suggestion': f'Reduce to {self.MAX_WORDS} words or fewer'
            })

        return result

    def _generate_template(self, analysis: dict, company_name: str, role_name: str,
                           hiring_manager: str, job_description: str) -> dict:
        """Generate from template using Problem-Solution format."""

        role = role_name or "this position"
        company = company_name or "your company"
        job_category = analysis.get('job_category', 'management')
        use_ai_framing = JOB_CATEGORIES.get(job_category, {}).get('use_ai_framing', False)
        hook = self._get_hook(job_category, analysis)

        lines = []

        # Greeting (only if hiring manager provided)
        if hiring_manager:
            lines.append(f"Dear {hiring_manager},")
            lines.append("")

        # HOOK - Lead with achievement (expanded)
        lines.append(hook)
        hook_follow = self._get_hook_followup(job_category)
        lines.append(hook_follow)
        lines.append("")

        # THEIR CHALLENGE - Show understanding (expanded)
        challenge_text = self._get_challenge_text(job_category, job_description)
        lines.append(challenge_text)
        challenge_expand = self._get_challenge_expansion(job_category)
        lines.append(challenge_expand)
        lines.append("")

        # YOUR SOLUTION - Evidence points (with intro)
        solution_intro = self._get_solution_intro(job_category)
        lines.append(solution_intro)
        lines.append("")
        self._add_category_evidence(lines, job_category, analysis)
        lines.append("")

        # Evidence summary - ties bullets together
        evidence_summary = self._get_evidence_summary(job_category)
        lines.append(evidence_summary)
        lines.append("")

        # Add matched skills with evidence (top 2) if different from category evidence
        # Skip skills that would duplicate content already in category evidence
        skip_keywords = {
            'qa': ['qa', 'test', 'quality', 'jira'],
            'research': ['research', 'analysis', 'data', 'sorbonne'],
            'management': ['team', 'lead', 'management', 'sla'],
            'customer': ['customer', 'csat', 'support', 'service'],
            'operations': ['process', 'production', 'efficiency', 'transformation'],
            'technical': ['os', 'kernel', 'ml', 'model', 'technical'],
        }
        category_skip = skip_keywords.get(job_category, [])

        added_matches = 0
        for match in analysis['matches'][:3]:
            if match.get('evidence') and added_matches < 2:
                skill_lower = match['skill'].lower()
                evidence_lower = match['evidence'].lower()
                # Skip if already covered in category evidence or hook
                if not any(kw in skill_lower or kw in evidence_lower for kw in category_skip):
                    lines.append(f"My {match['skill'].lower()} background includes: {match['evidence']}")
                    added_matches += 1

        if added_matches > 0:
            lines.append("")

        # Additional context based on category (ensures minimum content)
        additional_context = self._get_additional_context(job_category)
        if additional_context:
            lines.append(additional_context)
            lines.append("")

        # FIT - Why this role specifically (expanded)
        if company_name and company_name != "your company":
            lines.append(f"The {role} role at {company} aligns with my background in {self._get_fit_phrase(job_category)}.")
            lines.append("I've worked in France, Canada, Ireland, the UK and Japan, including 8 years in Japanese-only workplaces.")
        else:
            lines.append(f"This {role} role aligns with my background in {self._get_fit_phrase(job_category)}.")
            lines.append("I've worked in five countries, including 8 years in Japanese-only workplaces.")
        lines.append("")

        # International asset if relevant
        if self._job_mentions_international(job_description):
            lines.append("I'm native in French, fluent in English, with basic Japanese (JLPT N4 level), and have direct experience managing teams across UK, Germany, and France.")
            lines.append("")

        # AI framing for technical roles
        if use_ai_framing:
            lines.append("I use AI tools for implementation, which allows me to move quickly from concept to working prototype. What I bring is problem definition, systematic debugging, and project management skills that ensure complete delivery.")
            lines.append("")

        # Gaps acknowledgment if significant (only if major gap)
        if analysis.get('gaps') and len(analysis['gaps']) > 1:
            gap = analysis['gaps'][0]
            lines.append(f"My {gap} experience is limited. I learned the food-production side at Ribbon Foods the same way: on the job, then measured.")
            lines.append("")

        # Practical details (visa status - important per profile)
        lines.append("I'm an EU citizen with a Japan spouse visa, available for remote work or relocation without sponsorship requirements.")
        lines.append("")

        # CLOSE - Value + CTA (expanded)
        close_line = self._get_close_line(job_category, company)
        lines.append(close_line)
        lines.append("")
        lines.append(self.pm.get_name())

        content = '\n'.join(lines)
        word_count = len(content.split())

        result = self.basin.generate('cover_letter', content)
        result['analysis'] = analysis
        result['word_count'] = word_count
        result['within_limit'] = self.MIN_WORDS <= word_count <= self.MAX_WORDS

        return result

    def _get_hook_followup(self, job_category: str) -> str:
        """Get follow-up sentence for hook to add context."""
        followups = {
            'research': "This role combined systematic methodology with practical business outcomes.",
            'management': "This experience taught me how to coordinate diverse teams toward shared objectives.",
            'customer': "Building that track record required systematic attention to each interaction.",
            'operations': "This transformation came from methodical process analysis, not luck.",
            'qa': "That experience built my foundation in systematic testing and defect prevention.",
            'technical': "Each milestone required clear problem definition and iterative refinement.",
        }
        return followups.get(job_category, "This experience shaped how I approach complex challenges.")

    def _get_challenge_expansion(self, job_category: str) -> str:
        """Expand on the challenge with specifics."""
        expansions = {
            'research': "The challenge is finding someone who can handle both the analytical rigor and the stakeholder communication that turns data into decisions.",
            'management': "Finding someone who combines hands-on execution experience with the communication skills to align different teams is the hard part.",
            'customer': "The difficulty is maintaining quality at scale while adapting to different customer contexts and expectations.",
            'operations': "The real test is sustaining those improvements while managing the day-to-day realities of production.",
            'qa': "What separates good QA from great is the ability to think systematically about where defects hide and how to find them before users do.",
            'technical': "The challenge is balancing technical depth with the project management needed to actually ship.",
        }
        return expansions.get(job_category, "The key is combining practical experience with systematic thinking.")

    def _get_solution_intro(self, job_category: str) -> str:
        """Get introduction for solution section."""
        intros = {
            'research': "My background addresses these needs directly:",
            'management': "Here's what I bring to solve that challenge:",
            'customer': "My track record demonstrates I can deliver:",
            'operations': "I've solved similar challenges before:",
            'qa': "My QA experience maps directly to what you need:",
            'technical': "Here's evidence that I can deliver:",
        }
        return intros.get(job_category, "Here's what I bring:")

    def _get_close_line(self, job_category: str, company: str) -> str:
        """Get closing line with specific value prop."""
        closes = {
            'research': f"I welcome the opportunity to discuss how my research methodology and cross-cultural experience can strengthen {company}'s market insights.",
            'management': f"I would be glad to discuss how my team leadership and process improvement background can contribute to {company}'s objectives.",
            'customer': f"I welcome the opportunity to discuss how my customer success track record can support {company}'s client relationships.",
            'operations': f"I would be glad to discuss how my process optimization experience can drive efficiency improvements at {company}.",
            'qa': f"I welcome the opportunity to discuss how my QA methodology can strengthen {company}'s quality processes.",
            'technical': f"I would be glad to discuss how my technical project management approach can contribute to {company}'s product development.",
        }
        return closes.get(job_category, f"I welcome the opportunity to discuss how my experience can contribute to {company}'s goals.")

    def _get_evidence_summary(self, job_category: str) -> str:
        """Get summary sentence that ties evidence together."""
        summaries = {
            'research': "The common thread is turning systematic analysis into practical business outcomes that stakeholders can act on.",
            'management': "Each of these roles required coordinating people with different priorities toward shared goals while maintaining measurable standards.",
            'customer': "These results came from treating each customer interaction as an opportunity to solve real problems, not just close tickets.",
            'operations': "The pattern across these experiences is identifying bottlenecks through data, then implementing solutions that the team can sustain.",
            'qa': "What connects these experiences is a systematic approach to quality: define the criteria, test against them, and document everything.",
            'technical': "Each project required breaking complex problems into manageable pieces, tracking progress against milestones, and iterating based on what worked.",
        }
        return summaries.get(job_category, "These experiences demonstrate consistent delivery across different contexts and challenges.")

    def _get_additional_context(self, job_category: str) -> str:
        """Get additional context sentence to ensure minimum content."""
        contexts = {
            'research': "",  # Research usually has international section
            'management': "Beyond metrics, I focus on building team capability - people who understand the 'why' behind processes perform better when situations change.",
            'customer': "My approach to customer success is understanding the underlying business need, not just resolving the immediate issue. This leads to fewer repeat contacts and stronger relationships.",
            'operations': "I document every improvement so the team can maintain gains without my direct involvement. Sustainable improvement requires systems, not heroes. At Eishin I made a colour-coded photo guide for the operators; they still use it.",
            'qa': "I build test documentation that helps the team, not just the audit. When testers understand what they're checking and why, they find better bugs.",
            'technical': "",  # Technical usually has AI framing section
        }
        return contexts.get(job_category, "")

    def _get_challenge_text(self, job_category: str, job_description: str) -> str:
        """Generate challenge understanding text based on category."""
        challenges = {
            'research': "You need someone who can turn market research into actionable insights that drive business decisions.",
            'management': "You need a leader who can coordinate teams, manage stakeholders, and deliver results on schedule.",
            'customer': "You need someone who can maintain high satisfaction while handling complex customer relationships.",
            'operations': "You need someone who can optimize processes and drive measurable efficiency improvements.",
            'qa': "You need systematic quality assurance that catches issues before they reach production.",
            'technical': "You need someone who can ship working software while managing technical complexity.",
        }
        return challenges.get(job_category, "You need someone who can deliver measurable results.")

    def _add_category_evidence(self, lines: list, job_category: str, analysis: dict):
        """Add category-specific evidence points."""
        evidence = {
            'research': [
                "- Sorbonne research training in critical analysis and methodology",
                "- Cut production losses from 35% to 5% at a Japanese food factory",
                "- Worked in France, Canada, Ireland, the UK and Japan",
            ],
            'management': [
                "- Led a Tier 3 escalation team at EA based in England, Germany and France",
                "- Owned SLA and KPI performance from the creation of the mission",
                "- Cut production losses from 35% to 5% with Lean 6 Sigma methods",
            ],
            'customer': [
                "- 100% CSAT rating from day one at EA",
                "- Tier 3 escalation for Star Wars: The Old Republic, with daily bug hand-off to BioWare Austin via JIRA",
                "- Customer support in French and English for the French market",
            ],
            'operations': [
                "- Cut production losses from 35% to 5% at a food factory",
                "- Built a Flutter app replacing a 24-hour production reporting cycle with live data",
                "- Led complete analog-to-digital business transformation at a wine company",
            ],
            'qa': [
                "- QA testing for Elder Scrolls Online and SWTOR through Alpha and Beta phases",
                "- Functionality, regression and BAT/smoke testing in alpha and beta",
                "- JIRA-based defect tracking and nightly reports coordinating with development teams",
            ],
            'technical': [
                "- Building a custom OS kernel (ChronOS): 19 of 34 milestones done, preemptive multitasking, boots on real hardware",
                "- Built with AI assistance; I designed it, directed the work and debugged it",
                "- Trained 60+ specialized LoRA models on local hardware (RTX 2080)",
            ],
        }
        for line in evidence.get(job_category, evidence['management'])[:3]:
            lines.append(line)

    def _get_fit_phrase(self, job_category: str) -> str:
        """Get role-fit phrase for closing."""
        phrases = {
            'research': "research methodology and data-driven decision making",
            'management': "team leadership and process improvement",
            'customer': "customer success and relationship management",
            'operations': "operational efficiency and process optimization",
            'qa': "quality assurance and systematic testing",
            'technical': "technical project management and shipping products",
        }
        return phrases.get(job_category, "delivering results")

    def _job_mentions_international(self, job_description: str) -> bool:
        """Check if job mentions international/global aspects."""
        jd_lower = job_description.lower()
        international_keywords = ['global', 'international', 'european', 'multinational',
                                  'cross-cultural', 'multilingual', 'worldwide']
        return any(kw in jd_lower for kw in international_keywords)

    def _basic_analysis(self, job_description: str, job_category: str) -> dict:
        """Basic keyword matching without AI."""

        jd_lower = job_description.lower()

        found = []
        for skill, patterns in SKILL_KEYWORDS.items():
            if any(p in jd_lower for p in patterns):
                found.append(skill)

        matches = self._find_matches({'required': found, 'nice_to_have': []}, job_category)
        gaps = self._find_gaps_smart(found, matches, job_category)

        # Generate challenge based on category
        challenge = self._get_challenge_text(job_category, job_description)

        return {
            'requirements': {'required': found, 'nice_to_have': []},
            'matches': matches,
            'gaps': gaps,
            'match_score': len(matches) / max(len(found), 1) * 100,
            'job_category': job_category,
            'challenge': challenge,
        }

    def _find_matches(self, requirements: dict, job_category: str) -> list[dict]:
        """Find matches between requirements and profile."""

        matches = []
        seen_skills = set()
        all_required = requirements.get('required', []) + requirements.get('nice_to_have', [])

        skill_map = self._build_skill_map()

        for req in all_required:
            req_lower = req.lower()

            for skill_name, skill_info in skill_map.items():
                if self._skill_matches(skill_name, req_lower):
                    if skill_info.get('ai_assisted') and job_category != 'technical':
                        continue

                    if skill_info['display_name'] in seen_skills:
                        continue
                    seen_skills.add(skill_info['display_name'])

                    matches.append({
                        'requirement': req,
                        'skill': skill_info['display_name'],
                        'evidence': skill_info.get('evidence', ''),
                        'type': 'ai_assisted' if skill_info.get('ai_assisted') else 'direct',
                    })
                    break

        return matches

    def _build_skill_map(self) -> dict:
        """Build comprehensive skill map from profile."""
        skill_map = {}

        for skill in self.pm.get_skills_direct():
            skill_map[skill['skill'].lower()] = {
                'display_name': skill['skill'],
                'evidence': skill.get('evidence', ''),
                'ai_assisted': False,
            }

        for skill in self.pm.get_skills_ai_assisted():
            skill_map[skill['skill'].lower()] = {
                'display_name': skill['skill'],
                'evidence': skill.get('evidence', ''),
                'ai_assisted': True,
            }

        # Add implicit skills from experience
        skill_map['international'] = {
            'display_name': 'International Experience',
            'evidence': 'Led a team across England, Germany, France; worked in 5 countries',
            'ai_assisted': False,
        }
        skill_map['research methodology'] = {
            'display_name': 'Research Methodology',
            'evidence': 'Sorbonne training in research and critical analysis',
            'ai_assisted': False,
        }
        skill_map['data analysis'] = {
            'display_name': 'Data Analysis',
            'evidence': 'Google Data Analytics certificate; production loss analysis (35% to 5%)',
            'ai_assisted': False,
        }
        skill_map['market research'] = {
            'display_name': 'Research & Analysis',
            'evidence': 'Sorbonne research training; ran field survey logistics at Audirep',
            'ai_assisted': False,
        }
        skill_map['stakeholder management'] = {
            'display_name': 'Stakeholder Management',
            'evidence': 'Cross-functional coordination at EA, vendor management at Audirep',
            'ai_assisted': False,
        }
        skill_map['languages'] = {
            'display_name': 'Multilingual',
            'evidence': 'French (native), English (fluent), Japanese (basic, N4)',
            'ai_assisted': False,
        }

        return skill_map

    def _find_gaps_smart(self, found_requirements: list, matches: list, job_category: str) -> list[str]:
        """Find gaps, being smart about what to report."""

        matched_reqs = {m['requirement'].lower() for m in matches}
        gaps = []

        for req in found_requirements:
            if req.lower() not in matched_reqs:
                if job_category != 'technical' and req in ['python', 'technical']:
                    continue
                gaps.append(req)

        return gaps

    def _skill_matches(self, skill: str, requirement: str) -> bool:
        """Check if a skill matches a requirement."""

        skill_lower = skill.lower()

        if skill_lower in requirement or requirement in skill_lower:
            return True

        for key, synonyms in SKILL_KEYWORDS.items():
            if key in skill_lower or skill_lower in key:
                if any(s in requirement for s in synonyms):
                    return True

        return False


if __name__ == "__main__":
    # Test with pharma job
    generator = CoverLetterGenerator()

    pharma_job = """
    Position Summary
    We are looking for a strategic Customer Insights Analyst to join a global European
    pharmaceutical company as a key business partner. In this role, you will work with
    the therapeutic area and analytics teams to turn market research into actionable
    strategies that drive growth and profit.

    Responsibilities
    - Design and execute high-quality market research
    - Analyze market data to identify unmet customer needs
    - Partner with various internal teams, such as marketing and legal
    - Manage multiple research projects and external vendors
    - Follow all strict legal regulations and company ethical standards

    Qualifications
    - Proven experience in planning and analyzing both qualitative and quantitative market research
    - Strong understanding of the pharmaceutical industry, healthcare policies
    """

    result = generator.generate(pharma_job, "Pharma Corp", "Customer Insights Analyst")

    print(f"JOB CATEGORY: {result['analysis']['job_category']}")
    print(f"MATCH SCORE: {result['analysis']['match_score']:.0f}%")
    print(f"WORD COUNT: {result['word_count']} (limit: {generator.MAX_WORDS})")
    print(f"WITHIN LIMIT: {result['within_limit']}")
    print(f"KEYWORDS: {result['analysis'].get('keywords', [])[:5]}")
    print(f"MATCHES: {[m['skill'] for m in result['analysis']['matches']]}")
    print(f"GAPS: {result['analysis']['gaps']}")
    print()
    print("COVER LETTER:")
    print(result['content'])
