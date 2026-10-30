"""
Job Analyzer - Fetch and analyze job postings, match against profile.

Features:
- Fetch job posting from URL
- Extract requirements and keywords
- Match against user profile
- Calculate fit score
- Identify strengths and gaps
"""

import logging
import re
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Optional imports
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

from core.profile_manager import ProfileManager


@dataclass
class JobPosting:
    """Parsed job posting data."""
    url: str
    title: str = ""
    company: str = ""
    location: str = ""
    description: str = ""
    requirements: list = field(default_factory=list)
    nice_to_have: list = field(default_factory=list)
    keywords: list = field(default_factory=list)
    salary: str = ""
    job_type: str = ""  # remote, hybrid, onsite
    raw_text: str = ""


@dataclass
class MatchResult:
    """Job match analysis result."""
    score: float  # 0-100
    strengths: list  # What the candidate has
    gaps: list  # What's missing
    keywords_matched: list
    keywords_missing: list
    recommendation: str  # "Strong match", "Worth applying", "Stretch role", "Poor fit"
    job: JobPosting = None


class JobAnalyzer:
    """Analyze job postings and match against profile."""

    # Keywords that indicate requirements vs nice-to-have
    REQUIRED_INDICATORS = [
        'required', 'must have', 'essential', 'mandatory', 'need to have',
        'minimum', 'at least', 'years of experience'
    ]
    OPTIONAL_INDICATORS = [
        'nice to have', 'preferred', 'bonus', 'plus', 'ideally', 'desirable',
        'advantageous', 'a plus'
    ]

    # Common job type indicators
    REMOTE_KEYWORDS = ['remote', 'work from home', 'wfh', 'distributed', 'anywhere']
    HYBRID_KEYWORDS = ['hybrid', 'flexible', 'partly remote']

    def __init__(self, profile_path: Optional[Path] = None):
        self.pm = ProfileManager(profile_path)
        self.profile = self.pm.load()
        self._build_skill_index()

    def _build_skill_index(self):
        """Build searchable index of profile skills."""
        self.skill_index = {}

        # Direct skills
        for skill in self.pm.get_skills_direct():
            skill_name = skill['skill'].lower()
            self.skill_index[skill_name] = {
                'name': skill['skill'],
                'evidence': skill.get('evidence', ''),
                'years': skill.get('years', 0),
                'type': 'direct'
            }
            # Add aliases
            for alias in self._get_skill_aliases(skill_name):
                self.skill_index[alias] = self.skill_index[skill_name]

        # AI-assisted skills
        for skill in self.pm.get_skills_ai_assisted():
            skill_name = skill['skill'].lower()
            self.skill_index[skill_name] = {
                'name': skill['skill'],
                'evidence': skill.get('evidence', ''),
                'years': 0,
                'type': 'ai_assisted'
            }

        # Implicit skills from experience
        self._add_implicit_skills()

    def _get_skill_aliases(self, skill: str) -> list:
        """Get common aliases for a skill."""
        aliases = {
            'qa game testing': ['qa', 'quality assurance', 'testing', 'game testing', 'qc'],
            'team leadership': ['leadership', 'team lead', 'management', 'supervising'],
            'process improvement': ['process optimization', 'lean', 'continuous improvement', 'efficiency'],
            'customer service': ['customer support', 'client service', 'customer success'],
            'project management': ['pm', 'project lead', 'program management'],
            'jira': ['bug tracking', 'issue tracking', 'atlassian'],
            'python': ['python3', 'scripting'],
            'data analysis': ['analytics', 'data analytics', 'analysis'],
        }
        return aliases.get(skill, [])

    def _add_implicit_skills(self):
        """Add skills implied by experience."""
        implicit = {
            'international experience': {
                'name': 'International Experience',
                'evidence': 'Worked in France, Canada, Ireland, the UK and Japan',
                'years': 0,
                'type': 'direct'
            },
            'multilingual': {
                'name': 'Multilingual',
                'evidence': 'French (native), English (fluent), Japanese (basic, N4)',
                'years': 0,
                'type': 'direct'
            },
            'french': {
                'name': 'French Language',
                'evidence': 'Native speaker',
                'years': 0,
                'type': 'direct'
            },
            'english': {
                'name': 'English Language',
                'evidence': 'Fluent',
                'years': 0,
                'type': 'direct'
            },
            'japanese': {
                'name': 'Japanese Language',
                'evidence': 'Conversational',
                'years': 0,
                'type': 'direct'
            },
            'cross-cultural': {
                'name': 'Cross-cultural Communication',
                'evidence': 'Managed teams across UK, Germany, France',
                'years': 2,
                'type': 'direct'
            },
            'stakeholder management': {
                'name': 'Stakeholder Management',
                'evidence': 'Cross-functional coordination at EA and multiple companies',
                'years': 5,
                'type': 'direct'
            },
            'agile': {
                'name': 'Agile Methodology',
                'evidence': 'Sprint-based QA testing, JIRA workflow management',
                'years': 3,
                'type': 'direct'
            },
            'research': {
                'name': 'Research & Analysis',
                'evidence': 'Sorbonne training; field survey logistics at Audirep',
                'years': 4,
                'type': 'direct'
            },
        }
        self.skill_index.update(implicit)

    def fetch_job(self, url: str) -> Optional[JobPosting]:
        """Fetch and parse a job posting from URL."""
        if not HAS_REQUESTS:
            logger.error("requests not installed. Run: pip install requests")
            return None
        if not HAS_BS4:
            logger.error("beautifulsoup4 not installed. Run: pip install beautifulsoup4")
            return None

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove script and style elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()

            # Extract text
            raw_text = soup.get_text(separator='\n', strip=True)

            # Parse based on domain
            domain = urlparse(url).netloc.lower()
            job = self._parse_generic(url, soup, raw_text)

            # Try domain-specific parsing
            if 'linkedin' in domain:
                job = self._parse_linkedin(url, soup, raw_text) or job
            elif 'indeed' in domain:
                job = self._parse_indeed(url, soup, raw_text) or job
            elif 'glassdoor' in domain:
                job = self._parse_glassdoor(url, soup, raw_text) or job

            return job

        except requests.RequestException as e:
            logger.error(f"Failed to fetch URL: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing job posting: {e}")
            return None

    def _parse_generic(self, url: str, soup: BeautifulSoup, raw_text: str) -> JobPosting:
        """Generic job posting parser."""
        job = JobPosting(url=url, raw_text=raw_text)

        # Try to find title
        title_candidates = soup.find_all(['h1', 'h2'], limit=5)
        for t in title_candidates:
            text = t.get_text(strip=True)
            if len(text) > 5 and len(text) < 100:
                job.title = text
                break

        # Try to find company
        company_patterns = [
            r'(?:at|@)\s+([A-Z][A-Za-z0-9\s&]+?)(?:\s*[-|]|$)',
            r'Company:\s*([^\n]+)',
            r'Employer:\s*([^\n]+)',
        ]
        for pattern in company_patterns:
            match = re.search(pattern, raw_text)
            if match:
                job.company = match.group(1).strip()
                break

        # Extract location
        location_patterns = [
            r'Location:\s*([^\n]+)',
            r'(?:in|at)\s+([\w\s,]+(?:Japan|USA|UK|Germany|France|Remote))',
        ]
        for pattern in location_patterns:
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                job.location = match.group(1).strip()
                break

        # Detect job type (remote/hybrid/onsite)
        text_lower = raw_text.lower()
        if any(kw in text_lower for kw in self.REMOTE_KEYWORDS):
            job.job_type = 'remote'
        elif any(kw in text_lower for kw in self.HYBRID_KEYWORDS):
            job.job_type = 'hybrid'
        else:
            job.job_type = 'onsite'

        # Extract requirements
        job.requirements = self._extract_requirements(raw_text)
        job.nice_to_have = self._extract_nice_to_have(raw_text)
        job.keywords = self._extract_keywords(raw_text)
        job.description = raw_text[:2000]  # First 2000 chars

        return job

    def _parse_linkedin(self, url: str, soup: BeautifulSoup, raw_text: str) -> Optional[JobPosting]:
        """LinkedIn-specific parser."""
        job = JobPosting(url=url, raw_text=raw_text)

        # LinkedIn job titles
        title_elem = soup.find('h1', class_=re.compile('job.*title', re.I))
        if title_elem:
            job.title = title_elem.get_text(strip=True)

        # Company
        company_elem = soup.find('a', class_=re.compile('company', re.I))
        if company_elem:
            job.company = company_elem.get_text(strip=True)

        # Location
        location_elem = soup.find('span', class_=re.compile('location', re.I))
        if location_elem:
            job.location = location_elem.get_text(strip=True)

        job.requirements = self._extract_requirements(raw_text)
        job.nice_to_have = self._extract_nice_to_have(raw_text)
        job.keywords = self._extract_keywords(raw_text)
        job.description = raw_text[:2000]

        return job if job.title else None

    def _parse_indeed(self, url: str, soup: BeautifulSoup, raw_text: str) -> Optional[JobPosting]:
        """Indeed-specific parser."""
        job = JobPosting(url=url, raw_text=raw_text)

        title_elem = soup.find('h1', class_=re.compile('jobTitle', re.I))
        if title_elem:
            job.title = title_elem.get_text(strip=True)

        company_elem = soup.find(attrs={'data-company-name': True})
        if company_elem:
            job.company = company_elem.get_text(strip=True)

        job.requirements = self._extract_requirements(raw_text)
        job.nice_to_have = self._extract_nice_to_have(raw_text)
        job.keywords = self._extract_keywords(raw_text)
        job.description = raw_text[:2000]

        return job if job.title else None

    def _parse_glassdoor(self, url: str, soup: BeautifulSoup, raw_text: str) -> Optional[JobPosting]:
        """Glassdoor-specific parser."""
        # Similar structure to generic
        return self._parse_generic(url, soup, raw_text)

    def _extract_requirements(self, text: str) -> list:
        """Extract required skills/qualifications."""
        requirements = []
        lines = text.split('\n')

        in_requirements_section = False
        for line in lines:
            line_lower = line.lower().strip()

            # Check for section headers
            if any(h in line_lower for h in ['requirement', 'qualification', 'must have', 'what you need']):
                in_requirements_section = True
                continue
            if any(h in line_lower for h in ['nice to have', 'preferred', 'bonus', 'benefits', 'what we offer']):
                in_requirements_section = False
                continue

            # Extract bullet points in requirements section
            if in_requirements_section and line.strip().startswith(('-', '*', '•', '·')):
                clean = line.strip().lstrip('-*•· ')
                if len(clean) > 10:
                    requirements.append(clean)

        return requirements[:15]  # Limit to top 15

    def _extract_nice_to_have(self, text: str) -> list:
        """Extract nice-to-have skills."""
        nice_to_have = []
        lines = text.split('\n')

        in_nice_section = False
        for line in lines:
            line_lower = line.lower().strip()

            if any(h in line_lower for h in ['nice to have', 'preferred', 'bonus', 'plus']):
                in_nice_section = True
                continue
            if any(h in line_lower for h in ['benefits', 'what we offer', 'salary', 'how to apply']):
                in_nice_section = False
                continue

            if in_nice_section and line.strip().startswith(('-', '*', '•', '·')):
                clean = line.strip().lstrip('-*•· ')
                if len(clean) > 10:
                    nice_to_have.append(clean)

        return nice_to_have[:10]

    def _extract_keywords(self, text: str) -> list:
        """Extract important keywords from job posting."""
        # Common skill keywords to look for
        skill_patterns = [
            r'\b(python|java|javascript|typescript|sql|react|node\.?js|aws|azure|gcp)\b',
            r'\b(agile|scrum|kanban|jira|confluence)\b',
            r'\b(qa|testing|automation|selenium|cypress)\b',
            r'\b(project management|product management|pm)\b',
            r'\b(leadership|team lead|management)\b',
            r'\b(data analysis|analytics|bi|tableau|power bi)\b',
            r'\b(machine learning|ml|ai|deep learning)\b',
            r'\b(communication|stakeholder|cross-functional)\b',
            r'\b(remote|hybrid|onsite)\b',
            r'\b(bilingual|multilingual|japanese|french|german)\b',
            r'\b(\d+\+?\s*years?\s*(?:of\s*)?experience)\b',
        ]

        keywords = set()
        text_lower = text.lower()

        for pattern in skill_patterns:
            matches = re.findall(pattern, text_lower)
            keywords.update(matches)

        return list(keywords)

    def analyze(self, job: JobPosting) -> MatchResult:
        """Analyze how well profile matches job posting."""
        if not job:
            return MatchResult(
                score=0,
                strengths=[],
                gaps=[],
                keywords_matched=[],
                keywords_missing=[],
                recommendation="Could not analyze job posting"
            )

        # Combine all job text for matching
        job_text = f"{job.title} {job.description} {' '.join(job.requirements)}".lower()

        # Find matching skills
        matched_skills = []
        matched_keywords = []

        for skill_key, skill_info in self.skill_index.items():
            if skill_key in job_text or any(alias in job_text for alias in self._get_skill_aliases(skill_key)):
                matched_skills.append({
                    'skill': skill_info['name'],
                    'evidence': skill_info['evidence'],
                    'type': skill_info['type']
                })
                matched_keywords.append(skill_key)

        # Find keywords we don't have
        missing_keywords = []
        for kw in job.keywords:
            kw_lower = kw.lower()
            if kw_lower not in self.skill_index and kw_lower not in matched_keywords:
                # Check if it's a common requirement we might have
                if not self._has_equivalent(kw_lower):
                    missing_keywords.append(kw)

        # Calculate score - weighted approach
        # Don't penalize for having many keywords in job posting
        total_requirements = min(len(job.requirements) + len(job.keywords), 15)  # Cap at 15
        if total_requirements == 0:
            total_requirements = 10

        matches = len(matched_skills)
        base_score = min(100, (matches / max(total_requirements, 1)) * 100)

        # Bonus for matching the job title/role type
        title_lower = job.title.lower()
        role_bonus = 0
        if any(r in title_lower for r in ['project manager', 'pm', 'program manager']):
            # Check if we have PM experience
            for exp in self.pm.get_experience():
                if any(r in exp.get('title', '').lower() for r in ['project', 'manager', 'lead']):
                    role_bonus += 25
                    break
        if any(r in title_lower for r in ['qa', 'quality', 'test', 'qc']):
            for exp in self.pm.get_experience():
                if any(r in exp.get('title', '').lower() for r in ['qa', 'quality', 'test']):
                    role_bonus += 25
                    break

        # Bonus for key skill matches
        if any('leadership' in s['skill'].lower() for s in matched_skills):
            role_bonus += 10
        if any('international' in s['skill'].lower() for s in matched_skills):
            role_bonus += 5
        if len(matched_keywords) >= 3:
            role_bonus += 10  # Good keyword overlap

        score = min(100, base_score + role_bonus)

        # Penalize for critical gaps (but less severely)
        critical_gaps = self._identify_critical_gaps(job, matched_keywords)
        score = max(0, score - len(critical_gaps) * 3)

        # Determine recommendation
        if score >= 75:
            recommendation = "Strong match - Apply with confidence"
        elif score >= 60:
            recommendation = "Good match - Worth applying"
        elif score >= 45:
            recommendation = "Stretch role - Apply if interested"
        else:
            recommendation = "Weak match - Consider carefully"

        # Build strengths list (with evidence)
        strengths = []
        for s in matched_skills[:8]:  # Top 8
            if s['type'] == 'direct':
                strengths.append(f"{s['skill']}: {s['evidence']}")
            else:
                strengths.append(f"{s['skill']} (AI-assisted): {s['evidence']}")

        return MatchResult(
            score=score,
            strengths=strengths,
            gaps=critical_gaps,
            keywords_matched=matched_keywords,
            keywords_missing=missing_keywords,
            recommendation=recommendation,
            job=job
        )

    def _has_equivalent(self, keyword: str) -> bool:
        """Check if we have an equivalent skill."""
        equivalents = {
            'degree': True,  # We have education
            'bachelor': True,
            'communication': True,  # Implicit
            'english': True,
            'team player': True,
        }
        return equivalents.get(keyword, False)

    def _identify_critical_gaps(self, job: JobPosting, matched: list) -> list:
        """Identify critical missing requirements."""
        gaps = []
        job_text = f"{job.title} {job.description}".lower()

        # Check for specific technology requirements we don't have
        tech_requirements = ['kubernetes', 'docker', 'terraform', 'ci/cd', 'devops']
        for tech in tech_requirements:
            if tech in job_text and tech not in matched:
                gaps.append(f"No {tech} experience")

        # Check for years of experience requirements
        years_match = re.search(r'(\d+)\+?\s*years?\s*(?:of\s*)?experience', job_text)
        if years_match:
            required_years = int(years_match.group(1))
            if required_years > 10:  # We have lots of experience
                pass  # OK
            # Could add more specific checks here

        # Check for degree requirements
        if 'computer science' in job_text or 'engineering degree' in job_text:
            gaps.append("No CS/Engineering degree (have business degree)")

        return gaps[:5]  # Limit to top 5 gaps

    def analyze_url(self, url: str) -> MatchResult:
        """Convenience method to fetch and analyze a job URL."""
        job = self.fetch_job(url)
        return self.analyze(job)

    def analyze_text(self, job_text: str, title: str = "", company: str = "") -> MatchResult:
        """Analyze job from pasted text instead of URL."""
        job = JobPosting(
            url="",
            title=title,
            company=company,
            description=job_text,
            raw_text=job_text,
            requirements=self._extract_requirements(job_text),
            nice_to_have=self._extract_nice_to_have(job_text),
            keywords=self._extract_keywords(job_text),
        )

        # Detect job type
        text_lower = job_text.lower()
        if any(kw in text_lower for kw in self.REMOTE_KEYWORDS):
            job.job_type = 'remote'
        elif any(kw in text_lower for kw in self.HYBRID_KEYWORDS):
            job.job_type = 'hybrid'
        else:
            job.job_type = 'onsite'

        return self.analyze(job)


def analyze_job_url(url: str) -> MatchResult:
    """Convenience function to analyze a job URL."""
    analyzer = JobAnalyzer()
    return analyzer.analyze_url(url)
