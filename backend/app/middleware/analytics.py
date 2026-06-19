"""
Analytics middleware for automatic event tracking
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging

logger = logging.getLogger(__name__)

class AnalyticsMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically track API usage and performance"""
    
    async def dispatch(self, request: Request, call_next):
        # Start timing
        start_time = time.time()
        
        # Get user info if available
        user_id = None
        if hasattr(request.state, 'user'):
            user_id = request.state.user.id
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        process_time = time.time() - start_time
        
        # Track API usage analytics
        try:
            if hasattr(request.app.state, 'analytics'):
                await request.app.state.analytics.track_event(
                    event_name="api_request",
                    properties={
                        "method": request.method,
                        "path": str(request.url.path),
                        "status_code": response.status_code,
                        "response_time": round(process_time * 1000, 2),  # milliseconds
                        "user_agent": request.headers.get("user-agent"),
                        "ip_address": request.client.host if request.client else None,
                        "query_params": dict(request.query_params) if request.query_params else None
                    },
                    user_id=user_id,
                    request=request
                )
        except Exception as e:
            logger.warning(f"Analytics tracking failed: {e}")
        
        # Add response time header
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
