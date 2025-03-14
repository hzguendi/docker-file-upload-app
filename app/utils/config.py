import os
import yaml
from pathlib import Path

# Global config variable
_config = None


def get_config():
    """
    Get configuration from config file.
    Uses singleton pattern to avoid reloading on every call.
    """
    global _config
    
    if _config is None:
        config_path = os.environ.get("CONFIG_PATH", "config/config.yml")
        _config = load_config(config_path)
    
    return _config


def load_config(config_path):
    """Load configuration from YAML file."""
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        # Ensure required directories exist
        upload_dir = Path(config["upload"]["directory"])
        upload_dir.mkdir(exist_ok=True, parents=True)
        
        logs_dir = Path(os.path.dirname(config["logging"]["file"]))
        logs_dir.mkdir(exist_ok=True, parents=True)
        
        return config
    except Exception as e:
        # If we can't load config, use defaults
        print(f"Error loading config: {str(e)}")
        return {
            "server": {
                "host": "0.0.0.0",
                "port": 8000,
                "ssl": {
                    "enabled": False,
                    "port": 8443,
                    "cert_path": "config/ssl/cert.pem",
                    "key_path": "config/ssl/key.pem"
                }
            },
            "upload": {
                "max_size": 100,
                "directory": "uploads",
                "whitelist_extensions": [],
                "blacklist_extensions": [".exe", ".bat", ".sh", ".php"],
                "naming_format": "{timestamp}_{original}"
            },
            "logging": {
                "level": "INFO",
                "file": "logs/server.log",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "rotation": True,
                "max_size_mb": 10,
                "backup_count": 5
            },
            "security": {
                "secret_key": "insecure_default_key",
                "token_expire_minutes": 60,
                "passwords_file": "config/passwords.yml",
                "ip_whitelist_file": "config/ip_whitelist.yml"
            },
            "rate_limit": {
                "enabled": True,
                "max_uploads": 10,
                "window_minutes": 5
            }
        }
