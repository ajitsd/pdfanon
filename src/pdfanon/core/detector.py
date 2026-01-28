"""PII detection using Microsoft Presidio."""

import subprocess
import sys
from typing import List, Optional

from presidio_analyzer import AnalyzerEngine, RecognizerResult


# Supported entity types for detection
SUPPORTED_ENTITIES = [
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


def ensure_spacy_model(model_name: str = "en_core_web_lg") -> None:
    """Ensure spaCy model is installed, download if needed."""
    try:
        import spacy
        spacy.load(model_name)
    except OSError:
        print(f"Downloading spaCy model '{model_name}' (this may take a few minutes)...")
        subprocess.run(
            [sys.executable, "-m", "spacy", "download", model_name],
            check=True
        )
        print(f"Model '{model_name}' downloaded successfully.")


class PIIDetector:
    """Detects PII entities in text using Presidio."""

    def __init__(self, language: str = "en"):
        self.language = language
        ensure_spacy_model()
        self.analyzer = AnalyzerEngine()

    def detect(
        self,
        text: str,
        entities: Optional[List[str]] = None,
    ) -> List[RecognizerResult]:
        """
        Detect PII entities in the given text.

        Args:
            text: Text to analyze
            entities: List of entity types to detect (defaults to SUPPORTED_ENTITIES)

        Returns:
            List of RecognizerResult with detected entities
        """
        if entities is None:
            entities = SUPPORTED_ENTITIES

        results = self.analyzer.analyze(
            text=text,
            language=self.language,
            entities=entities,
        )
        return results

    def detect_with_context(
        self,
        text: str,
        entities: Optional[List[str]] = None,
    ) -> List[dict]:
        """
        Detect PII and return results with extracted values.

        Args:
            text: Text to analyze
            entities: List of entity types to detect

        Returns:
            List of dicts with entity_type, value, start, end, score
        """
        results = self.detect(text, entities)

        return [
            {
                "entity_type": r.entity_type,
                "value": text[r.start:r.end],
                "start": r.start,
                "end": r.end,
                "score": r.score,
            }
            for r in results
        ]
