# PDF PII Anonymizer

A CLI tool for reversibly anonymizing PII in PDFs using realistic fake data.

**Use case**: Safely sanitize documents before sharing, then restore original values when needed.

---

## Installation

### Option A: pipx (Recommended for global CLI)

```bash
cd pdf_anonymizer
pipx install .

# The spaCy model downloads automatically on first run
```

### Option B: pip in virtual environment

```bash
cd pdf_anonymizer
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

---

## Usage

### Anonymize a PDF

```bash
# Single file - outputs sample_with_pii_anonymized.pdf
pdfanon anonymize document.pdf

# With verbose output showing detected PII
pdfanon anonymize document.pdf --verbose

# Specify output path
pdfanon anonymize document.pdf -o safe_document.pdf

# Output as text instead of PDF
pdfanon anonymize document.pdf --format txt
```

### Anonymize a directory of PDFs

```bash
# Process all PDFs in a folder
pdfanon anonymize ./documents/

# Specify output directory
pdfanon anonymize ./documents/ -o ./anonymized_docs/
```

### Reverse anonymization

```bash
# Restore original values using the mapping file
pdfanon reverse document_anonymized.pdf

# Specify mapping file
pdfanon reverse document_anonymized.pdf -m my_mapping.json
```

### View mappings

```bash
# Display as table
pdfanon mappings

# Export as JSON
pdfanon mappings --format json

# Export as CSV
pdfanon mappings --format csv
```

---

## What PII is detected?

| Type | Example | Replacement |
|------|---------|-------------|
| Person names | John Smith | Michael Davis |
| Email addresses | john@example.com | mdavis@example.org |
| Phone numbers | (415) 555-1234 | (312) 555-8976 |
| Social Security Numbers | 123-45-6789 | 456-78-9012 |
| Credit card numbers | 4532-1234-5678-9012 | 5412-9876-5432-1098 |
| IP addresses | 192.168.1.100 | 10.45.67.89 |
| Dates | March 15, 1985 | July 22, 1979 |
| Locations | San Francisco | Austin |
| Driver's license | D1234567 | F9876543 |

---

## Example Workflow

### 1. Original PDF contains:
```
Employee: John Smith
Email: john.smith@acme.com
Phone: (415) 555-1234
```

### 2. Anonymized PDF contains:
```
Employee: Michael Davis
Email: mdavis@example.org
Phone: (312) 555-8976
```

### 3. Mapping file (pii_mapping.json):
```json
{
  "original_to_pseudo": {
    "John Smith": "Michael Davis",
    "john.smith@acme.com": "mdavis@example.org"
  }
}
```

### 4. Reverse when needed:
```bash
pdfanon reverse anonymized.pdf -o restored.pdf
```

---

## Important Notes

### Security
- **Keep `pii_mapping.json` secure** - it contains the real PII values
- Don't commit the mapping file to version control
- Delete mapping files when no longer needed

### Accuracy
- Presidio uses ML models - ~95% accurate but not perfect
- Review anonymized output before sharing
- Some entities like SSNs may need pattern customization

### Limitations
- Text-based PDFs only (not scanned/image PDFs)
- PDF formatting may change during anonymization
- For scanned PDFs, use OCR first (e.g., pytesseract)

---

## CLI Reference

```
pdfanon --help
pdfanon --version

pdfanon anonymize --help
  -o, --output PATH      Output path
  -m, --mapping PATH     Mapping file (default: pii_mapping.json)
  -s, --seed INT         Random seed for reproducible fake data
  -f, --format TEXT      Output format: pdf or txt
  --verbose              Show detected PII details

pdfanon reverse --help
  -o, --output PATH      Output path
  -m, --mapping PATH     Mapping file
  -f, --format TEXT      Output format: pdf or txt

pdfanon mappings --help
  -m, --mapping PATH     Mapping file
  -f, --format TEXT      Output format: table, json, or csv
```

---

## Legacy Script

The original `anonymizer.py` script is still available for backwards compatibility:

```bash
source venv/bin/activate
python anonymizer.py anonymize input.pdf output.txt
python anonymizer.py reverse output.txt restored.txt
python anonymizer.py mappings
```

Note: The legacy script uses placeholder format `[PERSON_001]` instead of realistic fake data.

---

## License

MIT - Use freely for personal and commercial projects.
