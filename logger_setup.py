import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import threading
import time

_logger = None
_current_date = None
_monitor_thread = None
_lock = threading.Lock()


class CustomRotatingFileHandler(RotatingFileHandler):
    """
    RotatingFileHandler that names rotated files like:
    kafka_processor.log → kafka_processor_1.log → kafka_processor_2.log
    instead of the default .log.1, .log.2
    """
    def rotate(self, source, dest):
        # Remove destination if exists
        if os.path.exists(dest):
            os.remove(dest)
        os.rename(source, dest)

    def doRollover(self):
        """
        Customized rollover to rename files in desired format.
        """
        if self.stream:
            self.stream.close()
            self.stream = None

        # Rotate older backups first
        for i in range(self.backupCount - 1, 0, -1):
            sfn = self.rotation_filename(self.baseFilename.replace(".log", f"_{i}.log"))
            dfn = self.rotation_filename(self.baseFilename.replace(".log", f"_{i+1}.log"))
            if os.path.exists(sfn):
                self.rotate(sfn, dfn)

        # Rename current file to _1
        dfn = self.rotation_filename(self.baseFilename.replace(".log", "_1.log"))
        self.rotate(self.baseFilename, dfn)

        # Reopen the stream
        if not self.delay:
            self.stream = self._open()


def _get_log_dir():
    today = datetime.now().strftime('%Y-%m-%d')
    path = os.path.join("logs", today)
    os.makedirs(path, exist_ok=True)
    return today, path


def _setup_logger():
    global _logger, _current_date

    with _lock:
        _current_date, log_dir = _get_log_dir()

        log_file = os.path.join(log_dir, "kafka_processor.log")

        if _logger is None:
            _logger = logging.getLogger("FeedProcessor")
            _logger.setLevel(logging.INFO)

        if _logger.hasHandlers():
            _logger.handlers.clear()

        # Our custom rotating file handler
        file_handler = CustomRotatingFileHandler(
            log_file,
            maxBytes=30 * 1024 * 1024,  # 10 MB
            backupCount=100,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s'
        ))

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s'
        ))

        _logger.addHandler(file_handler)
        _logger.addHandler(console_handler)

        _logger.info(f"Logger initialized for date: {_current_date} at {log_file}")


def _monitor_date():
    global _current_date
    while True:
        time.sleep(60)
        today = datetime.now().strftime('%Y-%m-%d')
        if today != _current_date:
            _setup_logger()


def init_logger_with_monitor():
    global _monitor_thread

    if _monitor_thread is None or not _monitor_thread.is_alive():
        _setup_logger()
        _monitor_thread = threading.Thread(target=_monitor_date, daemon=True)
        _monitor_thread.start()

    return _logger
