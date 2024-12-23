import os
import io
import cv2
import numpy as np
from PIL import Image
from pdf2image import convert_from_path
from PyPDF2 import PdfReader, PdfWriter

drawing = False
ix, iy = -1, -1
fields = {}
fields_to_draw = 0
done = False

def draw_rectangle(event, x, y, flags, param):
    global ix, iy, drawing, img, img_display, fields, done

    if done:
        return

    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        ix, iy = x, y

    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing:
            img_display = img.copy()
            cv2.rectangle(img_display, (ix, iy), (x, y), (0, 255, 0), 2)

    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        x1, y1 = ix, iy
        x2, y2 = x, y
        if x1 > x2:
            x1, x2 = x2, x1
        if y1 > y2:
            y1, y2 = y2, y1

        cv2.rectangle(img_display, (x1, y1), (x2, y2), (0, 255, 0), 2)
        field_id = input("\nEnter Field ID (e.g. 'Name', 'DOB'): ")
        if not field_id.strip():
            print("No field ID entered. Rectangle ignored.")
            return

        text_value = input(f"Enter text for field '{field_id}': ")
        fields[field_id] = (x1, y1, x2, y2, text_value)
        place_text_in_rectangle(img_display, x1, y1, x2, y2, text_value, draw_rect=True)
        place_text_in_rectangle(img, x1, y1, x2, y2, text_value, draw_rect=True)

        if len(fields) >= fields_to_draw:
            print(f"\nYou have annotated {fields_to_draw} field(s). Saving and exiting...")
            done = True

def place_text_in_rectangle(image, x1, y1, x2, y2, text_value, draw_rect=True):
    if draw_rect:
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)

    text_x = x1 + 5
    text_y = y1 + 30
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1
    color = (0, 0, 0)
    thickness = 2

    cv2.putText(image, text_value, (text_x, text_y), font, font_scale, color, thickness, cv2.LINE_AA)

def main():
    global img, img_display, fields_to_draw, done

    pdf_path = input("Enter the path to the PDF file: ")
    if not os.path.exists(pdf_path):
        print(f"Error: The file '{pdf_path}' does not exist.")
        return

    try:
        page_number = int(input("Which page do you want to annotate? (1-based): "))
    except ValueError:
        print("Please enter a valid integer.")
        return

    try:
        pages = convert_from_path(pdf_path, dpi=150)
    except Exception as e:
        print(f"Error converting PDF to images: {e}")
        return

    if page_number < 1 or page_number > len(pages):
        print(f"Invalid page number. The PDF has {len(pages)} pages.")
        return

    pil_page = pages[page_number - 1]
    page_array = np.array(pil_page.convert("RGB"))
    img = cv2.cvtColor(page_array, cv2.COLOR_RGB2BGR)
    img_display = img.copy()

    while True:
        try:
            fields_to_draw = int(input("How many fields do you want to annotate? "))
            if fields_to_draw <= 0:
                raise ValueError
            break
        except ValueError:
            print("Please enter a positive integer.")

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
        if key == 27:
            print("ESC pressed. Saving and exiting early...")
            break

    cv2.destroyAllWindows()
    final_img = cv2.cvtColor(np.array(pil_page.convert("RGB")), cv2.COLOR_RGB2BGR)

    for f_id, (x1, y1, x2, y2, text_val) in fields.items():
        place_text_in_rectangle(final_img, x1, y1, x2, y2, text_val, draw_rect=False)

    final_img_rgb = cv2.cvtColor(final_img, cv2.COLOR_BGR2RGB)
    annotated_page_pil = Image.fromarray(final_img_rgb)
    temp_annotated_pdf = "temp_annotated_page.pdf"
    annotated_page_pil.save(temp_annotated_pdf, "PDF", resolution=150.0)

    try:
        pdf_reader = PdfReader(pdf_path)
        pdf_writer = PdfWriter()
        with open(temp_annotated_pdf, "rb") as f:
            annotated_pdf_data = f.read()

        annotated_pdf_reader = PdfReader(io.BytesIO(annotated_pdf_data))
        annotated_page = annotated_pdf_reader.pages[0]

        for i in range(len(pdf_reader.pages)):
            if i == (page_number - 1):
                pdf_writer.add_page(annotated_page)
            else:
                pdf_writer.add_page(pdf_reader.pages[i])

        replaced_pdf_path = "output_document.pdf"
        with open(replaced_pdf_path, "wb") as output_file:
            pdf_writer.write(output_file)

        if os.path.exists(temp_annotated_pdf):
            os.remove(temp_annotated_pdf)

        print(f"\nSuccessfully replaced page {page_number}.")
        print(f"Final PDF saved as '{replaced_pdf_path}'.")

    except Exception as e:
        print(f"Error while replacing the page: {e}")

    print("\nCollected fields:")
    for f_id, (x1, y1, x2, y2, text_val) in fields.items():
        print(f"  {f_id}: BBox=({x1},{y1},{x2},{y2}), Text='{text_val}'")

if __name__ == "__main__":
    main()
