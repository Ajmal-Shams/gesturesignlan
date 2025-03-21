import os
from django.shortcuts import render
from django.conf import settings
from django.http import JsonResponse
import pytesseract
from pypdf import PdfReader
from docx import Document
from PIL import Image
from django.views.decorators.csrf import csrf_exempt

# Set the path for Tesseract OCR
pytesseract.pytesseract.tesseract_cmd = r'F:\Applications\Tesseract\tesseract.exe'  # Update this path

def extract_text_from_file(file_path):
    """Extract text from image, PDF, or DOCX file."""
    try:
        if file_path.endswith(('.png', '.jpg', '.jpeg')):
            return pytesseract.image_to_string(Image.open(file_path))

        elif file_path.endswith('.pdf'):
            text = ""
            with open(file_path, "rb") as pdf_file:
                pdf_reader = PdfReader(pdf_file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text.strip()

        elif file_path.endswith('.docx'):
            doc = Document(file_path)
            return "\n".join([para.text for para in doc.paragraphs])

        return "Unsupported file format."

    except Exception as e:
        return f"Error extracting text: {str(e)}"

@csrf_exempt  # Use CSRF token properly in production
def upload_file(request):
    """Handles file upload, extracts text, and sends text to frontend."""
    if request.method == "POST" and request.FILES.get("file"):
        file = request.FILES["file"]

        # Ensure the uploads directory exists
        upload_dir = os.path.join(settings.MEDIA_ROOT, "uploads")
        os.makedirs(upload_dir, exist_ok=True)

        file_path = os.path.join(upload_dir, file.name)

        # Save new file
        with open(file_path, "wb") as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        # Verify file is saved
        if not os.path.exists(file_path):
            return JsonResponse({"error": "File upload failed."}, status=500)

        # Extract text
        extracted_text = extract_text_from_file(file_path)

        # Delete the uploaded file after processing
        os.remove(file_path)

        return JsonResponse({"text": extracted_text}, status=200)

    return JsonResponse({"error": "Invalid request"}, status=400)

def speech_page(request):
    """Render the speech conversion page."""
    return render(request, "speechtotext.html")
