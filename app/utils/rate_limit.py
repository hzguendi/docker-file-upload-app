import time
from collections import defaultdict
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """
    Simple in-memory rate limiter.
    Tracks upload counts per IP address within a time window.
    """
    
    def __init__(self, max_uploads=10, window_minutes=5):
        self.max_uploads = max_uploads
        self.window_seconds = window_minutes * 60
        self.upload_history = defaultdict(list)
        logger.info(f"Rate limiter initialized: {max_uploads} uploads per {window_minutes} minutes")
        
    def is_allowed(self, ip_address):
        """
        Check if an IP address is allowed to upload.
        Returns True if allowed, False if rate limit exceeded.
        """
        current_time = time.time()
        
        # Clean up old entries
        self._cleanup(ip_address, current_time)
        
        # Check if rate limit is exceeded
        if len(self.upload_history[ip_address]) >= self.max_uploads:
            logger.warning(f"Rate limit exceeded for IP {ip_address}: {len(self.upload_history[ip_address])} uploads in window")
            return False
            
        # Add new upload timestamp
        self.upload_history[ip_address].append(current_time)
        return True
        
    def _cleanup(self, ip_address, current_time):
        """Remove upload history entries older than the time window."""
        if ip_address not in self.upload_history:
            return
            
        cutoff_time = current_time - self.window_seconds
        self.upload_history[ip_address] = [
            t for t in self.upload_history[ip_address] if t >= cutoff_time
        ]
        
        # Remove empty entries to save memory
        if not self.upload_history[ip_address]:
            del self.upload_history[ip_address]
            
    def get_remaining(self, ip_address):
        """Get remaining upload count for an IP address."""
        current_time = time.time()
        self._cleanup(ip_address, current_time)
        return max(0, self.max_uploads - len(self.upload_history[ip_address]))

    def get_reset_time(self, ip_address):
        """Get seconds until next upload slot becomes available."""
        if ip_address not in self.upload_history or not self.upload_history[ip_address]:
            return 0
            
        current_time = time.time()
        oldest_timestamp = min(self.upload_history[ip_address])
        return max(0, oldest_timestamp + self.window_seconds - current_time)
