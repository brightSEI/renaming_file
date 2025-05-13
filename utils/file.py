import os
import shutil
import psutil
from datetime import datetime
from PIL import Image
import csv
from pathlib import Path
import re
from threading import Lock
from utils.format import organize_files


CROP_WIDTH   = int(os.getenv('CROP_WIDTH', 300))

home_dir = Path.home()
image_folder = home_dir / "OCRHeader" / "image"
result_folder = home_dir / "OCRHeader" / "result_log"

file_operation_lock = Lock()


def add_log_message(message, log_file):
    """Logs a message to the log file."""
    with open(log_file, "a", encoding="utf-8", errors="replace") as log:
        log.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")


def log_result_to_csv(file_path, extracted_data, status, error_message=None):
    """Append OCR results to a CSV file."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    log_file_path = result_folder / f"result_log_{date_str}.csv"

    log_entry = {
        "file_name": os.path.basename(file_path),
        "new_file_name": (
            f"{sanitize_file_name(extracted_data.get('item_name', ''))}-"
            f"{sanitize_file_name(extracted_data.get('document_id', ''))}-"
            f"{sanitize_file_name(extracted_data.get('date', ''))}.pdf"
            if extracted_data else "Unknown.pdf"
        ),
        "extracted_data": extracted_data if extracted_data else "",
        "status": "Success" if status else "Failed",
        "error_message": error_message if not status else "",
        "date_processed": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    write_header = not os.path.exists(log_file_path)
    with open(log_file_path, mode="a", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=log_entry.keys())
        if write_header:
            writer.writeheader()
        writer.writerow(log_entry)

def get_datetime():
    now = datetime.now()
    formatted_datetime = now.strftime("%Y%m%d_%H%M%S") + f"_{now.microsecond // 1000:03d}"
    return formatted_datetime

def sanitize_file_name(file_name):
    """
    Sanitize the file name by replacing or removing invalid characters.
    """
    sanitized_name = re.sub(r'[<>:"/\\|?*]', '-', file_name)
    sanitized_name = sanitized_name.strip()
    return sanitized_name

def format_date(date_str):
    """Format the date into yyyy-mm-dd format. Return 'Unknown' if invalid."""
    try:
        # try to parse the date
        parsed_date = datetime.strptime(date_str, "%d-%b-%y")
        return parsed_date.strftime("%d-%b-%y")
    except ValueError:
        return ""

def process_file(status, pdf_path, extracted_data, success_folder, failed_folder, backup_folder, log_file, doc_type={"version": "", "barcode": "", "type": 1}):
    """Processes a file: rename, log, and move to appropriate folders."""
    datetime_str = get_datetime()
    
    doc_type = extracted_data.get("type", 1)

    item_name = sanitize_file_name(extracted_data.get("item_name", ""))
    document_id = sanitize_file_name(extracted_data.get("document_id", ""))
    date = sanitize_file_name(extracted_data.get("date", ""))
    date = format_date(date)
    # create subfolder
    # subfolder_name = date if date != "Unknown" else "Unknown"
    # success_subfolder = os.path.join(success_folder, subfolder_name)
    # failed_subfolder = os.path.join(failed_folder, subfolder_name)
    # backup_subfolder = os.path.join(backup_folder, subfolder_name)

    # if status:
    #     os.makedirs(success_subfolder, exist_ok=True)
    #     os.makedirs(backup_subfolder, exist_ok=True)
    # else:
    #     os.makedirs(failed_subfolder, exist_ok=True)
    
    
    if doc_type == 3:
        barcode = sanitize_file_name(extracted_data.get("barcode", ""))
        new_filename = f"{barcode}-{date}.pdf"
    else:
        new_filename = f"{item_name}-{document_id}-{date}.pdf"
    
    new_filename = sanitize_file_name(new_filename)

    success_path = os.path.join(success_folder, get_unique_filename(success_folder, new_filename))
    fail_path = os.path.join(failed_folder, os.path.basename(pdf_path))
    backup_path = os.path.join(backup_folder, get_unique_filename(backup_folder, os.path.basename(pdf_path)))
    
    print("PDF: ", pdf_path)
    print("New filename: ", new_filename)


    # print(failed_folder, os.path.basename(pdf_path), os.path.join(failed_folder, os.path.basename(pdf_path)))
    with file_operation_lock:
        try:
            if status:
                if os.path.exists(pdf_path):
                    shutil.copy(pdf_path, success_path)
                    # add_log_message(f"{datetime_str} - SUCCESS: {os.path.basename(pdf_path)} moved to Success folder. New file name is {new_filename}", log_file)
                    if os.path.exists(success_path):
                        organize_files(success_folder, doc_type=extracted_data)
                        log_message = f"SUCCESS: {os.path.basename(os.path.basename(pdf_path))} moved to Success folder. New file name is {os.path.basename(success_path)}."
                        add_log_message(log_message, log_file)
                    else:
                        add_log_message(f"ERROR: File {os.path.basename(pdf_path)} move to success failed.", log_file)
            else:
                if os.path.exists(pdf_path):
                    shutil.move(pdf_path, fail_path)
                    add_log_message(f"FAILED: {os.path.basename(pdf_path)} moved to Failed folder.", log_file)

            if status and os.path.exists(pdf_path):
                shutil.move(pdf_path, backup_path)
                add_log_message(f"BACKUP: {os.path.basename(pdf_path)} copied to Backup folder.", log_file)
    
        except Exception as e:
            # print(e)
            if os.path.exists(pdf_path):
                fail_path = os.path.join(failed_folder, os.path.basename(pdf_path))
                if not status and fail_path:
                    shutil.move(pdf_path, fail_path)

            add_log_message(f"{datetime_str} - Error processing {pdf_path}: {str(e)}", log_file)

def get_unique_filename(folder, filename):
    """
    Generate a unique filename by appending a counter if the file already exists.
    Args:
        folder (str): The target folder where the file will be saved.
        filename (str): The original filename.

    Returns:
        str: A unique filename.
    """
    base_name, extension = os.path.splitext(filename)
    counter = 1
    unique_filename = filename

    # Check if the file exists and generate a new name
    while os.path.exists(os.path.join(folder, unique_filename)):
        unique_filename = f"{base_name}_{counter}{extension}"
        counter += 1

    return unique_filename

def crop_init_image(images, crop_width=CROP_WIDTH):

    width, height = images[0].size
    if width > crop_width:
        new_height = int(height * (crop_width / width))
        images = images[0].resize((crop_width, new_height), Image.ANTIALIAS)

    datetimestr = get_datetime()
    # image_path = f"./image/image_{datetimestr}.jpg"
    image_path = image_folder / f"image_{datetimestr}.jpg" 
    images[0].save(image_path)

    return image_path

def delete_folders(*folder_paths):
    """
    Deletes the specified folders and their contents.

    Args:
        folder_paths (tuple): Paths to the folders to be deleted.

    Returns:
        None
    """
    for folder_path in folder_paths:
        if folder_path and os.path.exists(folder_path):
            try:
                shutil.rmtree(folder_path)
                print(f"Deleted folder: {folder_path}")
            except Exception as e:
                print(f"Error deleting folder {folder_path}: {e}")
        else:
            print(f"Folder does not exist: {folder_path}")

def get_memory_usage():
    """Get the current memory usage of the process in MB"""
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    return memory_info.rss / (1024 ** 2)

def get_dynamic_batch_size():
    """Calculate the batch size dynamically based on system resources. (unit: MB)"""
    total_memory = psutil.virtual_memory().total / (1024 ** 2)
    available_memory = psutil.virtual_memory().available / (1024 ** 2)
    cpu_cores = os.cpu_count()

    memory_per_file = 200

    batch_size_based_on_memory = max(1, int(available_memory / memory_per_file))
    batch_size_based_on_cpu = max(1, cpu_cores - 1)

    return min(batch_size_based_on_memory, batch_size_based_on_cpu)




