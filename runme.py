import cv2
import numpy as np
import os.path
import screeninfo
import logging
import sys
import requests
from io import BytesIO

EXIT_WARNING = 2
EXIT_ERROR = 1

# class DataFountain:
#     def __init__(self):
#         self.type = 'Undefined'

#     def connect(self):
#         self.connector = None
        
        
# class DropboxFountain(DataFountain):
#     def	__init__(self):
#         Parent.__init__(self)
#         self.type = 'Dropbox'
        
#     def load_access_data(self, init_file):


# class LocalMediaRepository:

#     def __init__(self):
#         self.local_ledger = 'image_repository.json'
        
        
#     def load_local_ledger(self):
#         if is.path.isfile(self.local_ledger):

def load_image_from_url(image_url):
    response = requests.get(image_url)
    image_array = np.asarray(bytearray(response.content), dtype=np.uint8)
    return cv2.imdecode(image_array, cv2.IMREAD_COLOR)

def load_image(image_path):
    img = cv2.imread(image_path)
    if img is None:
        logging.error(f"{image_path} not found.")
    else:
        logging.info(f"{image_path} loaded successfully.")
    
    return img
        

def display_image(image, monitor_width, monitor_height):
    # Get image dimensions
    image_height, image_width, _ = image.shape

    # Calculate aspect ratio
    image_aspect_ratio = image_width / image_height
    monitor_aspect_ratio = monitor_width / monitor_height

    # Calculate new dimensions to fill the screen while maintaining aspect ratio
    if image_aspect_ratio > monitor_aspect_ratio:
        new_width = monitor_width
        new_height = int(monitor_width / image_aspect_ratio)
    else:
        new_width = int(monitor_height * image_aspect_ratio)
        new_height = monitor_height

    # Resize the image
    resized_image = cv2.resize(image, (new_width, new_height))

    # Calculate padding to center the image
    pad_x = (monitor_width - new_width) // 2
    pad_y = (monitor_height - new_height) // 2

    # Create a full-screen window
    cv2.namedWindow('Image', cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty('Image', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    # Create a black background to fill the entire screen
    background = np.zeros((monitor_height, monitor_width, 3), dtype=np.uint8)

    # Place the resized image in the center of the background
    background[pad_y:pad_y+new_height, pad_x:pad_x+new_width] = resized_image

    # Display the image
    cv2.imshow('Image', background)

    # Wait for a key press
    cv2.waitKey(0)

    # Close all OpenCV windows
    cv2.destroyAllWindows()

                
if __name__ == '__main__':
    
    logging.basicConfig(level=logging.DEBUG, filename="/tmp/MemoryLane.log",filemode="w")
    logging.info(f"Starting!")
    monitor = (next((m for m in screeninfo.get_monitors() if m.is_primary), None))

    if monitor is None:
        logging.critical(f"No monitors found. Terminating program")
        sys.exit(EXIT_ERROR)
            
    logging.info(f"Found active monitor.")
    
    width, height = monitor.width, monitor.height

    image_path = '/home/memorylane/MemoryLane/stamp.jpg'
    
    image = load_image(image_path)
    # image = load_image_from_url('http://memorylane.canton.cat/sammamish2300/IMG_2567.JPG')
    display_image(image, width, height)

    # image = np.ones((height, width, 3), dtype=np.float32)
    # image[:10, :10] = 0  # black at top-left corner
    # image[height - 10:, :10] = [1, 0, 0]  # blue at bottom-left
    # image[:10, width - 10:] = [0, 1, 0]  # green at top-right
    # image[height - 10:, width - 10:] = [0, 0, 1]  # red at bottom-right
    
    # window_name = 'projector'
    # cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    # cv2.moveWindow(window_name, monitor.x - 1, monitor.y - 1)
    # cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN,
    #                       cv2.WINDOW_FULLSCREEN)
    # cv2.imshow(window_name, image)
    # cv2.waitKey()
    # cv2.destroyAllWindows()


