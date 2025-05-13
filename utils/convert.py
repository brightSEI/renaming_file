from pdf2image import convert_from_path
import os
import numpy as np
import cv2
import sys
from PIL import Image

def is_running_as_exe():
    """Detect if the application is running as a compiled .exe."""
    return getattr(sys, 'frozen', False)

def pdf_to_image(pdf_path, poppler_path, dpi=300, width=3600, height=1000):
    """Convert PDF to images.""" 
    print(pdf_path, dpi, width, height)
    images = convert_from_path(pdf_path, dpi=dpi, poppler_path=poppler_path)
    return images
    # resized_images = []

    # for i, image in enumerate(images):
    #     image_array = np.array(image)  # Convert Pillow image to NumPy array
    #     if i == 0:  # Resize only the first image
    #         resized_image_array = cv2.resize(image_array, (width, height), interpolation=cv2.INTER_AREA)
    #         resized_image = Image.fromarray(resized_image_array)  # Convert back to Pillow
    #     else:
    #         resized_image = image  # Keep other images as Pillow images
    #     resized_images.append(resized_image)  # Append to list

    # return resized_images


# t = pdf_to_image('C:/laragon/htdocs/SSWT/ocr-pdf-header/sswt_data\Document_20240927_0005.pdf')
# print(t)