# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PDF PII Anonymizer - A Python utility for reversibly pseudonymizing Personally Identifiable Information (PII) in PDF documents. Designed to sanitize documents before sending to LLMs, then restore original values in responses.

## Development Commands

```bash
# Setup (first time)
chmod +x setup.sh && ./setup.sh

# Or manual setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_lg

# Run anonymization
python anonymizer.py anonymize <input.pdf> <output.txt>

# Reverse anonymization (restore original values)
python anonymizer.py reverse <input.txt> <output.txt>

# View current PII mappings
python anonymizer.py mappings

# Generate sample test PDF
python create_sample_pdf.py
```

## Architecture

### Core Components

**ReversibleAnonymizer** (`anonymizer.py`) - Single class handling the complete pipeline:
- `extract_text_from_pdf()` - Uses PyMuPDF (fitz) for text extraction
- `analyze_text()` - Presidio ML-based PII detection (13 entity types)
- `anonymize_text()` - Replaces PII with pseudonyms like `[PERSON_001]`
- `reverse_text()` - Restores original values from mapping
- `process_pdf()` - Orchestrates the full pipeline

### Data Flow

```
PDF → extract text → detect PII → replace with pseudonyms → save output
                                                          → save mappings (pii_mapping.json)
```

### Key Design Decisions

1. **Bidirectional Mappings**: Same PII value always maps to same pseudonym (enables consistent reversal)
2. **Position-Preserving Replacement**: Replaces from end→start to avoid offset shifts during iteration
3. **Entity Prefixes**: Human-readable pseudonyms (`[EMAIL_ADDRESS_001]` not `[PII_xyz]`)
4. **Stateless CLI**: JSON mapping file enables independent operations

### Dependencies

- **PyMuPDF (fitz)**: PDF text extraction (text-only, no OCR)
- **presidio-analyzer/anonymizer**: Microsoft's ML-based PII detection (~95% accuracy)
- **spaCy (en_core_web_lg)**: NLP foundation for Presidio

### Supported PII Types

PERSON, EMAIL_ADDRESS, PHONE_NUMBER, CREDIT_CARD, US_SSN, US_DRIVER_LICENSE, IP_ADDRESS, DATE_TIME, LOCATION, IBAN_CODE, US_BANK_NUMBER, US_PASSPORT

## Known Limitations

- Text-only PDFs (scanned documents require OCR preprocessing)
- Presidio detection is ~95% accurate - SSNs and credit cards may not always be detected
- Mapping file stored as plaintext JSON (secure appropriately in production)
