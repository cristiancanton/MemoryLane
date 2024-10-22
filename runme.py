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
import hashlib
import exifread

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
    try:
        response = requests.get(image_url)
        raw_data = BytesIO(response.content)

        image_array = np.asarray(bytearray(raw_data.read()), dtype=np.uint8)
        img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        logging.info(f"Loaded image {image_url}")

        # tags = exifread.process_file(raw_data)
        
        # for tag in tags.keys():
        #     if tag not in ["JPEGThumbnail", "TIFFThumbnail", "Filename", "EXIF MakerNote"]:
        #         logging.info(f"{tag}: {tags[tag]}")


    except Exception as e:
        logging.critical(f"An error occurred loading image {image_url}: {e}")

    return img


def load_image(image_path):
    img = cv2.imread(image_path)
    if img is None:
        logging.error(f"{image_path} not found.")
    else:
        logging.info(f"{image_path} loaded successfully.")
    
    return img

def draw_horizontal_line(image, alpha):
    """
    Draws a horizontal line at the bottom of the image.

    Args:
    image (numpy array): The input image.
    alpha (float): A value between 0 and 1 that controls the length of the line.

    Returns:
    image (numpy array): The image with the horizontal line drawn.
    """
    height, width, _ = image.shape

    # Calculate the end point of the line based on alpha
    end_x = int(width * alpha)

    # Draw the line
    cv2.line(image, (0, height-2), (end_x, height-2), (255, 255, 255), 4)

    return image

class ImageFetcher(threading.Thread):
    def __init__(self, queue, media_repo):
        threading.Thread.__init__(self)
        self.queue = queue
        self.media_repo = media_repo

    def run(self):
        while True:
            
            try:
                image = self.media_repo.next_random_sequential_item()
                self.queue.put(image)
            except Exception as e:
                logging.info(f"Error fetching image: {e}")

            time.sleep(FETCH_INTERVAL)


class URLFountain:
    def	__init__(self, url):
        self.type = 'URL' 
        self.url = url
        self.items = None

        self.update_files()

    def update_files(self):
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
            logging.critical(f"Can't load files from Internet. An error occurred: {e}")
            return []
    


class MediaRepository:

    def __init__(self, monitor_width, monitor_height, url_fountain):
        self.local_ledger_filename = 'image_repository.json'
        self.local_ledger = {}
        self.monitor_width, self.monitor_height = monitor_width, monitor_height
        self.url_fountain = url_fountain

        #Sequential display of images
        self.images_to_display = []

    def internal_hash(self, input_string):
        return hashlib.md5(input_string.encode()).hexdigest()
    
    def save_local_ledger(self):
        with open(self.local_ledger_filename, "w") as file:
            json.dump(self.local_ledger, file, indent=4)

    def load_local_ledger(self):
        if os.path.isfile(self.local_ledger_filename):
            with open(self.local_ledger_filename, 'r') as f:
                self.local_ledger = json.load(f)
                logging.info(f"Read {self.local_ledger_filename}")
        else:
            self.local_ledger = {}
            logging.info(f"Ledger file {self.local_ledger_filename} not present. Initialized to empty.")

    def update(self):
        self.url_fountain.update_files()
        new_files = self.url_fountain.items

        set_filenames_hashed = []

        # Add new images

        for curr_file in new_files:
            filename_hashed = self.internal_hash(curr_file)

            set_filenames_hashed.append(filename_hashed)

            if filename_hashed not in self.local_ledger:
                data = {}
                data['url'] = curr_file
                data['local_path'] = f'{filename_hashed}.jpg'
                self.local_ledger[filename_hashed] = data
            
        # Remove images not in url_fountain
        keys_to_remove = []
        for curr_hash in self.local_ledger.keys():
            if curr_hash in set_filenames_hashed:
                continue
            
            keys_to_remove.append(curr_hash)

        for curr_hash in keys_to_remove:

            logging.info(f"Removed {curr_hash} --> {self.local_ledger[curr_hash]['url']}")

            if os.path.exists(self.local_ledger[curr_hash]['local_path']):
                os.remove(self.local_ledger[curr_hash]['local_path'])
                logging.info(f"Deleted {self.local_ledger[curr_hash]['local_path']}")

            del self.local_ledger[curr_hash]

    def prepare_image(self, image):
        # Get image dimensions
        image_height, image_width, _ = image.shape

        # Calculate aspect ratio
        image_aspect_ratio = image_width / image_height
        monitor_aspect_ratio = self.monitor_width / self.monitor_height

        # Calculate new dimensions to fill the screen while maintaining aspect ratio
        if image_aspect_ratio > monitor_aspect_ratio:
            new_width = self.monitor_width
            new_height = int(self.monitor_width / image_aspect_ratio)
        else:
            new_width = int(self.monitor_height * image_aspect_ratio)
            new_height = self.monitor_height

        # Resize the image
        resized_image = cv2.resize(image, (new_width, new_height))

        # Calculate padding to center the image
        pad_x = (self.monitor_width - new_width) // 2
        pad_y = (self.monitor_height - new_height) // 2

        # Create a black background to fill the entire screen
        background = np.zeros((self.monitor_height, self.monitor_width, 3), dtype=np.uint8)

        # Place the resized image in the center of the background
        background[pad_y:pad_y+new_height, pad_x:pad_x+new_width] = resized_image

        return background

    def load_item(self, key_to_item):
        item_to_load = self.local_ledger[key_to_item]
        
        if os.path.exists(item_to_load['local_path']): #cached
            logging.info(f"Image {item_to_load['local_path']} cached. Loading from disk!")
            return load_image(item_to_load['local_path'])
                
        img = load_image_from_url(item_to_load['url'])
        img = self.prepare_image(img)

        cv2.imwrite(item_to_load['local_path'], img) # cache it for the future
        return img

    def next_random_item(self):
        key_to_item = random.choice(list(self.local_ledger.keys()))
        logging.info(f"Loading {key_to_item}")
        return self.load_item(key_to_item)
    
    def next_random_sequential_item(self):
        if len(self.images_to_display) == 0:

            self.update()

            self.images_to_display = list(self.local_ledger.keys())
            random.shuffle(self.images_to_display)
            logging.info(f"Reshuffled images to display (total = {len(self.images_to_display)})")

        key_to_item = self.images_to_display.pop()
        logging.info(f"Loading {key_to_item}")
        return self.load_item(key_to_item)


# def display_image(image, monitor_width, monitor_height):

#     image_to_display = prepare_image(image, monitor_width, monitor_height)
   
#     # Create a full-screen window
#     cv2.namedWindow('Image', cv2.WND_PROP_FULLSCREEN)
#     cv2.setWindowProperty('Image', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

#     # Display the image
#     cv2.imshow('Image', image_to_display)

#     # Wait for a key press
#     cv2.waitKey(0)

#     # Close all OpenCV windows
#     cv2.destroyAllWindows()

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
    
    version = '1.0 from 22102024'

    logging.basicConfig(level=logging.DEBUG, filename="/tmp/MemoryLane.log",filemode="w")
    logging.info(f"Starting! Running version {version}")

    monitor = Monitor()
    monitor.initialize()
    
    monitor_width, monitor_height = monitor.device.width, monitor.device.height

    data_fountain = URLFountain('http://memorylane.canton.cat/sammamish2300')

    media_repository = MediaRepository(monitor_width, monitor_height, data_fountain)
    media_repository.load_local_ledger()
    media_repository.update()
    media_repository.save_local_ledger()

    image_queue = queue.Queue(maxsize=QUEUE_SIZE)

    # Create image fetcher thread
    fetcher = ImageFetcher(image_queue, media_repository)
    fetcher.daemon = True
    fetcher.start()
   
    # Create a full-screen window
    cv2.namedWindow('Image', cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty('Image', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    time_show = 30
 
    try:
        while(True):
            image = image_queue.get()

            # image_to_display = draw_horizontal_line(image.copy(), 1)
        
            # Display the image
            # cv2.imshow('Image', image_to_display)
            cv2.imshow('Image', image)
            
            start_time = time.time()

            previous_second = time_show

            while True:
                t_passed = time.time() - start_time

                second = time_show - int(t_passed)
                # if second != previous_second:
                #     alpha = second / time_show
                    
                #     image_to_display = draw_horizontal_line(image.copy(), alpha)
                #     cv2.imshow('Image', image_to_display)
                #     previous_second = second

                if second <= 0:
                    break

                cv2.waitKey(1)

        # Close all OpenCV windows
        cv2.destroyAllWindows()
    except Exception as e:
        logging.critical(f"An error occurred: {e}")
    

