"""
Email Dispatcher module supporting SMTP, SendGrid API, and Mailgun API engines.
"""

import ssl
import smtplib
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
import requests

from config import config
from src.logger import app_logger

class SMTPAuthError(Exception):
    """Exception raised when SMTP authentication fails fatally."""
    pass

class SMTPSender:
    """SMTP Email Sender using smtplib + ssl."""

    def __init__(self, host: str, port: int, user: str, password: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password

    def send(self, msg: MIMEMultipart) -> Dict[str, Any]:
        """Send MIMEMultipart email message over SMTP with TLS/SSL."""
        recipient = msg["To"]
        context = ssl.create_default_context()

        try:
            if self.port == 465:
                # SSL Connection
                with smtplib.SMTP_SSL(self.host, self.port, context=context, timeout=15) as server:
                    server.login(self.user, self.password)
                    server.send_message(msg)
            else:
                # STARTTLS Connection (ports 587, 25, etc.)
                with smtplib.SMTP(self.host, self.port, timeout=15) as server:
                    server.ehlo()
                    server.starttls(context=context)
                    server.ehlo()
                    server.login(self.user, self.password)
                    server.send_message(msg)

            return {"success": True, "status": "SUCCESS", "error": ""}
        except smtplib.SMTPAuthenticationError as e:
            raw_err = e.smtp_error.decode('utf-8') if isinstance(e.smtp_error, bytes) else str(e)
            err_msg = f"Authentication failed — check your Gmail App Password in .env ({raw_err})"
            app_logger.error(f"SMTP Auth error for {recipient}: {err_msg}")
            # Raise SMTPAuthError so caller stops processing immediately instead of retrying endlessly
            raise SMTPAuthError(err_msg) from e
        except smtplib.SMTPException as e:
            err_msg = f"SMTP Protocol Error: {str(e)}"
            app_logger.error(f"SMTP error for {recipient}: {err_msg}")
            return {"success": False, "status": "FAILED", "error": err_msg}
        except Exception as e:
            err_msg = f"Network or Connection Error: {str(e)}"
            app_logger.error(f"Connection failure sending email to {recipient}: {err_msg}")
            return {"success": False, "status": "FAILED", "error": err_msg}

class SendGridSender:
    """Email API sender via SendGrid REST API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.sendgrid.com/v3/mail/send"

    def send(
        self,
        recipient_email: str,
        subject: str,
        from_name: str,
        from_email: str,
        html_content: str,
        plain_text: str
    ) -> Dict[str, Any]:
        """Send email using SendGrid v3 API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "personalizations": [
                {
                    "to": [{"email": recipient_email}],
                    "subject": subject,
                }
            ],
            "from": {"email": from_email, "name": from_name},
            "content": [
                {"type": "text/plain", "value": plain_text},
                {"type": "text/html", "value": html_content},
            ],
        }

        try:
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=15)
            if response.status_code in [200, 201, 202]:
                return {"success": True, "status": "SUCCESS", "error": ""}
            elif response.status_code in [401, 403]:
                err_msg = f"SendGrid API Authentication Failed — check your SENDGRID_API_KEY in .env [{response.status_code}]: {response.text}"
                app_logger.error(err_msg)
                raise SMTPAuthError(err_msg)
            else:
                err_msg = f"SendGrid API error [{response.status_code}]: {response.text}"
                app_logger.error(f"SendGrid error for {recipient_email}: {err_msg}")
                return {"success": False, "status": "FAILED", "error": err_msg}
        except SMTPAuthError:
            raise
        except Exception as e:
            err_msg = f"SendGrid Request Exception: {str(e)}"
            app_logger.error(err_msg)
            return {"success": False, "status": "FAILED", "error": err_msg}

class MailgunSender:
    """Email API sender via Mailgun REST API."""

    def __init__(self, api_key: str, domain: str):
        self.api_key = api_key
        self.domain = domain
        self.api_url = f"https://api.mailgun.net/v3/{domain}/messages"

    def send(
        self,
        recipient_email: str,
        subject: str,
        from_name: str,
        from_email: str,
        html_content: str,
        plain_text: str
    ) -> Dict[str, Any]:
        """Send email using Mailgun REST API."""
        auth = ("api", self.api_key)
        data = {
            "from": f"{from_name} <{from_email}>" if from_name else from_email,
            "to": recipient_email,
            "subject": subject,
            "text": plain_text,
            "html": html_content,
        }

        try:
            response = requests.post(self.api_url, auth=auth, data=data, timeout=15)
            if response.status_code == 200:
                return {"success": True, "status": "SUCCESS", "error": ""}
            elif response.status_code in [401, 403]:
                err_msg = f"Mailgun API Authentication Failed — check your MAILGUN_API_KEY in .env [{response.status_code}]: {response.text}"
                app_logger.error(err_msg)
                raise SMTPAuthError(err_msg)
            else:
                err_msg = f"Mailgun API error [{response.status_code}]: {response.text}"
                app_logger.error(f"Mailgun error for {recipient_email}: {err_msg}")
                return {"success": False, "status": "FAILED", "error": err_msg}
        except SMTPAuthError:
            raise
        except Exception as e:
            err_msg = f"Mailgun Request Exception: {str(e)}"
            app_logger.error(err_msg)
            return {"success": False, "status": "FAILED", "error": err_msg}

class UnifiedEmailSender:
    """Unified Email Sender choosing appropriate provider from configuration."""

    def __init__(self):
        self.provider = config.EMAIL_PROVIDER
        if self.provider == "smtp":
            self.smtp_sender = SMTPSender(
                host=config.SMTP_HOST,
                port=config.SMTP_PORT,
                user=config.SMTP_USER,
                password=config.SMTP_PASSWORD,
            )
        elif self.provider == "api":
            if config.API_PROVIDER == "sendgrid":
                self.api_sender = SendGridSender(api_key=config.SENDGRID_API_KEY)
            elif config.API_PROVIDER == "mailgun":
                self.api_sender = MailgunSender(api_key=config.MAILGUN_API_KEY, domain=config.MAILGUN_DOMAIN)
            else:
                raise ValueError(f"Unsupported API provider '{config.API_PROVIDER}'")
        else:
            raise ValueError(f"Unsupported EMAIL_PROVIDER '{self.provider}'")

    def send_email(
        self,
        msg: MIMEMultipart,
        html_content: str = "",
        plain_text: str = ""
    ) -> Dict[str, Any]:
        """Unified method to dispatch email via configured backend."""
        recipient = msg["To"]
        subject = msg["Subject"]

        if self.provider == "smtp":
            return self.smtp_sender.send(msg)
        elif self.provider == "api":
            return self.api_sender.send(
                recipient_email=recipient,
                subject=subject,
                from_name=config.FROM_NAME,
                from_email=config.FROM_EMAIL,
                html_content=html_content,
                plain_text=plain_text,
            )
        else:
            return {"success": False, "status": "FAILED", "error": f"Invalid provider {self.provider}"}
