# pdf_editor

Convert from PDF to Image:
The entire PDF is converted to a list of images using pdf2image.convert_from_path(...). The chosen page is then processed in OpenCV.

On-Screen Drawing:
You click and drag to draw rectangles. Once you release the mouse, you enter your Field ID and text in the terminal.

Internally, these rectangles and text values are stored in a dictionary.
Final Text Overlay:
The script reloads the clean page (so no rectangle outlines appear in the final output) and only draws the text onto the image.

Replace the Original PDF Page:

The text-only annotated page is saved as a single-page PDF.
Using PyPDF2, the script inserts that newly created page in place of the original page in the PDF, preserving the rest of the document.
Complete PDF:
The final PDF (with your modified page) is saved as filled_entire_document.pdf



Create and activate a Python virtual environment:

python -m venv venv
source venv/bin/activate

Install Python dependencies:

pip install -r requirements.txt