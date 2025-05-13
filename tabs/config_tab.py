from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox, QApplication
from dotenv import set_key
import os
import sys
import subprocess


class ConfigTab(QWidget):
    def __init__(self):
        super().__init__()

        # Layout
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(10, 10, 10, 10)  # Add internal margins
        self.layout.setSpacing(10)  # Space between widgets

        # Data Folder
        self.data_folder_layout = self.create_folder_input("Data Folder:", "DATA_PATH")

        # Failed Backup Folder
        self.failed_folder_layout = self.create_folder_input("Failed Folder:", "FAILED_PATH")

        # Success Folder
        self.success_folder_layout = self.create_folder_input("Success Folder:", "SUCCESS_PATH")

        self.backup_folder_layout = self.create_folder_input("Backup Folder:", "BACKUP_PATH")

        # Log Folder
        self.log_folder_layout = self.create_folder_input("Log Folder:", "LOG_PATH")



        # Save Button
        self.save_button = QPushButton("Save Configuration")
        self.save_button.clicked.connect(self.save_configuration)
        self.layout.addWidget(self.save_button)

        self.setLayout(self.layout)

    def create_folder_input(self, label_text, env_key):
        """Create a folder input field with a browse button."""
        layout = QHBoxLayout()
        label = QLabel(label_text)
        line_edit = QLineEdit()
        line_edit.setText(os.getenv(env_key, ""))  # Load current value from .env
        line_edit.setStyleSheet("""
            QLineEdit {
                color: #8BC34A; 
                font-weight:bold;
                padding: 5px;
            }
        """)

        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(lambda: self.browse_folder(line_edit, env_key))

        layout.addWidget(label)
        layout.addWidget(line_edit)
        layout.addWidget(browse_button)
        self.layout.addLayout(layout)

        return layout

    def browse_folder(self, line_edit, env_key):
        """Open file dialog to select a folder."""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            line_edit.setText(folder)
            set_key(".env", env_key, folder)  # Update .env file

    def save_configuration(self):
        """Save the updated configuration."""
        print("Configuration saved!")

        # Ask for confirmation
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setText("The application needs to close to apply changes. Do you want to close now?")
        msg_box.setWindowTitle("Restart Application")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        response = msg_box.exec()

        if response == QMessageBox.StandardButton.Yes:
            # Restart using subprocess
            if getattr(sys, 'frozen', False): 
                QApplication.quit()
            else:
                python = sys.executable  
                os.execl(python, python, *sys.argv)
        else:
            print("Restart canceled.")
