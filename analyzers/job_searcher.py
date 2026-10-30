"""
Job Searcher - Search job boards for matching positions.

Features:
- Search multiple job boards (Indeed, LinkedIn, RemoteOK, etc.)
- Auto-generate queries from profile
- Filter by location, remote, keywords
- Return jobs with basic match scoring
"""

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import quote_plus, urljoin
from pathlib import Path

logger = logging.getLogger(__name__)

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
class JobListing:
    """A job listing from search results."""
    title: str
    company: str
    location: str
    url: str
    source: str  # indeed, linkedin, remoteok, etc.
    snippet: str = ""
    salary: str = ""
    posted: str = ""
    job_type: str = ""  # remote, hybrid, onsite
    quick_score: float = 0  # Quick match score based on title/keywords


@dataclass
class SearchQuery:
    """Search parameters."""
    keywords: str
    location: str = ""
    remote_only: bool = False
    days_ago: int = 7  # Jobs posted within X days


class JobSearcher:
    """Search job boards for matching positions."""

    # Job board configurations - prioritizing worldwide/APAC-friendly sources
    SOURCES = {
        'jobicy': {
            'name': 'Jobicy',
            'base_url': 'https://jobicy.com',
            'search_url': 'https://jobicy.com/api/v2/remote-jobs',
            'remote_only': True,
            'note': 'Worldwide remote with good geo filtering',
        },
        'arbeitnow': {
            'name': 'Arbeitnow',
            'base_url': 'https://arbeitnow.com',
            'search_url': 'https://arbeitnow.com/api/job-board-api',
            'remote_only': True,
        },
        'remotive': {
            'name': 'Remotive',
            'base_url': 'https://remotive.com',
            'search_url': 'https://remotive.com/api/remote-jobs?search={keyword}',
            'remote_only': True,
        },
    }

    # Keywords that indicate good matches for the profile
    PROFILE_KEYWORDS = [
        'qa lead', 'quality assurance', 'test lead', 'qc manager',
        'technical pm', 'technical project manager', 'project manager',
        'process improvement', 'operations manager',
        'research analyst', 'market research', 'insights analyst',
        'customer success', 'customer experience',
        'remote', 'international', 'multilingual',
    ]

    def __init__(self, profile_path: Optional[Path] = None):
        self.pm = ProfileManager(profile_path)
        self.profile = self.pm.load()
        self._build_skill_keywords()

    def _build_skill_keywords(self):
        """Build list of keywords from profile for matching."""
        self.skill_keywords = set()

        # From direct skills
        for skill in self.pm.get_skills_direct():
            skill_name = skill['skill'].lower()
            self.skill_keywords.add(skill_name)
            # Add individual words
            for word in skill_name.split():
                if len(word) > 3:
                    self.skill_keywords.add(word)

        # Add common variations
        self.skill_keywords.update([
            'qa', 'quality', 'testing', 'test', 'jira',
            'leadership', 'team lead', 'manager', 'management',
            'process', 'improvement', 'optimization',
            'project', 'pm', 'agile', 'scrum',
            'remote', 'international', 'multilingual',
            'french', 'english', 'bilingual',
            'research', 'analysis', 'analyst', 'insights',
        ])

    def suggest_searches(self) -> list[SearchQuery]:
        """Suggest search queries based on profile."""
        suggestions = []
        seen_keywords = set()

        # Get user location from profile
        personal = self.profile.get('personal', {})
        user_location = personal.get('location', '')  # e.g., "Osaka, Japan"

        # Extract job titles from past experience
        for exp in self.pm.get_experience():
            title = exp.get('title', '')
            if title and title.lower() not in seen_keywords:
                seen_keywords.add(title.lower())
                suggestions.append(SearchQuery(keywords=title, remote_only=True))

        # Extract from direct skills - focus on leadership/management skills
        leadership_keywords = ['lead', 'manager', 'director', 'head', 'supervisor']
        for skill in self.pm.get_skills_direct():
            skill_name = skill.get('skill', '')
            skill_lower = skill_name.lower()
            # Only add if it sounds like a job title
            if any(lk in skill_lower for lk in leadership_keywords):
                if skill_lower not in seen_keywords:
                    seen_keywords.add(skill_lower)
                    suggestions.append(SearchQuery(keywords=skill_name, remote_only=True))

        # Add variations for top skills
        top_skills = []
        for skill in self.pm.get_skills_direct()[:5]:
            skill_name = skill.get('skill', '')
            if skill_name:
                top_skills.append(skill_name)

        # Create combined searches from top skills
        if top_skills:
            # First skill + "remote"
            suggestions.append(SearchQuery(keywords=f"{top_skills[0]} remote", remote_only=True))
            # First two skills combined
            if len(top_skills) >= 2:
                suggestions.append(SearchQuery(keywords=f"{top_skills[0]} {top_skills[1]}", remote_only=True))

        # Location-aware searches (for Japan, add APAC-friendly keywords)
        if 'japan' in user_location.lower():
            suggestions.append(SearchQuery(keywords="QA APAC", remote_only=True))
            suggestions.append(SearchQuery(keywords="Project Manager Asia", remote_only=True))
            suggestions.append(SearchQuery(keywords="remote worldwide", remote_only=True))

        # Fallback defaults if profile didn't yield enough
        fallbacks = [
            ("QA Lead", True),
            ("Project Manager", True),
            ("Test Manager", True),
            ("Operations Manager", True),
        ]
        for kw, remote in fallbacks:
            if kw.lower() not in seen_keywords and len(suggestions) < 10:
                suggestions.append(SearchQuery(keywords=kw, remote_only=remote))

        return suggestions[:12]  # Limit to 12 suggestions

    def search(self, query: SearchQuery, sources: list[str] = None, limit: int = 20) -> list[JobListing]:
        """
        Search for jobs across multiple sources.

        Args:
            query: Search parameters
            sources: List of sources to search (default: all remote sources)
            limit: Maximum results per source

        Returns:
            List of JobListing objects
        """
        if not HAS_REQUESTS or not HAS_BS4:
            logger.error("requests and beautifulsoup4 required. Run: pip install requests beautifulsoup4")
            return []

        if sources is None:
            # Default to worldwide remote-friendly sources (no rate limits)
            sources = ['jobicy', 'remotive']

        all_jobs = []

        for source in sources:
            if source not in self.SOURCES:
                continue

            try:
                jobs = self._search_source(source, query, limit)
                all_jobs.extend(jobs)
                time.sleep(1)  # Be nice to servers
            except Exception as e:
                logger.warning(f"Error searching {source}: {e}")

        # Sort by quick score
        all_jobs.sort(key=lambda j: j.quick_score, reverse=True)

        return all_jobs

    def _search_source(self, source: str, query: SearchQuery, limit: int) -> list[JobListing]:
        """Search a specific job board."""
        if source == 'jobicy':
            return self._search_jobicy(query, limit)
        elif source == 'arbeitnow':
            return self._search_arbeitnow(query, limit)
        elif source == 'remotive':
            return self._search_remotive(query, limit)
        else:
            return []

    def _search_jobicy(self, query: SearchQuery, limit: int) -> list[JobListing]:
        """Search Jobicy - has good geographic data."""
        jobs = []
        keywords = query.keywords.lower().split()

        url = f"https://jobicy.com/api/v2/remote-jobs?count={limit*3}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()

            for item in data.get('jobs', []):
                title = item.get('jobTitle', '')
                company = item.get('companyName', '')
                location = item.get('jobGeo', '')  # Geographic location
                industry = item.get('jobIndustry', [])

                # Filter by keywords
                searchable = f"{title} {company} {' '.join(industry) if industry else ''}".lower()
                if keywords and not any(kw in searchable for kw in keywords):
                    continue

                # Skip US-only jobs unless they explicitly say worldwide
                loc_lower = location.lower() if location else ''
                is_us_only = any(us in loc_lower for us in ['usa only', 'us only', 'united states only'])
                is_worldwide = any(w in loc_lower for w in ['worldwide', 'anywhere', 'global', 'asia', 'apac', 'japan'])

                if is_us_only:
                    continue  # Skip completely

                job = JobListing(
                    title=title,
                    company=company,
                    location=location if location else 'Remote',
                    url=item.get('url', ''),
                    source='jobicy',
                    snippet=item.get('jobExcerpt', '')[:200] if item.get('jobExcerpt') else '',
                    salary=item.get('annualSalaryMin', ''),
                    posted=item.get('pubDate', ''),
                    job_type='remote',
                    quick_score=self._quick_score(title, company, industry if industry else [], location),
                )

                if len(jobs) < limit:
                    jobs.append(job)

        except Exception as e:
            logger.warning(f"Jobicy search failed: {e}")

        return jobs

    def _search_arbeitnow(self, query: SearchQuery, limit: int) -> list[JobListing]:
        """Search Arbeitnow - worldwide remote jobs."""
        jobs = []
        keywords = query.keywords.lower().split()

        url = "https://arbeitnow.com/api/job-board-api"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()

            for item in data.get('data', []):
                title = item.get('title', '')
                company = item.get('company_name', '')
                location = item.get('location', '')
                remote = item.get('remote', False)
                tags = item.get('tags', [])

                # Only include remote jobs
                if not remote:
                    continue

                # Filter by keywords
                searchable = f"{title} {company} {' '.join(tags)}".lower()
                if keywords and not any(kw in searchable for kw in keywords):
                    continue

                # Check if location is worldwide/global compatible
                loc_lower = location.lower()
                is_worldwide = any(w in loc_lower for w in ['worldwide', 'global', 'anywhere', 'remote', 'international', 'apac', 'asia'])

                job = JobListing(
                    title=title,
                    company=company,
                    location=location if location else 'Worldwide',
                    url=item.get('url', ''),
                    source='arbeitnow',
                    snippet=item.get('description', '')[:200] if item.get('description') else '',
                    salary=item.get('salary', ''),
                    posted=item.get('created_at', ''),
                    job_type='remote',
                    quick_score=self._quick_score(title, company, tags, location),
                )

                if len(jobs) < limit:
                    jobs.append(job)

        except Exception as e:
            logger.warning(f"Arbeitnow search failed: {e}")

        return jobs

    def _search_himalayas(self, query: SearchQuery, limit: int) -> list[JobListing]:
        """Search Himalayas - async-friendly worldwide remote."""
        jobs = []
        keywords = query.keywords.lower().split()

        url = "https://himalayas.app/jobs/api"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()

            for item in data.get('jobs', []):
                title = item.get('title', '')
                company = item.get('companyName', '')
                location = item.get('location', '')
                categories = item.get('categories', [])

                # Filter by keywords
                searchable = f"{title} {company} {' '.join(categories)}".lower()
                if keywords and not any(kw in searchable for kw in keywords):
                    continue

                # Prefer worldwide/APAC compatible
                loc_lower = location.lower() if location else ''
                is_worldwide = any(w in loc_lower for w in ['worldwide', 'global', 'anywhere', 'apac', 'asia', 'japan'])

                job = JobListing(
                    title=title,
                    company=company,
                    location=location if location else 'Worldwide',
                    url=item.get('applicationLink', '') or f"https://himalayas.app/jobs/{item.get('slug', '')}",
                    source='himalayas',
                    snippet=item.get('excerpt', '')[:200] if item.get('excerpt') else '',
                    salary=item.get('salary', ''),
                    posted=item.get('pubDate', ''),
                    job_type='remote',
                    quick_score=self._quick_score(title, company, categories, location),
                )

                if len(jobs) < limit:
                    jobs.append(job)

        except Exception as e:
            logger.warning(f"Himalayas search failed: {e}")

        return jobs

    def _search_remoteok(self, query: SearchQuery, limit: int) -> list[JobListing]:
        """Search RemoteOK."""
        jobs = []

        # RemoteOK API - get all jobs and filter locally
        # The tag= param only works for specific categories, not text search
        keywords = query.keywords.lower().split()

        # Try to map to RemoteOK tags if possible
        tag_mapping = {
            'qa': 'qa', 'quality': 'qa', 'test': 'qa',
            'dev': 'dev', 'developer': 'dev', 'engineer': 'dev',
            'manager': 'exec', 'lead': 'exec', 'director': 'exec',
            'project': 'exec', 'pm': 'exec',
            'data': 'data', 'analyst': 'data',
            'marketing': 'marketing', 'sales': 'sales',
            'design': 'design', 'ux': 'design', 'ui': 'design',
        }

        # Find best matching tag
        tag = None
        for kw in keywords:
            if kw in tag_mapping:
                tag = tag_mapping[kw]
                break

        url = "https://remoteok.com/api"
        if tag:
            url += f"?tag={tag}"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            data = response.json()

            # First item is metadata, skip it
            for item in data[1:]:
                if not isinstance(item, dict):
                    continue
                if len(jobs) >= limit:
                    break

                title = item.get('position', '')
                company = item.get('company', '')
                description = item.get('description', '')
                location = item.get('location', 'Remote')
                tags = item.get('tags', [])

                # Local keyword filtering - check if any keyword matches
                searchable = f"{title} {company} {description} {' '.join(tags)}".lower()
                if keywords and not any(kw in searchable for kw in keywords):
                    continue  # Skip if no keyword matches

                job = JobListing(
                    title=title,
                    company=company,
                    location=location,
                    url=item.get('url', f"https://remoteok.com/l/{item.get('id', '')}"),
                    source='remoteok',
                    snippet=description[:200],
                    salary=item.get('salary', ''),
                    posted=item.get('date', ''),
                    job_type='remote',
                    quick_score=self._quick_score(title, company, tags, location),
                )
                jobs.append(job)

        except Exception as e:
            logger.warning(f"RemoteOK search failed: {e}")

        return jobs

    def _search_remotive(self, query: SearchQuery, limit: int) -> list[JobListing]:
        """Search Remotive.com - has proper search API."""
        jobs = []

        # Remotive has a real search API
        keyword = quote_plus(query.keywords)
        url = f"https://remotive.com/api/remote-jobs?search={keyword}&limit={limit}"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            data = response.json()
            job_list = data.get('jobs', [])

            for item in job_list[:limit]:
                title = item.get('title', '')
                company = item.get('company_name', '')
                location = item.get('candidate_required_location', 'Remote')

                job = JobListing(
                    title=title,
                    company=company,
                    location=location,
                    url=item.get('url', ''),
                    source='remotive',
                    snippet=item.get('description', '')[:200] if item.get('description') else '',
                    salary=item.get('salary', ''),
                    posted=item.get('publication_date', ''),
                    job_type='remote',
                    quick_score=self._quick_score(title, company, item.get('tags', []), location),
                )
                jobs.append(job)

        except Exception as e:
            logger.warning(f"Remotive search failed: {e}")

        return jobs

    def _search_weworkremotely(self, query: SearchQuery, limit: int) -> list[JobListing]:
        """Search We Work Remotely."""
        jobs = []

        keyword = quote_plus(query.keywords)
        url = f"https://weworkremotely.com/remote-jobs/search?term={keyword}"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find job listings
            listings = soup.find_all('li', class_='feature')[:limit]

            for listing in listings:
                title_elem = listing.find('span', class_='title')
                company_elem = listing.find('span', class_='company')
                link_elem = listing.find('a', href=True)

                if not title_elem or not link_elem:
                    continue

                title = title_elem.get_text(strip=True)
                company = company_elem.get_text(strip=True) if company_elem else ''
                job_url = urljoin('https://weworkremotely.com', link_elem['href'])

                job = JobListing(
                    title=title,
                    company=company,
                    location='Remote',
                    url=job_url,
                    source='weworkremotely',
                    snippet='',
                    job_type='remote',
                    quick_score=self._quick_score(title, company, []),
                )
                jobs.append(job)

        except Exception as e:
            logger.warning(f"WeWorkRemotely search failed: {e}")

        return jobs

    def _search_indeed(self, query: SearchQuery, limit: int) -> list[JobListing]:
        """Search Indeed (basic scraping - may be blocked)."""
        jobs = []

        keyword = quote_plus(query.keywords)
        location = quote_plus(query.location) if query.location else ''
        days = query.days_ago

        url = f"https://www.indeed.com/jobs?q={keyword}&l={location}&fromage={days}"

        if query.remote_only:
            url += "&remotejob=032b3046-06a3-4876-8dfd-474eb5e7ed11"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Indeed's structure changes frequently, try multiple selectors
            job_cards = soup.find_all('div', class_=re.compile('job_seen_beacon|jobsearch-SerpJobCard'))[:limit]

            for card in job_cards:
                title_elem = card.find(['h2', 'a'], class_=re.compile('jobTitle|title'))
                company_elem = card.find('span', class_=re.compile('companyName|company'))
                location_elem = card.find('div', class_=re.compile('companyLocation|location'))
                link_elem = card.find('a', href=True)

                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                company = company_elem.get_text(strip=True) if company_elem else ''
                loc = location_elem.get_text(strip=True) if location_elem else ''

                job_url = ''
                if link_elem and 'href' in link_elem.attrs:
                    href = link_elem['href']
                    if href.startswith('/'):
                        job_url = f"https://www.indeed.com{href}"
                    else:
                        job_url = href

                job_type = 'remote' if 'remote' in loc.lower() else 'onsite'

                job = JobListing(
                    title=title,
                    company=company,
                    location=loc,
                    url=job_url,
                    source='indeed',
                    job_type=job_type,
                    quick_score=self._quick_score(title, company, []),
                )
                jobs.append(job)

        except Exception as e:
            logger.warning(f"Indeed search failed: {e}")

        return jobs

    def _quick_score(self, title: str, company: str, tags: list, location: str = '') -> float:
        """Calculate a quick match score based on title, tags, and location."""
        score = 0
        title_lower = title.lower()
        tags_lower = ' '.join(str(t).lower() for t in tags)
        loc_lower = location.lower() if location else ''

        # High-value exact title matches (strong signal)
        high_value = ['customer service', 'customer support', 'technical support', 'support specialist',
                      'team leader', 'escalation', 'qa lead', 'qa manager', 'test lead', 'test manager',
                      'quality assurance', 'qc manager', 'quality manager',
                      'technical pm', 'technical project manager', 'project manager',
                      'process improvement', 'operations manager', 'program manager']
        for term in high_value:
            if term in title_lower:
                score += 40
                break

        # Medium-value matches
        medium_value = ['qa ', 'qc ', 'test', 'quality', 'project', 'lead', 'manager']
        for term in medium_value:
            if term in title_lower:
                score += 15
                break

        # Keyword matches from profile skills
        matched_skills = 0
        for keyword in self.skill_keywords:
            if len(keyword) > 2 and keyword in title_lower:
                matched_skills += 1
            if len(keyword) > 2 and keyword in tags_lower:
                matched_skills += 1
        score += min(20, matched_skills * 5)  # Cap skill bonus at 20

        # Location scoring - boost APAC, penalize US/EU (user is in Japan)
        apac_terms = ['worldwide', 'global', 'anywhere', 'apac', 'asia', 'japan', 'australia', 'singapore', 'philippines', 'india', 'new zealand']
        restricted_terms = ['only', 'based', 'must be in', 'must reside']

        if any(w in loc_lower for w in apac_terms):
            score += 25  # Boost APAC-compatible jobs
        elif any(r in loc_lower for r in restricted_terms):
            score -= 50  # Heavily penalize location-restricted jobs
        elif any(c in loc_lower for c in ['united states', 'usa', 'u.s.', 'america']):
            score -= 30  # Strong penalty for US jobs

        # Negative signals - likely not a fit
        negative = ['developer', 'engineer', 'designer', 'therapist', 'nurse',
                    'sales rep', 'accountant', 'lawyer', 'artist', 'writer',
                    'marketing manager', 'social media']
        for term in negative:
            if term in title_lower and 'qa' not in title_lower and 'test' not in title_lower:
                score -= 20
                break

        # Cap between 0 and 100
        return max(0, min(100, score))

    def search_all_suggestions(self, limit_per_query: int = 10, min_score: int = 20) -> list[JobListing]:
        """Search using all suggested queries."""
        all_jobs = []
        seen_urls = set()
        seen_titles = set()  # Also dedupe by title+company

        for query in self.suggest_searches():
            jobs = self.search(query, limit=limit_per_query)
            for job in jobs:
                # Deduplicate by URL and by title+company
                title_key = f"{job.title.lower()}|{job.company.lower()}"
                if job.url in seen_urls or title_key in seen_titles:
                    continue

                seen_urls.add(job.url)
                seen_titles.add(title_key)

                # Only include jobs with minimum relevance score
                if job.quick_score >= min_score:
                    all_jobs.append(job)

        # Sort by score
        all_jobs.sort(key=lambda j: j.quick_score, reverse=True)

        return all_jobs


def search_jobs(keywords: str, remote_only: bool = True, limit: int = 20) -> list[JobListing]:
    """Convenience function to search for jobs."""
    searcher = JobSearcher()
    query = SearchQuery(keywords=keywords, remote_only=remote_only)
    return searcher.search(query, limit=limit)
