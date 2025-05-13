import csv
import os
import shutil
from datetime import datetime
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QHBoxLayout, QHeaderView, QLabel, QDateEdit, QMessageBox, QFileDialog
from PyQt6.QtCore import QDate, Qt
from pathlib import Path


home_dir = Path.home()
image_folder = home_dir / "OCRHeader" / "image"
result_folder = home_dir / "OCRHeader" / "result_log"

class ResultsTab(QWidget):
    def __init__(self, results_folder=result_folder):
        super().__init__()
        self.results_folder = results_folder

        # Layout
        self.layout = QVBoxLayout()

        # Table Widget
        self.table = QTableWidget()
        self.layout.addWidget(self.table)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # Filter Buttons
        button_layout = QHBoxLayout()
        self.all_button = QPushButton("All")
        self.success_button = QPushButton("Success")
        self.failed_button = QPushButton("Failed")

        # Connect Buttons to Filter Functions
        self.all_button.clicked.connect(lambda: self.load_results_log(filter_by=None))
        self.success_button.clicked.connect(lambda: self.load_results_log(filter_by="Success"))
        self.failed_button.clicked.connect(lambda: self.load_results_log(filter_by="Failed"))

        button_layout.addWidget(self.all_button)
        button_layout.addWidget(self.success_button)
        button_layout.addWidget(self.failed_button)

        date_layout = QHBoxLayout()
        self.date_label = QLabel("Select Date:")
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.date_label.setStyleSheet("""
            QLabel {
                margin-top: 10px;
            }
        """)
        self.date_picker = QDateEdit()
        self.date_picker.setCalendarPopup(True)
        self.date_picker.setDate(QDate.currentDate())
        self.date_picker.dateChanged.connect(self.load_results_log_for_date)
        self.date_picker.setStyleSheet("""
            QDateEdit {
                color: #8BC34A; 
                font-weight:bold;
                padding: 5px;
            }
            QDateEdit::down-arrow {
                width: 10px;  /* Adjust size if needed */
                height: 10px; /* Adjust size if needed */
                image: none;  /* Remove default arrow */
                border-style: none;
            }
            QDateEdit::down-arrow {
                border: none;
                background: none;
                border-bottom: 2px solid #8BC34A; /* Triangle style */
                border-right: 2px solid #8BC34A;
                transform: rotate(45deg);
            }
        """)

        self.download_button = QPushButton("Download CSV")
        self.download_button.clicked.connect(self.download_log_file)

        date_layout.addWidget(self.date_label)
        date_layout.addWidget(self.date_picker)
        date_layout.addWidget(self.download_button)

        self.layout.addLayout(date_layout)
        self.layout.addLayout(button_layout)

        # Set Layout
        self.setLayout(self.layout)

        # Load Data
        self.load_results_log()
    
    def get_log_file_path(self, selected_date=None):
        """Get the log file path for the specified date or today."""
        if not selected_date:
            selected_date = datetime.now().strftime("%Y-%m-%d")
        return os.path.join(self.results_folder, f"result_log_{selected_date}.csv")

    def load_results_log(self, filter_by=None):
        """Load data from today's results log and optionally filter by status."""
        log_file_path = self.get_log_file_path(selected_date=self.date_picker.date().toString("yyyy-MM-dd"))
        try:
            with open(log_file_path, "r", encoding="utf-8", errors="replace") as file:
                reader = csv.reader(file)

                header = next(reader, None)

                data = list(reader)

                # Filter data if needed
                if filter_by:
                    data = [row for row in data if row[3] == filter_by]  

                if not data:  # If filtered or loaded data is empty
                    self.update_table([], message="No data found for the selected filter.")
                else:
                    self.update_table(data)
        except FileNotFoundError:
            self.update_table([], message="No data found for the selected date.")

    def load_results_log_for_date(self):
        """Load data for the selected date."""
        self.load_results_log()

    def download_log_file(self):
        """Download the log file for the selected date."""
        selected_date = self.date_picker.date().toString("yyyy-MM-dd")
        log_file_path = self.get_log_file_path(selected_date=selected_date)

        if not os.path.exists(log_file_path):
            QMessageBox.warning(self, "Error", f"No log file found for {selected_date}.")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Log File", f"result_log_{selected_date}.csv", "CSV Files (*.csv)"
        )

        if save_path:
            try:
                shutil.copy(log_file_path, save_path)
                QMessageBox.information(self, "Success", f"Log file saved to {save_path}.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save the log file: {e}")


    def update_table(self, data, message=None):
        """Update the table with the given data or show a message if no data is available."""
        self.table.setRowCount(0)  
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Original Name", "New Name", "Status", "Error Cause"])

        if not data:
            # If no data, show the message in the first row
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem(message if message else "No data available."))
            self.table.setSpan(0, 0, 1, 4)  # Span across all columns
            return
        
        for row_data in data:
            # Handle empty new_file_name for failed entries
            file_name = row_data[0]
            new_file_name = row_data[1] if row_data[1] else "N/A"  
            status = row_data[3]
            error_message = row_data[4] if len(row_data) > 4 else ""

            row_number = self.table.rowCount()
            self.table.insertRow(row_number)

            # Add file name
            file_item = QTableWidgetItem(file_name)
            # file_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # file_item.setFlags(file_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  
            self.table.setItem(row_number, 0, file_item)

            # Add new file name (use "N/A" if empty)
            new_file_item = QTableWidgetItem(new_file_name)
            # new_file_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # new_file_item.setFlags(new_file_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  
            self.table.setItem(row_number, 1, new_file_item)

            # Add status
            status_item = QTableWidgetItem(status)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  
            self.table.setItem(row_number, 2, status_item)

            # Add error cause
            error_item = QTableWidgetItem(error_message)
            # error_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # error_item.setFlags(error_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  
            self.table.setItem(row_number, 3, error_item)

