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
from tqdm import tqdm
import argparse

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

    

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Memory Lane')
    parser.add_argument('--no-update-ledger', action='store_true', help='Do not update ledger from cloud')
    parser.add_argument('--log-analytics', action='store_true', help='Log analytics data')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, 
                        filename='/tmp/MemoryLane.log',
                        filemode="w")
    logging.info(f"Starting! Running version {VERSION}")

    check_execution_paths()

    monitor = Monitor()
    monitor.initialize()

    configData = ConfigRepository('config.json', monitor)
    
    mediaRepsitory = MediaRepository(configData)
 
    startup_checks(configData)

    sftp = SFTPClient(configData.config['sftp_address'], 
                      configData.config['sftp_user'], 
                      configData.config['sftp_password'])
    
    # Initial initialization
    if not args.no_update_ledger:
        update_ledger(sftp, mediaRepsitory, configData)
    
    # Initialize Pygame
    pygame.init()

    # Get the display dimensions
    infoObject = pygame.display.Info()

    # Set the display dimensions to the screen resolution
    screen = pygame.display.set_mode((infoObject.current_w, infoObject.current_h), pygame.FULLSCREEN)

    while True:
        
        if not args.no_update_ledger:
            update_ledger(sftp, mediaRepsitory, configData)

        ledger_local = mediaRepsitory.local_ledger.copy()
        random.shuffle(ledger_local)
        
        if args.log_analytics:
            logging.info(f"[Analytics] Shuffling {len(ledger_local)} items")

        count_items = 0
        tshow = time.time()

        while ledger_local:
            curr_element = ledger_local.pop(0)
            count_items += 1

            curr_filename = os.path.join(configData.get_cache_path(), curr_element['filename'])
            
            # Load the image
            if args.log_analytics:
                ts = time.time()

            image = pygame.image.load(curr_filename)

            if args.log_analytics:
                te_load = time.time() - ts
                

            # Draw the image    
            if args.log_analytics:
                ts = time.time()

            screen.blit(image, (0, 0))

            start_time = time.time()

            if args.log_analytics:
                te_draw = time.time() - ts

            # Update the display
            pygame.display.flip()

            if args.log_analytics:
                tmp_time = time.time()
                tshownow = tmp_time - tshow
                logging.info(f"[Analytics] Showing {curr_element['filename']} | Load time: {te_load:.5f}s | Draw time: {te_draw:.5f}s | Shown for {tshownow:.5f}s")
                tshow = tmp_time
            
            end_time = start_time + configData.config['time_show']

            time_to_wait = end_time - time.time()

            pygame.time.delay(int(time_to_wait*1000))

            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    # If any key is pressed, exit the loop
                    print("Key pressed, exiting")
                    exit()
            
            # while time.time() < end_time:
            #     for event in pygame.event.get():
            #         if event.type == pygame.KEYDOWN:
            #             # If any key is pressed, exit the loop
            #             print("Key pressed, exiting")
            #             exit()
            #     # # Update the display to keep the image visible
            #     # pygame.display.flip()
            #     # Briefly yield control to the Pygame event loop
            #     pygame.time.delay(10)
        
        if args.log_analytics:
            logging.info(f"[Analytics] Showed {count_items} items")
