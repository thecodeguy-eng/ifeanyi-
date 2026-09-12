# platform_app/email_service.py

import requests
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

# Fallback used only if a caller doesn't pass an absolute logo URL built from
# the current request (register() does; anything calling this off-request
# falls back to the known production host).
DEFAULT_LOGO_URL = "https://mirrorwavetrades.vercel.app/static/platform_app/img/logo-512.png"

BRAND = {
    'bg': '#05070a',
    'card': '#0d1117',
    'card_alt': '#111827',
    'border': '#1f2937',
    'accent': '#38bdf8',
    'primary': '#2563eb',
    'text_main': '#f3f4f6',
    'text_muted': '#9aa3b2',
    'text_faint': '#64748b',
    'danger': '#ef4444',
    'success': '#22c55e',
}


def _email_shell(preheader, body_html, logo_url=None):
    """
    Shared HTML wrapper for every transactional email.

    Declares color-scheme as dark-only so Gmail/Outlook/Apple Mail's
    automatic dark-mode re-coloring doesn't fight our own dark palette
    and mangle it - without this meta tag, clients that auto-darken mail
    can invert or wash out custom dark backgrounds unpredictably.
    """
    logo_url = logo_url or DEFAULT_LOGO_URL
    b = BRAND

    return f"""
    <!DOCTYPE html>
    <html lang="en" style="background-color:{b['bg']};">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="color-scheme" content="dark">
        <meta name="supported-color-schemes" content="dark">
        <title>Mirrorwavetrades</title>
        <!--[if mso]>
        <style>table, td {{ font-family: Arial, sans-serif; }}</style>
        <![endif]-->
    </head>
    <body style="margin:0; padding:0; background-color:{b['bg']}; -webkit-text-size-adjust:100%;">
        <div style="display:none; max-height:0; overflow:hidden; opacity:0; font-size:1px; line-height:1px; color:{b['bg']};">
            {preheader}
        </div>

        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:{b['bg']};">
            <tr>
                <td align="center" style="padding: 32px 16px;">
                    <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px; width:100%; background-color:{b['card']}; border-radius:16px; overflow:hidden; border:1px solid {b['border']};">

                        <!-- Header -->
                        <tr>
                            <td align="center" style="padding: 32px 24px 24px 24px; border-bottom:1px solid {b['border']};">
                                <img src="{logo_url}" width="44" height="44" alt="Mirrorwavetrades"
                                     style="display:block; border-radius:10px; margin:0 auto 12px auto;">
                                <span style="font-family: Arial, Helvetica, sans-serif; font-size:18px; font-weight:bold; color:{b['text_main']};">
                                    Mirrorwavetrades
                                </span>
                            </td>
                        </tr>

                        <!-- Body -->
                        <tr>
                            <td style="padding: 32px 28px; font-family: Arial, Helvetica, sans-serif;">
                                {body_html}
                            </td>
                        </tr>

                        <!-- Footer -->
                        <tr>
                            <td style="padding: 22px 28px; border-top:1px solid {b['border']}; font-family: Arial, Helvetica, sans-serif;" align="center">
                                <p style="color:{b['text_faint']}; font-size:12px; margin:0 0 6px 0;">
                                    Need help? Our support team is available 24/7 via live chat on the platform.
                                </p>
                                <p style="color:{b['text_faint']}; font-size:11px; margin:0;">
                                    &copy; {timezone.now().year} Mirrorwavetrades. All rights reserved.
                                </p>
                            </td>
                        </tr>

                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """


def _button(label, url, brand):
    return f"""
    <table role="presentation" cellpadding="0" cellspacing="0" style="margin: 26px auto 4px auto;">
        <tr>
            <td align="center" bgcolor="{brand['primary']}" style="border-radius:8px;">
                <a href="{url}" target="_blank"
                   style="display:inline-block; padding:14px 32px; font-family: Arial, Helvetica, sans-serif;
                          font-size:15px; font-weight:bold; color:#ffffff; text-decoration:none;">
                    {label}
                </a>
            </td>
        </tr>
    </table>
    """


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

    def send_password_reset_email(self, user_email, user_name, reset_code, logo_url=None):
        """Send password reset code email"""
        b = BRAND
        subject = "Password Reset Code - Mirrorwavetrades"

        body_html = f"""
            <h2 style="color:{b['text_main']}; margin:0 0 14px 0; font-size:22px; text-align:center;">
                Password Reset Request
            </h2>
            <p style="color:{b['text_muted']}; font-size:15px; line-height:1.6; margin:0 0 24px 0; text-align:center;">
                Hello <strong style="color:{b['text_main']};">{user_name}</strong>,
                we received a request to reset your password. Use the code below - it expires in
                <strong style="color:{b['accent']};">15 minutes</strong>.
            </p>

            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin: 0 0 24px 0;">
                <tr>
                    <td align="center" bgcolor="{b['card_alt']}" style="border-radius:10px; padding:24px; border:1px solid {b['border']};">
                        <p style="color:{b['text_muted']}; font-size:12px; margin:0 0 8px 0; letter-spacing:.05em; text-transform:uppercase;">
                            Your reset code
                        </p>
                        <p style="color:{b['accent']}; font-size:40px; font-weight:bold; letter-spacing:8px; margin:0;">
                            {reset_code}
                        </p>
                    </td>
                </tr>
            </table>

            <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                <tr>
                    <td bgcolor="#2a1416" style="border-left:3px solid {b['danger']}; border-radius:6px; padding:16px 18px;">
                        <p style="color:#fca5a5; margin:0; font-size:13px; line-height:1.5;">
                            <strong>Didn't request this?</strong> Ignore this email - your account is safe
                            and no changes will be made.
                        </p>
                    </td>
                </tr>
            </table>
        """

        return self.send_email(user_email, user_name, subject, _email_shell("Your password reset code", body_html, logo_url))

    def send_welcome_email(self, user_email, user_name, dashboard_url=None, logo_url=None):
        """Send a welcome email right after a new account is created."""
        b = BRAND
        subject = "Welcome to Mirrorwavetrades"
        dashboard_url = dashboard_url or "https://mirrorwavetrades.vercel.app/dashboard/"

        steps = [
            ("1", "Complete your profile", "Confirm your details so we can personalize your dashboard."),
            ("2", "Fund your account", "Make your first deposit to unlock live trading and copy trading."),
            ("3", "Explore the markets", "Check live rates and pick an investment plan that fits your goals."),
        ]
        steps_html = "".join(f"""
            <tr>
                <td bgcolor="{b['card_alt']}" style="border-radius:10px; padding:16px 18px; border-left:3px solid {b['accent']};">
                    <p style="color:{b['text_main']}; margin:0; font-size:14px; font-weight:bold;">{num}. {title}</p>
                    <p style="color:{b['text_muted']}; margin:4px 0 0 0; font-size:13px; line-height:1.4;">{desc}</p>
                </td>
            </tr>
            <tr><td style="height:10px; line-height:10px; font-size:0;">&nbsp;</td></tr>
        """ for num, title, desc in steps)

        body_html = f"""
            <h2 style="color:{b['text_main']}; margin:0 0 14px 0; font-size:22px; text-align:center;">
                Welcome aboard, {user_name}!
            </h2>
            <p style="color:{b['text_muted']}; font-size:15px; line-height:1.6; margin:0 0 26px 0; text-align:center;">
                Your Mirrorwavetrades account is ready. You now have access to live markets,
                copy trading, AI trading bots, and 24/7 global market access.
            </p>

            <p style="color:{b['text_main']}; font-size:14px; font-weight:bold; margin:0 0 12px 0;">
                Get started in 3 steps
            </p>
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                {steps_html}
            </table>

            <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                <tr><td align="center">{_button("Go to My Dashboard", dashboard_url, b)}</td></tr>
            </table>
        """

        return self.send_email(user_email, user_name, subject, _email_shell(f"Welcome to Mirrorwavetrades, {user_name}", body_html, logo_url))

    def send_deposit_reminder_email(self, user_email, user_name, deposit_url=None, logo_url=None):
        """Friendly nudge to make a first deposit, sent shortly after signup."""
        b = BRAND
        subject = "Fund your account to start trading - Mirrorwavetrades"
        deposit_url = deposit_url or "https://mirrorwavetrades.vercel.app/deposit/"

        body_html = f"""
            <h2 style="color:{b['text_main']}; margin:0 0 14px 0; font-size:22px; text-align:center;">
                Hi {user_name}, ready to make your first move?
            </h2>
            <p style="color:{b['text_muted']}; font-size:15px; line-height:1.6; margin:0 0 8px 0; text-align:center;">
                Your account is set up, but it's still waiting for its first deposit.
                Fund your account now to unlock live trading, copy trading, and our AI bots.
            </p>
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                <tr><td align="center">{_button("Make a Deposit", deposit_url, b)}</td></tr>
            </table>
        """

        return self.send_email(user_email, user_name, subject, _email_shell("Fund your account to unlock live trading", body_html, logo_url))

    def send_admin_new_registration_email(self, username, email, account_id, country, registered_at, admin_url=None, logo_url=None):
        """Notify the admin inbox whenever a new account is created."""
        b = BRAND
        if not self.admin_email:
            logger.warning("ADMIN_NOTIFICATION_EMAIL is not set - skipping admin registration notice")
            return {'success': False, 'error': 'ADMIN_NOTIFICATION_EMAIL not configured'}

        subject = f"New registration: {username} - Mirrorwavetrades"

        def row(label, value, bold=False):
            weight = 'bold' if bold else 'normal'
            return f"""
            <tr>
                <td style="padding:10px 0; border-bottom:1px solid {b['border']}; color:{b['text_muted']}; font-size:13px; width:130px;">{label}</td>
                <td style="padding:10px 0; border-bottom:1px solid {b['border']}; color:{b['text_main']}; font-size:14px; font-weight:{weight};">{value}</td>
            </tr>
            """

        rows_html = (
            row("Username", username, bold=True)
            + row("Email", email)
            + row("Account ID", f"#{account_id}")
            + row("Country", country or "Unknown")
            + row("Registered at", registered_at)
        )

        cta_html = ""
        if admin_url:
            cta_html = f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                <tr><td align="center">{_button("View User in Admin", admin_url, b)}</td></tr>
            </table>"""

        body_html = f"""
            <p style="color:{b['accent']}; font-size:12px; text-transform:uppercase; letter-spacing:.05em; margin:0 0 8px 0; text-align:center;">
                Admin Notification
            </p>
            <h2 style="color:{b['text_main']}; margin:0 0 22px 0; font-size:20px; text-align:center;">
                New user registered
            </h2>
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:8px;">
                {rows_html}
            </table>
            {cta_html}
        """

        return self.send_email(self.admin_email, 'Admin', subject, _email_shell(f"New registration: {username}", body_html, logo_url))


# Convenience functions for easy import
def send_password_reset_code(user_email, user_name, reset_code, logo_url=None):
    """
    Convenience function to send password reset email

    Usage:
        from platform_app.email_service import send_password_reset_code
        send_password_reset_code('user@example.com', 'John Doe', '123456')
    """
    email_service = BrevoEmailService()
    return email_service.send_password_reset_email(user_email, user_name, reset_code, logo_url)


def send_welcome_email(user_email, user_name, dashboard_url=None, logo_url=None):
    """Convenience function to send the post-registration welcome email."""
    email_service = BrevoEmailService()
    return email_service.send_welcome_email(user_email, user_name, dashboard_url, logo_url)


def send_deposit_reminder(user_email, user_name, deposit_url=None, logo_url=None):
    """Convenience function to send the deposit-reminder email."""
    email_service = BrevoEmailService()
    return email_service.send_deposit_reminder_email(user_email, user_name, deposit_url, logo_url)


def send_admin_new_registration_email(username, email, account_id, country, registered_at, admin_url=None, logo_url=None):
    """Convenience function to notify the admin inbox of a new registration."""
    email_service = BrevoEmailService()
    return email_service.send_admin_new_registration_email(
        username, email, account_id, country, registered_at, admin_url, logo_url
    )
