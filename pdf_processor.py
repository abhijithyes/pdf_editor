import os
import io
import cv2
import numpy as np
from PIL import Image
from pdf2image import convert_from_path
from PyPDF2 import PdfReader, PdfWriter

# Global variables for mouse interaction
drawing = False  # True when left mouse button is held down
ix, iy = -1, -1  # Initial click coordinates

# We'll store field data here: {field_id: (x1, y1, x2, y2, text)}
fields = {}
fields_to_draw = 0  # Number of fields user wants to annotate
done = False         # Flag to signal we've finished drawing enough fields

def draw_rectangle(event, x, y, flags, param):
    """
    Mouse callback function. Lets you click-drag to draw rectangles on the image.
    When you release the mouse, you're prompted for a field ID and text.
    """
    global ix, iy, drawing, img, img_display, fields, done

    if done:
        # If we've already annotated the required fields, ignore further mouse events.
        return

    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        ix, iy = x, y

    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing:
            # Copy the base image so we don't keep layering multiple rectangles
            img_display = img.copy()
            cv2.rectangle(img_display, (ix, iy), (x, y), (0, 255, 0), 2)

    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        x1, y1 = ix, iy
        x2, y2 = x, y

        # Normalize coordinates so x1 < x2 and y1 < y2
        if x1 > x2:
            x1, x2 = x2, x1
        if y1 > y2:
            y1, y2 = y2, y1

        # Draw the final rectangle on the displayed image
        cv2.rectangle(img_display, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # Prompt user for field ID
        field_id = input("\nEnter Field ID (e.g. 'Name', 'DOB'): ")
        if not field_id.strip():
            print("No field ID entered. Rectangle ignored.")
            return

        # Prompt user for the text to place in that field
        text_value = input(f"Enter text for field '{field_id}': ")

        # Store the bounding box and text in a dictionary
        fields[field_id] = (x1, y1, x2, y2, text_value)

        # Display the text + rectangle on the images so user sees it immediately
        place_text_in_rectangle(img_display, x1, y1, x2, y2, text_value, draw_rect=True)
        place_text_in_rectangle(img, x1, y1, x2, y2, text_value, draw_rect=True)

        # Check if we've reached the desired number of fields
        if len(fields) >= fields_to_draw:
            print(f"\nYou have annotated {fields_to_draw} field(s). Saving and exiting...")
            done = True

def place_text_in_rectangle(image, x1, y1, x2, y2, text_value, draw_rect=True):
    """
    Places text inside the given rectangle. 
    If draw_rect=False, we skip drawing the rectangle outline.
    """
    if draw_rect:
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)

    # Slight offset for text placement
    text_x = x1 + 5
    text_y = y1 + 30

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1
    color = (0, 0, 0)  # black text
    thickness = 2

    cv2.putText(
        image, text_value, (text_x, text_y),
        font, font_scale, color, thickness, cv2.LINE_AA
    )

def main():
    global img, img_display, fields_to_draw, done

    # ------------------ 1) Prompt for PDF Path & Page Number --------------------
    pdf_path = input("Enter the path to the PDF file: ")
    if not os.path.exists(pdf_path):
        print(f"Error: The file '{pdf_path}' does not exist.")
        return

    try:
        page_number = int(input("Which page do you want to annotate? (1-based): "))
    except ValueError:
        print("Please enter a valid integer.")
        return

    # Convert the entire PDF to a list of PIL Images
    try:
        pages = convert_from_path(pdf_path, dpi=150)  # adjust DPI as needed
    except Exception as e:
        print(f"Error converting PDF to images: {e}")
        return

    if page_number < 1 or page_number > len(pages):
        print(f"Invalid page number. The PDF has {len(pages)} pages.")
        return

    # The specific page we want to annotate
    pil_page = pages[page_number - 1]

    # Convert that page to an OpenCV BGR image
    page_array = np.array(pil_page.convert("RGB"))
    img = cv2.cvtColor(page_array, cv2.COLOR_RGB2BGR)
    img_display = img.copy()

    # ------------------ 2) Prompt for Number of Fields to Draw ------------------
    while True:
        try:
            fields_to_draw = int(input("How many fields do you want to annotate? "))
            if fields_to_draw <= 0:
                raise ValueError
            break
        except ValueError:
            print("Please enter a positive integer.")

    # ------------------ 3) Annotate: Draw Rectangles & Input Text ---------------
    cv2.namedWindow("Form", cv2.WINDOW_NORMAL)
    cv2.setMouseCallback("Form", draw_rectangle)

    print("\nINSTRUCTIONS:")
    print(" - Click and drag to draw a rectangle around a form field (for reference).")
    print(" - Release the mouse, then enter a Field ID and the text to place there.")
    print(f" - Repeat until you've drawn {fields_to_draw} fields.")
    print(" - Or press ESC at any time to exit early.\n")

    while True:
        cv2.imshow("Form", img_display)
        key = cv2.waitKey(1) & 0xFF
        if done:
            break
        if key == 27:  # ESC
            print("ESC pressed. Saving and exiting early...")
            break

    cv2.destroyAllWindows()

    # ------------------ 4) Create a Single-Page Annotated PDF (Text Only) -------
    # Reuse the original PIL page to avoid rectangle outlines
    final_img = cv2.cvtColor(np.array(pil_page.convert("RGB")), cv2.COLOR_RGB2BGR)

    # Place text only on this clean copy
    for f_id, (x1, y1, x2, y2, text_val) in fields.items():
        place_text_in_rectangle(final_img, x1, y1, x2, y2, text_val, draw_rect=False)

    # Save the annotated single page as a temporary PDF
    final_img_rgb = cv2.cvtColor(final_img, cv2.COLOR_BGR2RGB)
    annotated_page_pil = Image.fromarray(final_img_rgb)
    temp_annotated_pdf = "temp_annotated_page.pdf"
    annotated_page_pil.save(temp_annotated_pdf, "PDF", resolution=150.0)

    # ------------------ 5) Replace the Original PDF Page with Annotated Page ----
    try:
        # Load original PDF
        pdf_reader = PdfReader(pdf_path)
        pdf_writer = PdfWriter()

        # Read the single-page annotated PDF into memory (to avoid "seek of closed file")
        with open(temp_annotated_pdf, "rb") as f:
            annotated_pdf_data = f.read()

        annotated_pdf_reader = PdfReader(io.BytesIO(annotated_pdf_data))
        annotated_page = annotated_pdf_reader.pages[0]

        # Build the final PDF with the replaced page
        for i in range(len(pdf_reader.pages)):
            if i == (page_number - 1):
                # Insert the newly annotated page
                pdf_writer.add_page(annotated_page)
            else:
                pdf_writer.add_page(pdf_reader.pages[i])

        # Write the final "filled" PDF
        replaced_pdf_path = "filled_entire_document.pdf"
        with open(replaced_pdf_path, "wb") as output_file:
            pdf_writer.write(output_file)

        # Clean up the temp file
        if os.path.exists(temp_annotated_pdf):
            os.remove(temp_annotated_pdf)

        print(f"\nSuccessfully replaced page {page_number}.")
        print(f"Final PDF saved as '{replaced_pdf_path}'.")

    except Exception as e:
        print(f"Error while replacing the page: {e}")

    # ------------------ 6) Print Summary ----------------------------------------
    print("\nCollected fields:")
    for f_id, (x1, y1, x2, y2, text_val) in fields.items():
        print(f"  {f_id}: BBox=({x1},{y1},{x2},{y2}), Text='{text_val}'")

if __name__ == "__main__":
    main()
