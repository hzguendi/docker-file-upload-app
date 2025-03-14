import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import uvicorn
from fastapi import FastAPI, File, UploadFile, Request, HTTPException, Depends, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import shutil
import requests

from app.utils.config import get_config
from app.utils.auth import authenticate_user, get_current_user
from app.utils.logging_utils import setup_logger
from app.utils.file_utils import is_file_allowed, get_file_path
from app.utils.ip_utils import is_ip_allowed, get_ip_info
from app.utils.rate_limit import RateLimiter

# Initialize FastAPI
app = FastAPI(title="Docker File Upload App")

# Load configuration
config = get_config()

# Setup logging
logger = setup_logger()

# Initialize rate limiter
rate_limiter = RateLimiter(
    max_uploads=config["rate_limit"]["max_uploads"],
    window_minutes=config["rate_limit"]["window_minutes"]
)

# Create upload directory if it doesn't exist
upload_dir = Path(config["upload"]["directory"])
upload_dir.mkdir(exist_ok=True, parents=True)

# Create logs directory if it doesn't exist
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True, parents=True)

# Set up templates
templates = Jinja2Templates(directory="app/templates")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

security = HTTPBasic()


@app.get("/", response_class=HTMLResponse)
async def get_upload_page(request: Request):
    """Render the upload page."""
    client_ip = request.client.host
    
    # Check if IP is allowed
    if not is_ip_allowed(client_ip):
        logger.warning(f"Access denied from IP: {client_ip}")
        return templates.TemplateResponse(
            "error.html", 
            {"request": request, "error": "Your IP address is not allowed to access this service."}
        )
    
    # Get disk usage information
    total, used, free = shutil.disk_usage(upload_dir)
    disk_info = {
        "total": f"{total // (2**30)} GB",
        "used": f"{used // (2**30)} GB",
        "free": f"{free // (2**30)} GB",
        "percent_used": round((used / total) * 100, 2)
    }
    
    # Get IP info
    ip_info = get_ip_info(client_ip)
    
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request, 
            "max_size": config["upload"]["max_size"],
            "client_ip": client_ip,
            "ip_info": ip_info,
            "disk_info": disk_info,
            "blacklist": config["upload"]["blacklist_extensions"],
            "whitelist": config["upload"]["whitelist_extensions"],
        }
    )


@app.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    user: str = Depends(get_current_user)
):
    """Handle file uploads from the web interface."""
    client_ip = request.client.host
    
    # Check if IP is allowed
    if not is_ip_allowed(client_ip):
        logger.warning(f"Upload denied from IP: {client_ip}")
        raise HTTPException(status_code=403, detail="Your IP is not allowed to upload files")
    
    # Check rate limit
    if config["rate_limit"]["enabled"] and not rate_limiter.is_allowed(client_ip):
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    
    # Process the file
    return await process_upload(file, client_ip, user)


@app.post("/api/upload")
async def api_upload_file(
    request: Request,
    file: UploadFile = File(...),
    user: str = Depends(get_current_user)
):
    """API endpoint for programmatic uploads."""
    client_ip = request.client.host
    
    # Check if IP is allowed
    if not is_ip_allowed(client_ip):
        logger.warning(f"API upload denied from IP: {client_ip}")
        raise HTTPException(status_code=403, detail="Your IP is not allowed to upload files")
    
    # Check rate limit
    if config["rate_limit"]["enabled"] and not rate_limiter.is_allowed(client_ip):
        logger.warning(f"API rate limit exceeded for IP: {client_ip}")
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    
    # Process the file
    result = await process_upload(file, client_ip, user)
    
    # Return JSON response for API
    return {
        "success": True,
        "filename": result["filename"],
        "size": result["size"],
        "path": result["path"]
    }


async def process_upload(file: UploadFile, client_ip: str, user: str):
    """Process and save an uploaded file."""
    # Check file extension
    if not is_file_allowed(file.filename):
        logger.warning(f"Rejected file with blocked extension: {file.filename} from IP: {client_ip}")
        raise HTTPException(status_code=400, detail="File type not allowed")
    
    # Check file size
    file_size_mb = 0
    content = await file.read()
    file_size_mb = len(content) / (1024 * 1024)
    
    if file_size_mb > config["upload"]["max_size"]:
        logger.warning(f"Rejected file exceeding size limit: {file.filename} ({file_size_mb}MB) from IP: {client_ip}")
        raise HTTPException(status_code=400, detail=f"File size exceeds the maximum allowed size of {config['upload']['max_size']}MB")
    
    # Create file path using the configured naming format
    file_path = get_file_path(file.filename, user)
    
    # Write file
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Log the upload
    logger.info(f"File uploaded successfully: {file_path} ({file_size_mb:.2f}MB) by user '{user}' from IP: {client_ip}")
    
    return {
        "filename": os.path.basename(file_path),
        "size": f"{file_size_mb:.2f}MB",
        "path": str(file_path)
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    # Run the app
    if config["server"]["ssl"]["enabled"]:
        # Start with SSL
        uvicorn.run(
            "app.main:app",
            host=config["server"]["host"],
            port=config["server"]["ssl"]["port"],
            ssl_keyfile=config["server"]["ssl"]["key_path"],
            ssl_certfile=config["server"]["ssl"]["cert_path"]
        )
    else:
        # Start without SSL
        uvicorn.run(
            "app.main:app",
            host=config["server"]["host"],
            port=config["server"]["port"]
        )
