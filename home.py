import os, shutil
import time
import streamlit as st
import fitz
import re
from PyPDF2 import PdfReader, PdfWriter, PdfMerger
import pytesseract
from pdf2image import convert_from_path, convert_from_bytes
from PIL import Image
import io


st.set_page_config(
    layout="wide",
    page_title="ExtracTHOR"
)

poppler_path = r'C:\Users\ssolwa001\Desktop\poppler-23.08.0\Library\bin'
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def read_pdf(file):
    try:
        doc = fitz.open(stream=file.read(), filetype='pdf')

        total_page_area = 0.0
        total_text_area = 0.0

        for page_num, page in enumerate(doc):
            total_page_area = total_page_area + abs(page.rect)
            text_area = 0.0
            for b in page.get_text_blocks():
                r = fitz.Rect(b[:4])  # rectangle where block text appears
                text_area = text_area + abs(r)
            total_text_area = total_text_area + text_area

        text_perc = total_text_area/total_page_area

        text_by_page = {}
        if text_perc < 2:
            pdf_bytes = file.getvalue()

            images = convert_from_bytes(pdf_bytes, poppler_path=poppler_path)

            for i in range(len(images)):
                images[i].save("temp.png", "PNG")
                text = pytesseract.image_to_string(os.path.abspath("temp.png"))
                text_by_page[i + 1] = text

            os.remove("temp.png")

        else:
            for i in range(doc.page_count):
                page = doc.load_page(i)
                page.get_images()
                text = page.get_text("text")
                text_by_page[i + 1] = text

        doc.close()

        return text_by_page

    except Exception as e:
        st.warning(f"Failed to read the file!")
        st.warning(str(e))


def get_keyword_page_number_pairs(text_dict, keywords):
    try:
        page_keyword_pair = {}
        for page_number, text in text_dict.items():
            for keyword in keywords:
                for m in re.finditer(keyword.lower(), text.lower()):
                    page_keyword_pair[f'{page_number}'] = keyword

        return page_keyword_pair

    except Exception as e:
        return {}


def save_pages_from_pdf(input_pdf, pages_dict):
        created_pdf_status_dict = {}

        pdf_reader = PdfReader(input_pdf)

        # Iterate through the pages specified in the dictionary
        for page_number, text in pages_dict.items():
            try:
                # Ensure the page number is within the range
                if 1 <= int(page_number) <= len(pdf_reader.pages):
                    # Get the specific page
                    page = pdf_reader.pages[int(page_number) - 1]

                    # Create a new PDF file in write-binary mode with the keyword as the filename
                    if not os.path.exists(f"./extracted pages/{text}"):
                        os.makedirs(f"./extracted pages/{text}")

                    with open(f'./extracted pages/{text}/{input_pdf.name}_{text}_{page_number}.pdf', 'wb') as output_pdf:
                        # Create a PDF file writer object
                        pdf_writer = PdfWriter()

                        # Add the specific page to the PDF file writer object
                        pdf_writer.add_page(page)

                        # Write the PDF file writer object to the output file
                        pdf_writer.write(output_pdf)

                        created_pdf_status_dict[f'success_{input_pdf.name}_{text}_{page_number}.pdf'] = "Successfully created pdf."

            except Exception as e:
                print(str(e))
                created_pdf_status_dict[
                    f'failed_{input_pdf.name}_{text}_{page_number}.pdf'] = "Failed to create pdf."

        if not os.path.exists(r'./merged'):
            os.makedirs(r'./merged')
        merged_pdf_status_dict = {}
        root_directory = r'./extracted pages'
        try:
            for subdir in os.listdir(root_directory):
                subdir_path = os.path.join(root_directory, subdir)
                if os.path.isdir(subdir_path):
                    merger = PdfMerger()
                    for filename in os.listdir(subdir_path):
                        if filename.endswith(".pdf"):
                            filepath = os.path.join(subdir_path, filename)
                            merger.append(PdfReader(open(filepath, 'rb')))
                    output_filename = os.path.join(r'./merged', subdir + '.pdf')
                    with open(output_filename, 'wb') as output_file:
                        merger.write(output_file)
                    merged_pdf_status_dict[f'Successful merge'] = "Successfully created merged pdf!"
        except Exception as e:
            merged_pdf_status_dict[f'Failed merge'] = "Failed to create merged pdf!"

        time.sleep(2)
        shutil.rmtree(r'./extracted pages')

        return created_pdf_status_dict

def highlight_words(folder_path):
    if not os.path.exists(r'./merged highlighted'):
        os.makedirs(r'./merged highlighted')
    keyword = ''
    try:
        for filename in os.listdir(folder_path):
            filepath = os.path.join(folder_path, filename)
            if os.path.isfile(filepath):
                keyword = filename.split('.')[0]
                doc = fitz.open(filepath)
                for page in doc:
                    text = page.get_text()
                    lines = text.split('\n')
                    for i, line in enumerate(lines):
                        if keyword.lower() in line.lower():
                            bbox = page.search_for(keyword)
                            if bbox:
                                highlight = page.add_highlight_annot(bbox)
                                highlight.set_colors(fitz.utils.getColor('yellow'))

                doc.save(rf'./merged highlighted/{keyword}.pdf')
                doc.close()

        time.sleep(20)
        shutil.rmtree(r'./merged')

        st.success("Successfully merged and highlighted output pdf results.")


    except Exception as e:
        st.warning("Failed to merge and highlight output pdf files. Please contact admin.")

def main():
    st.header(f"ExtracTHOR \u2692 \U000026A1")
    st.subheader("PDF Keyword and Page Extractor")

    file = st.file_uploader("Upload your document here", type=["pdf"])

    if file is not None:
        text_dict = read_pdf(file)

        keywords = st.text_input("Enter keywords to search for", placeholder="Separate the keywords with a comma")
        if st.button("Process", key="Process_Button"):
            if keywords is not None:
                processed_keywords = keywords.split(",")
                for i in range(len(processed_keywords)):
                    processed_keywords[i] = processed_keywords[i].lstrip().rstrip()
                page_keyword_pairs = get_keyword_page_number_pairs(text_dict, processed_keywords)
                status_dict = save_pages_from_pdf(file, page_keyword_pairs)
                st.write(status_dict)
                highlight_words(r'./merged')
            else:
                st.warning("Please add keywords!")

if __name__ == "__main__":
    main()