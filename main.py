import sys, traceback
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QPushButton, QMessageBox, QSplashScreen, QLabel
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QMovie
from qt_material import apply_stylesheet
from tabs.status_tab import StatusTab
from tabs.config_tab import ConfigTab
from tabs.result_tab import ResultsTab
from tabs.version_tab import VersionTab
import os
import time
from dotenv import load_dotenv

# os.environ.clear()

# run command below to compile .exe
# pyinstaller --add-data "C:\Users\cvwhcy244\AppData\Local\Programs\Python\Python312\Lib\site-packages\setuptools\_vendor\jaraco\text\lorem ipsum.txt;setuptools/_vendor/jaraco/text" --add-data "asset/loading.gif;." --hidden-import PyQt6.QtWidgets --upx-dir=C:\upx --onefile --debug all --clean  main.py  

class MainWindow(QMainWindow):
    def __init__(self, splash_screen):
        super().__init__()

        self.splash_screen = splash_screen

        self.setWindowTitle("OCR Manager")
        self.setGeometry(150, 50, 900, 700)

        self.layout = QVBoxLayout()

        # Create the tab widget
        self.tabs = QTabWidget()

        # Add tabs
        self.status_tab = StatusTab()
        self.config_tab = ConfigTab()
        self.result_tab = ResultsTab()
        self.version_tab = VersionTab()

        self.tabs.addTab(self.status_tab, "Status Monitor")
        self.tabs.addTab(self.result_tab, "Result")
        self.tabs.addTab(self.config_tab, "Configuration")
        self.tabs.addTab(self.version_tab, "Version")
        self.layout.addWidget(self.tabs)

        self.quit_button = QPushButton("Quit")
        self.quit_button.clicked.connect(self.close)

        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)

    def keyPressEvent(self, a0):
        if a0.key() == Qt.Key.Key_Q:
            QApplication.quit()
        
        return super().keyPressEvent(a0)
    
    def showEvent(self, event):
        super().showEvent(event)
        # Close the splash screen when the main window is displayed
        if self.splash_screen:
            self.splash_screen.close()
            self.splash_screen = None  # Remove reference to avoid issues


def handle_global_error(exc_type, exc_value, exc_traceback):
    """Handle uncaught exceptions."""
    error_message = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(f"Unhandled exception: {error_message}")  # Log to console or file

    # Show a user-friendly error dialog
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Icon.Critical)
    msg_box.setText("An unexpected error occurred.")
    msg_box.setInformativeText(str(exc_value))
    msg_box.setDetailedText(error_message)
    msg_box.setWindowTitle("Error")
    msg_box.setMinimumWidth(600)
    msg_box.setMaximumHeight(400)
    msg_box.exec()

def show_error_dialog(title, message):
    """Show an error dialog box."""
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Icon.Critical)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg_box.exec()

def load_environment():
    """Load the .env file and handle missing file gracefully."""
    # Determine the directory of the executable or script
    
    if getattr(sys, 'frozen', False): 
        # base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    env_path = os.path.join(base_path, '.env')
    
    # Check if .env exists
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        show_error_dialog("Configuration Error", f"The .env file is missing. Please ensure it exists at: {env_path}")
        sys.exit(1)  # Exit the application gracefully

class SplashScreen(QLabel):
    def __init__(self, gif_path, message="Loading..."):
        super().__init__()

        # Set up the label to display the GIF
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)  
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Load the GIF
        # self.movie = QMovie(gif_path)
        # self.setMovie(self.movie)
        # self.movie.start()

        # Add loading message below the GIF
        self.message_label = QLabel(message, self)
        self.message_label.setStyleSheet("""
            color: white; 
            font-size: 18px; 
            font-family: Arial, Helvetica, sans-serif; 
            text-align: center;
            padding-left:100px;
            padding-top:50px;
        """)  # Change the font-family as needed
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter)

        # Set background color
        self.setStyleSheet("background-color: black;")
        self.resize(400, 150)  # Adjust the size to fit your GIF and message



if __name__ == "__main__":
    app = QApplication(sys.argv)

    gif_path = "asset/loading.gif"  
    splash = SplashScreen(gif_path, message="Loading OCR Application...")
    splash.show()

    time.sleep(1)

    sys.excepthook = handle_global_error

    load_environment()

    apply_stylesheet(app, theme="dark_lightgreen.xml")

    main_window = MainWindow(splash)
    main_window.show()

    sys.exit(app.exec())