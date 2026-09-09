# platform_app/email_service.py

import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class BrevoEmailService:
    """Service for sending emails via Brevo API"""
    
    def __init__(self):
        self.api_key = settings.BREVO_API_KEY
        self.api_url = "https://api.brevo.com/v3/smtp/email"
        self.sender_email = settings.BREVO_SENDER_EMAIL
        self.sender_name = settings.BREVO_SENDER_NAME
    
    def send_email(self, to_email, to_name, subject, html_content):
        """
        Send email via Brevo API
        
        Args:
            to_email: Recipient email address
            to_name: Recipient name
            subject: Email subject
            html_content: HTML content of email
        
        Returns:
            dict: Response from Brevo API or error dict
        """
        headers = {
            'accept': 'application/json',
            'api-key': self.api_key,
            'content-type': 'application/json'
        }
        
        payload = {
            'sender': {
                'name': self.sender_name,
                'email': self.sender_email
            },
            'to': [
                {
                    'email': to_email,
                    'name': to_name
                }
            ],
            'subject': subject,
            'htmlContent': html_content
        }
        
        try:
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Email sent successfully to {to_email}")
            return {'success': True, 'message': 'Email sent successfully'}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def send_password_reset_email(self, user_email, user_name, reset_code):
        """
        Send password reset code email
        
        Args:
            user_email: User's email address
            user_name: User's name
            reset_code: 6-digit reset code
        
        Returns:
            dict: Response from send_email method
        """
        subject = "Password Reset Code - Mirrorwavetrades"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Password Reset</title>
        </head>
        <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #0f172a;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #1e293b; padding: 40px 20px;">
                <!-- Header -->
                <div style="text-align: center; margin-bottom: 40px;">
                    <h1 style="color: #06b6d4; margin: 0; font-size: 32px;">
                        Mirrorwavetrades
                    </h1>
                    <p style="color: #94a3b8; margin-top: 10px;">
                        Cryptocurrency Trading Platform
                    </p>
                </div>
                
                <!-- Main Content -->
                <div style="background: linear-gradient(135deg, #1e3a8a 0%, #0c4a6e 100%); 
                            border-radius: 15px; padding: 30px; text-align: center;">
                    <div style="margin-bottom: 20px;">
                        <svg width="80" height="80" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <circle cx="12" cy="12" r="10" stroke="#06b6d4" stroke-width="2"/>
                            <path d="M12 8V12L14 14" stroke="#06b6d4" stroke-width="2" stroke-linecap="round"/>
                        </svg>
                    </div>
                    
                    <h2 style="color: #ffffff; margin: 0 0 15px 0; font-size: 28px;">
                        Password Reset Request
                    </h2>
                    
                    <p style="color: #cbd5e1; font-size: 16px; line-height: 1.6; margin-bottom: 30px;">
                        Hello <strong>{user_name}</strong>,<br><br>
                        We received a request to reset your password. Use the code below to reset your password:
                    </p>
                    
                    <!-- Reset Code -->
                    <div style="background-color: rgba(6, 182, 212, 0.1); 
                                border: 2px solid #06b6d4; 
                                border-radius: 10px; 
                                padding: 25px; 
                                margin: 30px 0;">
                        <p style="color: #94a3b8; margin: 0 0 10px 0; font-size: 14px;">
                            Your Reset Code
                        </p>
                        <h1 style="color: #06b6d4; 
                                   margin: 0; 
                                   font-size: 48px; 
                                   letter-spacing: 8px; 
                                   font-weight: bold;">
                            {reset_code}
                        </h1>
                    </div>
                    
                    <p style="color: #cbd5e1; font-size: 14px; margin-top: 25px;">
                        ⏰ This code will expire in <strong style="color: #06b6d4;">15 minutes</strong>
                    </p>
                </div>
                
                <!-- Security Notice -->
                <div style="background-color: #334155; 
                            border-left: 4px solid #ef4444; 
                            padding: 20px; 
                            margin-top: 30px; 
                            border-radius: 5px;">
                    <p style="color: #f87171; margin: 0 0 10px 0; font-weight: bold; font-size: 16px;">
                        🔒 Security Notice
                    </p>
                    <p style="color: #cbd5e1; margin: 0; font-size: 14px; line-height: 1.6;">
                        If you didn't request this password reset, please ignore this email. 
                        Your account is secure and no changes will be made.
                    </p>
                </div>
                
                <!-- Footer -->
                <div style="text-align: center; margin-top: 40px; padding-top: 30px; border-top: 1px solid #334155;">
                    <p style="color: #64748b; font-size: 14px; margin: 0 0 10px 0;">
                        Need help? Contact our support team
                    </p>
                    <p style="color: #64748b; font-size: 12px; margin: 0;">
                        © 2024 Mirrorwavetrades. All rights reserved.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(user_email, user_name, subject, html_content)


# Convenience function for easy import
def send_password_reset_code(user_email, user_name, reset_code):
    """
    Convenience function to send password reset email
    
    Usage:
        from platform_app.email_service import send_password_reset_code
        send_password_reset_code('user@example.com', 'John Doe', '123456')
    """
    email_service = BrevoEmailService()
    return email_service.send_password_reset_email(user_email, user_name, reset_code)