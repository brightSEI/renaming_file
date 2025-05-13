

import os
import re
import shutil
from pathlib import Path
from difflib import get_close_matches
from datetime import datetime
from thefuzz import fuzz

# def find_best_match(file_name, folder_path):
#     folder_names = [f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]
#     closest_matches = get_close_matches(file_name, folder_names, n=1, cutoff=0.6)  # Adjust cutoff as needed
#     return closest_matches[0] if closest_matches else None

def find_best_match(file_name, folder_path):
    folder_names = [f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]
    if file_name in folder_names:
        return file_name
    closest_matches = get_close_matches(file_name, folder_names, n=1, cutoff=0.8) 
    if closest_matches:
        return max(closest_matches, key=len)
    return closest_matches[0] if closest_matches else None

def format_version(version):
    if version:
        return f"_{version}"
    else:
        return ""

def extract_and_update_s_part(serial_no):
    match = re.match(r"^(S)-(.*)", serial_no)
    if match:
        updated_serial_no = f"SS-{match.group(2)}"  
        return updated_serial_no
    return serial_no  

def extract_model_name(file_name):
    file_name = re.sub(r"\s+", " ", file_name).strip()
    match = re.match(r"^(.*?)-(SS|S).*", file_name)
    if match:
        model_name = match.group(1)
        model_name = remove_spaces_in_parentheses(model_name)
        return model_name
    file_name = remove_spaces_in_parentheses(file_name)
    return file_name

def is_valid_model_name(model_name):
    pattern = r"^.+?-\b[A-Z0-9]{2}\b-\b[A-Z0-9]{3}\b$"
    check = bool(re.match(pattern, model_name))
    if not check:
        pattern = r"^.+?-\bCX$"
        check = bool(re.match(pattern, model_name))
    return check

def remove_spaces_in_parentheses(text):
    text =  re.sub(r"\(\s*([^\)]+?)\s*\)", r"(\1)", text)
    while "))" in text:
        text = text.replace("))", ")")
    while "((" in text:
        text = text.replace("((", "(")
    return text

def validate_and_correct_date(date_str):
    if not date_str:
        return "No Date"
    
    try:
        match = re.match(r"(\d{2})-([A-Za-z]{3})-(\d{2})", date_str)
        if not match:
            return None

        day, month, year = match.groups()

        if day.startswith('4'):
            day = f"1{day[1]}"

        corrected_date = f"{day}-{month}-{year}"
        print("Correct Date: ", corrected_date)

        datetime.strptime(corrected_date, "%d-%b-%y")  # Will raise ValueError if invalid
        return corrected_date
    except ValueError:
        return "No Date"
    
def rename_with_versioning(new_file_path):
    base, ext = os.path.splitext(new_file_path)

    match = re.match(r"(.*?)(_([0-9]+))$", base)
    if match:
        base = match.group(1) 
        version = int(match.group(3)) + 1  
    else:
        version = 1  

    while os.path.exists(new_file_path):
        new_file_path = f"{base}_{version}{ext}"
        version += 1

    return new_file_path


def organize_files(folder_path, is_move=True, doc_type={"version": "", "barcode": "", "type": 1}):
    """
    Organizes files into folders by running in two passes:
    1. Process files with full and correct format names.
    2. Process incomplete or partially matched names.

    Args:
        folder_path (str): Path to the folder containing the files.
    """
    print(folder_path, is_move, doc_type)
    doc_version = doc_type.get('version', 1)
    doc_barcode = doc_type.get('barcode', '')
    doc_file    = doc_type.get('type', 'old')
    

    print("doc: ", doc_type)

    pattern = r"(.*?)-(S.*?)(?:-(\d{1,2}-[A-Za-z]{3}-\d{2}))?(?:_(\d+))?\.pdf"
    # pattern = r"^(.*?)-CX-([A-Z]{2}-[A-Z]-[A-Z]{2}-[A-Z]{2}-[A-Z0-9]{3}-\d{2}-\d-\d)(?:-(\d{1,2}-[A-Za-z]{3}-\d{2}))?(?:_(\d+))?\.pdf$"

    full_name_pattern = re.compile(pattern)
    

    # process fully matched file - create folder
    for file_name in os.listdir(folder_path):
        file_name = re.sub(r"\s+", " ", file_name).strip()
        file_path = os.path.join(folder_path, file_name)

        if os.path.isfile(file_path):
            file_name = remove_spaces_in_parentheses(file_name)
            
            model_name = extract_model_name(file_name)
            is_valid = is_valid_model_name(model_name)

            print("model name: ",model_name)

            # check if should use model or barcode as folder name
            if doc_file != 1:
                model_name = doc_barcode
            
            match = full_name_pattern.match(file_name)
            if not match:
                pattern = r"^.+?-CX-(S(?:[^-]*))(?:-(\d{1,2}-[A-Za-z]{3}-\d{2}))?$"
                match = bool(re.match(pattern, file_name))

            print('match after: ', match)
            

            if not match:
                # if not match this, check data in doc_type is type new, 
                # doc_type  =  {'document_id': '', 'date': '05-Feb-25', 'item_name': 'ST 1x4x0.22SHT (J04)-CI-RHA', 
                # 'barcode': 'CI03000766001', 'type': 3, 'version': 'new', 'machine': '030', 
                # 'supply': '00766'}
                
                print('in noy match')
                
                if doc_type.get('type') == 3 and doc_type.get('item_name') and doc_type.get('date'):
                    model_name = doc_type['item_name'].strip()
                    datename = doc_type['date'].strip()
                    
                    print("Using fallback for NEW type:")
                    print("Model Name:", model_name)
                    print("Date:", datename)
                    
                    model_folder = os.path.join(folder_path, model_name)
                    os.makedirs(model_folder, exist_ok=True)
                    
                    target_folder = model_folder
                    if datename:
                        date_folder = os.path.join(model_folder, datename)
                        os.makedirs(date_folder, exist_ok=True)
                        target_folder = date_folder
                        
                    target_file = os.path.join(target_folder, file_name)
                    target_file = rename_with_versioning(new_file_path=target_file)
                    
                    print("Target file:", target_file)
                    
                    try:
                        if is_move:
                            os.rename(file_path, target_file)
                        else:
                            shutil.copy(file_path, target_file)
                    except Exception as e:
                        print(f"Error moving/copying {file_name}: {str(e)}")
                    continue  # done with this file
                
                print(f"Skipping {file_name} (Does not match pattern)")
                continue
            
            else:
                print(f"Skipping {file_name} (Does not match pattern and no fallback doc_type)")

            # print('match: ', match)
            # print('is valid: ', is_valid)

            if is_valid and match:
                serial_no = extract_and_update_s_part(match.group(2))
                date = validate_and_correct_date(match.group(3))
                version = format_version(match.group(4))

                print('serial_no: ', serial_no)
                print('date: ', date)
                print('version: ', version)

                if date == 'No Date':
                    datename = ''
                else:
                    datename = date

                print("model name after: ", model_name)

                model_folder = os.path.join(folder_path, model_name)
                os.makedirs(model_folder, exist_ok=True)

                # print('model_folder: ', model_folder)

                target_folder = model_folder
                if date:
                    date_folder = os.path.join(model_folder, date)
                    os.makedirs(date_folder, exist_ok=True)
                    target_folder = date_folder

                target_file = os.path.join(target_folder, f"{model_name}-{serial_no}-{datename}{version}.pdf")

                target_file = rename_with_versioning(new_file_path=target_file)

                print("target file: "+target_file)

                os.rename(file_path, target_file)


    # process file that couldn't be handle in first loop
    for file_name in os.listdir(folder_path):
        file_name = re.sub(r"\s+", " ", file_name).strip()
        file_path = os.path.join(folder_path, file_name)

        if os.path.isfile(file_path):
            file_name = remove_spaces_in_parentheses(file_name)
            model_name = extract_model_name(file_name)
            match = full_name_pattern.match(file_name)


            # check if should use model or barcode as folder name
            if doc_file != 1 and doc_barcode != '':
                model_name = doc_barcode

            best_match_folder = find_best_match(model_name, folder_path)
            if match and best_match_folder:
                serial_no = extract_and_update_s_part(match.group(2))
                date = validate_and_correct_date(match.group(3))
                version = format_version(match.group(4))

                print('serial_no: ', serial_no)
                print('date: ', date)
                print('version: ', version)
                print("model: ", model_name)

                match = full_name_pattern.match(file_name)
                if not match:
                    pattern = r"^.+?-CX-(S(?:[^-]*))(?:-(\d{1,2}-[A-Za-z]{3}-\d{2}))?$"
                    match = bool(re.match(pattern, file_name))

                # print('match after: ', match)

                if not match: 
                    print(f"Skipping {file_name} (Does not match pattern)")
                    continue

                if date == 'No Date':
                    datename = ''
                else:
                    datename = date
                new_file_path = os.path.join(folder_path, best_match_folder,  date, f"{model_name}-{serial_no}-{datename}{version}.pdf")

                subfolder = os.path.join(folder_path, best_match_folder,  date)
                os.makedirs(subfolder, exist_ok=True)
            elif doc_type.get("version") == "new" and doc_type.get("item_name") and doc_type.get("date"):
                model_name = doc_type["item_name"].strip()
                datename = doc_type["date"].strip()

                print("Using fallback for NEW type (second loop):")
                print("Model Name:", model_name)
                print("Date:", datename)

                model_folder = os.path.join(folder_path, model_name)
                os.makedirs(model_folder, exist_ok=True)

                target_folder = model_folder
                if datename:
                    date_folder = os.path.join(model_folder, datename)
                    os.makedirs(date_folder, exist_ok=True)
                    target_folder = date_folder

                new_file_path = os.path.join(target_folder, file_name)
            else:
                new_file_path = os.path.join(folder_path, file_name)


            new_file_path = rename_with_versioning(new_file_path=new_file_path)

            try:
                if is_move:
                    os.rename(file_path, new_file_path)
                else:
                    shutil.copy(file_path, new_file_path)
            except:
                print('error')

    # wronged format file, move it to error folder instead
    error_folder = os.path.join(folder_path, "Error")
    os.makedirs(error_folder, exist_ok=True)  
    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)

        if os.path.isfile(file_path):
            error_path = os.path.join(error_folder, file_name)
            try:
                os.rename(file_path, error_path)
                print(f"Moved to Error Folder: {file_name}")
            except Exception as e:
                print(f"Error moving {file_name} to Error folder: {e}")

    return True



# # # Example usage
file = ''
folder_path = "C:/laragon/htdocs/SSWT/ocr-pdf-header/success"  # Replace with your folder path
# # organize_files(folder_path)
# t = find_best_match()

# file_name = "ST 1x2x0.295HT (J12)-CX"
# option1 = "ST 1x2x0.295HT (J12)-CX"
# option2 = "ST 1x2x0.295HT (J12)-CX-RHA"

# def find_best_match(file_name, folder_path):
#     folder_names = [f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]
#     if file_name in folder_names:
#         return file_name
#     closest_matches = get_close_matches(file_name, folder_names, n=2, cutoff=0.6) 
#     if closest_matches:
#         return max(closest_matches, key=len)
#     return closest_matches[0] if closest_matches else None

# file_name = '00'
# v = is_valid_model_name(file_name)
# print(v)

# match = find_best_match(file_name, folder_path=folder_path)
# print(match)






