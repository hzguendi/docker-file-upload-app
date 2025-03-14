import os
import uuid
from datetime import datetime
from pathlib import Path

from app.utils.config import get_config
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)
config = get_config()


def is_file_allowed(filename):
    """
    Check if a file is allowed based on extension whitelist/blacklist.
    Returns True if allowed, False otherwise.
    """
    _, ext = os.path.splitext(filename.lower())
    
    # Check blacklist (these extensions are always blocked)
    if ext in config["upload"]["blacklist_extensions"]:
        return False
    
    # Check whitelist (if empty, all non-blacklisted extensions are allowed)
    whitelist = config["upload"]["whitelist_extensions"]
    if whitelist and ext not in whitelist:
        return False
    
    return True


def get_file_path(original_filename, username):
    """
    Generate a file path for an uploaded file using the configured naming format.
    Returns the full path where the file should be saved.
    """
    # Prepare filename variables
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_id = str(uuid.uuid4())[:8]
    
    # Get extension and base filename
    _, ext = os.path.splitext(original_filename)
    base_name = os.path.basename(original_filename).replace(ext, "")
    
    # Format variables dictionary
    format_vars = {
        "original": base_name + ext,
        "basename": base_name,
        "extension": ext,
        "timestamp": timestamp,
        "uuid": random_id,
        "user": username
    }
    
    # Format the filename
    naming_format = config["upload"]["naming_format"]
    new_filename = naming_format.format(**format_vars)
    
    # Make sure extension is included
    if not new_filename.endswith(ext):
        new_filename += ext
        
    # Create full path
    upload_dir = Path(config["upload"]["directory"])
    file_path = upload_dir / new_filename
    
    return file_path


def get_disk_usage(path=None):
    """
    Get disk usage information for a path.
    Returns (total, used, free) in bytes.
    """
    if path is None:
        path = config["upload"]["directory"]
        
    try:
        import shutil
        return shutil.disk_usage(path)
    except Exception as e:
        logger.error(f"Failed to get disk usage: {str(e)}")
        return (0, 0, 0)
