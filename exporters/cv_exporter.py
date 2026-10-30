"""
CV Exporter - Export CVs to multiple formats.

Formats:
- PDF: Professional format, most commonly requested
- DOCX: Microsoft Word, recruiter-friendly
- HTML: Web format with styling
- TXT: Plain text, maximum ATS compatibility
- MD: Markdown format
"""

import logging
from pathlib import Path
from typing import Optional
from datetime import datetime
import re

logger = logging.getLogger(__name__)

# Optional imports for different formats
try:
    from fpdf import FPDF
    HAS_FPDF = True
except ImportError:
    HAS_FPDF = False

try:
    from docx import Document
    from docx.shared import Pt, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


class CVExporter:
    """Export CV content to various formats."""

    SUPPORTED_FORMATS = ['pdf', 'docx', 'html', 'txt', 'md']

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = Path(output_dir) if output_dir else Path("output/cvs")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_available_formats(self) -> list[dict]:
        """Get list of available export formats with status."""
        formats = [
            {
                'format': 'pdf',
                'name': 'PDF',
                'description': 'Professional format, most common',
                'available': HAS_FPDF,
                'install': 'pip install fpdf2' if not HAS_FPDF else None,
            },
            {
                'format': 'docx',
                'name': 'Word (DOCX)',
                'description': 'Microsoft Word, recruiter-friendly',
                'available': HAS_DOCX,
                'install': 'pip install python-docx' if not HAS_DOCX else None,
            },
            {
                'format': 'html',
                'name': 'HTML',
                'description': 'Web format with styling',
                'available': True,
                'install': None,
            },
            {
                'format': 'txt',
                'name': 'Plain Text',
                'description': 'Maximum ATS compatibility',
                'available': True,
                'install': None,
            },
            {
                'format': 'md',
                'name': 'Markdown',
                'description': 'Developer-friendly format',
                'available': True,
                'install': None,
            },
        ]
        return formats

    def export(self, content: str, format: str, filename: Optional[str] = None,
               metadata: Optional[dict] = None) -> Optional[Path]:
        """
        Export CV content to specified format.

        Args:
            content: CV content as plain text
            format: Export format (pdf, docx, html, txt, md)
            filename: Optional filename (without extension)
            metadata: Optional metadata (name, role, etc.)

        Returns:
            Path to exported file, or None if failed
        """
        format = format.lower()
        if format not in self.SUPPORTED_FORMATS:
            logger.error(f"Unsupported format: {format}")
            return None

        # Generate filename
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name = metadata.get('name', 'CV') if metadata else 'CV'
            safe_name = re.sub(r'[^\w\s-]', '', name).replace(' ', '_')
            filename = f"{safe_name}_{timestamp}"

        # Export based on format
        exporters = {
            'pdf': self._export_pdf,
            'docx': self._export_docx,
            'html': self._export_html,
            'txt': self._export_txt,
            'md': self._export_md,
        }

        try:
            return exporters[format](content, filename, metadata)
        except Exception as e:
            logger.error(f"Export to {format} failed: {e}")
            return None

    def _export_pdf(self, content: str, filename: str, metadata: dict = None) -> Optional[Path]:
        """Export to PDF format."""
        if not HAS_FPDF:
            logger.error("fpdf2 not installed. Run: pip install fpdf2")
            return None

        # Pre-process entire content to remove problematic Unicode
        content = self._sanitize_for_pdf(content)

        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        # Set margins
        pdf.set_left_margin(15)
        pdf.set_right_margin(15)

        # Use Helvetica font
        pdf.set_font("Helvetica", size=10)

        # Parse content into sections
        lines = content.split('\n')
        is_first_line = True

        for line in lines:
            line = line.rstrip()

            # Skip empty lines at start
            if not line.strip() and is_first_line:
                continue

            # Header (name - first line, all caps)
            if is_first_line and line.strip():
                pdf.set_font("Helvetica", 'B', 16)
                pdf.cell(0, 10, line, new_x="LMARGIN", new_y="NEXT", align='C')
                pdf.set_font("Helvetica", size=10)
                is_first_line = False
                continue

            is_first_line = False

            # Section headers
            if line.startswith('-' * 20):
                continue  # Skip divider lines

            if line in ['CORE COMPETENCIES', 'SUMMARY', 'SKILLS', 'PROJECTS',
                       'EXPERIENCE', 'EDUCATION']:
                pdf.ln(5)
                pdf.set_font("Helvetica", 'B', 12)
                pdf.cell(0, 8, line, new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", size=10)
                continue

            # Subsection headers (Direct Experience, AI-Assisted, etc.)
            if line.endswith(':') and not line.startswith(' ') and len(line) < 50:
                pdf.set_font("Helvetica", 'B', 10)
                pdf.cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", size=10)
                continue

            # Bullet points
            if line.strip().startswith(('-', '*', '>')) and not line.startswith('--'):
                clean_line = line.strip().lstrip('-*> ')
                if clean_line:
                    pdf.set_x(20)
                    pdf.multi_cell(0, 5, f"- {clean_line}")
                    pdf.set_x(pdf.l_margin)  # Reset X after multi_cell
                continue

            # Empty lines
            if not line.strip():
                pdf.ln(2)
                continue

            # Job/Project headers (contain |)
            if ' | ' in line:
                pdf.set_x(pdf.l_margin)  # Reset X before multi_cell
                pdf.set_font("Helvetica", 'B', 10)
                pdf.multi_cell(0, 5, line)
                pdf.set_x(pdf.l_margin)  # Reset X after multi_cell
                pdf.set_font("Helvetica", size=10)
                continue

            # Regular lines
            pdf.set_x(pdf.l_margin)  # Reset X before multi_cell
            pdf.multi_cell(0, 5, line)

        output_path = self.output_dir / f"{filename}.pdf"
        pdf.output(str(output_path))
        logger.info(f"Exported PDF: {output_path}")
        return output_path

    def _sanitize_for_pdf(self, content: str) -> str:
        """Remove or replace Unicode characters that can't be rendered in PDF."""
        # Replace common Unicode characters with ASCII equivalents
        replacements = {
            '→': '>',
            '★': '*',
            '•': '-',
            '—': '-',
            '–': '-',
            '"': '"',
            '"': '"',
            ''': "'",
            ''': "'",
            '…': '...',
            '©': '(c)',
            '®': '(R)',
            '™': '(TM)',
            '×': 'x',
            '÷': '/',
            '≤': '<=',
            '≥': '>=',
            '≠': '!=',
            '±': '+/-',
            '°': ' deg',
            'é': 'e',
            'è': 'e',
            'ê': 'e',
            'ë': 'e',
            'à': 'a',
            'â': 'a',
            'ä': 'a',
            'ù': 'u',
            'û': 'u',
            'ü': 'u',
            'ô': 'o',
            'ö': 'o',
            'î': 'i',
            'ï': 'i',
            'ç': 'c',
            'ñ': 'n',
            'É': 'E',
            'È': 'E',
            'Ê': 'E',
            'Ë': 'E',
            'À': 'A',
            'Â': 'A',
            'Ä': 'A',
            'Ù': 'U',
            'Û': 'U',
            'Ü': 'U',
            'Ô': 'O',
            'Ö': 'O',
            'Î': 'I',
            'Ï': 'I',
            'Ç': 'C',
            'Ñ': 'N',
        }

        for old, new in replacements.items():
            content = content.replace(old, new)

        # Remove any remaining non-ASCII characters (like Japanese)
        # by replacing them with their closest approximation or removing
        result = []
        for char in content:
            if ord(char) < 128:
                result.append(char)
            elif char in replacements:
                result.append(replacements[char])
            else:
                # Skip non-ASCII characters we don't have a replacement for
                # Or replace with a placeholder
                pass

        return ''.join(result)

    def _export_docx(self, content: str, filename: str, metadata: dict = None) -> Optional[Path]:
        """Export to DOCX format."""
        if not HAS_DOCX:
            logger.error("python-docx not installed. Run: pip install python-docx")
            return None

        doc = Document()

        # Set narrow margins for more content
        for section in doc.sections:
            section.top_margin = Inches(0.5)
            section.bottom_margin = Inches(0.5)
            section.left_margin = Inches(0.75)
            section.right_margin = Inches(0.75)

        lines = content.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i].rstrip()

            # Name (first line)
            if i == 0 and line.isupper():
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = p.add_run(line)
                run.bold = True
                run.font.size = Pt(18)

            # Section headers
            elif line in ['CORE COMPETENCIES', 'SUMMARY', 'SKILLS', 'PROJECTS',
                         'EXPERIENCE', 'EDUCATION']:
                doc.add_paragraph()  # Space before
                p = doc.add_paragraph()
                run = p.add_run(line)
                run.bold = True
                run.font.size = Pt(12)
                # Skip the divider line
                if i + 1 < len(lines) and lines[i + 1].startswith('-'):
                    i += 1

            # Divider lines - skip
            elif line.startswith('-' * 10):
                pass

            # Subsection headers
            elif line.endswith(':') and not line.startswith(' '):
                p = doc.add_paragraph()
                run = p.add_run(line)
                run.bold = True
                run.font.size = Pt(10)

            # Bullet points
            elif line.strip().startswith(('→', '•', '-')):
                clean = line.strip().lstrip('→•- ')
                p = doc.add_paragraph(clean, style='List Bullet')
                p.paragraph_format.left_indent = Inches(0.25)

            # Job titles (contain | )
            elif ' | ' in line and not line.startswith(' '):
                p = doc.add_paragraph()
                run = p.add_run(line.replace('★ ', ''))
                run.bold = True
                run.font.size = Pt(10)

            # Empty lines
            elif not line.strip():
                pass  # Skip empty lines

            # Regular text
            else:
                p = doc.add_paragraph(line)
                p.paragraph_format.space_after = Pt(2)

            i += 1

        output_path = self.output_dir / f"{filename}.docx"
        doc.save(str(output_path))
        logger.info(f"Exported DOCX: {output_path}")
        return output_path

    def _export_html(self, content: str, filename: str, metadata: dict = None) -> Optional[Path]:
        """Export to HTML format with professional styling."""

        name = metadata.get('name', 'CV') if metadata else 'CV'

        # Convert content to HTML
        html_content = self._text_to_html(content)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{name} - CV</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.5;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 40px 20px;
            background: #fff;
        }}
        @media print {{
            body {{
                padding: 0;
                max-width: none;
            }}
        }}
        .header {{
            text-align: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #2c3e50;
        }}
        .name {{
            font-size: 28px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 5px;
        }}
        .title {{
            font-size: 16px;
            color: #34495e;
            margin-bottom: 5px;
        }}
        .tagline {{
            font-size: 14px;
            color: #7f8c8d;
            font-style: italic;
        }}
        .contact {{
            font-size: 13px;
            color: #555;
            margin-top: 10px;
        }}
        .contact a {{
            color: #3498db;
            text-decoration: none;
        }}
        .section {{
            margin: 20px 0;
        }}
        .section-title {{
            font-size: 14px;
            font-weight: bold;
            color: #2c3e50;
            text-transform: uppercase;
            letter-spacing: 1px;
            border-bottom: 1px solid #bdc3c7;
            padding-bottom: 5px;
            margin-bottom: 10px;
        }}
        .competencies {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin: 10px 0;
        }}
        .competency {{
            background: #ecf0f1;
            padding: 4px 10px;
            border-radius: 3px;
            font-size: 12px;
            color: #2c3e50;
        }}
        .summary {{
            font-size: 14px;
            line-height: 1.6;
            color: #444;
        }}
        .subsection {{
            font-weight: bold;
            font-size: 13px;
            color: #34495e;
            margin: 15px 0 8px 0;
        }}
        ul {{
            list-style: none;
            padding-left: 0;
        }}
        li {{
            font-size: 13px;
            margin: 5px 0;
            padding-left: 15px;
            position: relative;
        }}
        li::before {{
            content: "→";
            position: absolute;
            left: 0;
            color: #3498db;
        }}
        .job {{
            margin: 15px 0;
        }}
        .job-header {{
            font-weight: bold;
            font-size: 14px;
            color: #2c3e50;
        }}
        .job-meta {{
            font-size: 12px;
            color: #7f8c8d;
            margin-bottom: 5px;
        }}
        .project {{
            margin: 12px 0;
        }}
        .project-name {{
            font-weight: bold;
            font-size: 13px;
            color: #2c3e50;
        }}
        .ai-tag {{
            background: #9b59b6;
            color: white;
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 3px;
            margin-left: 5px;
        }}
        .highlight {{
            color: #f39c12;
        }}
    </style>
</head>
<body>
{html_content}
</body>
</html>"""

        output_path = self.output_dir / f"{filename}.html"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        logger.info(f"Exported HTML: {output_path}")
        return output_path

    def _text_to_html(self, content: str) -> str:
        """Convert plain text CV to HTML structure."""
        lines = content.split('\n')
        html_parts = []
        current_section = None
        in_list = False

        i = 0
        while i < len(lines):
            line = lines[i].rstrip()

            # Name (first line)
            if i == 0:
                html_parts.append('<div class="header">')
                html_parts.append(f'<div class="name">{line}</div>')
                i += 1
                # Title
                if i < len(lines):
                    html_parts.append(f'<div class="title">{lines[i]}</div>')
                    i += 1
                # Tagline
                if i < len(lines):
                    html_parts.append(f'<div class="tagline">{lines[i]}</div>')
                    i += 1
                # Skip empty line
                while i < len(lines) and not lines[i].strip():
                    i += 1
                # Contact
                if i < len(lines):
                    html_parts.append(f'<div class="contact">{lines[i]}</div>')
                    i += 1
                # GitHub
                if i < len(lines) and 'github' in lines[i].lower():
                    url = lines[i].strip()
                    html_parts.append(f'<div class="contact"><a href="{url}">{url}</a></div>')
                    i += 1
                html_parts.append('</div>')
                continue

            # Section headers
            if line in ['CORE COMPETENCIES', 'SUMMARY', 'SKILLS', 'PROJECTS',
                       'EXPERIENCE', 'EDUCATION']:
                if in_list:
                    html_parts.append('</ul>')
                    in_list = False
                current_section = line
                html_parts.append(f'<div class="section">')
                html_parts.append(f'<div class="section-title">{line}</div>')
                # Skip divider
                i += 1
                if i < len(lines) and lines[i].startswith('-'):
                    i += 1
                continue

            # Skip dividers
            if line.startswith('-' * 10):
                i += 1
                continue

            # Core Competencies content
            if current_section == 'CORE COMPETENCIES' and line.strip():
                keywords = [k.strip() for k in line.replace('|', ',').split(',') if k.strip()]
                if keywords:
                    html_parts.append('<div class="competencies">')
                    for kw in keywords:
                        html_parts.append(f'<span class="competency">{kw}</span>')
                    html_parts.append('</div>')
                i += 1
                continue

            # Summary content
            if current_section == 'SUMMARY' and line.strip():
                html_parts.append(f'<p class="summary">{line}</p>')
                html_parts.append('</div>')
                current_section = None
                i += 1
                continue

            # Subsection headers
            if line.endswith(':') and not line.startswith(' '):
                if in_list:
                    html_parts.append('</ul>')
                    in_list = False
                html_parts.append(f'<div class="subsection">{line}</div>')
                i += 1
                continue

            # Project names
            if current_section == 'PROJECTS' and line and not line.startswith(' ') and not line.startswith('→'):
                if in_list:
                    html_parts.append('</ul>')
                    in_list = False
                ai_tag = '<span class="ai-tag">AI-assisted</span>' if '[AI-assisted]' in line else ''
                name = line.replace('[AI-assisted]', '').strip()
                html_parts.append(f'<div class="project"><span class="project-name">{name}</span>{ai_tag}</div>')
                i += 1
                continue

            # Job headers
            if current_section == 'EXPERIENCE' and ' | ' in line and not line.startswith(' '):
                if in_list:
                    html_parts.append('</ul>')
                    in_list = False
                highlight = '★' in line
                clean_line = line.replace('★ ', '')
                cls = 'job-header highlight' if highlight else 'job-header'
                html_parts.append(f'<div class="job"><div class="{cls}">{clean_line}</div>')
                # Next line is meta
                i += 1
                if i < len(lines):
                    html_parts.append(f'<div class="job-meta">{lines[i]}</div>')
                i += 1
                continue

            # Bullet points
            if line.strip().startswith(('→', '•', '-')):
                if not in_list:
                    html_parts.append('<ul>')
                    in_list = True
                clean = line.strip().lstrip('→•- ')
                html_parts.append(f'<li>{clean}</li>')
                i += 1
                continue

            # Empty lines close sections
            if not line.strip():
                if in_list:
                    html_parts.append('</ul>')
                    in_list = False
                i += 1
                continue

            # Regular text
            if line.strip():
                html_parts.append(f'<p>{line}</p>')

            i += 1

        # Close any open elements
        if in_list:
            html_parts.append('</ul>')

        return '\n'.join(html_parts)

    def _export_txt(self, content: str, filename: str, metadata: dict = None) -> Optional[Path]:
        """Export to plain text format (ATS-optimized)."""
        # Clean up any special characters for maximum compatibility
        clean_content = content
        clean_content = clean_content.replace('→', '-')
        clean_content = clean_content.replace('★', '*')
        clean_content = clean_content.replace('•', '-')

        output_path = self.output_dir / f"{filename}.txt"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(clean_content)
        logger.info(f"Exported TXT: {output_path}")
        return output_path

    def _export_md(self, content: str, filename: str, metadata: dict = None) -> Optional[Path]:
        """Export to Markdown format."""
        lines = content.split('\n')
        md_lines = []

        for line in lines:
            # Name (first line)
            if line.isupper() and not md_lines:
                md_lines.append(f"# {line}")
            # Section headers
            elif line in ['CORE COMPETENCIES', 'SUMMARY', 'SKILLS', 'PROJECTS',
                         'EXPERIENCE', 'EDUCATION']:
                md_lines.append(f"\n## {line}")
            # Dividers
            elif line.startswith('-' * 10):
                continue  # Skip dividers in MD
            # Subsection headers
            elif line.endswith(':') and not line.startswith(' '):
                md_lines.append(f"\n### {line[:-1]}")
            # Bullet points
            elif line.strip().startswith(('→', '•')):
                clean = line.strip().lstrip('→• ')
                md_lines.append(f"- {clean}")
            # Job/Project headers with pipe
            elif ' | ' in line and not line.startswith(' '):
                clean = line.replace('★ ', '**★** ')
                md_lines.append(f"\n**{clean}**")
            else:
                md_lines.append(line)

        output_path = self.output_dir / f"{filename}.md"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md_lines))
        logger.info(f"Exported MD: {output_path}")
        return output_path


def export_cv(content: str, format: str, filename: str = None) -> Optional[Path]:
    """Convenience function to export CV."""
    exporter = CVExporter()
    return exporter.export(content, format, filename)
