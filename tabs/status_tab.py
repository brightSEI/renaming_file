from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QLabel, QMessageBox, QTextEdit, QHeaderView, QHBoxLayout
from PyQt6.QtCore import Qt, QThread, QTimer
from utils.file import  process_file, get_datetime, log_result_to_csv, add_log_message, get_dynamic_batch_size

import os
from datetime import datetime
from worker.ocrworker import OCRWorker
import shutil
import gc


MAX_FILES   = int(os.getenv('MAX_FILES', 500))
RECOMMENDED_FILES   = int(os.getenv('RECOMMENDED_FILES', 300))

class StatusTab(QWidget):
    def __init__(self):
        super().__init__()

        self.data_folder = os.getenv("DATA_PATH", "")
        self.success_folder = os.getenv("SUCCESS_PATH", "")
        self.failed_folder = os.getenv("FAILED_PATH", "")
        self.backup_folder = os.getenv("BACKUP_PATH", "")
        self.log_folder = os.getenv("LOG_PATH", "")

        self.log_file = os.path.join(self.log_folder, f"{datetime.now().strftime('%Y-%m-%d')}_log.txt")

        self.pdf_files = []

        self.auto_ocr_running = False
        self.processing_ocr = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.auto_ocr_check)

        self.layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["File Name", "Date Added", "Size", "Status"])
        self.table.setRowCount(0)  
        self.layout.addWidget(self.table)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  

        self.table.setColumnWidth(0, 300) 

        self.button_layout = QHBoxLayout()

        self.start_button = QPushButton("Start OCR")
        self.start_button.clicked.connect(self.start_ocr)

        self.stop_button = QPushButton("Stop OCR")
        self.stop_button.clicked.connect(self.stop_ocr)
        self.stop_button.setEnabled(False)

        self.auto_ocr_button = QPushButton('Auto OCR')
        self.auto_ocr_button.setCheckable(True)
        self.auto_ocr_button.clicked.connect(self.toggle_auto_ocr)

        self.view_logs_button = QPushButton("View Logs File")
        self.view_logs_button.clicked.connect(self.view_log_file)

        self.open_success_button = QPushButton("Open Success Folder")
        self.open_success_button.clicked.connect(self.open_success_folder)

        self.refresh_button = QPushButton("Refresh Files")
        self.refresh_button.clicked.connect(self.refresh_file_list)

        self.clear_log_button = QPushButton("Clear Logs Area")
        self.clear_log_button.clicked.connect(self.clear_log_area)


        self.button_layout.addWidget(self.auto_ocr_button)
        self.button_layout.addWidget(self.start_button)
        self.button_layout.addWidget(self.stop_button)
        self.button_layout.addWidget(self.refresh_button)
        self.button_layout.addWidget(self.view_logs_button)
        self.button_layout.addWidget(self.open_success_button)
        self.button_layout.addWidget(self.clear_log_button)


        # Add a status label
        self.status_label = QLabel("Status: Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFixedHeight(200)

        self.layout.addWidget(self.status_label)
        self.layout.addLayout(self.button_layout)
        self.layout.addWidget(self.log_area)
        self.setLayout(self.layout)

        # thread and worker
        self.thread = None
        self.worker = None

        self.validate_paths()

        # self.add_mock_data()
        self.load_files()

    def validate_folders(self):
        missing_paths = []

        if not self.data_folder:
            missing_paths.append("Data Folder")
        if not self.success_folder:
            missing_paths.append("Success Folder")
        if not self.failed_folder:
            missing_paths.append("Failed Folder")
        if not self.backup_folder:
            missing_paths.append("Backup Folder")
        if not self.log_folder:
            missing_paths.append("Log Folder")
        
        return missing_paths

    def validate_paths(self):
        """Validate if all required paths are set and update UI accordingly."""
        missing_paths = self.validate_folders()
        if missing_paths:
            # Disable OCR buttons
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.auto_ocr_button.setEnabled(False)
            # Update status and log area
            self.status_label.setText("Status: Not Ready")
            self.log_area.append("The following paths are not set:")
            for path in missing_paths:
                self.log_area.append(f"- {path}")
            self.log_area.append("Please configure all paths before starting OCR.")
        else:
            # Enable OCR buttons
            self.auto_ocr_button.setEnabled(True)
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(True)
            self.status_label.setText("Status: Ready")

    def toggle_auto_ocr(self):
        """start or stop the auto OCR process."""
        if not self.auto_ocr_running:
            self.auto_ocr_running = True
            self.auto_ocr_button.setText('Stop Auto OCR')
            self.log_area.append("Auto OCR started. Monitoring folder...")

            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(False)

            self.timer.start(5000)
        else:
            self.auto_ocr_running = False
            self.processing_ocr = False
            self.auto_ocr_button.setText('Auto OCR')
            self.log_area.append("Auto OCR stopped.")

            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(True)

            self.stop_ongoing_ocr()

            self.timer.stop()

    def stop_ongoing_ocr(self):
        """Stop the currently running OCR process."""
        self.processing_ocr = False
        if self.thread and self.thread.isRunning():
            self.log_area.append("Stopping ongoing OCR process...")
            self.worker.stop()  # Custom stop method in OCRWorker
            self.thread.quit()  # Gracefully stop the thread
            self.thread.wait()
            self.thread = None
            self.worker = None
            self.log_area.append("OCR process stopped.")
        
        # Reset processing flag
        self.processing_ocr = False
        self.status_label.setText("Status: Ready")


    def auto_ocr_check(self):
        """Check the data folder for new PDF files periodically."""
        if self.processing_ocr:
            # self.log_area.append("OCR process is running. Skipping this check...")
            return 

        self.log_area.append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}-Checking for new files...")
        pdf_files = [os.path.join(self.data_folder, f) for f in os.listdir(self.data_folder) if f.endswith('.pdf')]

        if pdf_files and len(pdf_files) > 0:
            self.refresh_button.click()
            self.log_area.append(f"Found {len(pdf_files)} PDF file(s). Starting OCR...")
            self.start_ocr()  
        else:
            self.log_area.append("No new files found.")

    def view_log_file(self):
        """Open the current day's log file."""
        log_folder = os.getenv("LOG_PATH", "")
        if not log_folder:
            print("Log folder path not set in .env.")
            return

        log_file_name = f"{datetime.now().strftime('%Y-%m-%d')}_log.txt"
        log_file_path = os.path.join(log_folder, log_file_name)

        log_file_path = f"{log_folder}/{log_file_name}"

        if os.path.exists(log_file_path):
            try:
                if os.name == "nt":  # Windows
                    os.startfile(log_file_path)
            except Exception as e:
                print(f"Failed to open log file: {e}")
        else:
            print(f"Log file not found: {log_file_path}")
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setText(f"Log file for today does not exist: {log_file_name}")
            msg_box.setWindowTitle("Log File Not Found")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()
            return

    def batch_files(self, files, batch_size):
        print('in barch file: ', batch_size)
        for i in range(0, len(files), batch_size):
            yield files[i:i+batch_size]
        
    def start_ocr(self):
        # check for duplicate calls
        print('process status: ', self.processing_ocr)
        if self.processing_ocr:
            return 
        
        self.processing_ocr = True
        self.log_area.append("Starting OCR process...")

        self.status_label.setText("Status: Processing OCR...")
        

        all_files = [os.path.join(self.data_folder, f) for f in os.listdir(self.data_folder)]
        self.pdf_files = [os.path.join(self.data_folder, f) for f in os.listdir(self.data_folder) if f.endswith('.pdf')]
        non_pdf_files = [f for f in all_files if not f.endswith('.pdf')]

        for non_pdf in non_pdf_files:
            try:
                # Move to error folder
                dest_path = os.path.join(self.failed_folder, os.path.basename(non_pdf))
                # backup_destpath = os.path.join(self.backup_folder, os.path.basename(non_pdf))
                # shutil.copy(non_pdf, backup_destpath)
                shutil.move(non_pdf, dest_path)

                # Log error to text and CSV
                error_message = f"Non-PDF file moved: {os.path.basename(non_pdf)}"
                self.log_area.append(error_message)

                add_log_message(error_message, self.log_file)

                extracted_data = {"document_id": "", "error_message": error_message, "date":"", "item_name":""}
                log_result_to_csv(non_pdf, extracted_data, False, error_message)

            except Exception as e:
                self.log_area.append(f"Error handling file {non_pdf}: {str(e)}")

        if len(non_pdf_files) != 0:
            self.refresh_button.click()

        if not self.pdf_files:
            self.log_area.append("No files to process.")
            return
        

        batch_size_dynamic = get_dynamic_batch_size()
        print("-----------------------------------")
        print("batch size: ", batch_size_dynamic)
        print("-----------------------------------")
        
        self.batch_files(self.pdf_files, batch_size_dynamic)
        
        self.batches = list(self.batch_files(self.pdf_files, batch_size_dynamic))
        print("total batches", len(self.batches))
        self.current_batch = 0
        self.process_batch()

        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def process_batch(self):
        if self.current_batch >= len(self.batches):
            self.log_area.append("All files processed.")

            self.status_label.setText("Status: Ready")

            self.processing_ocr = False

            self.worker = None
            self.thread = None
            gc.collect()

            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            return

        batch = self.batches[self.current_batch]
        self.log_area.append(f"Processing batch {self.current_batch + 1}/{len(self.batches)}...")
        
        self.thread = QThread()
        self.worker = OCRWorker(batch, self.data_folder, self.success_folder, self.failed_folder, self.backup_folder, self.log_folder)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.log_area.append)
        self.worker.completed.connect(self.on_file_completed)
        self.worker.batch_completed.connect(self.on_batch_completed)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def on_batch_completed(self):
        self.log_area.append(f"Batch {self.current_batch + 1} completed.")

        if self.thread:
            if self.thread.isRunning():
                self.thread.quit()
                self.thread.wait()

        gc.collect()
        self.current_batch += 1
        self.process_batch()

    def stop_ocr(self):
        """Stop the OCR process."""
        self.processing_ocr = False
        self.log_area.append("Stopping OCR process...")
        self.status_label.setText("Status: Stopping OCR process...")
        # self.timer.stop()

        if self.worker:
            # self.worker.stop()
            self.worker._is_running = False
            self.log_area.append("Worker flagged for stopping.")

            if hasattr(self.worker, "thread_pool"):
                self.worker.thread_pool.clear()
                self.log_area.append("Thread pool cleared.")

            # # Ensure thread pool tasks are gracefully completed
            # if hasattr(self.worker, "thread_pool") and self.worker.thread_pool.activeThreadCount() > 0:
            #     self.log_area.append("Waiting for tasks to complete or stop...")
            #     self.worker.thread_pool.waitForDone()

        if self.thread:
            if self.thread.isRunning():
                self.thread.quit()
                self.thread.wait(3000)
            
        self.worker = None
        self.thread = None

        self.batches = []
        self.current_batch = 0



        self.log_area.append("OCR process stopped.")

        self.status_label.setText("Status: Ready")

        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def on_file_completed(self, file_name, status):
        """Update the status of a processed file."""
        datetime_str = get_datetime()
        self.log_area.append(f"{datetime_str} - Completed: {file_name} - {'Success' if status else 'Failed'}")

        # Update the table or other UI elements if necessary
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).text() == os.path.basename(file_name):
                status_item = QTableWidgetItem("Success" if status else "Failed")
                status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 3, status_item)
                QTimer.singleShot(3000, lambda r=row: self.table.removeRow(r))
                break

        if not os.listdir(self.data_folder):
            self.table.setRowCount(0)

    def log_message(self, message):
        """Append a log message to the log area"""
        self.log_area.append(message)

    def load_files(self):
        """Scan the data folder and populate the table with file details"""
        if not os.path.exists(self.data_folder) and self.data_folder != "":
            self.log_message(f"Data folder '{self.data_folder}' does not exist.")

        is_over_limit = self.check_folder_limit()
        if is_over_limit:
            return

        try:
            self.table.setRowCount(0)
            for file_name in os.listdir(self.data_folder):
                file_path = os.path.join(self.data_folder, file_name)
                # self.log_message(f"Found {file_path}")

                if os.path.isfile(file_path):
                    file_size = os.path.getsize(file_path)
                    file_size_str = self.human_readable_size(file_size)
                    file_date_added = self.get_date_added(file_path)
                    self.add_file_status(file_name, file_date_added, file_size_str, "Pending")
            
            self.check_table_rows()

        except Exception as e:
            self.log_message(f"Error scanning folder '{self.data_folder}': {e}")

    def add_file_status(self, file_name, added_date, file_size, processed_status):
        """Add a new file status to the table."""
        row = self.table.rowCount()
        self.table.insertRow(row)

        file_item = QTableWidgetItem(file_name)
        file_item.setFlags(file_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  
        self.table.setItem(row, 0, file_item)

        date_item = QTableWidgetItem(added_date)
        date_item.setFlags(date_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  
        date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, 1, date_item)

        size_item = QTableWidgetItem(file_size)
        size_item.setFlags(size_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  
        size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, 2, size_item)

        status_item = QTableWidgetItem(processed_status)
        status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, 3, status_item)

    def human_readable_size(self, size):
        """Convert file size to a human-readable format."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} TB"

    def get_date_added(self, file_path):
        """Get the file creation or modification date as dd/mm/yyyy."""
        try:
            if os.name == 'nt':  # For Windows
                timestamp = os.path.getctime(file_path)  
            return datetime.fromtimestamp(timestamp).strftime("%d/%m/%Y")
        except Exception as e:
            self.log_message(f"Error getting date for '{file_path}': {e}")
            return "Unknown"
        
    def open_success_folder(self):
        # Logic to open success folder
        success_folder = os.getenv("SUCCESS_PATH", "")
        if os.path.exists(success_folder):
            if os.name == 'nt':
                os.startfile(success_folder) 
                # os.system(f'explorer "{folder_path}"')
        else:
            self.log_area.append("Success folder path does not exist.")
        
    def refresh_file_list(self):
        """Refresh the list of files displayed in the table."""
        self.table.setRowCount(0)  # Clear the table

        is_over_limit = self.check_folder_limit()
        if is_over_limit:
            return 

        # Check if data folder exists
        if not os.path.exists(self.data_folder):
            self.check_table_rows()
            self.log_area.append("Data folder does not exist.")
            return

        # Populate table with files
        for file_name in os.listdir(self.data_folder):
            file_path = os.path.join(self.data_folder, file_name)
            if os.path.isfile(file_path):
                file_size = os.path.getsize(file_path)
                file_size_str = self.human_readable_size(file_size)
                file_date_added = self.get_date_added(file_path)
                self.add_file_status(file_name, file_date_added, file_size_str, "Pending")
        
        self.check_table_rows()
    
    def clear_log_area(self):
        self.log_area.clear()

    def check_table_rows(self):
        print("count: " , str(self.table.rowCount()))
        """Enable or disable the Start OCR button based on table row count."""
        if self.table.rowCount() == 0:
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(False)
        else:
            missing_paths = self.validate_folders()
            if len(missing_paths) > 0:
                self.start_button.setEnabled(False)
                self.stop_button.setEnabled(False)
            else:
                self.start_button.setEnabled(True)
                self.stop_button.setEnabled(True)

    def add_mock_data(self):
        """Add mock data to the table for testing."""
        mock_data = [
            ("file1.pdf", "08/12/2024", "2 MB", "Completed"),
            ("file2.pdf", "08/12/2024", "1.5 MB", "In Progress"),
            ("file3.pdf", "08/12/2024", "1 MB", "Pending..."),
            ("file4.pdf", "08/12/2024", "500 kB", "Pending..."),
        ]

        for file_name, added_date, file_size, processed_status in mock_data:
            self.add_file_status(file_name, added_date, file_size, processed_status)

    def check_folder_limit(self):
        # Check hard limit
        try:
            pdf_files = [os.path.join(self.data_folder, f) for f in os.listdir(self.data_folder) if f.endswith('.pdf')]
            if len(pdf_files) > MAX_FILES:
                QMessageBox.critical(
                    self,
                    "File Limit Exceeded",
                    f"The folder contains too many PDF files ({len(pdf_files)}). "
                    f"The maximum allowed is {MAX_FILES}. Please reduce the number of files and try again."
                )
                return True

            # Check recommended limit
            if len(pdf_files) > RECOMMENDED_FILES:
                QMessageBox.warning(
                    self,
                    "Warning: Large Number of Files",
                    f"The folder contains a large number of PDF files ({len(pdf_files)}). "
                    f"We recommend processing fewer than {RECOMMENDED_FILES} files for better performance."
                )

            return False
        except:
            return False
        

