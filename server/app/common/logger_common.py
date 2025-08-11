import logging
import os

class Logger:
    @staticmethod
    def _remove_logger():
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
    
    @staticmethod
    def set_logger(log_path, file_name):
        if not os.path.exists(log_path):
            os.makedirs(log_path)   
        Logger._remove_logger()             
        logging.basicConfig(filename=f'''{log_path}/{file_name}''', format = '%(asctime)s:%(levelname)s:%(message)s', level=logging.INFO)