from PyQt6.QtCore import QRunnable, pyqtSignal, QObject, QCoreApplication
from utils.file import  process_file, get_datetime, log_result_to_csv, sanitize_file_name, get_memory_usage
from utils.ocr import extract_specific_texts, detect_table_in_image, classify_document_type
from utils.convert import pdf_to_image
from pathlib import Path
import concurrent.futures
from pdf2image import convert_from_path
import time
import os


home_dir = Path.home()
image_folder = home_dir / "OCRHeader" / "image"
result_folder = home_dir / "OCRHeader" / "result_log"
MAX_RETRIES = 3

class OcrTaskSignals(QObject):
    progress = pyqtSignal(str)
    completed = pyqtSignal(str, bool)


class OcrTask(QRunnable):
    def __init__(self, pdf_path, success_folder, failed_folder, backup_folder, log_file, is_running, poppler_path):
        super().__init__()
        self.pdf_path = pdf_path
        self.success_folder = success_folder
        self.failed_folder = failed_folder
        self.backup_folder = backup_folder
        self.log_file = log_file
        self.poppler_path = poppler_path
        self.is_running = is_running
        self.signals = OcrTaskSignals()
        self.timeout = 10
        self.retry_count = 0


    def run(self):
        """Perform the OCR processing."""

        self.retry_count = 0        

        if not self.is_running:
            self.signals.progress.emit(f"Task canceled for: {self.pdf_path}")
            return
        
        datetime_str = get_datetime()
        self.signals.progress.emit(f"{datetime_str} - Processing: {self.pdf_path}")
        print(f"{datetime_str} - Processing: {self.pdf_path}")
        while self.retry_count < MAX_RETRIES:
            try:
                # Simulate OCR processing (replace with actual logic)
                # images = self.pdf_to_image(self.pdf_path, self.poppler_path)

                memory_before = get_memory_usage()

                images = self.process_pdf_to_images(self.pdf_path, self.poppler_path)

                if not images:
                    raise Exception("No images generated from PDF")
                    
                datetimestr = get_datetime()
                # image_path = f"./image/image_{datetimestr}.jpg"
                image_path = image_folder / f"image_{datetimestr}.jpg" 
                images[0].save(image_path)
                images[0].close()

                while not os.path.exists(image_path):
                    time.sleep(0.1)

                # need detect this which type it is
                doc_type = classify_document_type(image_path)
                
                # if type = 1 -> process normally
                # if 2,3 need skip below
                status = True
                error_message = []
                if doc_type['type'] == 1:
                    extracted_texts = detect_table_in_image(image_path)
                    extracted_data = extract_specific_texts(extracted_texts)
                    extracted_data['type'] = 1
                else:
                    extracted_data = doc_type
                    print(f"Extract Text: {extracted_data}")
                # self.progress.emit(f"Extracted: {extracted_data}")


                if not extracted_data.get("document_id") or len(extracted_data["document_id"]) < 14:
                    if doc_type['type'] == 1:
                        status = False
                        error_message.append("Cannot get document ID")
                else:
                    extracted_data['document_id'] = sanitize_file_name(extracted_data.get("document_id"))

                if not extracted_data.get("date"):
                    # status = False
                    extracted_data['date'] = ''
                    error_message.append("Cannot get date")
                else:
                    extracted_data['date'] = sanitize_file_name(extracted_data.get("date"))

                if not extracted_data.get("item_name"):
                    status = False
                    error_message.append("Cannot get document header")
                else:
                    extracted_data['item_name'] = sanitize_file_name(extracted_data.get("item_name"))

                error_message = "; ".join(error_message) if error_message else ""
                
                # file_path, extracted_data, status, error_message=None
                log_result_to_csv(self.pdf_path, extracted_data, status, error_message)

                process_file(status, self.pdf_path, extracted_data, self.success_folder, self.failed_folder, self.backup_folder, self.log_file, doc_type=doc_type)

                # os.remove(image_path)

                memory_after = get_memory_usage()

                memory_used = memory_after - memory_before

                print(f"Memory used for {os.path.basename(self.pdf_path)}: {memory_used:.2f} MB")


                # print(f"Test: {self.pdf_path}: {status}: {extracted_data}")
                
                # Emit success signal
                # status = True
                self.signals.completed.emit(self.pdf_path, status)

                break

            except TimeoutError as e:
                self.retry_count += 1
                self.signals.progress.emit(f"Retry {self.retry_count}/{MAX_RETRIES} for {self.pdf_path}") 
                if self.retry_count == MAX_RETRIES:
                    self.signals.progress.emit(f"Max retries reached for {self.pdf_path}. Marking as failed.")
            
            except Exception as e:
                # Emit failure signal
                error_message = str(e)
                if "Couldn't find trailer dictionary" in error_message or "Couldn't read xref table" in error_message:
                    error_message = "PDF is corrupted or unable to open the file or this file is not a pdf file."
                else:
                    error_message = "An error occurred during processing."

                extracted_data = {"document_id": "", "error_message": error_message, 'item_name': ''}
                log_result_to_csv(self.pdf_path, extracted_data, False, error_message)
                process_file(False, self.pdf_path, extracted_data, self.success_folder, self.failed_folder, self.backup_folder, self.log_file)
                # print(error_message)

                self.signals.completed.emit(self.pdf_path, False)
                self.signals.progress.emit(f"{datetime_str} - Error processing {self.pdf_path}: {error_message}")

                break

    def process_pdf_to_images(self, pdf_path, poppler_path):
        """Process PDF to images with timeout handling."""
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                # Submit the task
                future = executor.submit(self.pdf_to_image, pdf_path, poppler_path)
                return future.result(timeout=self.timeout)  # Wait for the result with timeout
        except concurrent.futures.TimeoutError:
            self.signals.progress.emit(f"Timeout: Failed to process {pdf_path}")
            raise TimeoutError(f"PDF to image conversion timed out for {pdf_path}")

    def pdf_to_image(self, pdf_path, poppler_path, dpi=300, width=3600, height=1000):
        """Convert PDF to images.""" 
        start_time = time.time()
        # print(pdf_path, dpi, width, height)
        images = convert_from_path(pdf_path, dpi=dpi, poppler_path=poppler_path, first_page=1, last_page=1)
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"PDF to image conversion time for {pdf_path}: {elapsed_time:.2f} seconds")
        # QCoreApplication.processEvents()
        return images