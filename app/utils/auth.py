import bcrypt
import yaml
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, List

from fastapi import Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.security.utils import get_authorization_scheme_param

from app.utils.config import get_config
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)
security = HTTPBasic()
config = get_config()

# Valid roles
ROLES = ["admin", "writer", "reader"]

# Active sessions stored in memory
# In a production environment, consider using a database or Redis
active_sessions = {}

def load_users():
    """Load user data from configuration file."""
    try:
        with open(config["security"]["users_file"], "r") as f:
            data = yaml.safe_load(f)
        return data.get("users", [])
    except Exception as e:
        logger.error(f"Failed to load users: {str(e)}")
        return []

def get_user_by_username(username: str):
    """Get user data by username."""
    users = load_users()
    
    for user in users:
        if user["username"] == username:
            return user
    
    return None

def authenticate_user(username: str, password: str):
    """Verify username and password against stored hashes."""
    user = get_user_by_username(username)
    
    if user and user.get("enabled", True):
        stored_hash = user["password_hash"]
        
        # Check password
        if bcrypt.checkpw(password.encode(), stored_hash.encode()):
            logger.info(f"Successful authentication for user: {username}")
            return user
    
    if user:
        logger.warning(f"Failed authentication attempt for user: {username}")
    else:
        logger.warning(f"Authentication attempt with unknown username: {username}")
    
    return None

def create_session(user: dict) -> str:
    """Create a new session for a user and return the session ID."""
    session_id = str(uuid.uuid4())
    expire_minutes = config["security"]["session_expire_minutes"]
    
    session_data = {
        "username": user["username"],
        "role": user.get("role", "reader"),  # Make sure we're getting the correct role
        "created_at": datetime.now(),
        "expires_at": datetime.now() + timedelta(minutes=expire_minutes)
    }
    
    active_sessions[session_id] = session_data
    logger.info(f"Created session for user: {user['username']}, role: {session_data['role']}")
    
    return session_id

def validate_session(session_id: str) -> Optional[Dict]:
    """Validate a session ID and return session data if valid."""
    if not session_id or session_id not in active_sessions:
        return None
    
    session_data = active_sessions[session_id]
    
    # Check if session has expired
    if datetime.now() > session_data["expires_at"]:
        # Remove expired session
        del active_sessions[session_id]
        logger.info(f"Session expired for user: {session_data['username']}")
        return None
    
    return session_data

def end_session(session_id: str) -> bool:
    """End a user session by removing it from active sessions."""
    if session_id in active_sessions:
        username = active_sessions[session_id]["username"]
        del active_sessions[session_id]
        logger.info(f"Session ended for user: {username}")
        return True
    
    return False

def get_current_user_from_session(request: Request) -> Optional[Dict]:
    """Get the current user from the session cookie."""
    session_id = request.cookies.get("session_id")
    
    if not session_id:
        logger.debug("No session_id cookie found")
        return None
    
    session_data = validate_session(session_id)
    
    if not session_data:
        logger.debug(f"Invalid or expired session: {session_id}")
        return None
    
    # Valid session found
    logger.debug(f"Valid session found: {session_id} for user {session_data.get('username')}")
    return session_data

def get_current_user_basic_auth(credentials: HTTPBasicCredentials = Depends(security)) -> Dict:
    """Dependency to get the current authenticated user via HTTP Basic Auth."""
    user = authenticate_user(credentials.username, credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return user

async def get_current_user(request: Request):
    """
    Dependency to get the current authenticated user.
    Tries session cookies and redirects to login if unauthorized.
    """
    # Try session authentication
    user_data = get_current_user_from_session(request)
    if user_data:
        return user_data
    
    # No valid authentication found, redirect to login
    raise HTTPException(
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        headers={"Location": f"/?next={request.url.path}"},
        detail="Not authenticated"
    )

def set_session_cookie(response: Response, session_id: str):
    """Set the session cookie on the response."""
    secure = config["security"]["cookies"].get("secure", False)
    httponly = config["security"]["cookies"].get("httponly", True)
    samesite = config["security"]["cookies"].get("samesite", "lax")
    
    logger.info(f"Setting session cookie: {session_id} (secure: {secure}, httponly: {httponly})")
    
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=httponly,
        secure=secure,
        samesite=samesite,
        max_age=config["security"]["session_expire_minutes"] * 60
    )

def clear_session_cookie(response: Response):
    """Clear the session cookie."""
    response.delete_cookie(key="session_id")

def check_role_permission(required_roles: List[str], user_data: Dict) -> bool:
    """Check if a user has the required role."""
    user_role = user_data.get("role", "")
    return user_role in required_roles

def admin_required(user_data: Dict = Depends(get_current_user)):
    """Dependency to require admin role."""
    if not check_role_permission(["admin"], user_data):
        logger.warning(f"Access denied: User {user_data.get('username')} with role {user_data.get('role')} attempted to access admin area")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return user_data

def writer_required(user_data: Dict = Depends(get_current_user)):
    """Dependency to require admin or writer role."""
    if not check_role_permission(["admin", "writer"], user_data):
        logger.warning(f"Access denied: User {user_data.get('username')} with role {user_data.get('role')} attempted to access writer area")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Upload privileges required"
        )
    return user_data

def reader_required(user_data: Dict = Depends(get_current_user)):
    """Dependency to require admin or reader role."""
    if not check_role_permission(["admin", "reader"], user_data):
        logger.warning(f"Access denied: User {user_data.get('username')} with role {user_data.get('role')} attempted to access reader area")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Download privileges required"
        )
    return user_data

def generate_password_hash(password: str) -> str:
    """Generate a bcrypt hash for a password."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

async def get_api_user(request: Request, credentials: HTTPBasicCredentials = Depends(security)):
    """Dependency for API authentication using Basic Auth."""
    user = authenticate_user(credentials.username, credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return user