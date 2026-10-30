"""
Cover Letter Exporter - Export cover letters to multiple formats.

Formats:
- PDF: Professional format for applications
- DOCX: Microsoft Word, recruiter-friendly
- HTML: Web format with styling
- TXT: Plain text, maximum compatibility
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


class CoverLetterExporter:
    """Export cover letter content to various formats."""

    SUPPORTED_FORMATS = ['pdf', 'docx', 'html', 'txt', 'md']

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = Path(output_dir) if output_dir else Path("output/cover_letters")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_available_formats(self) -> list[dict]:
        """Get list of available export formats with status."""
        formats = [
            {
                'format': 'pdf',
                'name': 'PDF',
                'description': 'Professional format for applications',
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
                'description': 'Maximum compatibility',
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
        Export cover letter content to specified format.

        Args:
            content: Cover letter content as plain text
            format: Export format (pdf, docx, html, txt, md)
            filename: Optional filename (without extension)
            metadata: Optional metadata (company, role, applicant_name, etc.)

        Returns:
            Path to exported file, or None if failed
        """
        format = format.lower()
        if format not in self.SUPPORTED_FORMATS:
            logger.error(f"Unsupported format: {format}")
            return None

        # Generate filename: Position_Company_ApplicantName_Date
        if not filename:
            date_str = datetime.now().strftime("%Y%m%d")
            company = metadata.get('company', 'Company') if metadata else 'Company'
            role = metadata.get('role', 'Position') if metadata else 'Position'
            applicant = metadata.get('applicant_name', 'Applicant') if metadata else 'Applicant'

            # Clean names for filesystem
            safe_role = re.sub(r'[^\w\s-]', '', role).replace(' ', '_')
            safe_company = re.sub(r'[^\w\s-]', '', company).replace(' ', '_')
            safe_applicant = re.sub(r'[^\w\s-]', '', applicant).replace(' ', '_')

            filename = f"CoverLetter_{safe_role}_{safe_company}_{safe_applicant}_{date_str}"

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

        # Pre-process content to remove problematic Unicode
        content = self._sanitize_for_pdf(content)

        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        # Set margins
        pdf.set_left_margin(25)
        pdf.set_right_margin(25)

        # Add date at top right
        pdf.set_font("Helvetica", size=10)
        pdf.set_x(pdf.l_margin)
        date_str = datetime.now().strftime("%B %d, %Y")
        pdf.cell(0, 10, date_str, new_x="LMARGIN", new_y="NEXT", align='R')
        pdf.ln(5)

        # Process content
        paragraphs = content.split('\n\n')

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Check if it's a greeting (Dear X,)
            if para.startswith('Dear '):
                pdf.set_font("Helvetica", size=11)
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(0, 6, para)
                pdf.ln(3)
                continue

            # Check if it's the signature (just a name, short line)
            if len(para.split()) <= 3 and not para.endswith('.'):
                pdf.ln(5)
                pdf.set_font("Helvetica", size=11)
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(0, 6, para)
                continue

            # Regular paragraph
            pdf.set_font("Helvetica", size=11)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, 6, para)
            pdf.ln(3)

        output_path = self.output_dir / f"{filename}.pdf"
        pdf.output(str(output_path))
        logger.info(f"Exported PDF: {output_path}")
        return output_path

    def _sanitize_for_pdf(self, content: str) -> str:
        """Remove or replace Unicode characters that can't be rendered in PDF."""
        replacements = {
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

        # Remove any remaining non-ASCII characters
        result = []
        for char in content:
            if ord(char) < 128:
                result.append(char)
            elif char in replacements:
                result.append(replacements[char])

        return ''.join(result)

    def _export_docx(self, content: str, filename: str, metadata: dict = None) -> Optional[Path]:
        """Export to DOCX format."""
        if not HAS_DOCX:
            logger.error("python-docx not installed. Run: pip install python-docx")
            return None

        doc = Document()

        # Set margins
        for section in doc.sections:
            section.top_margin = Inches(1)
            section.bottom_margin = Inches(1)
            section.left_margin = Inches(1.25)
            section.right_margin = Inches(1.25)

        # Add date
        date_para = doc.add_paragraph()
        date_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        date_run = date_para.add_run(datetime.now().strftime("%B %d, %Y"))
        date_run.font.size = Pt(11)

        doc.add_paragraph()  # Spacing

        # Process content
        paragraphs = content.split('\n\n')

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Handle single newlines within paragraph
            para = para.replace('\n', ' ')

            p = doc.add_paragraph()
            run = p.add_run(para)
            run.font.size = Pt(11)
            run.font.name = 'Calibri'

            # Add spacing after greeting
            if para.startswith('Dear '):
                p.paragraph_format.space_after = Pt(12)

        output_path = self.output_dir / f"{filename}.docx"
        doc.save(str(output_path))
        logger.info(f"Exported DOCX: {output_path}")
        return output_path

    def _export_html(self, content: str, filename: str, metadata: dict = None) -> Optional[Path]:
        """Export to HTML format with professional styling."""

        company = metadata.get('company', 'Company') if metadata else 'Company'
        role = metadata.get('role', 'Role') if metadata else 'Role'
        date_str = datetime.now().strftime("%B %d, %Y")

        # Convert paragraphs to HTML
        paragraphs = content.split('\n\n')
        html_paragraphs = []

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            para = para.replace('\n', '<br>')

            # Greeting
            if para.startswith('Dear '):
                html_paragraphs.append(f'<p class="greeting">{para}</p>')
            # Signature (short line, no period)
            elif len(para.split()) <= 3 and not para.endswith('.'):
                html_paragraphs.append(f'<p class="signature">{para}</p>')
            # Regular paragraph
            else:
                html_paragraphs.append(f'<p>{para}</p>')

        body_content = '\n'.join(html_paragraphs)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cover Letter - {role} at {company}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Georgia', 'Times New Roman', serif;
            font-size: 11pt;
            line-height: 1.6;
            color: #333;
            max-width: 700px;
            margin: 0 auto;
            padding: 50px 40px;
            background: #fff;
        }}
        @media print {{
            body {{
                padding: 0;
                max-width: none;
            }}
        }}
        .date {{
            text-align: right;
            margin-bottom: 30px;
            color: #555;
        }}
        .greeting {{
            margin-bottom: 20px;
        }}
        p {{
            margin-bottom: 15px;
            text-align: justify;
        }}
        .signature {{
            margin-top: 25px;
            margin-bottom: 0;
        }}
        ul {{
            margin: 10px 0 15px 25px;
        }}
        li {{
            margin-bottom: 5px;
        }}
    </style>
</head>
<body>
    <div class="date">{date_str}</div>
    {body_content}
</body>
</html>"""

        output_path = self.output_dir / f"{filename}.html"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        logger.info(f"Exported HTML: {output_path}")
        return output_path

    def _export_txt(self, content: str, filename: str, metadata: dict = None) -> Optional[Path]:
        """Export to plain text format."""
        # Add date header
        date_str = datetime.now().strftime("%B %d, %Y")
        full_content = f"{date_str}\n\n{content}"

        output_path = self.output_dir / f"{filename}.txt"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_content)
        logger.info(f"Exported TXT: {output_path}")
        return output_path

    def _export_md(self, content: str, filename: str, metadata: dict = None) -> Optional[Path]:
        """Export to Markdown format."""
        company = metadata.get('company', 'Company') if metadata else 'Company'
        role = metadata.get('role', 'Role') if metadata else 'Role'
        date_str = datetime.now().strftime("%B %d, %Y")

        # Convert to markdown
        paragraphs = content.split('\n\n')
        md_parts = []

        md_parts.append(f"# Cover Letter: {role} at {company}")
        md_parts.append(f"\n*{date_str}*\n")
        md_parts.append("---\n")

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Bullet points
            if para.startswith('- '):
                md_parts.append(para)
            else:
                md_parts.append(para)
            md_parts.append("")

        output_path = self.output_dir / f"{filename}.md"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md_parts))
        logger.info(f"Exported MD: {output_path}")
        return output_path


def export_cover_letter(content: str, format: str, filename: str = None,
                        company: str = None, role: str = None,
                        applicant_name: str = None) -> Optional[Path]:
    """Convenience function to export cover letter."""
    exporter = CoverLetterExporter()
    metadata = {
        'company': company,
        'role': role,
        'applicant_name': applicant_name
    }
    return exporter.export(content, format, filename, metadata)
