"""Main anonymization pipeline orchestrator."""

from pathlib import Path
from typing import List, Optional, Tuple

from ..faker.generator import DeterministicFakeGenerator
from ..faker.mapping import MappingStore
from .detector import PIIDetector
from .pdf_handler import PDFHandler


class Anonymizer:
    """
    Orchestrates the PDF anonymization pipeline.

    Coordinates PII detection, fake data generation, and PDF output.
    """

    def __init__(
        self,
        mapping_file: Path,
        seed: int = 42,
        language: str = "en",
    ):
        self.mapping_file = mapping_file
        self.mapping_store = MappingStore(mapping_file)
        self.detector = PIIDetector(language=language)
        self.generator = DeterministicFakeGenerator(base_seed=seed)
        self.pdf_handler = PDFHandler()

    def anonymize_pdf(
        self,
        input_path: Path,
        output_path: Path,
        output_format: str = "pdf",
    ) -> Tuple[int, List[dict]]:
        """
        Anonymize a PDF file.

        Args:
            input_path: Path to the input PDF
            output_path: Path for the anonymized output
            output_format: "pdf" or "txt"

        Returns:
            Tuple of (number of entities replaced, list of detection results)
        """
        # Extract text from PDF
        text = self.pdf_handler.extract_text(input_path)

        # Detect PII
        detections = self.detector.detect_with_context(text)

        if not detections:
            # No PII found, copy original
            if output_format == "pdf":
                import shutil
                output_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(input_path, output_path)
            else:
                self.pdf_handler.save_text(text, output_path)
            return 0, []

        # Generate fake replacements for each detected PII
        replacements = {}
        for detection in detections:
            original = detection["value"]
            entity_type = detection["entity_type"]

            fake = self.mapping_store.get_or_create_fake(
                original=original,
                entity_type=entity_type,
                generator=self.generator,
                document=input_path.name,
            )
            replacements[original] = fake

        # Save mappings
        self.mapping_store.save()

        # Create anonymized output
        if output_format == "pdf":
            success = self.pdf_handler.create_anonymized_pdf(
                input_path, output_path, replacements
            )
            if not success:
                # Fallback to text-based PDF
                anonymized_text = self._replace_text(text, replacements)
                self.pdf_handler.create_pdf_from_text(anonymized_text, output_path)
        else:
            anonymized_text = self._replace_text(text, replacements)
            self.pdf_handler.save_text(anonymized_text, output_path)

        return len(detections), detections

    def _replace_text(self, text: str, replacements: dict) -> str:
        """Replace all occurrences in text."""
        result = text
        # Sort by length (longest first) to avoid partial replacements
        for original in sorted(replacements.keys(), key=len, reverse=True):
            result = result.replace(original, replacements[original])
        return result

    def reverse_pdf(
        self,
        input_path: Path,
        output_path: Path,
        output_format: str = "pdf",
    ) -> int:
        """
        Reverse anonymization using stored mappings.

        Args:
            input_path: Path to the anonymized file (PDF or text)
            output_path: Path for the restored output
            output_format: "pdf" or "txt"

        Returns:
            Number of replacements made
        """
        # Read the anonymized content
        if input_path.suffix.lower() == ".pdf":
            text = self.pdf_handler.extract_text(input_path)
        else:
            text = input_path.read_text()

        # Get reverse mappings
        reverse_map = self.mapping_store.get_all_reverse_mappings()

        if not reverse_map:
            raise ValueError(
                f"No mappings found in {self.mapping_file}. "
                "Cannot reverse anonymization without the mapping file."
            )

        # Replace fake values with originals
        restored_text = text
        replacements_made = 0
        for fake, original in reverse_map.items():
            if fake in restored_text:
                restored_text = restored_text.replace(fake, original)
                replacements_made += 1

        # Save output
        if output_format == "pdf":
            self.pdf_handler.create_pdf_from_text(restored_text, output_path)
        else:
            self.pdf_handler.save_text(restored_text, output_path)

        return replacements_made

    def get_mapping_count(self) -> int:
        """Get the number of stored mappings."""
        return len(self.mapping_store)

    def get_mappings(self) -> list:
        """Get all mappings for display."""
        return self.mapping_store.get_mappings_list()


def process_directory(
    input_dir: Path,
    output_dir: Path,
    mapping_file: Path,
    output_format: str = "pdf",
    seed: int = 42,
    progress_callback=None,
) -> List[Tuple[Path, int, Optional[str]]]:
    """
    Process all PDFs in a directory.

    Args:
        input_dir: Directory containing PDF files
        output_dir: Directory for anonymized output
        mapping_file: Path for the shared mapping file
        output_format: "pdf" or "txt"
        seed: Random seed for consistent fake data
        progress_callback: Optional callback(current, total, filename)

    Returns:
        List of (file_path, entities_found, error_message) tuples
    """
    # Find all PDFs
    pdf_files = list(input_dir.glob("**/*.pdf"))

    if not pdf_files:
        return []

    results = []
    anonymizer = Anonymizer(mapping_file=mapping_file, seed=seed)

    for i, pdf_path in enumerate(pdf_files):
        if progress_callback:
            progress_callback(i, len(pdf_files), pdf_path.name)

        # Compute relative path for output
        relative_path = pdf_path.relative_to(input_dir)
        if output_format == "pdf":
            output_path = output_dir / relative_path
        else:
            output_path = output_dir / relative_path.with_suffix(".txt")

        try:
            count, _ = anonymizer.anonymize_pdf(
                pdf_path, output_path, output_format
            )
            results.append((pdf_path, count, None))
        except Exception as e:
            results.append((pdf_path, 0, str(e)))

    if progress_callback:
        progress_callback(len(pdf_files), len(pdf_files), "Done")

    return results
