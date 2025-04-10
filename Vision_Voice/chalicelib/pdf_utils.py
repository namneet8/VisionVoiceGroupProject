from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import tempfile

def generate_pdf(text, filename="extracted_text.pdf"):
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
        return tmp_file.name