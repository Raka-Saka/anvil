"""
YouTube Script Generator - Create scripts and descriptions for YouTube videos.

Generates:
- Video descriptions with hashtags and links
- Intro/outro text for TTS
- SRT subtitle files
"""

import re
from pathlib import Path
from typing import Optional
from datetime import datetime


class YouTubeScriptGenerator:
    """Generate scripts and metadata for YouTube videos."""

    # Intro templates
    INTROS = {
        'casual': "Hey everyone, welcome back to ChronOS Dev Diary. Today we're diving into {topic}.",
        'direct': "Welcome to ChronOS Dev Diary. In this episode: {topic}.",
        'story': "So there I was, staring at my screen at 2 AM, when {topic}.",
    }

    # Outro templates
    OUTROS = {
        'casual': "That's it for today's dev diary. If you found this useful, consider subscribing. See you in the next one.",
        'direct': "Thanks for watching. Subscribe for more OS development content.",
        'minimal': "Thanks for watching.",
    }

    def __init__(self, style: str = 'direct'):
        """
        Initialize script generator.

        Args:
            style: Script style ('casual', 'direct', 'story', 'minimal')
        """
        self.style = style

    def generate_tts_script(
        self,
        title: str,
        content: str,
        include_intro: bool = True,
        include_outro: bool = True
    ) -> str:
        """
        Generate a script optimized for TTS.

        Args:
            title: Article title
            content: Article content
            include_intro: Add intro
            include_outro: Add outro

        Returns:
            Script text ready for TTS
        """
        parts = []

        # Add intro
        if include_intro:
            intro_template = self.INTROS.get(self.style, self.INTROS['direct'])
            # Extract topic from title
            topic = title.lower()
            if ':' in topic:
                topic = topic.split(':')[1].strip()
            intro = intro_template.format(topic=topic)
            parts.append(intro)
            parts.append("")  # Pause

        # Add main content
        parts.append(title)
        parts.append("")
        parts.append(content)

        # Add outro
        if include_outro:
            parts.append("")
            outro = self.OUTROS.get(self.style, self.OUTROS['direct'])
            parts.append(outro)

        return "\n\n".join(parts)

    def generate_video_description(
        self,
        title: str,
        content: str,
        tags: list[str],
        canonical_url: Optional[str] = None,
        timestamps: Optional[list[tuple[str, str]]] = None
    ) -> str:
        """
        Generate YouTube video description.

        Args:
            title: Video title
            content: Article content (will be summarized)
            tags: Hashtags
            canonical_url: Link to full article
            timestamps: List of (time, description) tuples

        Returns:
            Formatted video description
        """
        lines = []

        # Summary (first paragraph or ~200 chars)
        summary = self._extract_summary(content)
        lines.append(summary)
        lines.append("")

        # Timestamps if provided
        if timestamps:
            lines.append("TIMESTAMPS:")
            for time, desc in timestamps:
                lines.append(f"{time} - {desc}")
            lines.append("")

        # Links section
        lines.append("---")
        if canonical_url:
            lines.append(f"Read the full article: {canonical_url}")
        lines.append("")

        # About section
        lines.append("ABOUT THIS CHANNEL:")
        lines.append("ChronOS Dev Diary documents the journey of building an operating system from scratch.")
        lines.append("New episodes every few days covering kernel development, bootloaders, memory management, and more.")
        lines.append("")

        # Hashtags
        clean_tags = [f"#{t.lstrip('#')}" for t in tags[:15]]
        lines.append(" ".join(clean_tags))

        return "\n".join(lines)

    def generate_srt_subtitles(
        self,
        content: str,
        words_per_minute: int = 150
    ) -> str:
        """
        Generate SRT subtitle file from content.

        Args:
            content: Text content
            words_per_minute: Estimated speaking rate

        Returns:
            SRT formatted subtitles
        """
        # Clean content
        clean = self._clean_for_subtitles(content)

        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', clean)

        srt_lines = []
        current_time = 0.0  # seconds
        subtitle_num = 1

        for sentence in sentences:
            if not sentence.strip():
                continue

            # Estimate duration based on word count
            word_count = len(sentence.split())
            duration = (word_count / words_per_minute) * 60

            # Format times
            start_time = self._format_srt_time(current_time)
            end_time = self._format_srt_time(current_time + duration)

            # Split long sentences into multiple subtitles
            if len(sentence) > 80:
                chunks = self._split_sentence(sentence, 80)
                chunk_duration = duration / len(chunks)

                for chunk in chunks:
                    start_time = self._format_srt_time(current_time)
                    end_time = self._format_srt_time(current_time + chunk_duration)

                    srt_lines.append(str(subtitle_num))
                    srt_lines.append(f"{start_time} --> {end_time}")
                    srt_lines.append(chunk)
                    srt_lines.append("")

                    current_time += chunk_duration
                    subtitle_num += 1
            else:
                srt_lines.append(str(subtitle_num))
                srt_lines.append(f"{start_time} --> {end_time}")
                srt_lines.append(sentence)
                srt_lines.append("")

                current_time += duration
                subtitle_num += 1

        return "\n".join(srt_lines)

    def _extract_summary(self, content: str, max_length: int = 300) -> str:
        """Extract a summary from content."""
        # Remove markdown
        clean = re.sub(r'```[\s\S]*?```', '', content)
        clean = re.sub(r'`[^`]+`', '', clean)
        clean = re.sub(r'^#+\s*', '', clean, flags=re.MULTILINE)
        clean = re.sub(r'\*\*([^*]+)\*\*', r'\1', clean)
        clean = re.sub(r'\*([^*]+)\*', r'\1', clean)
        clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', clean)
        clean = re.sub(r'\n{2,}', '\n', clean)

        # Get first paragraph or max_length chars
        paragraphs = clean.strip().split('\n')
        summary = paragraphs[0] if paragraphs else clean[:max_length]

        if len(summary) > max_length:
            summary = summary[:max_length].rsplit(' ', 1)[0] + "..."

        return summary

    def _clean_for_subtitles(self, text: str) -> str:
        """Clean text for subtitle display."""
        # Remove code blocks
        text = re.sub(r'```[\s\S]*?```', '[code example]', text)
        text = re.sub(r'`[^`]+`', '', text)

        # Remove markdown
        text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)

        # Remove URLs
        text = re.sub(r'https?://\S+', '', text)

        # Clean whitespace
        text = re.sub(r'\n{2,}', ' ', text)
        text = re.sub(r'\s{2,}', ' ', text)

        return text.strip()

    def _format_srt_time(self, seconds: float) -> str:
        """Format seconds as SRT timestamp (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def _split_sentence(self, sentence: str, max_length: int) -> list[str]:
        """Split a long sentence into chunks."""
        words = sentence.split()
        chunks = []
        current_chunk = []

        for word in words:
            if len(' '.join(current_chunk + [word])) <= max_length:
                current_chunk.append(word)
            else:
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                current_chunk = [word]

        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks

    def save_all(
        self,
        title: str,
        content: str,
        tags: list[str],
        output_dir: Path,
        canonical_url: Optional[str] = None
    ) -> dict[str, Path]:
        """
        Generate and save all YouTube files.

        Args:
            title: Article title
            content: Article content
            tags: Hashtags
            output_dir: Where to save files
            canonical_url: Link to article

        Returns:
            Dict of file type to path
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create safe filename base
        safe_title = "".join(c for c in title[:30] if c.isalnum() or c in ' -_').strip()
        safe_title = safe_title.replace(' ', '_')
        date_str = datetime.now().strftime('%Y%m%d')

        paths = {}

        # TTS Script
        script = self.generate_tts_script(title, content)
        script_path = output_dir / f"script_{safe_title}_{date_str}.txt"
        script_path.write_text(script, encoding='utf-8')
        paths['script'] = script_path
        print(f">>> YouTube: Saved script to {script_path}", flush=True)

        # Video description
        description = self.generate_video_description(title, content, tags, canonical_url)
        desc_path = output_dir / f"description_{safe_title}_{date_str}.txt"
        desc_path.write_text(description, encoding='utf-8')
        paths['description'] = desc_path
        print(f">>> YouTube: Saved description to {desc_path}", flush=True)

        # SRT subtitles
        srt = self.generate_srt_subtitles(content)
        srt_path = output_dir / f"subtitles_{safe_title}_{date_str}.srt"
        srt_path.write_text(srt, encoding='utf-8')
        paths['subtitles'] = srt_path
        print(f">>> YouTube: Saved subtitles to {srt_path}", flush=True)

        return paths
