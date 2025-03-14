import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict

import uvicorn
from fastapi import FastAPI, File, UploadFile, Request, Response, HTTPException, Depends, BackgroundTasks, Form, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import shutil
import requests

from app.utils.config import get_config
from app.utils.auth import (
    authenticate_user, get_current_user, create_session, set_session_cookie, 
    clear_session_cookie, writer_required, reader_required, admin_required,
    get_current_user_from_session, get_api_user
)
from app.utils.logging_utils import setup_logger
from app.utils.file_utils import is_file_allowed, get_file_path
from app.utils.download_utils import get_file_list, get_file_info
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

# Create required directories
upload_dir = Path(config["upload"]["directory"])
upload_dir.mkdir(exist_ok=True, parents=True)

logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True, parents=True)

# Set up templates
templates = Jinja2Templates(directory="app/templates")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Security setup
security = HTTPBasic()

# Middleware setup
@app.middleware("http")
async def check_ip_middleware(request: Request, call_next):
    """Middleware to check IP address restrictions."""
    client_ip = request.client.host
    
    # Skip IP check for the error page
    if request.url.path == "/error":
        return await call_next(request)
    
    # Check if IP is allowed
    if not is_ip_allowed(client_ip):
        logger.warning(f"Access denied from IP: {client_ip}")
        return RedirectResponse(
            url="/error?message=Your%20IP%20address%20is%20not%20allowed%20to%20access%20this%20service.",
            status_code=303
        )
    
    return await call_next(request)

# Helper function for common template context
def get_base_context(request: Request, user_data: Optional[Dict] = None):
    """Get base context data for all templates."""
    client_ip = request.client.host
    
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
    
    context = {
        "request": request,
        "user": user_data,
        "max_size": config["upload"]["max_size"],
        "client_ip": client_ip,
        "ip_info": ip_info,
        "disk_info": disk_info,
        "blacklist": config["upload"]["blacklist_extensions"],
        "whitelist": config["upload"]["whitelist_extensions"],
        "app_version": "2.0.0"
    }
    
    return context

# Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with login form or redirect to dashboard."""
    user_data = get_current_user_from_session(request)
    
    # If user is already logged in, redirect to dashboard
    if user_data:
        return RedirectResponse(url="/dashboard", status_code=303)
    
    # Show login page
    context = get_base_context(request)
    context["title"] = "Login"
    
    return templates.TemplateResponse("login.html", context)
    
@app.post("/login")
async def login(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/dashboard")
):
    """Handle login form submission."""
    user = authenticate_user(username, password)
    
    if not user:
        # Authentication failed
        context = get_base_context(request)
        context["title"] = "Login"
        context["error"] = "Invalid username or password"
        return templates.TemplateResponse("login.html", context)
    
    # Create session
    session_id = create_session(user)
    
    # Debug logging
    logger.info(f"Created session {session_id} for user {username}, role: {user.get('role', 'unknown')}")
    
    # Set cookie on the response
    set_session_cookie(response, session_id)
    
    # Create redirect response
    redirect = RedirectResponse(url=next if next.startswith("/") else "/dashboard", status_code=303)
    
    # Also set cookie on the redirect response
    set_session_cookie(redirect, session_id)
    
    return redirect

@app.get("/logout")
async def logout(request: Request, response: Response):
    """Log out the current user."""
    session_id = request.cookies.get("session_id")
    
    if session_id:
        # End the session
        from app.utils.auth import end_session
        end_session(session_id)
    
    # Clear session cookie
    clear_session_cookie(response)
    
    # Redirect to login page
    return RedirectResponse(url="/", status_code=303)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user_data: Dict = Depends(get_current_user)):
    """User dashboard page."""
    context = get_base_context(request, user_data)
    context["title"] = "Dashboard"

    from datetime import datetime
    context["now"] = datetime.now()
    
    return templates.TemplateResponse("dashboard.html", context)

@app.get("/upload", response_class=HTMLResponse)
async def get_upload_page(request: Request, user_data: Dict = Depends(writer_required)):
    """Render the upload page."""
    context = get_base_context(request, user_data)
    context["title"] = "Upload Files"
    
    return templates.TemplateResponse("upload.html", context)

@app.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    user_data: Dict = Depends(writer_required)
):
    """Handle file uploads from the web interface."""
    client_ip = request.client.host
    
    # Check rate limit
    if config["rate_limit"]["enabled"] and not rate_limiter.is_allowed(client_ip):
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    
    # Process the file
    result = await process_upload(file, client_ip, user_data.get("username", "unknown"))
    
    return result

@app.get("/download", response_class=HTMLResponse)
async def download_page(
    request: Request, 
    user_data: Dict = Depends(reader_required),
    page: int = Query(1, ge=1),
    per_page: Optional[int] = Query(None)
):
    """File download page with file listing."""
    # Get file list
    file_list = get_file_list(page, per_page)
    
    context = get_base_context(request, user_data)
    context["title"] = "Download Files"
    context["files"] = file_list["files"]
    context["pagination"] = {
        "page": file_list["page"],
        "pages": file_list["pages"],
        "total": file_list["total"],
        "per_page": file_list["per_page"]
    }
    
    return templates.TemplateResponse("download.html", context)

@app.get("/files/{filename}")
async def download_file(
    filename: str,
    request: Request,
    user_data: Dict = Depends(reader_required)
):
    """Download a specific file."""
    file_path = Path(config["upload"]["directory"]) / filename
    
    # Check if file exists
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Log the download
    logger.info(f"File downloaded: {filename} by user '{user_data.get('username')}' from IP: {request.client.host}")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=None  # Let the server guess the content type
    )

@app.get("/preview/{filename}")
async def preview_file(
    filename: str,
    request: Request,
    user_data: Dict = Depends(reader_required)
):
    """Preview a file if it's previewable."""
    file_info = get_file_info(filename)
    
    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")
    
    if not file_info["previewable"]:
        raise HTTPException(status_code=400, detail="This file type cannot be previewed")
    
    context = get_base_context(request, user_data)
    context["title"] = f"Preview: {filename}"
    context["file"] = file_info
    
    # Add text content for text files
    if file_info["mime_type"] and file_info["mime_type"].startswith("text/"):
        try:
            # Check file size before attempting to read
            max_size_kb = config["download"].get("text_preview_max_size_kb", 1024)
            if file_info["size"] > max_size_kb * 1024:
                context["text_content"] = f"File too large to preview. Maximum size is {max_size_kb} KB."
                context["truncated"] = True
            else:
                file_path = Path(config["upload"]["directory"]) / filename
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    max_lines = config["download"].get("text_preview_max_lines", 500)
                    lines = []
                    for i, line in enumerate(f):
                        if i >= max_lines:
                            context["truncated"] = True
                            break
                        lines.append(line)
                    context["text_content"] = "".join(lines)
                    if context.get("truncated"):
                        context["text_content"] += f"\n\n[...File truncated, showing first {max_lines} lines...]"
        except Exception as e:
            logger.error(f"Error reading text file for preview: {e}")
            context["text_content"] = f"Error previewing file: {str(e)}"
    
    return templates.TemplateResponse("preview.html", context)

@app.post("/api/upload")
async def api_upload_file(
    request: Request,
    file: UploadFile = File(...),
    user_data: Dict = Depends(get_api_user)  # Use the API-specific auth function
):
    """API endpoint for programmatic uploads."""
    client_ip = request.client.host
    
    # Check rate limit
    if config["rate_limit"]["enabled"] and not rate_limiter.is_allowed(client_ip):
        logger.warning(f"API rate limit exceeded for IP: {client_ip}")
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    
    # Process the file
    result = await process_upload(file, client_ip, user_data.get("username", "unknown"))
    
    # Return JSON response for API
    return {
        "success": True,
        "filename": result["filename"],
        "size": result["size"],
        "path": result["path"]
    }

@app.get("/error")
async def error_page(request: Request, message: str = "An error occurred"):
    """Error page for displaying errors."""
    context = {
        "request": request,
        "error": message,
        "title": "Error"
    }
    return templates.TemplateResponse("error.html", context)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "2.0.0"}

async def process_upload(file: UploadFile, client_ip: str, username: str):
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
    file_path = get_file_path(file.filename, username)
    
    # Write file
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Log the upload
    logger.info(f"File uploaded successfully: {file_path} ({file_size_mb:.2f}MB) by user '{username}' from IP: {client_ip}")
    
    return {
        "filename": os.path.basename(file_path),
        "size": f"{file_size_mb:.2f}MB",
        "path": str(file_path)
    }

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

@app.middleware("http")
async def check_authentication_middleware(request: Request, call_next):
    """Middleware to check if user is authenticated."""
    # Skip authentication for login, error, static and health check pages
    public_paths = ["/", "/login", "/error", "/static", "/health"]
    if any(request.url.path.startswith(path) for path in public_paths):
        return await call_next(request)
    
    # Check if user is authenticated
    user_data = get_current_user_from_session(request)
    if not user_data:
        return RedirectResponse(
            url=f"/?next={request.url.path}", 
            status_code=303
        )
    
    return await call_next(request)

@app.delete("/files/{filename}")
async def delete_file(
    filename: str,
    request: Request,
    user_data: Dict = Depends(admin_required)
):
    """Delete a specific file (admin only)."""
    file_path = Path(config["upload"]["directory"]) / filename
    
    # Check if file exists
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Delete the file
    try:
        os.remove(file_path)
        logger.info(f"File deleted: {filename} by user '{user_data.get('username')}' from IP: {request.client.host}")
        return {"success": True, "message": f"File {filename} deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting file {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")