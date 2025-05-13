from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QMessageBox
from PyQt6.QtCore import Qt
import os, sys
from worker.groupfilesworker import GroupFilesWorker

def get_base_path():
    """Return the base path for the application."""
    if hasattr(sys, '_MEIPASS'):  # PyInstaller temp directory
        return sys._MEIPASS
    return os.path.abspath(".")


def load_file_content(file_name):
    """Read the content of a file, or return None if it doesn't exist."""
    try:
        # base_path = get_base_path()
        # base_path = os.path.dirname(sys.executable)
        if getattr(sys, 'frozen', False): 
            # When running as an executable
            base_path = os.path.dirname(sys.executable)
        else:
            # When running locally, use the directory of the current script
            base_path = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_path, file_name)
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read().strip()
    except FileNotFoundError:
        return None

class VersionTab(QWidget):
    def __init__(self):
        super().__init__()
        
        # self.version = version
        # self.changelog = changelog or []

        # Load version and changelog dynamically
        self.version = load_file_content("version.txt") or "Unknown"
        self.changelog = load_file_content("changelog.txt") or "No updates available."

        self.success_folder = os.getenv("SUCCESS_PATH", "")

        # Layout
        layout = QVBoxLayout()

        # Version Label
        version_label = QLabel(f"Application Version: {self.version}")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)

        # Changelog
        changelog_area = QTextEdit()
        changelog_area.setReadOnly(True)
        changelog_area.setText(self.changelog)
        layout.addWidget(changelog_area)

        # Check for Updates Button (Optional)
        update_button = QPushButton("Check for Updates")
        update_button.clicked.connect(self.check_for_updates)
        layout.addWidget(update_button)

        self.group_file = QPushButton("Group Files in Success Folder (old format without barcode only)")
        self.group_file.clicked.connect(self.group_file_into_folder)
        layout.addWidget(self.group_file)

        self.setLayout(layout)

    def format_changelog(self):
        """Format the changelog as a string."""
        if not self.changelog:
            return "No updates available."
        return "\n".join(self.changelog)

    def check_for_updates(self):
        """Simulate checking for updates."""
        # In a real application, this would connect to a server to check for updates
        print("Checking for updates...")
        QMessageBox.information(self, "Update Check", "Your application is up-to-date.")

    def group_file_into_folder(self):

        if not self.success_folder:
            QMessageBox.warning(self, "Error", "The success folder path is not set.")
            return
        
        self.group_file.setEnabled(False)

        self.worker = GroupFilesWorker(self.success_folder)
        self.worker.finished.connect(lambda result: self.on_group_files_finished(result))
        self.worker.start()
        
    def on_group_files_finished(self, result):
        self.group_file.setEnabled(True)
        if result:
            QMessageBox.information(self, "Task Complete", "Files have been grouped successfully.")
        else:
            QMessageBox.warning(self, "Task Failed", "Failed to group files. Please check the logs.")
