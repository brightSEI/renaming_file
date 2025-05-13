from PyQt6.QtCore import QThread, pyqtSignal
from utils.format import organize_files


class GroupFilesWorker(QThread):
    finished = pyqtSignal(bool)

    def __init__(self, success_folder):
        super().__init__()
        self.success_folder = success_folder
    
    def run(self):
        result = organize_files(self.success_folder)
        self.finished.emit(result)