import cv2
import pytesseract
import re
import os
from PIL import Image
import numpy as np
import easyocr

# env
SHARPNESS    = int(os.getenv('SHARPNESS', 650))
TEXT_PADDING = int(os.getenv('TEXT_PADDING', 33))
CROP_WIDTH   = int(os.getenv('CROP_WIDTH', 4000))
CROP_HEIGHT  = int(os.getenv('CROP_HEIGHT', 300))
MIN_CELL_WIDTH  = int(os.getenv('MIN_CELL_WIDTH', 250))
MIN_CELL_HEIGHT = int(os.getenv('MIN_CELL_HEIGHT', 100))

test = [{'cell_number': 1, 'coordinates': (0, 0, 4000, 300), 'text': 'yom Bao Me _ eo 7.\n, .- SS-F-PR-ST-047-81-1/3\ni . Mnluvinaszadaunisviwiwudaas ST 1x5x0.38H] (MRF)-DF-RHA'}, {'cell_number': 1, 'coordinates': (2038, 202, 288, 171), 'text': '}-F-PR-ST-047-81-1/3\n_'}, {'cell_number': 2, 'coordinates': (828, 202, 658, 167), 'text': 'niuvinaszadaUuNIsviaWIUAAaY ST 1)\n(Check Sheet of Work ST 1x5x0.38\nty'}, {'cell_number': 3, 'coordinates': (1486, 202, 549, 167), 'text': 'Ss\n5x0.38HI (MRF)-DF-RHA\nHI (MRF)-DF-RHA)'}, {'cell_number': 4, 'coordinates': (324, 237, 1998, 127), 'text': 'ie UhluvinasyadaunasviwwiUyaY ST 1x5x0.38HI (MRE)-DF-RHA\n(Check Sheet of Work ST 1x5x0.3GHI (MRF)-DF-RHA)'}]


# seperate into three format and need to support other format in future too
# old (use model)
# old + barcode
# new + barcode


def identify_document_format(cell_data):
    """
    Identify the format of the document based on specific patterns.

    Args:
        cell_data (list): List of dictionaries containing cell data with OCR text.

    Returns:
        str: The identified document format (e.g., 'Format_A', 'Format_B', etc.).
    """
    for cell in cell_data:
        text = cell["text"]
        if "Format_A_Keyword" in text:
            return "Format_A"
        elif "Format_B_Keyword" in text:
            return "Format_B"
        elif re.search(r"\bUniquePatternForFormatC\b", text):
            return "Format_C"
    return "Unknown_Format"

def extract_specific_texts(cell_data):
    """
    Extract specific parts of the OCR text using regex patterns.

    Args:
        cell_data (list): List of dictionaries containing cell data with OCR text.

    Returns:
        dict: Extracted data with relevant parts.
    """
    extracted_data = {
        "document_id": '',  
        "date": None,          
        "item_name": ''      
    }

    # need identify first which format it is
    doc_format = identify_document_format(cell_data)

    for cell in cell_data:
        text = cell["text"]

        # extract document ID (e.g., SS-F-PR-ST-047-54-1/5)
        if not extracted_data["document_id"] or len(extracted_data["document_id"]) <5:
            # match = re.search(r"\b[A-Z0-9\-\.]+(?:/\d)?\b", text) 
            # match = re.search(r"\b[A-Z0-9](?:[A-Z0-9\s\-\.]*(?:/\d)?)\b", text)
            match = re.search(r"\b[A-Z0-9]+(?:-[A-Z0-9]+)+(?:/\d+)?\b", text)
            if match:
                raw_document_id = match.group()
                formatted_document_id = format_document_id(raw_document_id.replace('.', '-'))
                extracted_data["document_id"] = formatted_document_id

        # extract date (e.g., 19-Aug-24)
        if not extracted_data["date"]:
            match = re.search(r"\b\d{1,2}[-/][A-Za-z]{3}[-/]?\d{2}\b", text)
            match = re.search(r"\b(\d{1,2})[-/]([A-Za-z]{3,})[-/]?(\d{2})\b", text)
            if match:
                # date = match.group()
                # extracted_data["date"] = re.sub(r"([A-Za-z]{3})(\d{2})$", r"\1-\2", date)
                day, month, year = match.groups()
                month = month[:3]  
                formatted_date = f"{day}/{month}/{year}"
                extracted_data["date"] = formatted_date



        # extract item name (e.g., ST 1x4x0.22SHT (J04)-CI-RHA)
        if not extracted_data["item_name"] or len(extracted_data["item_name"]) <5:
            text = text.replace("{", "(")
            text = text.replace("}", ")")
            # match = re.search(r"[A-Z0-9]+(?:\s+[\w\.\-x]+)+\s*\(.*?\)-[A-Z0-9\-]+", text)
            # match = re.search(r"[A-Z0-9]+(?:\s+[A-Z0-9\.\-\+x]+)+\s*\(.*?\)-[A-Z0-9\-]+", text)
            match = re.search(r"\b[A-Z]{2}\s+[A-Z0-9\.\-\+x]+(?:\s+[A-Z0-9\.\-\+x]+)*\s*\(.*?\)-[A-Z0-9\-]+", text)
            if match:
                raw_document_name = match.group()
                formatted_document_name = format_document_name(raw_document_name)
                extracted_data["item_name"] = formatted_document_name

    return extracted_data

def match_document_name(text, department=''):
    text = text.replace("{", "(")
    text = text.replace("}", ")")
            
    match = re.search(r"\b[A-Z]{2}\s+[A-Z0-9\.\-\+x]+(?:\s+[A-Z0-9\.\-\+x]+)*\s*\(.*?\)-[A-Z0-9\-]+", text)
    if match:
        return match.group()
    
    return ''        
        
def format_document_id(text):
    """
    Processes the document ID to ensure proper formatting:
    - Removes extra spaces.
    - Corrects OCR mistakes: '3' or '5' to 'S', 'D' to '0'.
    - Adds hyphens between segments if necessary.
    - Formats the last part based on its length or content.
    - Handles cases like '/3' or trailing '1/'.
    - final format is `{2}-{1}-{2}-{2}-{3}-{2}-{1}-{1}`.
    Args:
        text (str): The input string containing the document ID.

    Returns:
        str: The properly formatted document ID.
    """
    text = re.sub(r"\s+", "", text)  # Remove spaces
    text = re.sub(r"-+", "-", text)  # Collapse multiple hyphens
    text = text.strip("-")  # Strip leading and trailing hyphens

    # text = re.sub(r"\b(?:S[53]|[53]{2})\b", "SS", text)  # Replace 'S5' or 'S3' with 'SS'
    text = re.sub(r"\b(?:S[53]|[53]S)\b", "SS", text)
    text = re.sub(r"-D", "-0", text)  # Replace '-D' with '-0'
    text = re.sub(r"\bD(\d+)", r"0\1", text)  # Replace 'D47' with '047'


    pattern = r"^(.*?)-(?:\d{1,3}/\d|-1/n|\d{1,3}|/d)?$"
    match = re.match(pattern, text)

    if match:
        main_part = match.group(1)  

        last_part_match = re.search(r"-(?:/(\d)|(\d{2}))$", text)
        if last_part_match:
            # If it's '/3' or similar
            if last_part_match.group(1):
                numeric_part = last_part_match.group(1)
                return re.sub(r"-(?:/\d)$", f"-1/{numeric_part}", text)
            
            # If it's '15' or similar
            if last_part_match.group(2):
                numeric_part = last_part_match.group(2)[1]  # Take the second digit
                return re.sub(r"-(?:\d{2})$", f"-1/{numeric_part}", text)

        # Properly formatted last parts like '1/3'
        last_part_match = re.search(r"-(\d{1,3}/\d)$", text)
        if last_part_match:
            last_part = last_part_match.group(1)
            return f"{main_part}-{last_part}"

        # Handle cases like '-41' by converting to '1/41'
        trailing_hyphen_match = re.search(r"-(\d{1,3})$", text)
        if trailing_hyphen_match:
            numeric_part = trailing_hyphen_match.group(1)
            formatted_last_part = f"1/{numeric_part}"
            return f"{main_part}-{formatted_last_part}"

        return f"{main_part}-1/n"
    
    str_split = text.split('-')
    if len(str_split) > 0:
        last_part = str_split[len(str_split) - 1]
        new_last_part = ''
        if '/' in last_part:
            if last_part[0] == '/':
                new_last_part = f"1{last_part}"
            elif last_part[len(last_part) - 1]:
                new_last_part = f"{last_part}n"
            str_split[len(str_split) - 1] = new_last_part
        else:
            if len(last_part) == 2:
                new_last_part = f"{last_part[0]}/{last_part[1]}"
            elif len(last_part) == 1:
                new_last_part = f"1/{last_part}"
            str_split[len(str_split) - 1] = new_last_part
        return '-'.join(str_split)
    
    if len(text) < 14:
        text = None

    return text  

# def format_document_name(item_name):
#     item_name = item_name.replace('l', 'I').replace('{', '(').replace('}', ')')
    
#     if '\n' in item_name:
#         parts = item_name.split('\n', 1)
#         if len(parts) > 1:
#             item_name = parts[1].strip()
#             match = re.search(r'\b[A-Z]{2}[\w\s.+()-]+', item_name)
#             if match:
#                 item_name = match.group(0).strip()
#             else:
#                 item_name = ""


#     return item_name




def format_document_name(item_name):
    item_name = item_name.replace('l', 'I').replace('{', '(').replace('}', ')')

    lines = item_name.split('\n')
    for line in lines:
        # Look for a pattern matching the expected document name format
        match = re.search(r'\bST\s[\w\s.+()-]+', line)
        if match:
            return match.group(0).strip()

    return item_name

def measure_sharpness(image):
    """
    Measure the sharpness of an image using Laplacian varian
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    return laplacian_var


def preprocess_image(image_path, output_path, crop_region=(400, 80, 4000, 190)):
    """
    process blurred image
    """
    image = cv2.imread(image_path)
    if crop_region:
        x, y, w, h = crop_region
        image = image[y:y + h, x:x + w]
        cv2.imwrite(image_path, image)
    
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # noise reduction 
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    #   contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    clahe_img = clahe.apply(gray)
    # sharpen image
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened_img = cv2.filter2D(clahe_img, -1, kernel)

    thresh = cv2.threshold(sharpened_img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    text = pytesseract.image_to_string(thresh, config="--psm 6")
    text = text.strip()

    extracted_texts = [{"text":"", "coordinates":"", "cell_number":""}]
    if text:
        extracted_texts = [{
            "cell_number": 1,
            "coordinates": crop_region,
            "text": text
        }]
    return extracted_texts



    # gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    # sharpened = cv2.addWeighted(gray, 1.4, blurred, -0.2, 0)
    # denoised = cv2.bilateralFilter(sharpened, 5, 25, 25)
    # kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    # morphed = cv2.morphologyEx(denoised, cv2.MORPH_CLOSE, kernel)
    # resized = cv2.resize(morphed, None, fx=0.895, fy=0.895, interpolation=cv2.INTER_CUBIC)
    # binary = cv2.adaptiveThreshold(
    #     resized, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    # )

    # cv2.imwrite(output_path, binary)

    # table = detect_table_preprocessed_image(output_path)
    # cv2.imwrite(output_path, table)

    # processed_image = cv2.imread(image_path)
    # return pil_image
    return processed_image


def detect_table_in_image(image_path, rand=0, min_cell_width=MIN_CELL_WIDTH, min_cell_height=MIN_CELL_HEIGHT):
    """
    Detect the table and its cells in an image, and number each cell.

    Args:
        image_path (str): Path to the input image.
        min_cell_width (int): Minimum width of a cell to filter noise.
        min_cell_height (int): Minimum height of a cell to filter noise.

    Returns:
        List[tuple]: List of bounding boxes for table cells (x, y, w, h).
        str: Path to the saved image with bounding boxes and numbers.
    """
    # read image file
    image = cv2.imread(image_path)

    # measure sharpness, if blurred -> need preprocessed, if clear -> continue
    sharpness = measure_sharpness(image)
    is_blurred = sharpness < SHARPNESS
    # is_blurred = True
    extracted_texts_blur = preprocess_image(image_path, image_path, (0, 0, CROP_WIDTH, CROP_HEIGHT))

    # if is_blurred:
    #     extracted_texts = preprocess_image(image_path, image_path, (0, 0, CROP_WIDTH, CROP_HEIGHT))
    #     return extracted_texts
        
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)

    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (30, 1)))
    vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 30)))

    table_mask = cv2.bitwise_or(horizontal, vertical)

    cell_bounding_boxes = []
    extracted_texts = []
    extracted_texts_clear = []


    contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    table_bounding_box = None
    table_area = 0
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        if area > table_area:
            table_area = area
            table_bounding_box = (x, y, w, h)

    if not table_bounding_box:
        print("No table detected.")
        return []

    x, y, w, h = table_bounding_box
    table_region = binary[y:y + h, x:x + w]

    cell_contours, _ = cv2.findContours(table_region, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    for cell in cell_contours:
        cx, cy, cw, ch = cv2.boundingRect(cell)
        # cell_bounding_boxes.append((x + cx, y + cy, cw, ch))
        if cw >= MIN_CELL_WIDTH and ch > MIN_CELL_HEIGHT and ch < 130:
            if cw < 1000:
                adjusted_y = max(0, cy - TEXT_PADDING)
                adjusted_h = ch + (cy - adjusted_y)
                cell_bounding_boxes.append((x + cx, y - TEXT_PADDING, cw, adjusted_h + TEXT_PADDING))  # Filter small noise
            else:
                cell_bounding_boxes.append((x + cx, y + cy, cw, ch))  # Add offset for table position

    print(len(cell_bounding_boxes))

    # !!! Important
    # cell_bounding_boxes = sorted(cell_bounding_boxes, key=lambda box: (box[1], box[0]))

    for i, (x, y, w, h) in enumerate(cell_bounding_boxes):
        cell_image = image[y:y + h, x:x + w]

        text = pytesseract.image_to_string(cell_image, config="--psm 6 --oem 1").strip()
        # extracted_texts.append({
        #     "cell_number": i + 1,
        #     "coordinates": (x, y, w, h),
        #     "text": text
        # })

        extracted_texts_clear.append({
            "cell_number": i + 1,
            "coordinates": (x, y, w, h),
            "text": text
        })

        cv2.rectangle(image, (x, y), (x + w, y + h), (255, 0, 0), 3)


        # below is to draw number over detected box, in case need test!!!

        # cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)

        cell_number = str(i + 1)
        font_scale = 0.6
        thickness = 2
        text_size = cv2.getTextSize(cell_number, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
        text_x = x + (w - text_size[0]) // 2
        text_y = y + (h + text_size[1]) // 2
        cv2.putText(image, cell_number, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 0, 0), thickness)


    # Save the image with bounding boxes and numbers
    output_path = f"./image/000{rand}.jpg"
    cv2.imwrite(image_path, image)
    print(f"Bounding box image with numbers saved to: {image_path}")

    extracted_texts = merge_extracted_texts(extracted_texts_blur, extracted_texts_clear)

    return extracted_texts


def merge_extracted_texts(blurred_texts, clear_texts):
    """
    Merge texts from blurred and clear processing paths, avoiding duplicates.

    Args:
        blurred_texts (list[dict]): Extracted texts from blurred image processing.
        clear_texts (list[dict]): Extracted texts from clear image processing.

    Returns:
        list[dict]: Combined extracted texts.
    """
    # Use a set to track unique text contents to avoid duplicates
    unique_texts = set()
    combined_results = []

    for text_entry in blurred_texts + clear_texts:
        text = text_entry.get("text", "").strip()
        if text and text not in unique_texts:
            unique_texts.add(text)
            combined_results.append(text_entry)

    return combined_results

def extract_information(text):
    extracted_data = {
        'document_id': '',
        'date': '',
        'item_name': '',
        'barcode': '',
        'type': '',
        'version': ''
    }

    barcode_match = re.search(r'\b[A-Z]+\d+\b', text)

    date_match = re.search(r'\d{2}-[A-Za-z]{3}-\d{2}', text)

    if barcode_match:
        barcode = barcode_match.group()
        
        # Replace '1' with 'I' **ONLY** if '1' is at index 0 or 1
        if len(barcode) > 1 and barcode[0] == '1':
            barcode = 'I' + barcode[1:]  # Replace first character if it's '1'
        elif len(barcode) > 2 and barcode[1] == '1':
            barcode = barcode[0] + 'I' + barcode[2:]  # Replace second character if it's '1'

        extracted_data['barcode'] = barcode

    if date_match:
        extracted_data['date'] = date_match.group()

    item_name_match = re.findall(r'-(\b[A-Z]{2,3}\b)-', text)

    if extracted_data['barcode']:
        extracted_data['item_name'] = item_name_match[0] if item_name_match else ''
    else:
        match_parts = re.findall(r'\d+', text)  # Extract all numbers
        if len(match_parts) >= 3:
            extracted_data['item_name'] = f"CI{match_parts[1]}{match_parts[0]}{match_parts[2]}"

    number_matches = re.findall(r'\b\d{3,5}\b', text)  # Find numbers with 3-5 digits

    if len(number_matches) > 0:
        extracted_data['machine'] = number_matches[1] 
    if len(number_matches) > 1:
        extracted_data['supply'] = number_matches[0]  

    if extracted_data['barcode'] == '' or len(extracted_data['barcode']) < 10:
        extracted_data['barcode'] =  extracted_data['item_name'] + extracted_data['machine'] + extracted_data['supply'] + '001'
    
    if len(extracted_data['barcode']) > 10:
        extracted_data['version'] = 'new'
        extracted_data['item_name'] = extracted_data['barcode']

    return extracted_data

def classify_document_type(image_path):
    """
    3 formats 
        1. old + ''
        2. old + '{barcode}'
        3. new + '{barcode}'
    """
    image = cv2.imread(image_path)
    info = detect_header_type(image, image_path)
    # barcode = detect_barcode(image_path)
    version = info.get('version', 'old')
    barcode = info.get('barcode', '')

    # document = {"version": header_type, "barcode": barcode, "type": 1}
    info['type'] = 1
    # if version == 'old' and len(barcode) > 10:
    #     info['type'] = 2
    if version == 'new':
        info['type'] = 3
        
    print('info: ', info)

    return info

def detect_header_type(image, image_path):
    """
    detect the cell header of file if have SSWT
    if old -> old document
    if new -> new document
    """

    header_roi = (60, 50, 3000, 350)
    
    if header_roi:
        x, y, w, h = header_roi
        header_image = image[y:y+h, x:x+w]
    else:
        header_image = image

    cell_text = ''
    yellow_detected = False
    black_table_detected = False

    hsv = cv2.cvtColor(header_image, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(header_image, cv2.COLOR_BGR2GRAY)

    # -- this is for yellow area ---
    # yellow range
    lower_yellow = np.array([20, 100, 100])
    upper_yellow = np.array([30, 255, 255])
    # create mask
    yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
    # apply morphological operation to clean the mask
    kernel = np.ones((5,5), np.uint8)
    yellow_mask = cv2.morphologyEx(yellow_mask, cv2.MORPH_CLOSE, kernel)
    yellow_mask = cv2.morphologyEx(yellow_mask, cv2.MORPH_OPEN, kernel)

    yellow_contours, _ = cv2.findContours(yellow_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)


    # this is for black table borders
    black_mask = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 15, 4)
    kernel = np.ones((3,3), np.uint8)
    black_mask = cv2.dilate(black_mask, kernel, iterations=2)
    black_mask = cv2.morphologyEx(black_mask, cv2.MORPH_CLOSE, kernel)
    # black_mask = cv2.morphologyEx(black_mask, cv2.MORPH_OPEN, kernel)
    edges = cv2.Canny(black_mask, 50, 150)
    black_contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # extracted_text = pytesseract.image_to_string(header_image, config="--oem 1 --psm 3 -c preserve_interword_spaces=1")  
    # cell_text += extracted_text.strip() + "\n"
    # print(cell_text)
    # return
    
    index = 1
    for contour in yellow_contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w > 20 and h > 20: 
            yellow_detected = True
            cv2.rectangle(header_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
            # extract yellow are for text recog.
            roi_text = header_image[y:y+h, x:x+w]
            gray_roi = cv2.cvtColor(roi_text, cv2.COLOR_BGR2GRAY)
            gray_roi = cv2.bitwise_not(gray_roi)
            gray_roi = cv2.resize(gray_roi, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            # ocr 
            extracted_text = pytesseract.image_to_string(gray_roi, config="--psm 4")  
            cell_text += extracted_text.strip() + "\n"

            index += 1

    if yellow_detected:
        black_cell_text = ''
        for i, contour in enumerate(black_contours):
            x, y, w, h = cv2.boundingRect(contour)
            if w > 550 and (100 > h > 50):  # Adjust threshold to remove noise
                cv2.rectangle(header_image, (x, y), (x + w, y + h), (0, 0, 255), 2)  # Red for table borders

                roi_text = header_image[y:y+h, x:x+w]
                gray_roi = cv2.cvtColor(roi_text, cv2.COLOR_BGR2GRAY)
                gray_roi = cv2.bitwise_not(gray_roi)
                gray_roi = cv2.resize(gray_roi, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                # ocr 
                extracted_text = pytesseract.image_to_string(gray_roi, config="--psm 4")  
                black_cell_text += extracted_text
                cell_text += extracted_text.strip() + "\n"

        cv2.imwrite(image_path, header_image)
        
        print("cell text: ",cell_text)

        info  = extract_information(cell_text)
        
        info['item_name'] = match_document_name(black_cell_text)

        return info
    
    if not yellow_detected:
        return extract_information(cell_text)
    
    return extract_information(cell_text)
 

def detect_barcode(image_path):
    """
    detect if the document barcode is handwritten or printed text
    if possible need to actually read the text so that it would not effect process after this

    there is two place that can check 
    1. barcode at header
    2. below left at header

    """
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    roi = (100, 150, 700, 300)
    roi = (60, 50, 400, 400)
    if roi:
        x, y, w, h = roi
        image = image[y:y+h, x:x+w]

    _, thresh = cv2.threshold(image, 150, 255, cv2.THRESH_BINARY_INV)

    ocr_result = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    print(ocr_result)

    confidence_scores = ocr_result['conf']

    extracted_data = { "machine":'', 'supply': '', 'machine_valid': -1, 'supply_valid': -1}
    text = ocr_result['text']
    for i, word in enumerate(text):
        if word == 'Machine' and i + 2 < len(text) and text[i + 1] == 'No.':
            extracted_data['machine'] = text[i + 3]
            extracted_data['machine_valid'] = confidence_scores[i + 3] > 70
        elif word == 'Supply' and i + 2 < len(text) and text[i + 1] == 'No.':
            extracted_data['supply'] = text[i + 2]
            extracted_data['supply_valid'] = confidence_scores[i + 2] > 70

    print('text: ', text)
    print("Extracted Data:")
    for key, value in extracted_data.items():
        print(f"{key} No.: {value}")

    barcode = ''
    if extracted_data['machine_valid']:
        barcode += extracted_data['machine']
    if extracted_data['supply_valid']:
        barcode += extracted_data['supply']


    # reader = easyocr.Reader(['en', 'th'])
    # results = reader.readtext(image)
    # for (bbox, text, prob) in results:
    #     print(f"Detected Text: {text} (Confidence: {prob})")
    
    return barcode


# path_image = 'C:/laragon/htdocs/SSWT/ocr-pdf-header/success/Test Sample/image_20250129_083309_603.jpg'
# path_image = 'C:/Users/cvwhcy244/OCRHeader/image/image_20250130_100122_504.jpg'
# type = classify_document_type(path_image)
# print(type)