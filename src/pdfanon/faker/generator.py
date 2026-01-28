"""Deterministic fake data generator for PII replacement."""

import hashlib
import re
from datetime import datetime
from typing import Optional

from faker import Faker


class DeterministicFakeGenerator:
    """
    Generate consistent fake data for the same input.

    Uses hash-based seeding to ensure the same original value
    always produces the same fake value (required for reversibility).
    """

    def __init__(self, base_seed: int = 42, locale: str = "en_US"):
        self.base_seed = base_seed
        self.locale = locale
        self.faker = Faker(locale)

    def _get_seed_for_value(self, original_value: str) -> int:
        """Generate deterministic seed from original value."""
        hash_bytes = hashlib.sha256(original_value.encode()).digest()
        return int.from_bytes(hash_bytes[:4], 'big') ^ self.base_seed

    def generate(self, original_value: str, entity_type: str) -> str:
        """
        Generate fake data deterministically based on original value.

        Args:
            original_value: The original PII value to replace
            entity_type: The Presidio entity type (PERSON, EMAIL_ADDRESS, etc.)

        Returns:
            A realistic fake replacement value
        """
        seed = self._get_seed_for_value(original_value)
        self.faker.seed_instance(seed)

        generators = {
            "PERSON": self._fake_person,
            "EMAIL_ADDRESS": self._fake_email,
            "PHONE_NUMBER": self._fake_phone,
            "US_SSN": self._fake_ssn,
            "DATE_TIME": self._fake_date,
            "LOCATION": self._fake_location,
            "US_DRIVER_LICENSE": self._fake_drivers_license,
            "CREDIT_CARD": self._fake_credit_card,
            "IP_ADDRESS": self._fake_ip,
            "IBAN_CODE": self._fake_iban,
            "US_BANK_NUMBER": self._fake_bank_number,
            "US_PASSPORT": self._fake_passport,
        }

        generator = generators.get(entity_type, self._fake_generic)
        return generator(original_value)

    def _fake_person(self, original: str) -> str:
        """Generate a fake person name."""
        # Try to match the format (first only, first last, first middle last)
        parts = original.split()
        if len(parts) == 1:
            return self.faker.first_name()
        elif len(parts) == 2:
            return self.faker.name()
        else:
            # Full name with possible middle name
            return f"{self.faker.first_name()} {self.faker.first_name()} {self.faker.last_name()}"

    def _fake_email(self, original: str) -> str:
        """Generate a fake email address."""
        return self.faker.email()

    def _fake_phone(self, original: str) -> str:
        """Generate a fake phone number matching the original format."""
        # Detect format patterns
        if original.startswith("("):
            return f"({self.faker.random_int(200, 999)}) {self.faker.random_int(200, 999)}-{self.faker.random_int(1000, 9999)}"
        elif "-" in original and not original.startswith("+"):
            parts = original.split("-")
            if len(parts) == 3:
                return f"{self.faker.random_int(200, 999)}-{self.faker.random_int(200, 999)}-{self.faker.random_int(1000, 9999)}"
            else:
                return self.faker.phone_number()
        else:
            return self.faker.phone_number()

    def _fake_ssn(self, original: str) -> str:
        """Generate a fake SSN in the same format."""
        # SSN format: XXX-XX-XXXX
        area = self.faker.random_int(100, 999)
        group = self.faker.random_int(10, 99)
        serial = self.faker.random_int(1000, 9999)

        if "-" in original:
            return f"{area}-{group}-{serial}"
        else:
            return f"{area}{group}{serial}"

    def _fake_date(self, original: str) -> str:
        """Generate a fake date trying to match the original format."""
        fake_date = self.faker.date_of_birth(minimum_age=18, maximum_age=80)

        # Try to detect and match common date formats
        formats_to_try = [
            ("%B %d, %Y", lambda d: d.strftime("%B %d, %Y")),  # March 15, 1985
            ("%m/%d/%Y", lambda d: d.strftime("%m/%d/%Y")),    # 03/15/1985
            ("%Y-%m-%d", lambda d: d.strftime("%Y-%m-%d")),    # 1985-03-15
            ("%d/%m/%Y", lambda d: d.strftime("%d/%m/%Y")),    # 15/03/1985
            ("%m-%d-%Y", lambda d: d.strftime("%m-%d-%Y")),    # 03-15-1985
        ]

        for date_format, formatter in formats_to_try:
            try:
                datetime.strptime(original, date_format)
                return formatter(fake_date)
            except ValueError:
                continue

        # Check for month name patterns
        month_pattern = r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\b'
        if re.search(month_pattern, original):
            return fake_date.strftime("%B %d, %Y")

        # Default format
        return fake_date.strftime("%B %d, %Y")

    def _fake_location(self, original: str) -> str:
        """Generate a fake location/address."""
        # Check if it looks like a full address or just a city/state
        if "," in original:
            parts = original.split(",")
            if len(parts) == 2:
                # City, State format
                return f"{self.faker.city()}, {self.faker.state_abbr()}"
            else:
                # Full address
                return self.faker.address().replace("\n", ", ")
        else:
            # Just a city or location name
            return self.faker.city()

    def _fake_drivers_license(self, original: str) -> str:
        """Generate a fake driver's license number."""
        # Format varies by state, generate a generic one
        letter = self.faker.random_uppercase_letter()
        numbers = self.faker.random_int(1000000, 9999999)
        return f"{letter}{numbers}"

    def _fake_credit_card(self, original: str) -> str:
        """Generate a fake credit card number in the same format."""
        cc = self.faker.credit_card_number()

        # Match original format (dashes, spaces, or none)
        if "-" in original:
            return "-".join([cc[i:i+4] for i in range(0, 16, 4)])
        elif " " in original:
            return " ".join([cc[i:i+4] for i in range(0, 16, 4)])
        else:
            return cc[:16]

    def _fake_ip(self, original: str) -> str:
        """Generate a fake IP address."""
        if ":" in original:
            return self.faker.ipv6()
        else:
            return self.faker.ipv4()

    def _fake_iban(self, original: str) -> str:
        """Generate a fake IBAN."""
        return self.faker.iban()

    def _fake_bank_number(self, original: str) -> str:
        """Generate a fake bank account number."""
        length = len(re.sub(r'\D', '', original))
        if length == 0:
            length = 10
        return ''.join([str(self.faker.random_int(0, 9)) for _ in range(length)])

    def _fake_passport(self, original: str) -> str:
        """Generate a fake passport number."""
        # US passport format: letter followed by 8 digits
        letter = self.faker.random_uppercase_letter()
        numbers = self.faker.random_int(10000000, 99999999)
        return f"{letter}{numbers}"

    def _fake_generic(self, original: str) -> str:
        """Fallback generator for unknown entity types."""
        # Generate a string of similar length with random words
        return self.faker.text(max_nb_chars=len(original))[:len(original)]
