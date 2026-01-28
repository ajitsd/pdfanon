"""
PDF PII Anonymizer with Reversible Pseudonymization
Uses Microsoft Presidio for detection and custom mapping for reversibility.

Usage:
    python anonymizer.py anonymize input.pdf output.txt
    python anonymizer.py reverse output.txt restored.txt
"""

import json
import sys
import uuid
from pathlib import Path
from typing import Dict, List, Tuple

import fitz  # PyMuPDF
from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig


class ReversibleAnonymizer:
    """Handles PII detection and reversible pseudonymization."""
    
    def __init__(self, mapping_file: str = "pii_mapping.json"):
        self.mapping_file = Path(mapping_file)
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        
        # Mapping dictionaries
        self.original_to_pseudo: Dict[str, str] = {}
        self.pseudo_to_original: Dict[str, str] = {}
        
        # Entity type prefixes for readable pseudonyms
        self.entity_prefixes = {
            "PERSON": "PERSON",
            "EMAIL_ADDRESS": "EMAIL",
            "PHONE_NUMBER": "PHONE",
            "CREDIT_CARD": "CARD",
            "US_SSN": "SSN",
            "US_DRIVER_LICENSE": "LICENSE",
            "IP_ADDRESS": "IP",
            "DATE_TIME": "DATE",
            "NRP": "NRP",  # Nationality, Religion, Political group
            "LOCATION": "LOCATION",
            "IBAN_CODE": "IBAN",
            "US_BANK_NUMBER": "BANK",
            "US_PASSPORT": "PASSPORT",
            "MEDICAL_LICENSE": "MEDLIC",
        }
        
        # Load existing mappings if available
        self._load_mappings()
    
    def _load_mappings(self):
        """Load existing mappings from file."""
        if self.mapping_file.exists():
            with open(self.mapping_file, "r") as f:
                data = json.load(f)
                self.original_to_pseudo = data.get("original_to_pseudo", {})
                self.pseudo_to_original = data.get("pseudo_to_original", {})
                print(f"Loaded {len(self.original_to_pseudo)} existing mappings")
    
    def _save_mappings(self):
        """Save mappings to file for later reversal."""
        with open(self.mapping_file, "w") as f:
            json.dump({
                "original_to_pseudo": self.original_to_pseudo,
                "pseudo_to_original": self.pseudo_to_original
            }, f, indent=2)
        print(f"Saved {len(self.original_to_pseudo)} mappings to {self.mapping_file}")
    
    def _get_pseudonym(self, original: str, entity_type: str) -> str:
        """Get or create a pseudonym for the given original value."""
        # Normalize the original (strip whitespace, consistent casing for lookup)
        normalized = original.strip()
        
        # Return existing pseudonym if we've seen this value before
        if normalized in self.original_to_pseudo:
            return self.original_to_pseudo[normalized]
        
        # Create new pseudonym
        prefix = self.entity_prefixes.get(entity_type, "PII")
        counter = sum(1 for k in self.pseudo_to_original if k.startswith(f"[{prefix}_")) + 1
        pseudonym = f"[{prefix}_{counter:03d}]"
        
        # Store bidirectional mapping
        self.original_to_pseudo[normalized] = pseudonym
        self.pseudo_to_original[pseudonym] = normalized
        
        return pseudonym
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract all text from a PDF file."""
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        text_parts = []
        with fitz.open(pdf_path) as doc:
            for page_num, page in enumerate(doc, 1):
                text = page.get_text()
                if text.strip():
                    text_parts.append(f"--- Page {page_num} ---\n{text}")
        
        full_text = "\n\n".join(text_parts)
        print(f"Extracted {len(full_text)} characters from {len(text_parts)} pages")
        return full_text
    
    def analyze_text(self, text: str, language: str = "en") -> List[RecognizerResult]:
        """Detect PII entities in text."""
        results = self.analyzer.analyze(
            text=text,
            language=language,
            # Detect common PII types
            entities=[
                "PERSON",
                "EMAIL_ADDRESS", 
                "PHONE_NUMBER",
                "CREDIT_CARD",
                "US_SSN",
                "US_DRIVER_LICENSE",
                "IP_ADDRESS",
                "DATE_TIME",
                "LOCATION",
                "IBAN_CODE",
                "US_BANK_NUMBER",
                "US_PASSPORT",
            ]
        )
        print(f"Found {len(results)} PII entities")
        return results
    
    def anonymize_text(self, text: str, results: List[RecognizerResult]) -> str:
        """Replace detected PII with pseudonyms."""
        if not results:
            return text
        
        # Sort results by start position (descending) to replace from end to start
        # This preserves character positions during replacement
        sorted_results = sorted(results, key=lambda x: x.start, reverse=True)
        
        anonymized = text
        for result in sorted_results:
            original_value = text[result.start:result.end]
            pseudonym = self._get_pseudonym(original_value, result.entity_type)
            anonymized = anonymized[:result.start] + pseudonym + anonymized[result.end:]
        
        # Save mappings after processing
        self._save_mappings()
        
        return anonymized
    
    def reverse_text(self, anonymized_text: str) -> str:
        """Reverse pseudonymization using stored mappings."""
        if not self.pseudo_to_original:
            print("Warning: No mappings loaded. Cannot reverse.")
            return anonymized_text
        
        restored = anonymized_text
        for pseudonym, original in self.pseudo_to_original.items():
            restored = restored.replace(pseudonym, original)
        
        return restored
    
    def process_pdf(self, pdf_path: str, output_path: str) -> Tuple[str, str]:
        """Full pipeline: PDF -> extracted text -> anonymized text."""
        # Extract text
        original_text = self.extract_text_from_pdf(pdf_path)
        
        # Detect PII
        results = self.analyze_text(original_text)
        
        # Print what we found
        print("\nDetected PII:")
        print("-" * 50)
        for r in sorted(results, key=lambda x: x.start):
            original_value = original_text[r.start:r.end]
            print(f"  {r.entity_type}: '{original_value}' (confidence: {r.score:.2f})")
        print("-" * 50)
        
        # Anonymize
        anonymized_text = self.anonymize_text(original_text, results)
        
        # Save anonymized text
        output_path = Path(output_path)
        with open(output_path, "w") as f:
            f.write(anonymized_text)
        print(f"\nAnonymized text saved to: {output_path}")
        
        return original_text, anonymized_text
    
    def print_mapping_summary(self):
        """Print current mappings for review."""
        print("\nCurrent PII Mappings:")
        print("=" * 60)
        for original, pseudo in self.original_to_pseudo.items():
            # Truncate long values for display
            display_original = original[:40] + "..." if len(original) > 40 else original
            print(f"  {pseudo:20} <- {display_original}")
        print("=" * 60)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        print("\nCommands:")
        print("  anonymize <input.pdf> <output.txt>  - Anonymize PDF and save text")
        print("  reverse <input.txt> <output.txt>    - Reverse anonymization")
        print("  mappings                            - Show current mappings")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    anonymizer = ReversibleAnonymizer()
    
    if command == "anonymize":
        if len(sys.argv) < 4:
            print("Usage: python anonymizer.py anonymize <input.pdf> <output.txt>")
            sys.exit(1)
        
        input_pdf = sys.argv[2]
        output_txt = sys.argv[3]
        
        print(f"Processing: {input_pdf}")
        original, anonymized = anonymizer.process_pdf(input_pdf, output_txt)
        
        anonymizer.print_mapping_summary()
        
        print("\n✓ Done! You can now safely send the anonymized text to an LLM.")
        print(f"  Anonymized file: {output_txt}")
        print(f"  Mapping file: {anonymizer.mapping_file}")
    
    elif command == "reverse":
        if len(sys.argv) < 4:
            print("Usage: python anonymizer.py reverse <input.txt> <output.txt>")
            sys.exit(1)
        
        input_txt = sys.argv[2]
        output_txt = sys.argv[3]
        
        with open(input_txt, "r") as f:
            anonymized_text = f.read()
        
        restored_text = anonymizer.reverse_text(anonymized_text)
        
        with open(output_txt, "w") as f:
            f.write(restored_text)
        
        print(f"✓ Restored text saved to: {output_txt}")
    
    elif command == "mappings":
        anonymizer.print_mapping_summary()
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
