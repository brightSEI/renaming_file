from PyQt6.QtCore import QObject, QThread, pyqtSignal
from pdf2image import convert_from_path
import numpy as np
import cv2
from PIL import Image

class PDFWorker(QObject):
    progress = pyqtSignal(str)
    result = pyqtSignal(str, list)  # Emit PDF path and list of images
    error = pyqtSignal(str, str)   # Emit PDF path and error message
    finished = pyqtSignal()        # Signal when task is done

    def __init__(self, pdf_path, poppler_path):
        super().__init__()
        self.pdf_path = pdf_path
        self.poppler_path = poppler_path

    def process_pdf(self):
        """Process a single PDF."""
        try:
            self.progress.emit(f"Processing: {self.pdf_path}")
            images = convert_from_path(self.pdf_path, dpi=300, poppler_path=self.poppler_path)
            resized_images = []

            for i, image in enumerate(images):
                image_array = np.array(image)
                if i == 0:  # Resize only the first image
                    resized_image_array = cv2.resize(image_array, (3600, 1000), interpolation=cv2.INTER_AREA)
                    resized_image = Image.fromarray(resized_image_array)
                else:
                    resized_image = image
                resized_images.append(resized_image)

            self.result.emit(self.pdf_path, resized_images)  # Emit PDF path and processed images
        except Exception as e:
            self.error.emit(self.pdf_path, str(e))  # Emit error message
        finally:
            self.finished.emit()

