import cv2
import numpy as np
import os.path
import screeninfo
import logging
import sys
import requests
from io import BytesIO
import json
import random
import time

import requests
from bs4 import BeautifulSoup
import re

import threading
import queue

EXIT_WARNING = 2
EXIT_ERROR = 1

FETCH_INTERVAL = 3
QUEUE_SIZE = 3

def load_image_from_url(image_url):
    response = requests.get(image_url)
    image_array = np.asarray(bytearray(response.content), dtype=np.uint8)
    return cv2.imdecode(image_array, cv2.IMREAD_COLOR)

class ImageFetcher(threading.Thread):
    def __init__(self, queue, urls):
        threading.Thread.__init__(self)
        self.queue = queue
        self.urls = urls

    def run(self):
        while True:
            
            random.shuffle(self.urls)

            for url in self.urls:
                try:
                    image = load_image_from_url(url)
                    self.queue.put(image)
                    logging.info(f"Fetched image from {url}")
                except Exception as e:
                    logging.info(f"Error fetching image from {url}: {e}")
                time.sleep(FETCH_INTERVAL)


class URLFountain:
    def	__init__(self, url):
        self.type = 'URL' 
        self.url = url
        self.items = self.get_files()

    def get_files(self):
        try:
            response = requests.get(self.url)
            soup = BeautifulSoup(response.text, 'html.parser')
            file_urls = []
            for a in soup.find_all('a', href=True):
                link = a['href']
                # Very basic check for file extensions, adjust as needed
                if re.search(r'\.(jpg|JPG|png|PNG)$', link):
                    # Ensure full URL (in case of relative paths)
                    if not link.startswith('http'):
                        if link.startswith('/'):
                            link = self.url + link
                        else:
                            link = self.url + '/' + link
                    file_urls.append(link)
            return file_urls
        except Exception as e:
            logging.critical(f"An error occurred: {e}")
            return []
    
class LocalMediaRepository:

    def __init__(self):
        self.local_ledger_filename = 'image_repository.json'
        self.local_ledger = None
        
    def load_local_ledger(self):
        if os.path.isfile(self.local_ledger_filename):
            with open(self.local_ledger_filename, 'r') as f:
                self.local_ledger = json.load(f)
                logging.info(f"Read {self.local_ledger_filename}")
        else:
            self.local_ledger = []
            logging.info(f"Ledger file {self.local_ledger_filename} not present. Initialized to empty.")

    def update(self, )
    




def load_image(image_path):
    img = cv2.imread(image_path)
    if img is None:
        logging.error(f"{image_path} not found.")
    else:
        logging.info(f"{image_path} loaded successfully.")
    
    return img


def prepare_image(image, monitor_width, monitor_height):
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

     # Create a black background to fill the entire screen
    background = np.zeros((monitor_height, monitor_width, 3), dtype=np.uint8)

    # Place the resized image in the center of the background
    background[pad_y:pad_y+new_height, pad_x:pad_x+new_width] = resized_image

    return background

def display_image(image, monitor_width, monitor_height):

    image_to_display = prepare_image(image, monitor_width, monitor_height)
   
    # Create a full-screen window
    cv2.namedWindow('Image', cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty('Image', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    # Display the image
    cv2.imshow('Image', image_to_display)

    # Wait for a key press
    cv2.waitKey(0)

    # Close all OpenCV windows
    cv2.destroyAllWindows()

class Monitor:
    def __init__(self):
        self.device = None

    def initialize(self):
        _monitors = screeninfo.get_monitors()
        if _monitors is None:
            logging.critical(f"No monitors found. Terminating program")
            sys.exit(EXIT_ERROR)
                
        if len(_monitors) == 1:
            self.device = _monitors[0]
        else:
            self.device = (next((m for m in _monitors if m.is_primary), None))

        if self.device is None:
            logging.critical(f"No *primary* monitors found. Terminating program")
            sys.exit(EXIT_ERROR)
                
        logging.info(f"Found active monitor.")

                
if __name__ == '__main__':
    
    logging.basicConfig(level=logging.DEBUG, filename="/tmp/MemoryLane.log",filemode="w")
    logging.info(f"Starting!")

    monitor = Monitor()
    monitor.initialize()
    
    monitor_width, monitor_height = monitor.device.width, monitor.device.height

    image_path = '/home/memorylane/MemoryLane/stamp.jpg'
    data_fountain = URLFountain('http://memorylane.canton.cat/sammamish2300')

    image_queue = queue.Queue(maxsize=QUEUE_SIZE)

    # Create image fetcher thread
    fetcher = ImageFetcher(image_queue, data_fountain.items)
    fetcher.daemon = True
    fetcher.start()

    # #image = load_image(image_path)
   
    # Create a full-screen window
    cv2.namedWindow('Image', cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty('Image', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    items_to_display = []
    try:
        while(True):
            image = image_queue.get()
            image_to_display = prepare_image(image, monitor_width, monitor_height)
        
            # Display the image
            cv2.imshow('Image', image_to_display)
            
            start_time = time.time()
            while time.time() - start_time < 30:
                cv2.waitKey(1)

        # Close all OpenCV windows
        cv2.destroyAllWindows()
    except Exception as e:
        logging.critical(f"An error occurred: {e}")
    

