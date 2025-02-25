import numpy as np
import os
import screeninfo

import logging
from logging.handlers import RotatingFileHandler

import sys
import platform
import json
import random
import time
import pygame
from PIL import Image
import tempfile
from tqdm import tqdm
import argparse
import requests

from config_engine import ConfigRepository, Monitor
from media_repository import MediaRepository, SFTPClient

VERSION = '1.0/25022025'

def get_cpu_temperature():
    """
    Returns the current CPU temperature in degrees Celsius.
    If the machine is not running Linux, returns 0.
    """
    # Check if the machine is running Linux
    if platform.system() != 'Linux':
        return 0
 
    # Check if the temperature file exists
    temp_file = '/sys/class/thermal/thermal_zone0/temp'
    if not os.path.exists(temp_file):
        return 0
 
    # Read the temperature from the sysfs file
    with open(temp_file, 'r') as f:
        temp = f.read().strip()
    
    # Convert the temperature from millidegrees Celsius to degrees Celsius
    temp = int(temp) / 1000
    
    return temp

def test_internet(timeout=1):
    """
    Tests internet connectivity by attempting to connect to Google.
 
    Args:
        timeout (int): The timeout in seconds for the connection attempt. Defaults to 1.
 
    Returns:
        bool: True if internet is available, False otherwise.
    """
    try:
        requests.head('https://www.google.com', timeout=timeout)
        return True
    except requests.ConnectionError:
        return False

def check_execution_paths():
    execution_path =  os.getcwd()
    repository_path = os.path.dirname(__file__)
    
    if execution_path != repository_path:
        logging.debug(f'Execution path ({execution_path}) is different than repository path ({repository_path}). Forcing the change...')
                
        os.chdir(repository_path)
        logging.debug(f'Now, execution path is: {os.getcwd()}')


def startup_checks(config_data):
    
    _cache_path = config_data.get_cache_path()

    if not os.path.exists(_cache_path):
        logging.debug(f'Cache path not exists. Creating {_cache_path}')
        os.makedirs(_cache_path)

def update_ledger(mediaRepository, configData):

    sftp = SFTPClient(configData.config['sftp_address'], 
                      configData.config['sftp_user'], 
                      configData.config['sftp_password'])
    
    if not sftp.is_connected():
        sftp.connect()

    files_to_test = sftp.list_files(configData.config['sftp_path_ingest_new_items'])
    
    if files_to_test:
        for curr_file in tqdm(files_to_test):
            curr_file_full_path = os.path.join(configData.config['sftp_path_ingest_new_items'], curr_file)

            file_extension = os.path.splitext(curr_file)[1]
            sftp.download_file(curr_file_full_path, '/tmp' , 'tmp' + file_extension)

            if mediaRepsitory.add_image('/tmp/tmp' + file_extension) is False:
                logging.error(f'{curr_file} is a duplicate')
            else:
                logging.info(f'{curr_file} inserted to media repository')
            
            if configData.config['delete_after_ingest']:
                logging.info(f'Deleting {curr_file_full_path}')
                sftp.delete_file(curr_file_full_path)

            if os.path.exists('/tmp/tmp' + file_extension):
                os.remove('/tmp/tmp' + file_extension)

            mediaRepsitory.save_local_ledger()

    # test_ledger_integrity(mediaRepository, configData)

    if sftp.is_connected():
        sftp.close()

# def test_ledger_integrity(mediaRepository, configData):

#     files_in_cache = os.listdir(configData.get_cache_path())
        
#     num_files_in_cache = len(files_in_cache)
#     num_files_in_ledger = len(mediaRepository.local_ledger)

#     if num_files_in_cache != num_files_in_ledger:
#         logging.info(f'Files in cache ({num_files_in_cache}) is different than files in ledger ({num_files_in_ledger})')

#     for curr_file_in_cache in files_in_cache:
#         found = False
#         for curr_file_in_ledger in mediaRepository.local_ledger:
#             if curr_file_in_ledger['filename'] == curr_file_in_cache:
#                 found = True
#                 break

#         if not found:
#             logging.info(f'Files ({curr_file_in_cache}) not found, adding.')
#             mediaRepository.add_image_in_cache(curr_file_in_cache)

#         mediaRepsitory.save_local_ledger()


def get_logger(name, log_filename):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Create a rotating file handler which logs even debug messages
    # up to 10MB in size, keeping up to 5 backup files
    fh = RotatingFileHandler(log_filename, mode='a', maxBytes=10*1024*1024, backupCount=5)
    fh.setLevel(logging.DEBUG)
    
    # Create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    
    # Add the handler to the logger
    logger.addHandler(fh)
    
    return logger


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Memory Lane')
    parser.add_argument('--no-update-ledger', action='store_true', help='Do not update ledger from cloud')
    parser.add_argument('--log-analytics', action='store_true', help='Log analytics data')
    args = parser.parse_args()

    logging = get_logger('MemoryLane', '/tmp/MemoryLane.log')

    logging.info(f"Starting! Running version {VERSION}")

    check_execution_paths()

    monitor = Monitor()
    monitor.initialize()

    configData = ConfigRepository('config.json', monitor)
    
    mediaRepsitory = MediaRepository(configData)
 
    startup_checks(configData)

    # Initialize Pygame
    pygame.init()

    # Get the display dimensions
    infoObject = pygame.display.Info()

    # Set the display dimensions to the screen resolution
    screen = pygame.display.set_mode((infoObject.current_w, infoObject.current_h), pygame.FULLSCREEN)

    if not args.no_update_ledger and test_internet():
        update_ledger(mediaRepsitory, configData)

    ledger_local = mediaRepsitory.local_ledger.copy()
    random.shuffle(ledger_local)

    if args.log_analytics:
        logging.info(f"[Analytics] Shuffling {len(ledger_local)} items")

    while True:
       
        count_items = 0
        tshow = time.time()

        while ledger_local:

            if args.log_analytics:
                cpu_temp = get_cpu_temperature()
                logging.info(f"[Analytics] CPU temperature: {cpu_temp:.2f}°C")

            curr_element = ledger_local.pop(0)
            count_items += 1

            curr_filename = os.path.join(configData.get_cache_path(), curr_element['filename'])
            
            # Load the image
            if args.log_analytics:
                ts_load = time.time()

            image = pygame.image.load(curr_filename)

            if args.log_analytics:
                te_load = time.time() - ts_load
                
            # Draw the image    
            if args.log_analytics:
                ts_draw = time.time()

            screen.blit(image, (0, 0))

            if args.log_analytics:
                te_draw = time.time() - ts_draw

            # Update the display -- twice otherwise it leaves a trail of the previous image
            pygame.display.update()
            pygame.display.update()

            ts_show = time.time()
            
            end_time = ts_show + configData.config['time_show']
            time_to_wait = end_time - time.time()

            pygame.time.delay(int(time_to_wait*1000))

            if args.log_analytics:
                te_show = time.time() - ts_show
                logging.info(f"[Analytics] Showing {curr_element['filename']} | Load time: {te_load:.5f}s | Draw time: {te_draw:.5f}s | Shown for {te_show:.5f}s")
                
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    # If any key is pressed, exit the loop
                    print("Key pressed, exiting")
                    exit()
       
        if args.log_analytics:
            logging.info(f"[Analytics] Showed {count_items} items")

        if not args.no_update_ledger and test_internet():
            update_ledger( mediaRepsitory, configData)
        
        ledger_local = mediaRepsitory.local_ledger.copy()
        random.shuffle(ledger_local)

        if args.log_analytics:
            logging.info(f"[Analytics] Shuffling {len(ledger_local)} items")
