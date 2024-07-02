import os
import time
import datetime

class CustomLogGenerator:
    def __init__(self, log_folder, file_prefix, max_file_size=1e6):
        self.log_folder = log_folder + datetime.datetime.now().strftime("%d%m%Y")
        self.file_prefix = file_prefix
        self.max_file_size = max_file_size  # in bytes

        # Create log folder if it doesn't exist
        if not os.path.exists(self.log_folder):
            os.makedirs(self.log_folder)

    def _get_filename(self, date_str, file_number=None):

        if file_number:
            return f"{self.log_folder}/{self.file_prefix}_{file_number}.log"
        else:
            return f"{self.log_folder}/{self.file_prefix}.log"

    def _get_next_file_number(self, date_str):
        i = 1
        while True:
            log_file = self._get_filename(date_str, i)
            if not os.path.exists(log_file):
                return i
            i += 1

    def generate_log(self, message):
        date_str = datetime.datetime.now().strftime("%d%m%Y")
        log_file = self._get_filename(date_str)
        next_file_number = 1

        # Check if the log file exists and its size is more than the max_file_size
        if os.path.exists(log_file) and os.path.getsize(log_file) > self.max_file_size:
            while True:
                log_file = self._get_filename(date_str, next_file_number)
                if not os.path.exists(log_file) or os.path.getsize(log_file) <= self.max_file_size:
                    break
                next_file_number += 1

        # Write the log message to the log file
        with open(log_file, 'a') as f:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{timestamp} - {message}\n")

        return log_file
