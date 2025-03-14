import yaml
import re
import requests
from app.utils.config import get_config
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)
config = get_config()


def load_ip_whitelist():
    """Load IP whitelist from configuration file."""
    try:
        with open(config["security"]["ip_whitelist_file"], "r") as f:
            data = yaml.safe_load(f)
        return data
    except Exception as e:
        logger.error(f"Failed to load IP whitelist: {str(e)}")
        return {"enabled": False, "whitelist": []}


def is_ip_allowed(ip_address):
    """
    Check if an IP address is allowed based on the whitelist.
    If whitelist is disabled, all IPs are allowed.
    """
    whitelist_config = load_ip_whitelist()
    
    # If whitelist is not enabled, all IPs are allowed
    if not whitelist_config["enabled"]:
        return True
    
    # Check if IP is in whitelist
    for allowed_ip in whitelist_config["whitelist"]:
        # If it's an exact match
        if allowed_ip == ip_address:
            return True
        
        # If it's a wildcard pattern
        if "*" in allowed_ip:
            pattern = allowed_ip.replace(".", "\\.").replace("*", ".*")
            if re.match(f"^{pattern}$", ip_address):
                return True
    
    # IP not found in whitelist
    logger.warning(f"IP address not in whitelist: {ip_address}")
    return False


def get_ip_info(ip_address):
    """
    Get information about an IP address using ipinfo.io.
    Returns a dict with information or None on failure.
    """
    # Don't try to look up local addresses
    if ip_address in ["localhost", "127.0.0.1", "::1"]:
        return {
            "ip": ip_address,
            "hostname": "localhost",
            "city": "Local",
            "region": "Local",
            "country": "Local",
            "loc": "",
            "org": "Local Network"
        }
    
    try:
        response = requests.get(f"https://ipinfo.io/{ip_address}/json", timeout=3)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.error(f"Failed to get IP info for {ip_address}: {str(e)}")
    
    # Return minimal info if lookup fails
    return {"ip": ip_address}
