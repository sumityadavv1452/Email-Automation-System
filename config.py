"""
Configuration loader and validator for Email Automation System.

Loads environment settings from .env file via python-dotenv.
"""

import os
import sys
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

PLACEHOLDER_VALUES = {
    "your_email@gmail.com",
    "your_app_password",
    "your_16_digit_app_password",
    "your_sendgrid_api_key",
    "your_mailgun_api_key",
    "your_domain.com",
    "your_mailgun_domain.com",
}

@dataclass
class Config:
    """Application Configuration dataclass loading values from environment variables."""
    EMAIL_PROVIDER: str = os.getenv("EMAIL_PROVIDER", "smtp").lower()
    
    # SMTP Configuration
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587")) if os.getenv("SMTP_PORT", "587").isdigit() else 587
    SMTP_USER: str = os.getenv("SMTP_USER", "").strip()
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "").strip()
    
    # API Configuration
    API_PROVIDER: str = os.getenv("API_PROVIDER", "sendgrid").lower()
    SENDGRID_API_KEY: str = os.getenv("SENDGRID_API_KEY", "").strip()
    MAILGUN_API_KEY: str = os.getenv("MAILGUN_API_KEY", "").strip()
    MAILGUN_DOMAIN: str = os.getenv("MAILGUN_DOMAIN", "").strip()
    
    # Sender Details
    FROM_NAME: str = os.getenv("FROM_NAME", "Your Company").strip()
    FROM_EMAIL: str = os.getenv("FROM_EMAIL", os.getenv("SMTP_USER", "")).strip()
    
    # Retry and Throttle Settings
    RETRY_LIMIT: int = int(os.getenv("RETRY_LIMIT", "3")) if os.getenv("RETRY_LIMIT", "3").isdigit() else 3
    SEND_DELAY_SECONDS: float = float(os.getenv("SEND_DELAY_SECONDS", "0.5"))

    def validate(self, dry_run: bool = False) -> None:
        """
        Validate critical environment variables required for real email sending.
        During dry-run, environment credentials checks are bypassed.
        """
        if dry_run:
            return
            
        missing_vars = []

        if self.EMAIL_PROVIDER == "smtp":
            if not self.SMTP_USER or self.SMTP_USER in PLACEHOLDER_VALUES:
                missing_vars.append("SMTP_USER (set your email address in .env)")
            if not self.SMTP_PASSWORD or self.SMTP_PASSWORD in PLACEHOLDER_VALUES:
                missing_vars.append("SMTP_PASSWORD (set your Gmail App Password in .env)")
        elif self.EMAIL_PROVIDER == "api":
            if self.API_PROVIDER == "sendgrid":
                if not self.SENDGRID_API_KEY or self.SENDGRID_API_KEY in PLACEHOLDER_VALUES:
                    missing_vars.append("SENDGRID_API_KEY (set your SendGrid API key in .env)")
            elif self.API_PROVIDER == "mailgun":
                if not self.MAILGUN_API_KEY or self.MAILGUN_API_KEY in PLACEHOLDER_VALUES:
                    missing_vars.append("MAILGUN_API_KEY (set your Mailgun API key in .env)")
                if not self.MAILGUN_DOMAIN or self.MAILGUN_DOMAIN in PLACEHOLDER_VALUES:
                    missing_vars.append("MAILGUN_DOMAIN (set your Mailgun domain in .env)")
            else:
                missing_vars.append(f"API_PROVIDER '{self.API_PROVIDER}' is invalid (choose 'sendgrid' or 'mailgun')")
        else:
            missing_vars.append(f"EMAIL_PROVIDER '{self.EMAIL_PROVIDER}' is invalid (choose 'smtp' or 'api')")

        if missing_vars:
            print("\n" + "=" * 70)
            print("  CONFIGURATION ERROR: MISSING REQUIRED ENVIRONMENT VARIABLES")
            print("=" * 70)
            for var in missing_vars:
                print(f"  [X] Missing: {var}")
            print("\nPlease edit your .env file and set valid credentials before sending real emails.")
            print("Refer to .env.example for instructions on setting up Gmail App Passwords.")
            print("=" * 70 + "\n")
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Instantiate global config object
config = Config()
