"""
CV Generator - Create honest, evidence-based CVs optimized for interviews.

Based on research synthesis:
- 6-second F-pattern scan optimization
- ATS keyword optimization (97.8% of Fortune 500 use ATS)
- Quantified achievements (2.5x more interview invitations)
- Role-based tailoring
- Basin Method fraud prevention
"""

from pathlib import Path
from typing import Optional
import logging
import re

try:
    import anthropic
except ImportError:
    anthropic = None

from core.profile_manager import ProfileManager
from core.llm import get_client
from basin.method import BasinMethod

logger = logging.getLogger(__name__)


# Role title mappings for ATS title matching
ROLE_TITLES = {
    'qa_lead': 'QA Lead / Quality Assurance Manager',
    'technical_pm': 'Technical Project Manager',
    'process_improvement': 'Process Improvement Specialist / Operations Manager',
    'general': 'Technical Project Manager / QA Specialist',
    'ai_dev': 'AI/ML Project Lead',
}

# Role-specific summary evidence
ROLE_EVIDENCE = {
    'qa_lead': {
        'hook': "QA and escalation lead. Worked in five countries.",
        'evidence': "Led Tier 3 escalation at EA. Alpha/Beta tested ESO. Cut production losses 35% to 5% in a Japanese factory.",
        'proof': "OS kernel boots on real hardware.",
    },
    'technical_pm': {
        'hook': "Technical PM. Worked in France, Canada, Ireland, the UK and Japan.",
        'evidence': "Led a team across England, Germany, France at EA. Digitised a paper-based business end to end.",
        'proof': "Building a custom OS kernel with AI assistance; it boots on real hardware.",
    },
    'process_improvement': {
        'hook': "Process improvement specialist. Nine years in Japanese industry.",
        'evidence': "Cut production losses 35% to 5%. Lean Six Sigma White and Yellow Belt. ISO audit experience.",
        'proof': "Built the Flutter reporting app that made the loss reduction measurable.",
    },
    'general': {
        'hook': "Worked in France, Canada, Ireland, the UK and Japan.",
        'evidence': "Led a cross-border escalation team. Cut factory losses 35% to 5%. Builds software with AI assistance.",
        'proof': "I build things and ship them.",
    },
}


class CVGenerator:
    """Generate CVs from profile data using Basin Method with ATS optimization."""

    def __init__(self,
                 profile_path: Optional[Path] = None,
                 voice_path: Optional[Path] = None,
                 api_key: Optional[str] = None):

        self.pm = ProfileManager(profile_path, voice_path)
        self.profile = self.pm.load()
        self.voice = self.pm.load_voice()
        self.basin = BasinMethod(self.profile, self.voice)

        self.client = get_client(api_key)  # Claude Code subscription, or API key

    def generate(self,
                 target_role: str = "general",
                 include_projects: list[str] = None,
                 emphasis: str = "balanced",
                 use_ai: bool = True,
                 job_title: Optional[str] = None) -> dict:
        """
        Generate an interview-optimized CV.

        Args:
            target_role: Type of role (technical_pm, qa_lead, general, etc.)
            include_projects: List of project names to include (None = auto-select)
            emphasis: problem_solving, project_management, technical, balanced
            use_ai: Use Claude API for enhanced generation (if key available)
            job_title: Exact job title from posting (for ATS matching)

        Returns:
            dict with 'content', 'sections', 'warnings', 'ats_score'
        """

        # Build sections with role-based optimization
        sections = {
            'header': self._build_header(target_role, job_title),
            'core_competencies': self._build_core_competencies(target_role),
            'summary': self._build_summary(target_role, emphasis),
            'skills': self._build_skills(target_role),
            'projects': self._build_projects(include_projects, target_role),
            'experience': self._build_experience(target_role),
            'education': self._build_education(),
        }

        # Render to text with F-pattern optimization
        content = self._render(sections)

        # Use Claude for enhanced generation if available
        if use_ai and self.client:
            try:
                content = self._enhance_with_claude(content, target_role)
            except Exception as e:
                logger.warning(f"Claude enhancement failed, using template: {e}")

        # ATS keyword match on the final text
        ats_score = self._calculate_ats_score(content, target_role)

        # Apply Basin Method
        result = self.basin.generate('cv', content)
        result['sections'] = sections
        result['ats_score'] = ats_score

        return result

    def _build_header(self, target_role: str, job_title: Optional[str] = None) -> dict:
        """
        Build header section optimized for F-pattern (6-second scan).

        Top third must answer:
        1. What do you want to do? (title)
        2. What makes you qualified? (tagline)
        3. Is it compelling? (hook)
        """
        p = self.profile['personal']

        # Title matching: use exact job title if provided, else role-based
        if job_title:
            title = job_title
        else:
            title = ROLE_TITLES.get(target_role, ROLE_TITLES['general'])

        # Tagline with biggest evidence hook
        evidence = ROLE_EVIDENCE.get(target_role, ROLE_EVIDENCE['general'])
        tagline = f"{evidence['hook']} {evidence['proof']}"

        return {
            'name': p['name'],
            'title': title,
            'tagline': tagline,
            'email': p['email'],
            'phone': p.get('phone', ''),
            'location': p['location'],
            'website': p.get('website', ''),
            'github': p.get('github', ''),
        }

    def _build_core_competencies(self, target_role: str) -> list[str]:
        """
        Build ATS-optimized Core Competencies section.

        This keyword block captures ATS scanners and provides
        quick visual scan for recruiters.
        """
        return self.pm.get_core_competencies(target_role)

    def _build_summary(self, target_role: str, emphasis: str) -> str:
        """
        Build 3-sentence summary optimized for F-pattern top third.

        Structure:
        1. Who you are + international scope (hook)
        2. Biggest evidence (proof)
        3. Logistics (visa, availability)
        """
        evidence = ROLE_EVIDENCE.get(target_role, ROLE_EVIDENCE['general'])

        # Build based on emphasis
        if emphasis == "project_management":
            main_evidence = "Led international teams at EA (UK, Germany, France advisors). Currently managing 34-milestone OS project."
        elif emphasis == "problem_solving":
            main_evidence = "Cut production losses 35% to 5% in a Japanese factory. Live-bug triage at EA and Zenimax."
        elif emphasis == "technical":
            main_evidence = "Custom OS kernel with preemptive multitasking. QA at Zenimax/EA. Process optimization at Japanese electroplating facility."
        else:  # balanced - use role-specific evidence
            main_evidence = evidence['evidence']

        # Closing with logistics (important for international roles)
        closing = "EU citizen with Japan spouse visa. No sponsorship needed."

        return f"{evidence['hook']} {main_evidence} {closing}"

    def _build_skills(self, target_role: str) -> dict:
        """Build skills section with role-based prioritization and quantification."""

        direct, ai_assisted = self.pm.get_skills_for_role(target_role)
        tools = self.pm.get_tools()

        def format_skill(s: dict) -> str:
            """Format skill with quantified evidence."""
            parts = [s['skill']]
            if 'years' in s:
                parts.append(f"({s['years']}y)")
            if 'evidence' in s:
                # Quantify the evidence
                evidence = self._quantify_text(s['evidence'])
                parts.append(f"- {evidence}")
            return ' '.join(parts)

        return {
            'direct_experience': [format_skill(s) for s in direct],
            'ai_assisted_building': [format_skill(s) for s in ai_assisted],
            'tools': tools,
        }

    def _build_projects(self, include_names: list[str] = None, target_role: str = 'general') -> list[dict]:
        """Build projects section with quantified evidence."""

        if include_names:
            projects = [
                self.pm.get_project_by_name(name)
                for name in include_names
            ]
            projects = [p for p in projects if p]
        else:
            projects = self.pm.get_projects(limit=4)

        result = []
        for p in projects:
            # Quantify evidence
            evidence = [self._quantify_text(e) for e in p.get('evidence', [])[:3]]

            entry = {
                'name': p['name'],
                'description': p.get('description', ''),
                'status': p.get('status', ''),
                'evidence': evidence,
                'repo': p.get('repo', ''),
                'ai_assisted': p.get('ai_assisted', False),
            }
            result.append(entry)

        return result

    def _build_experience(self, target_role: str) -> list[dict]:
        """Build experience section with quantified achievements."""

        experience = self.pm.get_experience_for_role(target_role)

        result = []
        for exp in experience:
            if not exp.get('include_in_cv', True):
                continue

            # Quantify achievements
            achievements = []
            for i, ach in enumerate(exp.get('achievements', [])):
                quantified = self.pm.get_quantified_achievement(exp, i)
                if not quantified:
                    quantified = self._quantify_text(ach)
                achievements.append(quantified)

            entry = {
                'company': exp['company'],
                'role': exp['role'],
                'location': exp['location'],
                'period': exp['period'],
                'achievements': achievements,
                'highlight': exp.get('highlight', False),
            }
            result.append(entry)

        return result

    def _build_education(self) -> list[dict]:
        """Build education section."""
        return self.profile.get('education', [])

    def _quantify_text(self, text: str) -> str:
        """Return text unchanged. Numbers come from profile.yaml only, never added here."""
        return text

    def _calculate_ats_score(self, content: str, target_role: str) -> dict:
        """
        Calculate ATS keyword match score.

        Research shows 65-75% match rate is optimal.
        """
        keywords = self.pm.get_core_competencies(target_role)
        content_lower = content.lower()

        matched = []
        missing = []

        for kw in keywords:
            if kw.lower() in content_lower:
                matched.append(kw)
            else:
                missing.append(kw)

        score = len(matched) / len(keywords) * 100 if keywords else 0

        return {
            'score': round(score, 1),
            'matched': matched,
            'missing': missing,
            'recommendation': 'Good' if score >= 65 else 'Add more keywords',
        }

    def _render(self, sections: dict) -> str:
        """
        Render sections to plain text with F-pattern optimization.

        Top third (6-second zone):
        - Name, Title
        - Tagline (biggest evidence)
        - Core Competencies (keyword block)
        - Summary
        """
        lines = []

        # === F-PATTERN TOP THIRD (6-second zone) ===

        # Header
        h = sections['header']
        lines.append(h['name'].upper())
        lines.append(h['title'])
        lines.append(h['tagline'])
        lines.append('')
        lines.append(f"{h['email']} | {h['location']}")
        if h['github']:
            lines.append(h['github'])
        lines.append('')

        # Core Competencies (ATS keyword block)
        lines.append('CORE COMPETENCIES')
        lines.append('-' * 40)
        competencies = sections['core_competencies']
        # Format as 2-column layout for scanning
        for i in range(0, len(competencies), 3):
            row = competencies[i:i+3]
            lines.append('  ' + ' | '.join(row))
        lines.append('')

        # Summary
        lines.append('SUMMARY')
        lines.append('-' * 40)
        lines.append(sections['summary'])
        lines.append('')

        # === EVIDENCE ZONE (middle) ===

        # Skills (condensed)
        lines.append('SKILLS')
        lines.append('-' * 40)

        lines.append('Direct Experience:')
        for skill in sections['skills']['direct_experience'][:5]:  # Top 5 most relevant
            lines.append(f"  • {skill}")
        lines.append('')

        lines.append('AI-Assisted Building:')
        for skill in sections['skills']['ai_assisted_building']:
            lines.append(f"  • {skill}")
        lines.append('')

        # Projects (with quantified evidence)
        lines.append('PROJECTS')
        lines.append('-' * 40)
        for project in sections['projects']:
            ai_tag = " [AI-assisted]" if project['ai_assisted'] else ""
            lines.append(f"{project['name']}{ai_tag}")
            lines.append(f"  {project['description']}")
            for ev in project['evidence']:
                lines.append(f"  → {ev}")  # Arrow for visual scanning
            if project['repo']:
                lines.append(f"  {project['repo']}")
            lines.append('')

        # Experience (with quantified achievements)
        lines.append('EXPERIENCE')
        lines.append('-' * 40)
        for exp in sections['experience']:
            period = exp['period']
            period_str = f"{period.get('start', '')} - {period.get('end', 'present')}"

            # Highlight format for key roles
            if exp.get('highlight'):
                lines.append(f"★ {exp['role']} | {exp['company']}")
            else:
                lines.append(f"{exp['role']} | {exp['company']}")
            lines.append(f"{exp['location']} | {period_str}")

            for achievement in exp['achievements'][:4]:  # Max 4 per role
                lines.append(f"  → {achievement}")
            lines.append('')

        # === FOUNDATION (bottom) ===

        # Education (minimal)
        if sections['education']:
            lines.append('EDUCATION')
            lines.append('-' * 40)
            for edu in sections['education'][:2]:  # Max 2 entries
                lines.append(f"{edu['degree']} - {edu['institution']}")
                lines.append(f"{edu.get('location', '')} | {edu.get('period', '')}")
            lines.append('')

        return '\n'.join(lines)

    def _enhance_with_claude(self, content: str, target_role: str) -> str:
        """Enhance CV content using Claude API."""

        prompt = f"""Improve this CV for a {target_role} position. Return ONLY the improved CV text.

CURRENT CV:
{content}

CRITICAL RULES - FOLLOW EXACTLY:
- Keep all facts exactly as stated (dates, numbers, company names)
- Make language more active and concise
- Do NOT add buzzwords, superlatives, or marketing speak
- Do NOT use words like "passionate", "excited", "expert", "proven track record"
- Do NOT claim expertise - only state what was built
- Keep "AI-assisted" labels exactly as shown
- Maximum 20 words per sentence
- No exclamation marks
- Sound like a competent professional, not a salesperson
- Preserve the honest, direct tone
- Keep all quantified metrics (numbers, percentages)

Return the improved CV text only, no commentary."""

        response = self.client.messages.create(
            model="claude-opus-5-5",
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text


def generate_cv(target_role: str = "general",
                projects: list[str] = None,
                emphasis: str = "balanced",
                job_title: Optional[str] = None) -> str:
    """Convenience function to generate CV."""

    generator = CVGenerator()
    result = generator.generate(
        target_role=target_role,
        include_projects=projects,
        emphasis=emphasis,
        job_title=job_title
    )

    # Show ATS score
    ats = result.get('ats_score', {})
    if ats:
        print(f"\nATS SCORE: {ats.get('score', 0)}%")
        if ats.get('missing'):
            print(f"Missing keywords: {', '.join(ats['missing'][:5])}")
        print()

    if result['violations']:
        print("WARNINGS:")
        for v in result['violations']:
            print(f"  [{v['severity']}] {v['type']}: {v['found']}")
            print(f"           Suggestion: {v['suggestion']}")
        print()

    return result['content']


if __name__ == "__main__":
    # Test with different roles
    print("=" * 60)
    print("GENERAL CV")
    print("=" * 60)
    cv = generate_cv()
    print(cv[:2000])

    print("\n" + "=" * 60)
    print("QA LEAD CV")
    print("=" * 60)
    cv = generate_cv(target_role="qa_lead")
    print(cv[:2000])
