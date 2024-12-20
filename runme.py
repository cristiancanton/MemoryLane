import numpy as np
import os.path
import screeninfo
import logging
import sys
import json
import random
import time
import pygame
from PIL import Image
import tempfile

from config_engine import ConfigRepository, Monitor
from media_repository import MediaRepository, SFTPClient

VERSION = '1.0/17122024'

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

def update_ledger(sftp, mediaRepository, configData):
    
    if not sftp.is_connected():
        sftp.connect()

    files_to_test = sftp.list_files(configData.config['sftp_path_ingest_new_items'])
    
    for curr_file in files_to_test:
        curr_file_full_path = os.path.join(configData.config['sftp_path_ingest_new_items'], curr_file)

        file_extension = os.path.splitext(curr_file)[1]
        sftp.download_file(curr_file_full_path, '/tmp' , 'tmp' + file_extension)

        if mediaRepsitory.add_image('/tmp/tmp' + file_extension) is False:
            logging.error(f'{curr_file} is a duplicate')
        else:
            logging.info(f'{curr_file} inserted to media repository')
            sftp.delete_file(curr_file_full_path)

        if os.path.exists('/tmp/tmp' + file_extension):
            os.remove('/tmp/tmp' + file_extension)

    mediaRepsitory.save_local_ledger()

    if sftp.is_connected():
        sftp.close()

if __name__ == '__main__':

    logging.basicConfig(level=logging.ERROR, 
                        filename='/tmp/MemoryLane.log',
                        filemode="w")
    logging.info(f"Starting! Running version {VERSION}")

    configData = ConfigRepository('config.json')
    
    check_execution_paths()

    mediaRepsitory = MediaRepository(configData)
    
    monitor = Monitor()
    monitor.initialize()

    configData.config['monitor_width'], configData.config['monitor_height'] = monitor.device.width, monitor.device.height

    startup_checks(configData)

    sftp = SFTPClient(configData.config['sftp_address'], 
                      configData.config['sftp_user'], 
                      configData.config['sftp_password'])
    
    # Initialize Pygame
    pygame.init()

    # Get the display dimensions
    infoObject = pygame.display.Info()

    # Set the display dimensions to the screen resolution
    screen = pygame.display.set_mode((infoObject.current_w, infoObject.current_h), pygame.FULLSCREEN)

    while True:
        
        update_ledger(sftp, mediaRepsitory, configData)

        ledger_local = mediaRepsitory.local_ledger.copy()
        random.shuffle(ledger_local)

        while ledger_local:
            curr_element = ledger_local.pop(0)

            curr_filename = os.path.join(configData.get_cache_path(), curr_element['filename'])
                
            start_time = time.time()
            # Load the image
            image = pygame.image.load(curr_filename)

            # Draw the image    
            screen.blit(image, (0, 0))

            # Update the display
            pygame.display.flip()

            end_time = start_time + configData.config['time_show']
            while time.time() < end_time:
                for event in pygame.event.get():
                    if event.type == pygame.KEYDOWN:
                        # If any key is pressed, exit the loop
                        print("Key pressed, exiting")
                        exit()
                # # Update the display to keep the image visible
                # pygame.display.flip()
                # Briefly yield control to the Pygame event loop
                pygame.time.delay(1000)