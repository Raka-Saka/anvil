"""
Anvil Storage - Draft and job application management.
"""

from pathlib import Path
from datetime import datetime
from typing import Optional
import yaml


class DraftManager:
    """Manages auto-saved drafts."""

    def __init__(self):
        self.base_dir = Path(__file__).parent.parent / "output" / "drafts"

    def save_draft(self, content: str, draft_type: str, metadata: dict = None) -> Path:
        """
        Save a draft with timestamp.

        Args:
            content: The generated content
            draft_type: cv, cover_letter, or article
            metadata: Optional metadata (role, company, etc.)

        Returns:
            Path to saved draft
        """
        draft_dir = self.base_dir / draft_type
        draft_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Build filename from metadata
        name_parts = [draft_type]
        if metadata:
            if 'role' in metadata:
                name_parts.append(metadata['role'].replace(' ', '_')[:20])
            if 'company' in metadata:
                name_parts.append(metadata['company'].replace(' ', '_')[:20])
        name_parts.append(timestamp)

        filename = '_'.join(name_parts) + '.md'
        filepath = draft_dir / filename

        # Add metadata header
        header = f"---\n"
        header += f"type: {draft_type}\n"
        header += f"generated: {datetime.now().isoformat()}\n"
        if metadata:
            for k, v in metadata.items():
                header += f"{k}: {v}\n"
        header += "---\n\n"

        filepath.write_text(header + content, encoding='utf-8')
        return filepath

    def get_drafts(self, draft_type: str, limit: int = 10) -> list[dict]:
        """
        Get recent drafts of a type.

        Returns list of dicts with 'path', 'display', 'timestamp'.
        """
        draft_dir = self.base_dir / draft_type
        if not draft_dir.exists():
            return []

        drafts = []
        for f in sorted(draft_dir.glob('*.md'), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]:
            # Parse timestamp from filename or file
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            display = f"{mtime.strftime('%Y-%m-%d %H:%M')} - {f.stem[:40]}"

            drafts.append({
                'path': str(f),
                'display': display,
                'timestamp': mtime,
            })

        return drafts

    def load_draft(self, path: str) -> str:
        """Load a draft file, stripping metadata header."""
        content = Path(path).read_text(encoding='utf-8')

        # Strip YAML frontmatter if present
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                return parts[2].strip()

        return content


class JobTracker:
    """Old tracker API, kept for callers. Stored in the Pipeline now."""

    def __init__(self):
        from core.pipeline import Pipeline
        self.pipeline = Pipeline()

    def add_job(self, company: str, role: str, cover_letter_file: Optional[str] = None,
                job_description: Optional[str] = None, notes: Optional[str] = None,
                match_score: Optional[float] = None, url: Optional[str] = None,
                channel: str = "other", country: str = "") -> dict:
        return self.pipeline.add(
            company=company, role=role, channel=channel, country=country, stage="found",
            url=url or "", notes=notes or "", description=job_description or "",
            documents=[cover_letter_file] if cover_letter_file else [],
            fit={"score": match_score} if match_score is not None else None,
        )

    def update_status(self, job_id: int, status: str):
        self.pipeline.move(job_id, status)

    def get_jobs(self, status: Optional[str] = None) -> list[dict]:
        return [a for a in self.pipeline.apps if not status or a["stage"] == status]

    def get_job(self, job_id: int) -> Optional[dict]:
        return self.pipeline.get(job_id)

    def delete_job(self, job_id: int):
        self.pipeline.delete(job_id)
