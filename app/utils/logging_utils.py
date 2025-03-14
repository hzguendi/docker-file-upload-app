import logging
import os
from logging.handlers import RotatingFileHandler

from app.utils.config import get_config

# Store loggers by name to avoid duplicate setup
_loggers = {}


def get_logger(name=None):
    """Get a configured logger by name."""
    global _loggers
    
    if name is None:
        name = __name__
        
    if name in _loggers:
        return _loggers[name]
    
    # Create new logger
    logger = logging.getLogger(name)
    
    # Avoid adding duplicate handlers
    if not logger.handlers:
        setup_logger(logger, name)
        
    _loggers[name] = logger
    return logger


def setup_logger(logger=None, name=None):
    """
    Configure a logger with settings from config.
    If logger is None, the root logger is configured.
    """
    if logger is None:
        logger = logging.getLogger(name if name else "upload_server")
        
    try:
        config = get_config()
        log_config = config["logging"]
        
        # Set log level
        level = getattr(logging, log_config["level"])
        logger.setLevel(level)
        
        # Create formatter
        formatter = logging.Formatter(log_config["format"])
        
        # Add console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Add file handler
        log_file = log_config["file"]
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        if log_config.get("rotation", False):
            max_bytes = log_config.get("max_size_mb", 10) * 1024 * 1024
            backup_count = log_config.get("backup_count", 5)
            
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count
            )
        else:
            file_handler = logging.FileHandler(log_file)
            
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
    except Exception as e:
        # If we can't load config, set up a basic logger
        print(f"Error setting up logger: {str(e)}")
        logger.setLevel(logging.INFO)
        
        # Add console handler
        if not logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            logger.addHandler(console_handler)
            
    return logger
