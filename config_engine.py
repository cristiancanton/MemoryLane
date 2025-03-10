import screeninfo
import sys
import json
import os
import logging

EXIT_WARNING = 2
EXIT_ERROR = 1

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


    def get_size(self):
        assert(self.device is not None)
        return self.device.width, self.device.height

class ConfigRepository:
    def __init__(self, config_file_path, logger, monitor=None):
        """
        Initialize the ConfigRepository instance.
 
        :param config_file_path: Path to the JSON configuration file.
        """
        self.config_file_path = config_file_path
        self.config = {}
        self.logger = logger

        self.set_defaults()

        loaded = self.load_config()

        if monitor is not None:
            width, height = monitor.get_size()
            
            if self.config['monitor_width'] == 0 and self.config['monitor_height'] == 0:
                self.set_monitor(width, height)
                self.save_config()
            elif self.config['monitor_width'] != width or self.config['monitor_height'] != height:
                self.logger.warning(f"Monitor size mismatch. Expected {self.config['monitor_width']}x{self.config['monitor_height']}, but got {width}x{height}.")
                self.logger.warning(f"Setting monitor size to {width}x{height}")
                self.set_monitor(width, height) 
                self.save_config()

        if not loaded:
            self.save_config()
            
 
    def load_config(self):
        """
        Load the configuration from the JSON file.
 
        If the file does not exist, an empty configuration is returned.
        """
        if os.path.exists(self.config_file_path):
            self.logger.info(f'Loading config file {self.config_file_path}')
            with open(self.config_file_path, 'r') as config_file:
                self.config = json.load(config_file)
            return True
        else:
            self.logger.info(f'Config file {self.config_file_path} does not exists. Setting to defaults')
            return False
 
    def save_config(self):
        """
        Save the configuration to the JSON file.
 
        If the file does not exist, it will be created.
        """
        with open(self.config_file_path, 'w') as config_file:
            json.dump(self.config, config_file, indent=4)

        self.logger.info(f'Saved config file {self.config_file_path}')

    def data(self):
        return self.config

    def set_defaults(self):
        self.config['cache_path_prefix'] = 'cache'
        self.config['media_repository_path'] = 'media_repository.json'
        self.config['monitor_width'] = 0
        self.config['monitor_height'] = 0

        #SFTP data
        self.config['sftp_address'] = 'your address'
        self.config['sftp_user'] = 'user'
        self.config['sftp_password'] = 'password'
        self.config['sftp_path'] = 'your path'
        self.config['sftp_path_ingest_new_items'] = 'your ingestion path'
        self.config['delete_after_ingest'] = True

        #Display
        self.config['time_show'] = 35

    def set_monitor(self, width, height):
        self.config['monitor_width'], self.config['monitor_height'] = width, height

    def get_monitor_aspect_ratio(self):
        return self.config['monitor_width'] / self.config['monitor_height']
    
    def get_monitor_size(self):
        return self.config['monitor_width'], self.config['monitor_height']

    def get_cache_path(self):
        return self.config['cache_path_prefix'] + '_' + str(self.config['monitor_width']) + 'x' + str(self.config['monitor_height'])

    def update_config_if_changed(self):
        """
        Load the JSON config file and update self.config if the data has changed.
 
        :return: True if the config was updated, False otherwise.
        """
        try:
            with open(self.config_file_path, 'r') as config_file:
                new_config = json.load(config_file)
        except FileNotFoundError:
            self.logger.info(f'Config file {self.config_file_path} does not exist.')
            return False
        except json.JSONDecodeError as e:
            self.logger.error(f'Failed to parse JSON config file: {e}')
            return False
 
        if new_config != self.config:
            self.config = new_config
            self.logger.info(f'Updated config file {self.config_file_path}')
            return True
        else:
            self.logger.info(f'Config file {self.config_file_path} has not changed.')
            return False
    
    