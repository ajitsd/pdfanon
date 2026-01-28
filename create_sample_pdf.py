"""
Generate a sample PDF with fake PII for testing the anonymizer.
Run this to create a test file if you don't have a PDF handy.
"""

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def create_sample_pdf(filename: str = "sample_with_pii.pdf"):
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, height - 72, "Sample Document with PII")
    
    # Sample content with various PII types
    c.setFont("Helvetica", 12)
    
    content = [
        "EMPLOYEE RECORDS - CONFIDENTIAL",
        "",
        "Employee: John Michael Smith",
        "Email: john.smith@acmecorp.com",
        "Phone: (415) 555-1234",
        "Social Security Number: 123-45-6789",
        "Date of Birth: March 15, 1985",
        "",
        "Emergency Contact: Sarah Johnson",
        "Contact Phone: 650-555-9876",
        "Contact Email: sarah.j@gmail.com",
        "",
        "Banking Information:",
        "Account Holder: John M. Smith",
        "Credit Card: 4532-1234-5678-9012",
        "",
        "Office Location: 123 Market Street, San Francisco, CA 94105",
        "IP Address (VPN): 192.168.1.100",
        "",
        "Notes:",
        "John Smith joined the company on January 10, 2020.",
        "His manager is Dr. Emily Chen (emily.chen@acmecorp.com).",
        "He can be reached at john.smith@acmecorp.com or (415) 555-1234.",
    ]
    
    y_position = height - 120
    for line in content:
        c.drawString(72, y_position, line)
        y_position -= 20
    
    c.save()
    print(f"Created sample PDF: {filename}")


if __name__ == "__main__":
    # Check if reportlab is available
    try:
        create_sample_pdf()
    except ImportError:
        print("reportlab not installed. Install with: pip install reportlab")
        print("Or just use your own PDF for testing.")
