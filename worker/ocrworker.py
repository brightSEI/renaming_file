import os
import pytesseract
from PyQt6.QtCore import QObject, pyqtSignal, QThreadPool
from datetime import datetime
from utils.file import delete_folders
from utils.convert import is_running_as_exe 
from worker.ocrtask import OcrTask
from pathlib import Path
from functools import partial

print('Please wait...')

tesseract_path = os.path.abspath('./binaries/tesseract/tesseract.exe')
pytesseract.pytesseract.tesseract_cmd = tesseract_path
# pytesseract.pytesseract.tesseract_cmd = os.getenv('OCR_PATH')

# image_folder   = './image'
# result_folder  = './result_log'
home_dir = Path.home()
image_folder = home_dir / "OCRHeader" / "image"
result_folder = home_dir / "OCRHeader" / "result_log"
delete_folders(image_folder)
os.makedirs(image_folder, exist_ok=True)
os.makedirs(result_folder, exist_ok=True)

class OCRWorker(QObject):
    progress = pyqtSignal(str)
    completed = pyqtSignal(str, bool)
    batch_completed = pyqtSignal()

    def __init__(self, batch, data_folder, success_folder, failed_folder, backup_folder, log_folder):
        super().__init__()

        self.batch = batch

        self.poppler_path = os.path.abspath('./binaries/poppler/bin') if is_running_as_exe() else 'C:/poppler-24.07.0/Library/bin'


        self.log_file = os.path.join(log_folder, f"{datetime.now().strftime('%Y-%m-%d')}_log.txt")

        self.data_folder = data_folder
        self.success_folder = success_folder
        self.failed_folder = failed_folder
        self.backup_folder = backup_folder
        self.log_folder = log_folder
        self._is_running = True
         # Thread pool for parallel tasks
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(1)
    
    def run(self):
        """Worker initialization."""
        self.progress.emit("Worker started.")
        self.process_file()

    def process_file(self):
        """Process the files in the batch."""
        self.pending_tasks = len(self.batch)  # Track pending tasks
        for pdf_path in self.batch:
            if not self._is_running:
                self.progress.emit("Processing stopped.")
                return
            
            task = OcrTask(pdf_path, self.success_folder, self.failed_folder, self.backup_folder, self.log_file, self._is_running, self.poppler_path)
            task.signals.progress.connect(self.progress.emit)
            task.signals.completed.connect(self.on_task_completed)
            self.thread_pool.start(task)

        # self.thread_pool.waitForDone()
        # self.batch_completed.emit()

    
    # def process_file(self):
    #     """Process the next file in the list."""
    #     for pdf_path in self.batch:
    #         if not self._is_running:
    #             self.progress.emit("Processing stopped or no more files.")
    #             return
            
    #         task = OcrTask(pdf_path, self.success_folder, self.failed_folder, self.backup_folder, self.log_file)
    #         task.signals.progress.connect(self.progress.emit)
    #         task.signals.completed.connect(lambda path, status: self.completed.emit(path, status))
    #         # task.signals.completed.connect(partial(self.completed.emit, pdf_path))
    #         task.is_running = self._is_running
    #         # submit the task to thread pool
    #         self.thread_pool.start(task)

    #     # self.thread_pool.waitForDone()
    #     self.batch_completed.emit()



    def on_task_completed(self, pdf_path, status):
        """Handle the completion of a single file."""
        self.completed.emit(pdf_path, status)
        self.pending_tasks -= 1  # Decrement pending tasks counter
        if self.pending_tasks == 0:  # If all tasks are complete
            self.batch_completed.emit()


    def stop(self):
        """Stop the worker gracefully."""
        self._is_running = False
        self.thread_pool.clear()
        self.progress.emit("Processing stopped.")