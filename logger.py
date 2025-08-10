import logging
import os
from datetime import datetime, timezone, timedelta

def setup_logger(name, log_file=None, level=logging.INFO):
    """
    Set up a logger with file and console handlers
    
    Args:
        name (str): Logger name
        log_file (str): Log file path (optional)
        level: Logging level
    
    Returns:
        logging.Logger: Configured logger
    """
    # Create logs directory if it doesn't exist
    if log_file and not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create formatters with IST timezone
    detailed_formatter = logging.Formatter(
        '%(asctime)s IST - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    simple_formatter = logging.Formatter(
        '%(asctime)s IST - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Set timezone to IST (GMT+5:30)
    ist_timezone = timezone(timedelta(hours=5, minutes=30))
    
    # Override the default time converter to use IST
    def ist_time_converter(secs):
        dt = datetime.fromtimestamp(secs, ist_timezone)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    
    detailed_formatter.converter = ist_time_converter
    simple_formatter.converter = ist_time_converter
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # File handler (if log_file specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
    
    return logger

def get_logger(name, log_file=None):
    """
    Get a logger instance
    
    Args:
        name (str): Logger name
        log_file (str): Log file path (optional)
    
    Returns:
        logging.Logger: Logger instance
    """
    return setup_logger(name, log_file) 