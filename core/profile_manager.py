"""
Profile Manager - Load and validate user profile data.
"""

from pathlib import Path
from typing import Optional
import yaml

from core.store import read_yaml

class ProfileManager:
    """Manages loading and validation of user profile."""
    
    def __init__(self, profile_path: Optional[Path] = None, voice_path: Optional[Path] = None):
        self.data_dir = Path(__file__).parent.parent / "data"
        self.profile_path = profile_path or self.data_dir / "profile.yaml"
        self.voice_path = voice_path or self.data_dir / "voice.yaml"
        
        self._profile = None
        self._voice = None
    
    def load(self) -> dict:
        """Load profile from YAML file."""
        if self._profile is None:
            self._profile = read_yaml(self.profile_path)
        return self._profile
    
    def load_voice(self) -> dict:
        """Load voice configuration."""
        if self._voice is None:
            self._voice = read_yaml(self.voice_path)
        return self._voice
    
    @property
    def profile(self) -> dict:
        return self.load()
    
    @property
    def voice(self) -> dict:
        return self.load_voice()
    
    def get_name(self) -> str:
        return self.profile['personal']['name']
    
    def get_email(self) -> str:
        return self.profile['personal']['email']
    
    def get_summary(self) -> str:
        return self.profile['positioning']['summary'].strip()
    
    def get_tagline(self) -> str:
        return self.profile['positioning']['tagline']
    
    def get_experience(self, include_current: bool = True) -> list:
        """Get work experience, optionally excluding current job."""
        exp = self.profile['experience']
        if not include_current:
            exp = [e for e in exp if e.get('include_in_cv', True)]
        return exp
    
    def get_projects(self, status: Optional[str] = None, limit: int = None) -> list:
        """Get projects, optionally filtered by status."""
        projects = self.profile['projects']
        
        if status:
            projects = [p for p in projects if p.get('status') == status]
        
        # Sort by priority
        projects = sorted(projects, key=lambda p: p.get('priority', 99))
        
        if limit:
            projects = projects[:limit]
        
        return projects
    
    def get_skills_direct(self) -> list:
        """Get directly experienced skills."""
        return self.profile['skills']['direct_experience']
    
    def get_skills_ai_assisted(self) -> list:
        """Get AI-assisted building skills."""
        return self.profile['skills']['ai_assisted_building']
    
    def get_tools(self) -> dict:
        """Get tools by category."""
        return self.profile['skills']['tools']

    def get_education(self) -> list:
        """Get education entries."""
        return self.profile.get('education', [])

    def get_languages(self) -> list:
        """Get language skills."""
        return self.profile.get('personal', {}).get('languages', [])

    def get_evidence_for_skill(self, skill_name: str) -> Optional[str]:
        """Find evidence for a specific skill."""
        skill_lower = skill_name.lower()
        
        for s in self.get_skills_direct():
            if skill_lower in s['skill'].lower():
                return s.get('evidence')
        
        for s in self.get_skills_ai_assisted():
            if skill_lower in s['skill'].lower():
                return s.get('evidence')
        
        return None
    
    def get_project_by_name(self, name: str) -> Optional[dict]:
        """Find project by name."""
        name_lower = name.lower()
        for p in self.profile['projects']:
            if name_lower in p['name'].lower():
                return p
        return None
    
    def validate(self) -> list[str]:
        """Validate profile completeness. Returns list of issues."""
        issues = []
        
        # Required fields
        required = [
            ('personal.name', self.profile.get('personal', {}).get('name')),
            ('personal.email', self.profile.get('personal', {}).get('email')),
            ('positioning.summary', self.profile.get('positioning', {}).get('summary')),
        ]
        
        for field, value in required:
            if not value:
                issues.append(f"Missing required field: {field}")
        
        # Check that skills have evidence
        for skill in self.get_skills_direct():
            if 'evidence' not in skill:
                issues.append(f"Direct skill '{skill['skill']}' missing evidence")
        
        for skill in self.get_skills_ai_assisted():
            if 'evidence' not in skill:
                issues.append(f"AI-assisted skill '{skill['skill']}' missing evidence")
        
        # Check that projects have evidence
        for project in self.get_projects():
            skip_statuses = ('idea', 'canceled')
            if 'evidence' not in project and project.get('status') not in skip_statuses:
                issues.append(f"Project '{project['name']}' missing evidence")
        
        return issues


    # Role-based keyword mappings for ATS optimization
    ROLE_KEYWORDS = {
        'qa_lead': [
            'Quality Assurance', 'QA', 'Testing', 'Test Lead', 'Bug Tracking',
            'JIRA', 'Regression Testing', 'Smoke Testing', 'Team Leadership',
            'Process Improvement', 'Defect Management', 'Test Strategy'
        ],
        'technical_pm': [
            'Project Management', 'PM', 'Technical Leadership', 'Agile',
            'Cross-functional Teams', 'Roadmap', 'Stakeholder Management',
            'JIRA', 'International Teams', 'Process Optimization'
        ],
        'process_improvement': [
            'Process Optimization', 'Lean', 'Six Sigma', 'Continuous Improvement',
            'Manufacturing', 'Quality Control', 'KPI', 'Efficiency',
            'Production Management', 'Data Analysis'
        ],
        'general': [
            'Project Management', 'Team Leadership', 'Quality Assurance',
            'Process Improvement', 'Cross-Cultural', 'International',
            'Problem Solving', 'Data Analysis', 'JIRA'
        ]
    }

    # Role-based skill prioritization
    ROLE_SKILL_PRIORITY = {
        'qa_lead': ['QA Game Testing', 'Team Leadership', 'Process Improvement', 'Customer Service'],
        'technical_pm': ['Project Management', 'Team Leadership', 'Process Improvement', 'Database Development'],
        'process_improvement': ['Process Improvement', 'Project Management', 'Management Auditing', 'Survey/Market Research'],
        'general': ['Team Leadership', 'Process Improvement', 'Project Management', 'QA Game Testing']
    }

    def get_core_competencies(self, target_role: str = 'general') -> list[str]:
        """
        Get ATS-optimized core competencies for target role.
        Returns 10-12 keywords that match job requirements.
        """
        base_keywords = self.ROLE_KEYWORDS.get(target_role, self.ROLE_KEYWORDS['general'])

        # Add keywords from skills
        skill_keywords = set()
        for skill in self.get_skills_direct():
            skill_keywords.update(skill.get('keywords', []))
        for skill in self.get_skills_ai_assisted():
            skill_keywords.update(skill.get('keywords', []))

        # Combine and prioritize
        all_keywords = list(base_keywords)
        for kw in skill_keywords:
            if kw not in all_keywords:
                all_keywords.append(kw)

        return all_keywords[:12]

    def get_skills_for_role(self, target_role: str = 'general') -> tuple[list, list]:
        """
        Get skills prioritized for target role.
        Returns (direct_skills, ai_assisted_skills) sorted by relevance.
        """
        priority_order = self.ROLE_SKILL_PRIORITY.get(target_role, self.ROLE_SKILL_PRIORITY['general'])

        direct = self.get_skills_direct()
        ai_assisted = self.get_skills_ai_assisted()

        def sort_key(skill):
            skill_name = skill['skill']
            try:
                return priority_order.index(skill_name)
            except ValueError:
                return 99

        direct_sorted = sorted(direct, key=sort_key)

        return direct_sorted, ai_assisted

    def get_experience_for_role(self, target_role: str = 'general') -> list:
        """
        Get experience entries prioritized for target role.
        Highlights most relevant positions.
        """
        experience = self.get_experience(include_current=False)

        # Role-specific company/role priorities
        role_priorities = {
            'qa_lead': ['Zenimax', 'Electronic Arts', 'EA'],
            'technical_pm': ['Electronic Arts', 'Scenaris', 'Eishin'],
            'process_improvement': ['Eishin', 'Audirep', 'Groupe Saur'],
            'general': ['Electronic Arts', 'Eishin', 'Zenimax']
        }

        priorities = role_priorities.get(target_role, role_priorities['general'])

        def sort_key(exp):
            company = exp.get('company', '')
            for i, p in enumerate(priorities):
                if p.lower() in company.lower():
                    return i
            return 99

        # Sort by relevance but keep chronological as secondary
        sorted_exp = sorted(experience, key=sort_key)

        return sorted_exp

    def get_quantified_achievement(self, exp: dict, index: int = 0) -> str:
        """
        Get a quantified version of an achievement.
        Adds numbers where possible.
        """
        achievements = exp.get('achievements', [])
        if index >= len(achievements):
            return ""

        achievement = achievements[index]

        # No invented numbers: return the achievement as written in profile.yaml.
        return achievement


def load_profile(profile_path: Optional[Path] = None) -> ProfileManager:
    """Convenience function to load profile."""
    return ProfileManager(profile_path)
