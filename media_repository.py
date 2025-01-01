
import hashlib
import json
import os
import io
import sys
import tempfile

import logging
import random
import string
import numpy as np
import paramiko

import imagehash
from PIL import Image


def load_image_fix_orientation(image_path):
    """
    Fix the orientation of an image.
 
    Args:
        image_path (str): The path to the image file.
 
    Returns:
        Image: The image with its orientation fixed.
    """

    try:

        image = Image.open(image_path)
    
        # Get the EXIF data from the image
        exif_data = image._getexif()
    
        # If there's no EXIF data, return the original image
        if exif_data is None:
            return image
    
        # Get the image orientation from the EXIF data
        orientation = exif_data.get(274, 1)
    
        # Rotate the image based on its orientation
        if orientation == 2:
            # Horizontal mirror
            image = image.transpose(Image.FLIP_LEFT_RIGHT)
        elif orientation == 3:
            # Rotate 180
            image = image.transpose(Image.ROTATE_180)
        elif orientation == 4:
            # Vertical mirror
            image = image.transpose(Image.FLIP_TOP_BOTTOM)
        elif orientation == 5:
            # Horizontal mirror and rotate 270
            image = image.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.ROTATE_270)
        elif orientation == 6:
            # Rotate 270
            image = image.transpose(Image.ROTATE_270)
        elif orientation == 7:
            # Horizontal mirror and rotate 90
            image = image.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.ROTATE_90)
        elif orientation == 8:
            # Rotate 90
            image = image.transpose(Image.ROTATE_90)
    
        return image
    
    except FileNotFoundError:
        logging.error(f"Image file not found: {image_path}")
        raise
    except ValueError as e:
        logging.error(f"Invalid image file: {image_path} - {e}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error: {image_path} - {e}")
        raise

class SFTPClient:
    def __init__(self, host, username, password, port=22):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.transport = None
        self.sftp = None
        self.logger = logging.getLogger(__name__)
 
    def connect(self):
        try:
            self.transport = paramiko.Transport((self.host, self.port))
            self.transport.connect(username=self.username, password=self.password)
            self.sftp = paramiko.SFTPClient.from_transport(self.transport)
            self.logger.info("SFTP connection established")
        except paramiko.AuthenticationException:
            self.logger.error("Authentication failed")
            raise
        except paramiko.SSHException as e:
            self.logger.error(f"SSH error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error connecting to SFTP server: {e}")
            raise
 
    def is_connected(self):
        if self.transport is None:
            return False
        try:
            self.transport.send_ignore()
            return True
        except paramiko.SSHException:
            self.logger.error("SFTP connection is closed")
            return False
 
    def upload_file(self, local_path, remote_path):
        try:
            self.sftp.put(local_path, remote_path)
            self.logger.info(f"File uploaded to {remote_path}")
        except paramiko.SFTPError as e:
            self.logger.error(f"Error uploading file: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error uploading file: {e}")
            raise
 
    def delete_file(self, remote_path):
        try:
            self.sftp.remove(remote_path)
            self.logger.info(f"File deleted from {remote_path}")
        except paramiko.SFTPError as e:
            self.logger.error(f"Error deleting file: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error deleting file: {e}")
            raise
 
    def file_exists(self, remote_path):
        try:
            self.sftp.stat(remote_path)
            return True
        except paramiko.SFTPError:
            return False
 
    def close(self):
        if self.transport is not None:
            self.transport.close()
            self.transport = None
            self.sftp = None
            self.logger.info("SFTP connection closed")

    def list_files(self, remote_path):
        try:
            files = self.sftp.listdir(remote_path)
            jpg_files = [file for file in files if file.lower().endswith(('.jpg', '.jpeg'))]
            return jpg_files
        except paramiko.SFTPError as e:
            self.logger.error(f"Error listing files: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error listing files: {e}")
            raise

    def download_file(self, remote_path, local_path, filename):
        try:
            full_local_path = os.path.join(local_path, filename)
            self.sftp.get(remote_path, full_local_path)
        except paramiko.SFTPError as e:
            self.logger.error(f"Error downloading file: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error downloading file: {e}")
            raise

    
    def download_file_bytes(self, remote_path):
        with tempfile.TemporaryFile() as tmp:
            self.sftp.getfo(remote_path, tmp)
            tmp.seek(0)
            return tmp.read()
        
    def delete_file(self, remote_path):
        try:
            self.sftp.remove(remote_path)
            self.logger.info(f"File deleted from {remote_path}")
        except paramiko.SFTPError as e:
            self.logger.error(f"Error deleting file {remote_path} : {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error deleting file {remote_path}: {e}")
            raise


class MediaRepository:

    def __init__(self, config_data):
        self.local_ledger = []
        self.config_data = config_data
        self.load_local_ledger()

    def add_image_in_cache(self, filename):
        path_to_img = os.path.join(self.config_data.get_cache_path(), filename)
        img = load_image_fix_orientation(path_to_img)

        img_data = {}

        # Check if image is already in ---------------
        hash = self.compute_hash(img)
                
        for curr_img_ledger in self.local_ledger:
            if self.compare_hash(curr_img_ledger['phash'], hash):
                return False

        img_data['phash'] = hash
            
        # Select random name
        img_data['filename'] = filename

        self.local_ledger.append(img_data)

        return True
    
    def add_image(self, remote_path):
        
        img = load_image_fix_orientation(remote_path)

        img_data = {}

        # Check if image is already in ---------------
        hash = self.compute_hash(img)
                
        for curr_img_ledger in self.local_ledger:
            if self.compare_hash(curr_img_ledger['phash'], hash):
                return False

        img_data['phash'] = hash
            
        # Select random name
        img_data['filename'] = self.random_name() + '.jpg'

        # Convert image to monitor resolution
        img_resized = self.prepare_image(img)

        path_to_save = os.path.join(self.config_data.get_cache_path(), img_data['filename'])
        img_resized.save(path_to_save, 'JPEG', quality=95)

        self.local_ledger.append(img_data)

        return True
                

    def compare_hash(self, hash1, hash2, threshold=10):
        diff = abs(hash1 - hash2)
        return diff < threshold

    def compute_hash(self, img):
        return int(str(imagehash.phash(img)), 16) 
    
    def random_name(self, length = 10):
        """Generate a random alphanumeric string of a specified length."""
        return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))
   
    def save_local_ledger(self):
        with open(self.config_data.config['media_repository_path'], "w") as file:
            json.dump(self.local_ledger, file, indent=4)

    def load_local_ledger(self):
        if os.path.isfile(self.config_data.config['media_repository_path']):
            with open(self.config_data.config['media_repository_path'], 'r') as f:
                self.local_ledger = json.load(f)
                logging.info(f"Read {self.config_data.config['media_repository_path']}")
        else:
            logging.info(f"Ledger file {self.config_data.config['media_repository_path']} not present. Initialized to empty.")

    def prepare_image(self, img):
        # Get the size of the monitor (width, height)
        monitor_width, monitor_height = self.config_data.get_monitor_size()
        
        # Calculate the maximum size for the image to fit within the monitor while keeping its aspect ratio
        img_width, img_height = img.size
        ratio = min(monitor_width / img_width, monitor_height / img_height)
        new_size = (int(img_width * ratio), int(img_height * ratio))
        
        # Resize the image
        img = img.resize(new_size)
        
        # Create a new black image with the monitor's size
        back = Image.new('RGB', (monitor_width, monitor_height), (0, 0, 0))
        
        # Calculate the position to center the image
        x = (monitor_width - new_size[0]) // 2
        y = (monitor_height - new_size[1]) // 2
        
        # Paste the resized image onto the black background
        back.paste(img, (x, y))

        return back