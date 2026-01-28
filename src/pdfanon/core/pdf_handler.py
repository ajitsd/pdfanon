"""PDF reading and writing with anonymization support."""

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pymupdf


class PDFHandler:
    """Handles PDF reading and writing with text replacement."""

    def extract_text(self, pdf_path: Path) -> str:
        """
        Extract all text from a PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Extracted text with page markers
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        text_parts = []
        with pymupdf.open(str(pdf_path)) as doc:
            for page_num, page in enumerate(doc, 1):
                text = page.get_text()
                if text.strip():
                    text_parts.append(f"--- Page {page_num} ---\n{text}")

        return "\n\n".join(text_parts)

    def extract_text_by_page(self, pdf_path: Path) -> List[Tuple[int, str]]:
        """
        Extract text from each page separately.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            List of (page_number, text) tuples
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        pages = []
        with pymupdf.open(str(pdf_path)) as doc:
            for page_num, page in enumerate(doc, 1):
                text = page.get_text()
                pages.append((page_num, text))

        return pages

    def create_anonymized_pdf(
        self,
        input_path: Path,
        output_path: Path,
        replacements: Dict[str, str],
    ) -> bool:
        """
        Create an anonymized PDF by replacing text.

        Uses PyMuPDF's redaction API to search for and replace text.

        Args:
            input_path: Path to the original PDF
            output_path: Path for the anonymized PDF
            replacements: Dict mapping original values to fake values

        Returns:
            True if successful, False if fallback to text needed
        """
        if not input_path.exists():
            raise FileNotFoundError(f"PDF not found: {input_path}")

        try:
            doc = pymupdf.open(str(input_path))

            for page in doc:
                for original, fake in replacements.items():
                    # Search for all instances of the original text
                    instances = page.search_for(original)

                    for rect in instances:
                        # Add redaction annotation with replacement text
                        page.add_redact_annot(
                            rect,
                            text=fake,
                            fill=(1, 1, 1),  # White background
                        )

                # Apply all redactions on this page
                page.apply_redactions()

            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(output_path))
            doc.close()
            return True

        except Exception as e:
            # Log the error but don't fail - caller can fall back to text
            print(f"Warning: PDF modification failed ({e}). Consider using text output.")
            return False

    def create_pdf_from_text(
        self,
        text: str,
        output_path: Path,
        font_size: int = 11,
    ) -> None:
        """
        Create a simple PDF from text content.

        Used as fallback when PDF modification fails.

        Args:
            text: Text content to write
            output_path: Path for the output PDF
            font_size: Font size in points
        """
        doc = pymupdf.open()

        # Split text into pages (roughly 60 lines per page)
        lines = text.split('\n')
        lines_per_page = 55

        for i in range(0, len(lines), lines_per_page):
            page_lines = lines[i:i + lines_per_page]
            page_text = '\n'.join(page_lines)

            # Create new page (Letter size: 612 x 792 points)
            page = doc.new_page(width=612, height=792)

            # Insert text with margins
            rect = pymupdf.Rect(50, 50, 562, 742)
            page.insert_textbox(
                rect,
                page_text,
                fontsize=font_size,
                fontname="helv",  # Helvetica
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_path))
        doc.close()

    def save_text(self, text: str, output_path: Path) -> None:
        """
        Save text to a file.

        Args:
            text: Text content
            output_path: Path for the output file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text)
