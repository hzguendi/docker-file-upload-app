import os
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from app.utils.config import get_config
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)
config = get_config()

# Initialize mimetypes
mimetypes.init()

def get_file_list(page: int = 1, per_page: Optional[int] = None) -> Dict:
    """
    Get a paginated list of files in the upload directory.
    
    Returns:
        Dict with files, total, page, and pages
    """
    if per_page is None:
        per_page = config["download"].get("page_size", 20)
        
    upload_dir = Path(config["upload"]["directory"])
    
    # Get all files (excluding directories)
    all_files = []
    for item in upload_dir.iterdir():
        if item.is_file() and not item.name.startswith('.'):
            stats = item.stat()
            file_info = {
                "name": item.name,
                "path": str(item),
                "size": stats.st_size,
                "size_formatted": format_file_size(stats.st_size),
                "modified": datetime.fromtimestamp(stats.st_mtime),
                "modified_formatted": datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "type": get_file_type(item.name),
                "icon": get_file_icon(item.name),
                "previewable": is_file_previewable(item.name)
            }
            all_files.append(file_info)
    
    # Sort files by modified date (newest first)
    all_files.sort(key=lambda x: x["modified"], reverse=True)
    
    # Calculate pagination
    total_files = len(all_files)
    total_pages = (total_files + per_page - 1) // per_page
    
    # Adjust page if out of bounds
    if page < 1:
        page = 1
    elif page > total_pages and total_pages > 0:
        page = total_pages
    
    # Get files for current page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    files = all_files[start_idx:end_idx]
    
    return {
        "files": files,
        "total": total_files,
        "page": page,
        "pages": total_pages,
        "per_page": per_page
    }

def get_file_info(filename: str) -> Optional[Dict]:
    """Get detailed information about a specific file."""
    upload_dir = Path(config["upload"]["directory"])
    file_path = upload_dir / filename
    
    if not file_path.exists() or not file_path.is_file():
        return None
    
    stats = file_path.stat()
    
    file_info = {
        "name": file_path.name,
        "path": str(file_path),
        "size": stats.st_size,
        "size_formatted": format_file_size(stats.st_size),
        "modified": datetime.fromtimestamp(stats.st_mtime),
        "modified_formatted": datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        "created": datetime.fromtimestamp(stats.st_ctime),
        "created_formatted": datetime.fromtimestamp(stats.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
        "type": get_file_type(file_path.name),
        "mime_type": get_mime_type(file_path.name),
        "icon": get_file_icon(file_path.name),
        "previewable": is_file_previewable(file_path.name)
    }
    
    return file_info

def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

def get_file_type(filename: str) -> str:
    """Get the general type of a file based on its extension."""
    _, ext = os.path.splitext(filename.lower())
    
    # Common file types
    image_types = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp']
    document_types = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.md', '.csv']
    archive_types = ['.zip', '.rar', '.tar', '.gz', '.7z']
    audio_types = ['.mp3', '.wav', '.ogg', '.flac', '.aac']
    video_types = ['.mp4', '.avi', '.mov', '.wmv', '.mkv', '.webm']
    
    if ext in image_types:
        return "image"
    elif ext in document_types:
        return "document"
    elif ext in archive_types:
        return "archive"
    elif ext in audio_types:
        return "audio"
    elif ext in video_types:
        return "video"
    else:
        return "other"

def get_mime_type(filename: str) -> str:
    """Get the MIME type of a file."""
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or "application/octet-stream"

def get_file_icon(filename: str) -> str:
    """Get an appropriate icon for a file based on its type."""
    file_type = get_file_type(filename)
    
    icons = {
        "image": "📷",
        "document": "📄",
        "archive": "🗜️",
        "audio": "🎵",
        "video": "🎬",
        "other": "📁"
    }
    
    return icons.get(file_type, "📁")

def is_file_previewable(filename: str) -> bool:
    """Check if a file can be previewed in the browser."""
    if not config["download"].get("enable_previews", True):
        return False
        
    file_type = get_file_type(filename)
    mime_type = get_mime_type(filename)
    
    # Check if it's an image
    if file_type == "image" and mime_type.startswith("image/"):
        return True
    
    # Check if it's text
    if mime_type.startswith("text/"):
        return True
    
    # Some PDFs can be previewed
    if mime_type == "application/pdf":
        return True
    
    return False