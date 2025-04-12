from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import tempfile
import logging

# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def generate_pdf(text, filename="extracted_text.pdf"):
    """Generate a PDF file from the given text."""
    if not text.strip():
        logger.warning("Empty input text provided to generate_pdf")
        raise ValueError("Cannot generate PDF from empty text")

    try:
        logger.info("Audit: Starting PDF generation")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            c = canvas.Canvas(tmp_file.name, pagesize=letter)
            width, height = letter
            text_object = c.beginText(40, height - 40)
            text_object.setFont("Helvetica", 12)

            for line in text.split('\n'):
                wrapped_lines = [line[i:i+90] for i in range(0, len(line), 90)]
                for wrap in wrapped_lines:
                    text_object.textLine(wrap)

            c.drawText(text_object)
            c.showPage()
            c.save()

            logger.info(f"Audit: PDF successfully generated - Path: {tmp_file.name}")
            return tmp_file.name

    except Exception as e:
        logger.error(f"Error during PDF generation - Error: {e}", exc_info=True)
        raise RuntimeError("Failed to generate PDF") from e
