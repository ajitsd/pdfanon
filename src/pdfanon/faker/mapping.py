"""Bidirectional mapping storage for PII anonymization."""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from .generator import DeterministicFakeGenerator


@dataclass
class PIIMapping:
    """Represents a single PII mapping."""
    original: str
    fake: str
    entity_type: str
    document: str
    timestamp: str


class MappingStore:
    """
    Thread-safe bidirectional mapping storage.

    Stores mappings between original PII values and their fake replacements,
    enabling both anonymization and reversal.
    """

    def __init__(self, mapping_file: Path):
        self.mapping_file = mapping_file
        self.original_to_fake: Dict[str, PIIMapping] = {}
        self.fake_to_original: Dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        """Load existing mappings from file."""
        if self.mapping_file.exists():
            try:
                with open(self.mapping_file, "r") as f:
                    data = json.load(f)

                # Handle both old format (simple dict) and new format (with metadata)
                if "mappings" in data:
                    # New format with metadata
                    for mapping_data in data["mappings"]:
                        mapping = PIIMapping(**mapping_data)
                        self.original_to_fake[mapping.original] = mapping
                        self.fake_to_original[mapping.fake] = mapping.original
                else:
                    # Old format: original_to_pseudo / pseudo_to_original
                    old_o2p = data.get("original_to_pseudo", {})
                    for original, fake in old_o2p.items():
                        mapping = PIIMapping(
                            original=original,
                            fake=fake,
                            entity_type="UNKNOWN",
                            document="migrated",
                            timestamp=datetime.now().isoformat(),
                        )
                        self.original_to_fake[original] = mapping
                        self.fake_to_original[fake] = original
            except (json.JSONDecodeError, KeyError):
                # Corrupted file, start fresh
                pass

    def save(self) -> None:
        """Save mappings to file."""
        self.mapping_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": "2.0",
            "created": datetime.now().isoformat(),
            "mappings": [asdict(m) for m in self.original_to_fake.values()],
            # Also save in old format for backwards compatibility
            "original_to_pseudo": {m.original: m.fake for m in self.original_to_fake.values()},
            "pseudo_to_original": self.fake_to_original,
        }

        with open(self.mapping_file, "w") as f:
            json.dump(data, f, indent=2)

    def get_fake(self, original: str) -> Optional[str]:
        """Get existing fake value for an original."""
        mapping = self.original_to_fake.get(original)
        return mapping.fake if mapping else None

    def get_original(self, fake: str) -> Optional[str]:
        """Get original value for a fake."""
        return self.fake_to_original.get(fake)

    def get_or_create_fake(
        self,
        original: str,
        entity_type: str,
        generator: DeterministicFakeGenerator,
        document: str = "",
    ) -> str:
        """
        Get existing fake value or generate a new one.

        Args:
            original: The original PII value
            entity_type: The Presidio entity type
            generator: The fake data generator
            document: Source document name for traceability

        Returns:
            The fake replacement value
        """
        # Normalize the original value
        normalized = original.strip()

        # Return existing if we've seen this value
        existing = self.get_fake(normalized)
        if existing:
            return existing

        # Generate new fake value
        fake = generator.generate(normalized, entity_type)

        # Handle collision (unlikely but possible)
        collision_count = 0
        original_fake = fake
        while fake in self.fake_to_original:
            collision_count += 1
            # Regenerate with modified input
            fake = generator.generate(f"{normalized}_{collision_count}", entity_type)
            if collision_count > 100:
                # Safety valve - use a unique suffix
                fake = f"{original_fake}_{collision_count}"
                break

        # Create and store mapping
        mapping = PIIMapping(
            original=normalized,
            fake=fake,
            entity_type=entity_type,
            document=document,
            timestamp=datetime.now().isoformat(),
        )
        self.original_to_fake[normalized] = mapping
        self.fake_to_original[fake] = normalized

        return fake

    def get_all_mappings(self) -> Dict[str, str]:
        """Get all original -> fake mappings."""
        return {m.original: m.fake for m in self.original_to_fake.values()}

    def get_all_reverse_mappings(self) -> Dict[str, str]:
        """Get all fake -> original mappings."""
        return dict(self.fake_to_original)

    def get_mappings_list(self) -> list:
        """Get all mappings as a list of dicts for display."""
        return [
            {
                "original": m.original,
                "fake": m.fake,
                "type": m.entity_type,
                "document": m.document,
            }
            for m in self.original_to_fake.values()
        ]

    def __len__(self) -> int:
        return len(self.original_to_fake)
