# platform_app/email_service.py

import requests
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class BrevoEmailService:
    """Service for sending emails via Brevo API"""
    
    def __init__(self):
        self.api_key = settings.BREVO_API_KEY
        self.api_url = "https://api.brevo.com/v3/smtp/email"
        self.sender_email = settings.BREVO_SENDER_EMAIL
        self.sender_name = settings.BREVO_SENDER_NAME
        self.admin_email = getattr(settings, 'ADMIN_NOTIFICATION_EMAIL', '')
    
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

    def send_welcome_email(self, user_email, user_name):
        """Send a welcome email right after a new account is created."""
        subject = "Welcome to Mirrorwavetrades 🎉"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Welcome to Mirrorwavetrades</title>
        </head>
        <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #05070a;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #0d1117; padding: 40px 20px;">
                <!-- Header -->
                <div style="text-align: center; margin-bottom: 40px;">
                    <h1 style="color: #38bdf8; margin: 0; font-size: 32px;">
                        Mirrorwavetrades
                    </h1>
                    <p style="color: #9aa3b8; margin-top: 10px;">
                        Stocks · Crypto · Forex · Options
                    </p>
                </div>

                <!-- Main Content -->
                <div style="background: linear-gradient(135deg, #0b2a4a 0%, #0c4a6e 100%);
                            border-radius: 15px; padding: 35px; text-align: center;">
                    <div style="margin-bottom: 20px;">
                        <svg width="72" height="72" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M4 17L9 12L13 16L20 8" stroke="#38bdf8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            <path d="M14 8H20V14" stroke="#38bdf8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </div>

                    <h2 style="color: #ffffff; margin: 0 0 15px 0; font-size: 26px;">
                        Welcome aboard, {user_name}!
                    </h2>

                    <p style="color: #cbd5e1; font-size: 16px; line-height: 1.6; margin: 0 0 10px 0;">
                        Your Mirrorwavetrades account is ready. You now have access to live markets,
                        copy trading, AI trading bots, and 24/7 global market access.
                    </p>
                </div>

                <!-- Next steps -->
                <div style="margin-top: 30px;">
                    <h3 style="color: #ffffff; font-size: 16px; margin: 0 0 15px 0;">Get started in 3 steps</h3>

                    <div style="display: block; background-color: #111827; border-radius: 10px; padding: 16px 20px; margin-bottom: 12px; border-left: 3px solid #38bdf8;">
                        <p style="color: #f3f4f6; margin: 0; font-size: 14px; font-weight: bold;">1. Complete your profile</p>
                        <p style="color: #9aa3b8; margin: 4px 0 0 0; font-size: 13px;">Confirm your details so we can personalize your dashboard.</p>
                    </div>

                    <div style="display: block; background-color: #111827; border-radius: 10px; padding: 16px 20px; margin-bottom: 12px; border-left: 3px solid #38bdf8;">
                        <p style="color: #f3f4f6; margin: 0; font-size: 14px; font-weight: bold;">2. Fund your account</p>
                        <p style="color: #9aa3b8; margin: 4px 0 0 0; font-size: 13px;">Make your first deposit to unlock live trading and copy trading.</p>
                    </div>

                    <div style="display: block; background-color: #111827; border-radius: 10px; padding: 16px 20px; border-left: 3px solid #38bdf8;">
                        <p style="color: #f3f4f6; margin: 0; font-size: 14px; font-weight: bold;">3. Explore the markets</p>
                        <p style="color: #9aa3b8; margin: 4px 0 0 0; font-size: 13px;">Check live rates and pick an investment plan that fits your goals.</p>
                    </div>
                </div>

                <!-- CTA -->
                <div style="text-align: center; margin-top: 35px;">
                    <a href="https://mirrorwavetrades.com/dashboard/"
                       style="display: inline-block; background-color: #2563eb; color: #ffffff;
                              text-decoration: none; padding: 14px 32px; border-radius: 8px;
                              font-size: 15px; font-weight: bold;">
                        Go to My Dashboard
                    </a>
                </div>

                <!-- Footer -->
                <div style="text-align: center; margin-top: 40px; padding-top: 30px; border-top: 1px solid #1f2937;">
                    <p style="color: #64748b; font-size: 14px; margin: 0 0 10px 0;">
                        Questions? Our support team is available 24/7 via live chat on the platform.
                    </p>
                    <p style="color: #64748b; font-size: 12px; margin: 0;">
                        © {timezone.now().year} Mirrorwavetrades. All rights reserved.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        return self.send_email(user_email, user_name, subject, html_content)

    def send_deposit_reminder_email(self, user_email, user_name):
        """Friendly nudge to make a first deposit, sent shortly after signup."""
        subject = "Fund your account to start trading - Mirrorwavetrades"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Fund Your Account</title>
        </head>
        <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #05070a;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #0d1117; padding: 40px 20px;">
                <div style="text-align: center; margin-bottom: 40px;">
                    <h1 style="color: #38bdf8; margin: 0; font-size: 32px;">Mirrorwavetrades</h1>
                </div>

                <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
                            border-radius: 15px; padding: 35px; text-align: center;">
                    <h2 style="color: #ffffff; margin: 0 0 15px 0; font-size: 24px;">
                        Hi {user_name}, ready to make your first move?
                    </h2>
                    <p style="color: #cbd5e1; font-size: 15px; line-height: 1.6; margin: 0 0 25px 0;">
                        Your account is set up, but it's still waiting for its first deposit.
                        Fund your account now to unlock live trading, copy trading, and our AI bots.
                    </p>
                    <a href="https://mirrorwavetrades.com/deposit/"
                       style="display: inline-block; background-color: #2563eb; color: #ffffff;
                              text-decoration: none; padding: 14px 32px; border-radius: 8px;
                              font-size: 15px; font-weight: bold;">
                        Make a Deposit
                    </a>
                </div>

                <div style="text-align: center; margin-top: 40px; padding-top: 30px; border-top: 1px solid #1f2937;">
                    <p style="color: #64748b; font-size: 12px; margin: 0;">
                        © {timezone.now().year} Mirrorwavetrades. All rights reserved.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        return self.send_email(user_email, user_name, subject, html_content)

    def send_admin_new_registration_email(self, username, email, account_id, country, registered_at, admin_url=None):
        """Notify the admin inbox whenever a new account is created."""
        if not self.admin_email:
            logger.warning("ADMIN_NOTIFICATION_EMAIL is not set - skipping admin registration notice")
            return {'success': False, 'error': 'ADMIN_NOTIFICATION_EMAIL not configured'}

        subject = f"New registration: {username} - Mirrorwavetrades"

        rows = f"""
            <tr><td style="padding:8px 0;color:#9aa3b8;font-size:14px;width:140px;">Username</td><td style="padding:8px 0;color:#f3f4f6;font-size:14px;font-weight:bold;">{username}</td></tr>
            <tr><td style="padding:8px 0;color:#9aa3b8;font-size:14px;">Email</td><td style="padding:8px 0;color:#f3f4f6;font-size:14px;">{email}</td></tr>
            <tr><td style="padding:8px 0;color:#9aa3b8;font-size:14px;">Account ID</td><td style="padding:8px 0;color:#f3f4f6;font-size:14px;">#{account_id}</td></tr>
            <tr><td style="padding:8px 0;color:#9aa3b8;font-size:14px;">Country</td><td style="padding:8px 0;color:#f3f4f6;font-size:14px;">{country or 'Unknown'}</td></tr>
            <tr><td style="padding:8px 0;color:#9aa3b8;font-size:14px;">Registered at</td><td style="padding:8px 0;color:#f3f4f6;font-size:14px;">{registered_at}</td></tr>
        """

        cta = f"""
                    <div style="text-align: center; margin-top: 25px;">
                        <a href="{admin_url}"
                           style="display: inline-block; background-color: #2563eb; color: #ffffff;
                                  text-decoration: none; padding: 12px 28px; border-radius: 8px;
                                  font-size: 14px; font-weight: bold;">
                            View User in Admin
                        </a>
                    </div>
        """ if admin_url else ""

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>New Registration</title>
        </head>
        <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #05070a;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #0d1117; padding: 40px 20px;">
                <div style="text-align: center; margin-bottom: 30px;">
                    <h1 style="color: #38bdf8; margin: 0; font-size: 26px;">Mirrorwavetrades</h1>
                    <p style="color: #9aa3b8; margin-top: 8px; font-size: 13px;">Admin Notification</p>
                </div>

                <div style="background-color: #111827; border-radius: 12px; padding: 28px;">
                    <h2 style="color: #ffffff; margin: 0 0 20px 0; font-size: 20px;">
                        🆕 New user registered
                    </h2>
                    <table style="width: 100%; border-collapse: collapse;">
                        {rows}
                    </table>
                    {cta}
                </div>

                <div style="text-align: center; margin-top: 30px;">
                    <p style="color: #64748b; font-size: 12px; margin: 0;">
                        Automated notification · Mirrorwavetrades Admin
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        return self.send_email(self.admin_email, 'Admin', subject, html_content)


# Convenience functions for easy import
def send_password_reset_code(user_email, user_name, reset_code):
    """
    Convenience function to send password reset email

    Usage:
        from platform_app.email_service import send_password_reset_code
        send_password_reset_code('user@example.com', 'John Doe', '123456')
    """
    email_service = BrevoEmailService()
    return email_service.send_password_reset_email(user_email, user_name, reset_code)


def send_welcome_email(user_email, user_name):
    """Convenience function to send the post-registration welcome email."""
    email_service = BrevoEmailService()
    return email_service.send_welcome_email(user_email, user_name)


def send_deposit_reminder(user_email, user_name):
    """Convenience function to send the deposit-reminder email."""
    email_service = BrevoEmailService()
    return email_service.send_deposit_reminder_email(user_email, user_name)


def send_admin_new_registration_email(username, email, account_id, country, registered_at, admin_url=None):
    """Convenience function to notify the admin inbox of a new registration."""
    email_service = BrevoEmailService()
    return email_service.send_admin_new_registration_email(
        username, email, account_id, country, registered_at, admin_url
    )