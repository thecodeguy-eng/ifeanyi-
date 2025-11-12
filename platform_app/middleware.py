# platform_app/middleware.py

from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from .models import UserActivity
import logging

logger = logging.getLogger(__name__)


class UserActivityMiddleware(MiddlewareMixin):
    """Middleware to track all user activities and page visits"""
    
    def process_response(self, request, response):
        """Track activity after response is generated"""
        # Skip tracking for static files, media, and specific paths
        excluded_paths = [
            '/static/', '/media/', '/favicon.ico', 
            '/custom-admin/activities/',  # Don't track activities page itself
            '/api/',  # Skip API calls
        ]
        
        # Skip if any excluded path matches
        if any(request.path.startswith(path) for path in excluded_paths):
            return response
        
        # Skip if not a GET request (avoid tracking POST, DELETE, etc.)
        if request.method != 'GET':
            return response
            
        # Skip AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return response
        
        try:
            # Get user info
            user = request.user if request.user.is_authenticated else None
            
            # Get IP address
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0].strip()
            else:
                ip_address = request.META.get('REMOTE_ADDR', '')
            
            # Get user agent
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            # Get or create session key
            if not request.session.session_key:
                request.session.create()
            session_id = request.session.session_key
            
            # Determine action type based on path
            action_type = 'PAGE_VIEW'
            page_path = request.path.lower()
            
            if 'login' in page_path:
                action_type = 'LOGIN'
            elif 'logout' in page_path:
                action_type = 'LOGOUT'
            elif 'deposit' in page_path:
                action_type = 'DEPOSIT_PAGE'
            elif 'withdrawal' in page_path:
                action_type = 'WITHDRAWAL_PAGE'
            elif 'trading' in page_path:
                action_type = 'TRADING_PAGE'
            elif 'dashboard' in page_path:
                action_type = 'DASHBOARD'
            elif 'portfolio' in page_path:
                action_type = 'PORTFOLIO'
            elif 'transactions' in page_path:
                action_type = 'TRANSACTIONS'
            
            # Get page title from path
            page_title = request.path.strip('/').replace('-', ' ').replace('_', ' ').title()
            if not page_title:
                page_title = 'Home'
            elif page_title.startswith('Custom Admin'):
                page_title = page_title.replace('Custom Admin', 'Admin')
            
            # Create activity record
            UserActivity.objects.create(
                user=user,
                session_id=session_id,
                ip_address=ip_address[:45],  # Limit IP address length
                user_agent=user_agent[:500],  # Limit user agent length
                page_url=request.path[:500],  # Limit URL length
                page_title=page_title[:200],  # Limit title length
                action_type=action_type
            )
            
            logger.info(f"Activity tracked: {user.username if user else 'Anonymous'} - {page_title}")
            
        except Exception as e:
            # Log error but don't break the request
            logger.error(f"Error tracking user activity: {e}")
        
        return response