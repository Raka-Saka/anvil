"""
Cover Image Generator - Create cover images for blog posts.

Uses Pillow for local image generation.
Optionally uses Unsplash API for content-relevant background images.
Standard size: 1200x630 (works across all platforms).
"""

import logging
import requests
from pathlib import Path
from typing import Optional
from datetime import datetime
from io import BytesIO

logger = logging.getLogger(__name__)

# Try to import Pillow
try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False
    Image = None
    ImageDraw = None
    ImageFont = None


class CoverImageGenerator:
    """Generate cover images for blog posts."""

    # Standard cover image size (works across platforms)
    WIDTH = 1200
    HEIGHT = 630

    # Colors (dark theme)
    COLORS = {
        'background': '#1a1a2e',      # Dark blue-black
        'title': '#ffffff',            # White
        'subtitle': '#a0a0a0',         # Gray
        'accent': '#e94560',           # Red accent (ChronOS brand)
        'gradient_start': '#16213e',   # Dark blue
        'gradient_end': '#0f0f23',     # Darker blue
    }

    # Tag to search query mapping (for better Unsplash results)
    TAG_QUERIES = {
        'osdev': 'computer circuit board',
        'programming': 'code programming',
        'debugging': 'maze puzzle',
        'memory': 'computer ram circuit',
        'interrupts': 'lightning electricity',
        'bootloader': 'rocket launch',
        'kernel': 'core nucleus abstract',
        'assembly': 'gears machinery',
        'uefi': 'motherboard technology',
        'lowlevel': 'microchip circuit',
        'x86_64': 'processor cpu chip',
        'ai': 'artificial intelligence neural',
        'machinelearning': 'neural network brain',
        'lora': 'digital art abstract',
    }

    # Font sizes
    TITLE_SIZE = 56
    SUBTITLE_SIZE = 28
    BRAND_SIZE = 24

    def __init__(self, fonts_dir: Optional[Path] = None, unsplash_key: Optional[str] = None):
        """
        Initialize cover image generator.

        Args:
            fonts_dir: Directory containing custom fonts (optional)
            unsplash_key: Unsplash API access key for dynamic backgrounds
        """
        self.fonts_dir = fonts_dir
        self.unsplash_key = unsplash_key
        self._title_font = None
        self._subtitle_font = None
        self._brand_font = None

        # Try to load unsplash key from config if not provided
        if not self.unsplash_key:
            self._load_unsplash_key()

    def _load_unsplash_key(self):
        """Load Unsplash API key from config file."""
        try:
            import yaml
            # Try relative path first (from working dir)
            config_path = Path("config/api_keys.yaml")
            if not config_path.exists():
                # Try path relative to this file
                config_path = Path(__file__).parent.parent / "config" / "api_keys.yaml"

            print(f">>> Cover: Config path: {config_path}", flush=True)
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f) or {}
                self.unsplash_key = config.get('unsplash', {}).get('access_key')
                if self.unsplash_key:
                    print(f">>> Cover: Unsplash key loaded!", flush=True)
                else:
                    print(f">>> Cover: No unsplash.access_key in config", flush=True)
            else:
                print(f">>> Cover: Config file not found at {config_path}", flush=True)
        except Exception as e:
            print(f">>> Cover: Error loading config: {e}", flush=True)

    def _search_unsplash(self, query: str) -> Optional[str]:
        """
        Search Unsplash for an image and return the URL.

        Args:
            query: Search query

        Returns:
            URL of image or None
        """
        if not self.unsplash_key:
            return None

        try:
            url = "https://api.unsplash.com/search/photos"
            params = {
                'query': query,
                'per_page': 1,
                'orientation': 'landscape',
            }
            headers = {
                'Authorization': f'Client-ID {self.unsplash_key}'
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            if data.get('results'):
                # Get the regular size image (good quality, not too large)
                return data['results'][0]['urls']['regular']

        except Exception as e:
            logger.warning(f"Unsplash search failed: {e}")

        return None

    def _download_image(self, url: str) -> Optional[Image.Image]:
        """Download image from URL."""
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            return Image.open(BytesIO(response.content))
        except Exception as e:
            logger.warning(f"Image download failed: {e}")
            return None

    def _get_search_query(self, tags: list[str]) -> str:
        """Convert tags to a good Unsplash search query."""
        # Check if any tags have a mapped query
        for tag in tags:
            tag_lower = tag.lower().lstrip('#')
            if tag_lower in self.TAG_QUERIES:
                return self.TAG_QUERIES[tag_lower]

        # Otherwise use first few tags
        clean_tags = [t.lstrip('#') for t in tags[:3]]
        return ' '.join(clean_tags) + ' technology'

    def _create_overlay_background(self, bg_image: Image.Image) -> Image.Image:
        """
        Process background image: resize, darken, and add gradient overlay.
        """
        # Resize to cover dimensions (crop to fit)
        img_ratio = bg_image.width / bg_image.height
        target_ratio = self.WIDTH / self.HEIGHT

        if img_ratio > target_ratio:
            # Image is wider - fit height, crop width
            new_height = self.HEIGHT
            new_width = int(new_height * img_ratio)
        else:
            # Image is taller - fit width, crop height
            new_width = self.WIDTH
            new_height = int(new_width / img_ratio)

        bg_image = bg_image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Center crop
        left = (new_width - self.WIDTH) // 2
        top = (new_height - self.HEIGHT) // 2
        bg_image = bg_image.crop((left, top, left + self.WIDTH, top + self.HEIGHT))

        # Keep image bright (minimal darkening)
        enhancer = ImageEnhance.Brightness(bg_image)
        bg_image = enhancer.enhance(0.85)  # 85% brightness - almost full

        # Minimal overlay - just enough for white text to be readable
        gradient = Image.new('RGBA', (self.WIDTH, self.HEIGHT), (0, 0, 0, 0))
        gradient_draw = ImageDraw.Draw(gradient)

        # Very light gradient - only where text appears
        for y in range(self.HEIGHT):
            if y < self.HEIGHT // 5:
                # Top area (brand/date) - light shadow
                alpha = int(80 - (y / (self.HEIGHT // 5)) * 50)
            elif y > self.HEIGHT * 4 // 5:
                # Bottom area (accent line)
                alpha = int(30 + ((y - self.HEIGHT * 4 // 5) / (self.HEIGHT // 5)) * 40)
            else:
                # Middle (title area) - minimal overlay
                alpha = 25
            gradient_draw.line([(0, y), (self.WIDTH, y)], fill=(0, 0, 0, alpha))

        # Convert to RGBA if needed
        if bg_image.mode != 'RGBA':
            bg_image = bg_image.convert('RGBA')

        # Composite
        bg_image = Image.alpha_composite(bg_image, gradient)

        return bg_image.convert('RGB')

    def is_available(self) -> bool:
        """Check if Pillow is installed."""
        return HAS_PILLOW

    def _get_font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        """Get a font at specified size."""
        if not HAS_PILLOW:
            return None

        # Try custom fonts first
        if self.fonts_dir:
            font_name = "NotoSans-Bold.ttf" if bold else "NotoSans-Regular.ttf"
            font_path = self.fonts_dir / font_name
            if font_path.exists():
                try:
                    return ImageFont.truetype(str(font_path), size)
                except Exception:
                    pass

        # Try system fonts
        system_fonts = [
            # Windows
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            # Linux
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            # macOS
            "/System/Library/Fonts/Helvetica.ttc",
        ]

        for font_path in system_fonts:
            if Path(font_path).exists():
                try:
                    return ImageFont.truetype(font_path, size)
                except Exception:
                    continue

        # Fallback to default
        return ImageFont.load_default()

    def _hex_to_rgb(self, hex_color: str) -> tuple:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
        """Wrap text to fit within max_width."""
        if not HAS_PILLOW:
            return [text]

        words = text.split()
        lines = []
        current_line = []

        # Create temporary image for text measurement
        temp_img = Image.new('RGB', (1, 1))
        temp_draw = ImageDraw.Draw(temp_img)

        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = temp_draw.textbbox((0, 0), test_line, font=font)
            width = bbox[2] - bbox[0]

            if width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]

        if current_line:
            lines.append(' '.join(current_line))

        return lines

    def generate(
        self,
        title: str,
        subtitle: Optional[str] = None,
        brand: str = "ChronOS Dev Diary",
        date: Optional[datetime] = None,
        output_path: Optional[Path] = None,
        style: str = "gradient",
        tags: Optional[list[str]] = None,
        use_unsplash: bool = True
    ) -> Optional[Path]:
        """
        Generate a cover image.

        Args:
            title: Main title text
            subtitle: Optional subtitle
            brand: Brand name to display
            date: Date to display (defaults to today)
            output_path: Where to save the image
            style: Visual style ('gradient', 'solid', 'minimal') - fallback if no Unsplash
            tags: Article tags for Unsplash search
            use_unsplash: Whether to try Unsplash for background

        Returns:
            Path to generated image, or None if failed
        """
        if not HAS_PILLOW:
            logger.error("Pillow not installed. Run: pip install Pillow")
            return None

        if date is None:
            date = datetime.now()

        # Try to get Unsplash background if enabled and configured
        bg_image = None
        self.last_unsplash_url = None  # Store for blog platforms
        print(f">>> Cover: use_unsplash={use_unsplash}, has_key={bool(self.unsplash_key)}, tags={tags}", flush=True)
        if use_unsplash and self.unsplash_key and tags:
            query = self._get_search_query(tags)
            print(f">>> Unsplash searching: '{query}'", flush=True)
            image_url = self._search_unsplash(query)
            if image_url:
                self.last_unsplash_url = image_url  # Save URL for blog platforms
                print(f">>> Unsplash found! URL: {image_url[:60]}...", flush=True)
                print(f">>> Downloading for local processing...", flush=True)
                bg_image = self._download_image(image_url)
                if bg_image:
                    print(f">>> Processing background (darken + overlay)...", flush=True)
                    bg_image = self._create_overlay_background(bg_image)
                    print(f">>> Unsplash background ready!", flush=True)
                else:
                    print(f">>> Unsplash download failed, using gradient", flush=True)
            else:
                print(f">>> Unsplash no results, using gradient", flush=True)
        elif not self.unsplash_key:
            print(f">>> No Unsplash key configured, using gradient", flush=True)

        # Create base image
        if bg_image:
            img = bg_image
        else:
            img = Image.new('RGB', (self.WIDTH, self.HEIGHT), self._hex_to_rgb(self.COLORS['background']))
            # Draw background based on style
            if style == 'gradient':
                self._draw_gradient(img)
            elif style == 'minimal':
                draw = ImageDraw.Draw(img)
                self._draw_minimal_background(draw)

        draw = ImageDraw.Draw(img)

        # Draw accent elements
        self._draw_accent_elements(draw)

        # Get fonts
        title_font = self._get_font(self.TITLE_SIZE, bold=True)
        subtitle_font = self._get_font(self.SUBTITLE_SIZE)
        brand_font = self._get_font(self.BRAND_SIZE)

        # Calculate text positions
        margin = 80
        max_text_width = self.WIDTH - (margin * 2)

        # Draw brand text at top
        brand_y = 50
        draw.text(
            (margin, brand_y),
            brand,
            font=brand_font,
            fill=self._hex_to_rgb(self.COLORS['accent'])
        )

        # Draw date
        date_text = date.strftime("%B %d, %Y")
        date_bbox = draw.textbbox((0, 0), date_text, font=brand_font)
        date_width = date_bbox[2] - date_bbox[0]
        draw.text(
            (self.WIDTH - margin - date_width, brand_y),
            date_text,
            font=brand_font,
            fill=self._hex_to_rgb(self.COLORS['subtitle'])
        )

        # Wrap and draw title (centered vertically)
        title_lines = self._wrap_text(title, title_font, max_text_width)
        line_height = self.TITLE_SIZE + 10

        # Calculate total title height
        total_title_height = len(title_lines) * line_height
        title_start_y = (self.HEIGHT - total_title_height) // 2

        for i, line in enumerate(title_lines[:3]):  # Max 3 lines
            y = title_start_y + (i * line_height)
            draw.text(
                (margin, y),
                line,
                font=title_font,
                fill=self._hex_to_rgb(self.COLORS['title'])
            )

        # Draw subtitle if provided
        if subtitle:
            subtitle_y = title_start_y + total_title_height + 20
            subtitle_lines = self._wrap_text(subtitle, subtitle_font, max_text_width)
            for i, line in enumerate(subtitle_lines[:2]):  # Max 2 lines
                y = subtitle_y + (i * (self.SUBTITLE_SIZE + 5))
                draw.text(
                    (margin, y),
                    line,
                    font=subtitle_font,
                    fill=self._hex_to_rgb(self.COLORS['subtitle'])
                )

        # Draw bottom accent line
        draw.rectangle(
            [(0, self.HEIGHT - 8), (self.WIDTH, self.HEIGHT)],
            fill=self._hex_to_rgb(self.COLORS['accent'])
        )

        # Save image
        if output_path is None:
            output_dir = Path("output/covers")
            output_dir.mkdir(parents=True, exist_ok=True)
            safe_title = "".join(c for c in title[:30] if c.isalnum() or c in ' -_').strip()
            safe_title = safe_title.replace(' ', '_')
            output_path = output_dir / f"cover_{safe_title}_{date.strftime('%Y%m%d')}.png"

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        img.save(output_path, 'PNG', quality=95)
        logger.info(f"Generated cover image: {output_path}")

        return output_path

    def _draw_gradient(self, img: Image.Image):
        """Draw gradient background."""
        start_color = self._hex_to_rgb(self.COLORS['gradient_start'])
        end_color = self._hex_to_rgb(self.COLORS['gradient_end'])

        for y in range(self.HEIGHT):
            ratio = y / self.HEIGHT
            r = int(start_color[0] + (end_color[0] - start_color[0]) * ratio)
            g = int(start_color[1] + (end_color[1] - start_color[1]) * ratio)
            b = int(start_color[2] + (end_color[2] - start_color[2]) * ratio)

            for x in range(self.WIDTH):
                img.putpixel((x, y), (r, g, b))

    def _draw_minimal_background(self, draw: ImageDraw.Draw):
        """Draw minimal background with subtle pattern."""
        # Just a subtle border
        draw.rectangle(
            [(20, 20), (self.WIDTH - 20, self.HEIGHT - 20)],
            outline=self._hex_to_rgb(self.COLORS['accent']),
            width=2
        )

    def _draw_accent_elements(self, draw: ImageDraw.Draw):
        """Draw accent geometric elements."""
        accent = self._hex_to_rgb(self.COLORS['accent'])

        # Top-left corner accent
        draw.rectangle([(0, 0), (5, 100)], fill=accent)

        # Small decorative squares
        draw.rectangle([(self.WIDTH - 150, self.HEIGHT - 150), (self.WIDTH - 140, self.HEIGHT - 140)], fill=accent)
        draw.rectangle([(self.WIDTH - 120, self.HEIGHT - 120), (self.WIDTH - 100, self.HEIGHT - 100)], fill=accent)

    def generate_for_article(
        self,
        article_title: str,
        article_date: Optional[datetime] = None,
        tags: Optional[list[str]] = None,
        output_dir: Optional[Path] = None
    ) -> Optional[Path]:
        """
        Generate cover image specifically for a diary article.

        Args:
            article_title: Article title
            article_date: Article date
            tags: Article tags (used for subtitle)
            output_dir: Output directory

        Returns:
            Path to generated image
        """
        subtitle = None
        if tags:
            # Use first 3 tags as subtitle
            subtitle = " | ".join(f"#{tag}" for tag in tags[:3])

        if output_dir:
            safe_title = "".join(c for c in article_title[:30] if c.isalnum() or c in ' -_').strip()
            safe_title = safe_title.replace(' ', '_')
            date_str = (article_date or datetime.now()).strftime('%Y%m%d')
            output_path = Path(output_dir) / f"cover_{safe_title}_{date_str}.png"
        else:
            output_path = None

        return self.generate(
            title=article_title,
            subtitle=subtitle,
            date=article_date,
            output_path=output_path,
            tags=tags  # Pass tags for Unsplash search
        )
