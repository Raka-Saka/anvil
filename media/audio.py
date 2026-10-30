"""
Audio Generator - Convert articles to speech using edge-tts.

Uses Microsoft Edge TTS (FREE, high quality).
No API key required.
"""

import logging
import asyncio
import re
from pathlib import Path
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import edge-tts
try:
    import edge_tts
    HAS_EDGE_TTS = True
except ImportError:
    HAS_EDGE_TTS = False
    edge_tts = None


class AudioGenerator:
    """Generate audio from article text using edge-tts."""

    # Voice options (Microsoft Edge TTS)
    VOICES = {
        'en': {
            'male': 'en-US-GuyNeural',
            'female': 'en-US-JennyNeural',
            'narrative': 'en-US-AriaNeural',  # Good for storytelling
        },
        'ja': {
            'male': 'ja-JP-KeitaNeural',
            'female': 'ja-JP-NanamiNeural',
        }
    }

    def __init__(self, voice: Optional[str] = None, rate: str = "+0%", volume: str = "+0%"):
        """
        Initialize audio generator.

        Args:
            voice: Voice ID to use (default: en-US-AriaNeural)
            rate: Speech rate adjustment (e.g., "+10%", "-20%")
            volume: Volume adjustment (e.g., "+10%", "-20%")
        """
        self.voice = voice or self.VOICES['en']['narrative']
        self.rate = rate
        self.volume = volume

    def is_available(self) -> bool:
        """Check if edge-tts is installed."""
        return HAS_EDGE_TTS

    def set_language(self, lang: str = 'en', gender: str = 'narrative'):
        """
        Set voice based on language and gender preference.

        Args:
            lang: Language code ('en' or 'ja')
            gender: Voice type ('male', 'female', 'narrative')
        """
        lang_voices = self.VOICES.get(lang, self.VOICES['en'])
        self.voice = lang_voices.get(gender, lang_voices.get('female'))

    def _clean_text_for_speech(self, text: str) -> str:
        """
        Clean text for better speech synthesis.

        Removes markdown, code blocks, and other non-speech elements.
        """
        # Remove code blocks
        text = re.sub(r'```[\s\S]*?```', '', text)
        text = re.sub(r'`[^`]+`', '', text)

        # Remove markdown headers but keep text
        text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)

        # Remove markdown formatting
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*([^*]+)\*', r'\1', text)      # Italic
        text = re.sub(r'__([^_]+)__', r'\1', text)      # Bold
        text = re.sub(r'_([^_]+)_', r'\1', text)        # Italic

        # Remove links but keep text
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)

        # Remove images
        text = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', text)

        # Remove bullet points
        text = re.sub(r'^[\-\*]\s+', '', text, flags=re.MULTILINE)

        # Remove numbered lists prefix
        text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)

        # Remove hashtags (keep the word)
        text = re.sub(r'#(\w+)', r'\1', text)

        # Remove URLs
        text = re.sub(r'https?://\S+', '', text)

        # Clean up multiple newlines
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Clean up multiple spaces
        text = re.sub(r' {2,}', ' ', text)

        return text.strip()

    async def _generate_async(self, text: str, output_path: Path) -> bool:
        """Async implementation of audio generation."""
        if not HAS_EDGE_TTS:
            return False

        communicate = edge_tts.Communicate(
            text,
            self.voice,
            rate=self.rate,
            volume=self.volume
        )

        await communicate.save(str(output_path))
        return True

    def generate(
        self,
        text: str,
        output_path: Optional[Path] = None,
        title: Optional[str] = None
    ) -> Optional[Path]:
        """
        Generate audio from text.

        Args:
            text: Text to convert to speech
            output_path: Where to save the audio file
            title: Article title (used for filename if output_path not specified)

        Returns:
            Path to generated audio file, or None if failed
        """
        if not HAS_EDGE_TTS:
            logger.error("edge-tts not installed. Run: pip install edge-tts")
            return None

        print(f">>> Audio: Using voice '{self.voice}'", flush=True)
        print(f">>> Audio: Text length {len(text)} chars", flush=True)

        # Clean text for speech
        clean_text = self._clean_text_for_speech(text)
        print(f">>> Audio: Cleaned text {len(clean_text)} chars", flush=True)

        if not clean_text:
            logger.error("No speakable text after cleaning")
            return None

        # Determine output path
        if output_path is None:
            output_dir = Path("output/audio")
            output_dir.mkdir(parents=True, exist_ok=True)

            if title:
                safe_title = "".join(c for c in title[:30] if c.isalnum() or c in ' -_').strip()
                safe_title = safe_title.replace(' ', '_')
            else:
                safe_title = "article"

            date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = output_dir / f"audio_{safe_title}_{date_str}.mp3"

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Run async generation
            print(f">>> Audio: Generating TTS...", flush=True)
            asyncio.run(self._generate_async(clean_text, output_path))
            print(f">>> Audio: Saved to {output_path}", flush=True)
            logger.info(f"Generated audio: {output_path}")
            return output_path

        except Exception as e:
            print(f">>> Audio: ERROR - {e}", flush=True)
            logger.error(f"Audio generation failed: {e}")
            return None

    def generate_for_article(
        self,
        title: str,
        content: str,
        lang: str = 'en',
        output_dir: Optional[Path] = None,
        include_title_speech: bool = True,
        gender: Optional[str] = None
    ) -> Optional[Path]:
        """
        Generate audio specifically for a diary article.

        Args:
            title: Article title
            content: Article content (markdown)
            lang: Language code ('en' or 'ja')
            output_dir: Output directory
            include_title_speech: Whether to speak the title at the start
            gender: Voice gender ('male', 'female', 'narrative'). If None, uses current voice.

        Returns:
            Path to generated audio file
        """
        # Set voice for language/gender if specified
        if gender:
            self.set_language(lang, gender)

        # Build speech text
        speech_parts = []

        if include_title_speech:
            speech_parts.append(title)
            speech_parts.append("")  # Pause

        speech_parts.append(content)

        full_text = "\n\n".join(speech_parts)

        # Determine output path
        if output_dir:
            safe_title = "".join(c for c in title[:30] if c.isalnum() or c in ' -_').strip()
            safe_title = safe_title.replace(' ', '_')
            date_str = datetime.now().strftime('%Y%m%d')
            output_path = Path(output_dir) / f"audio_{safe_title}_{lang}_{date_str}.mp3"
        else:
            output_path = None

        return self.generate(
            text=full_text,
            output_path=output_path,
            title=title
        )

    @staticmethod
    def list_voices(lang: Optional[str] = None) -> list[dict]:
        """
        List available voices.

        Args:
            lang: Filter by language (e.g., 'en', 'ja')

        Returns:
            List of voice info dicts
        """
        if not HAS_EDGE_TTS:
            return []

        async def get_voices():
            voices = await edge_tts.list_voices()
            return voices

        try:
            voices = asyncio.run(get_voices())

            if lang:
                voices = [v for v in voices if v['Locale'].startswith(lang)]

            return voices
        except Exception:
            return []
