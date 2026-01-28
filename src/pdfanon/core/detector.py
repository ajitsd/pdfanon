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

# Minimum character length for each entity type to reduce false positives
MIN_LENGTH_BY_ENTITY = {
    "PERSON": 4,            # "ng" (2 chars) will be filtered
    "LOCATION": 5,          # "TX", "IA", "MD" (2-3 chars) will be filtered
    "DATE_TIME": 6,         # Avoid "2025" (4 chars) false positives
    "US_DRIVER_LICENSE": 7, # "T3", "T4" (2 chars) will be filtered
    "EMAIL_ADDRESS": 6,
    "PHONE_NUMBER": 7,
    "CREDIT_CARD": 13,
    "US_SSN": 9,
    "IP_ADDRESS": 7,
    "IBAN_CODE": 15,
    "US_BANK_NUMBER": 6,
    "US_PASSPORT": 6,
}

# Minimum confidence score by entity type
MIN_CONFIDENCE_BY_ENTITY = {
    "PERSON": 0.7,          # Higher threshold for names
    "LOCATION": 0.7,        # Higher for locations
    "DATE_TIME": 0.8,       # Higher for dates (many false positives)
    "US_DRIVER_LICENSE": 0.5,
    "EMAIL_ADDRESS": 0.8,
    "PHONE_NUMBER": 0.6,
    "CREDIT_CARD": 0.7,
    "US_SSN": 0.5,
    "IP_ADDRESS": 0.7,
    "IBAN_CODE": 0.7,
    "US_BANK_NUMBER": 0.3,
    "US_PASSPORT": 0.5,
}
DEFAULT_MIN_CONFIDENCE = 0.6

# Common false positives to ignore (case-insensitive)
BLOCKLIST = {
    # Medical abbreviations
    "tibc", "t3", "t4", "im", "iv", "ng", "mg", "dl", "ml", "ul",
    "mcg", "iu", "ph", "hba1c", "ldl", "hdl", "alt", "ast", "bun",
    "gfr", "tsh", "psa", "wbc", "rbc", "hgb", "hct", "mcv", "mch",
    "rdw", "mpv", "plt",
    # Common short words
    "in", "on", "at", "to", "of", "is", "it", "as", "or", "an",
    # Units and measurements
    "range", "reference", "normal", "high", "low", "final", "status",
}

# US state abbreviations - often falsely detected as locations
STATE_ABBREVS = {
    "tx", "ca", "fl", "md", "ny", "pa", "il", "oh", "ga", "nc",
    "mi", "nj", "va", "wa", "az", "ma", "tn", "in", "mo", "wi",
    "mn", "co", "al", "sc", "la", "ky", "or", "ok", "ct", "ia",
    "ut", "nv", "ar", "ms", "ks", "nm", "ne", "wv", "id", "hi",
    "nh", "me", "ri", "mt", "de", "sd", "nd", "ak", "dc", "vt", "wy",
}


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

    def _filter_results(
        self,
        results: List[RecognizerResult],
        text: str,
    ) -> List[RecognizerResult]:
        """
        Filter out false positive PII detections.

        Applies minimum length, confidence thresholds, and blocklist filtering.
        """
        filtered = []

        for r in results:
            value = text[r.start:r.end]
            entity_type = r.entity_type

            # Check minimum length
            min_len = MIN_LENGTH_BY_ENTITY.get(entity_type, 3)
            if len(value) < min_len:
                continue

            # Check confidence threshold
            min_conf = MIN_CONFIDENCE_BY_ENTITY.get(entity_type, DEFAULT_MIN_CONFIDENCE)
            if r.score < min_conf:
                continue

            # Check blocklist
            if value.lower().strip() in BLOCKLIST:
                continue

            # For LOCATION, also check state abbreviations (standalone only)
            if entity_type == "LOCATION" and value.lower() in STATE_ABBREVS:
                continue

            filtered.append(r)

        return filtered

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

        # Apply filtering to reduce false positives
        results = self._filter_results(results, text)

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
