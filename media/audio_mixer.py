"""
Audio Mixer - Mix background music with TTS audio.

Uses FFmpeg to combine voice narration with background music.
"""

import subprocess
import logging
import random
from pathlib import Path
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class AudioMixer:
    """Mix TTS audio with background music."""

    def __init__(self, music_dir: Optional[Path] = None):
        """
        Initialize audio mixer.

        Args:
            music_dir: Directory containing background music files
        """
        self.music_dir = Path(music_dir) if music_dir else Path("media/music")

    def get_available_music(self) -> list[Path]:
        """Get list of available background music files."""
        if not self.music_dir.exists():
            return []

        music_files = []
        for ext in ['*.mp3', '*.wav', '*.m4a', '*.ogg']:
            music_files.extend(self.music_dir.glob(ext))

        return sorted(music_files)

    def get_random_music(self) -> Optional[Path]:
        """Get a random background music file."""
        music_files = self.get_available_music()
        if music_files:
            selected = random.choice(music_files)
            print(f">>> Mixer: Selected track: '{selected.stem}'", flush=True)
            return selected
        return None

    def mix_audio(
        self,
        voice_path: Path,
        output_path: Path,
        music_path: Optional[Path] = None,
        music_volume: float = 0.15,
        fade_in: float = 2.0,
        fade_out: float = 3.0
    ) -> Optional[Path]:
        """
        Mix voice audio with background music.

        Args:
            voice_path: Path to TTS voice audio
            output_path: Where to save mixed audio
            music_path: Path to music file (or None for random)
            music_volume: Music volume relative to voice (0.0-1.0)
            fade_in: Fade in duration for music (seconds)
            fade_out: Fade out duration for music (seconds)

        Returns:
            Path to mixed audio file, or None if failed
        """
        voice_path = Path(voice_path)
        output_path = Path(output_path)

        if not voice_path.exists():
            print(f">>> Mixer: Voice file not found: {voice_path}", flush=True)
            return None

        # Get music file
        if music_path is None:
            music_path = self.get_random_music()
            if music_path:
                print(f">>> Mixer: Using random music: {music_path.name}", flush=True)

        if not music_path or not music_path.exists():
            print(f">>> Mixer: No music available, copying voice only", flush=True)
            # Just copy the voice file
            import shutil
            shutil.copy(voice_path, output_path)
            return output_path

        print(f">>> Mixer: Mixing voice with '{music_path.name}' at {music_volume*100:.0f}% volume", flush=True)

        try:
            # Get voice duration using ffprobe
            duration_cmd = [
                'ffprobe', '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                str(voice_path)
            ]
            result = subprocess.run(duration_cmd, capture_output=True, text=True, timeout=30)
            voice_duration = float(result.stdout.strip())
            print(f">>> Mixer: Voice duration: {voice_duration:.1f}s", flush=True)

            # Build FFmpeg filter for mixing
            # - Loop music if needed
            # - Apply volume to music
            # - Fade in/out music
            # - Mix with voice
            filter_complex = (
                f"[1:a]aloop=loop=-1:size=2e+09,atrim=0:{voice_duration + fade_out},"
                f"afade=t=in:st=0:d={fade_in},"
                f"afade=t=out:st={voice_duration - fade_out}:d={fade_out},"
                f"volume={music_volume}[music];"
                f"[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[out]"
            )

            cmd = [
                'ffmpeg', '-y',
                '-i', str(voice_path),
                '-i', str(music_path),
                '-filter_complex', filter_complex,
                '-map', '[out]',
                '-c:a', 'libmp3lame',
                '-b:a', '192k',
                str(output_path)
            ]

            print(f">>> Mixer: Running FFmpeg...", flush=True)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                print(f">>> Mixer: FFmpeg error: {result.stderr[:200]}", flush=True)
                logger.error(f"FFmpeg mix failed: {result.stderr}")
                return None

            print(f">>> Mixer: Saved mixed audio to {output_path}", flush=True)
            return output_path

        except FileNotFoundError:
            print(f">>> Mixer: FFmpeg not found!", flush=True)
            logger.error("FFmpeg not found")
            return None
        except Exception as e:
            print(f">>> Mixer: Error - {e}", flush=True)
            logger.error(f"Audio mixing failed: {e}")
            return None

    def mix_for_youtube(
        self,
        voice_path: Path,
        title: str,
        music_path: Optional[Path] = None,
        music_volume: float = 0.12
    ) -> Optional[Path]:
        """
        Mix audio specifically for YouTube video.

        Args:
            voice_path: Path to TTS audio
            title: Video title (for filename)
            music_path: Background music (or None for random)
            music_volume: Music volume (default 12%)

        Returns:
            Path to mixed audio
        """
        voice_path = Path(voice_path)

        # Create output path
        output_dir = Path("output/audio_mixed")
        output_dir.mkdir(parents=True, exist_ok=True)

        safe_title = "".join(c for c in title[:30] if c.isalnum() or c in ' -_').strip()
        safe_title = safe_title.replace(' ', '_')
        date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = output_dir / f"mixed_{safe_title}_{date_str}.mp3"

        return self.mix_audio(
            voice_path=voice_path,
            output_path=output_path,
            music_path=music_path,
            music_volume=music_volume,
            fade_in=2.0,
            fade_out=4.0
        )
