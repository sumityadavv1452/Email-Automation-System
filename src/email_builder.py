"""
Jinja2 Email Template Builder and MIME Message Constructor module.
"""

import os
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, Any, List, Optional, Tuple
from jinja2 import Environment, FileSystemLoader, TemplateNotFound, meta
from src.logger import app_logger

class EmailBuilder:
    """Renders personalized HTML emails from Jinja2 templates and constructs MIME messages."""

    def __init__(self, template_path: str = "templates/email_template.html"):
        self.template_path = os.path.abspath(template_path)
        if not os.path.exists(self.template_path):
            raise FileNotFoundError(f"Email template file not found: {self.template_path}")

        template_dir = os.path.dirname(self.template_path)
        template_file = os.path.basename(self.template_path)

        self.jinja_env = Environment(loader=FileSystemLoader(template_dir))
        try:
            self.template = self.jinja_env.get_template(template_file)
        except TemplateNotFound:
            raise FileNotFoundError(f"Could not load template file '{template_file}' from '{template_dir}'")

    def check_template_status(self, user_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Analyze Jinja2 template AST and verify if all required placeholders exist in user data.
        
        Returns:
            Tuple of (is_ok: bool, status_message: str)
        """
        try:
            template_file = os.path.basename(self.template_path)
            source, _, _ = self.jinja_env.loader.get_source(self.jinja_env, template_file)
            parsed_content = self.jinja_env.parse(source)
            undeclared_vars = meta.find_undeclared_variables(parsed_content)
            
            missing_vars = [v for v in undeclared_vars if v not in user_data or str(user_data[v]).strip() == ""]
            if missing_vars:
                return False, f"Missing variable(s): {', '.join(sorted(missing_vars))}"
            return True, "OK"
        except Exception as e:
            return False, f"Template Parse Error: {str(e)}"

    def render(self, user_data: Dict[str, Any]) -> str:
        """Render HTML content by substituting user data variables into Jinja2 template."""
        try:
            return self.template.render(**user_data)
        except Exception as e:
            app_logger.error(f"Error rendering Jinja2 template for recipient {user_data.get('email')}: {str(e)}")
            raise

    @staticmethod
    def generate_plain_text(html_content: str) -> str:
        """Generate plain text version fallback from HTML content by stripping HTML tags."""
        text = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', html_content)
        text = re.sub(r'<script[^>]*>[\s\S]*?</script>', '', text)
        text = re.sub(r'<br\s*/?>', '\n', text)
        text = re.sub(r'</p>', '\n\n', text)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\n\s*\n', '\n\n', text).strip()
        return text

    def build_message(
        self,
        user_data: Dict[str, Any],
        subject: str,
        from_name: str,
        from_email: str,
        attachment_paths: Optional[List[str]] = None
    ) -> Tuple[MIMEMultipart, str, str]:
        """
        Construct a complete MIME multipart email message.
        
        Returns:
            Tuple of (MIMEMultipart email_msg, html_body, plain_text_body)
        """
        html_body = self.render(user_data)
        plain_body = self.generate_plain_text(html_body)
        recipient_email = user_data["email"]

        msg = MIMEMultipart("mixed")
        msg["From"] = f"{from_name} <{from_email}>" if from_name else from_email
        msg["To"] = recipient_email
        msg["Subject"] = subject

        # Create alternative subpart for text & html
        msg_alternative = MIMEMultipart("alternative")
        msg_alternative.attach(MIMEText(plain_body, "plain", "utf-8"))
        msg_alternative.attach(MIMEText(html_body, "html", "utf-8"))
        msg.attach(msg_alternative)

        # Handle attachment paths
        all_attachments = []
        if attachment_paths:
            all_attachments.extend(attachment_paths)
        if "attachment_path" in user_data and user_data["attachment_path"]:
            all_attachments.append(user_data["attachment_path"])

        for attach_path in all_attachments:
            attach_path = attach_path.strip()
            if not attach_path:
                continue
            if not os.path.exists(attach_path):
                app_logger.warning(f"Attachment file not found: '{attach_path}'. Skipping attachment.")
                continue

            try:
                with open(attach_path, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                filename = os.path.basename(attach_path)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename=\"{filename}\"",
                )
                msg.attach(part)
                app_logger.info(f"Attached file '{filename}' to email for {recipient_email}")
            except Exception as e:
                app_logger.error(f"Failed to attach file '{attach_path}': {str(e)}")

        return msg, html_body, plain_body
