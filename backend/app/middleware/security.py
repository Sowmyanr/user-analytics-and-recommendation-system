"""
Security middleware for request validation and protection
"""

from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging
from typing import Dict, Set

logger = logging.getLogger(__name__)

class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware for basic security measures"""
    
    def __init__(self, app, rate_limit_requests: int = 100, rate_limit_window: int = 60):
        super().__init__(app)
        self.rate_limit_requests = rate_limit_requests
        self.rate_limit_window = rate_limit_window
        self.rate_limit_storage: Dict[str, list] = {}
        
        # Common security headers
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    
    def check_rate_limit(self, client_ip: str) -> bool:
        """Simple rate limiting based on IP address"""
        current_time = time.time()
        
        # Clean old entries
        if client_ip in self.rate_limit_storage:
            self.rate_limit_storage[client_ip] = [
                timestamp for timestamp in self.rate_limit_storage[client_ip]
                if current_time - timestamp < self.rate_limit_window
            ]
        else:
            self.rate_limit_storage[client_ip] = []
        
        # Check current request count
        if len(self.rate_limit_storage[client_ip]) >= self.rate_limit_requests:
            return False
        
        # Add current request
        self.rate_limit_storage[client_ip].append(current_time)
        return True
    
    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Skip rate limiting for health checks and static files
        skip_paths = {"/health", "/api/docs", "/api/redoc", "/api/openapi.json"}
        if request.url.path in skip_paths:
            response = await call_next(request)
        else:
            # Check rate limit
            if not self.check_rate_limit(client_ip):
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests"
                )
            
            # Process request
            response = await call_next(request)
        
        # Add security headers
        for header_name, header_value in self.security_headers.items():
            response.headers[header_name] = header_value
        
        return response
