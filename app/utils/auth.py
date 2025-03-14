import bcrypt
import yaml
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.utils.config import get_config
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)
security = HTTPBasic()
config = get_config()


def load_passwords():
    """Load password hashes from configuration file."""
    try:
        with open(config["security"]["passwords_file"], "r") as f:
            data = yaml.safe_load(f)
        return data.get("users", [])
    except Exception as e:
        logger.error(f"Failed to load passwords: {str(e)}")
        return []


def authenticate_user(username: str, password: str):
    """Verify username and password against stored hashes."""
    users = load_passwords()
    
    for user in users:
        if user["username"] == username:
            stored_hash = user["password_hash"]
            
            # Check password
            if bcrypt.checkpw(password.encode(), stored_hash.encode()):
                logger.info(f"Successful authentication for user: {username}")
                return True
            else:
                logger.warning(f"Failed authentication attempt for user: {username}")
                return False
    
    logger.warning(f"Authentication attempt with unknown username: {username}")
    return False


def get_current_user(credentials: HTTPBasicCredentials = Depends(security)):
    """Dependency to get the current authenticated user."""
    is_authenticated = authenticate_user(credentials.username, credentials.password)
    
    if not is_authenticated:
        logger.warning(f"Unauthorized access attempt with username: {credentials.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return credentials.username
