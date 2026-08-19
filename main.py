"""
Main Entry Point for Email Automation System.

Provides CLI commands for:
  --now        Execute immediate bulk dispatches
  --dry-run    Preview HTML rendering without sending emails
  --test-send  Send a single test email
  --schedule   Schedule daily bulk dispatches at specified time
"""

import os
import re
import sys
import time
import argparse
from typing import Dict, Any, List
from tqdm import tqdm

from config import config
from src.logger import app_logger, log_email_delivery, print_run_summary, CSV_LOG_PATH
from src.data_loader import load_users
from src.email_builder import EmailBuilder
from src.email_sender import UnifiedEmailSender, SMTPAuthError
from src.retry_handler import execute_with_retry
from src.scheduler import schedule_daily_job

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Production Email Automation System - End-to-End Bulk Email Dispatcher."
    )
    parser.add_argument(
        "--now",
        action="store_true",
        help="Execute bulk email dispatch immediately to all contacts in CSV.",
    )
    parser.add_argument(
        "--test-send",
        type=str,
        metavar="RECIPIENT_EMAIL",
        help="Send exactly ONE test email using the first row of CSV data, overriding recipient to RECIPIENT_EMAIL.",
    )
    parser.add_argument(
        "--schedule",
        type=str,
        metavar="HH:MM",
        help="Schedule daily bulk dispatches at specified time in HH:MM format (e.g. 09:00).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview personalized emails, render HTML files to preview/ folder, and print template status table without sending emails.",
    )
    parser.add_argument(
        "--csv",
        type=str,
        default="data/users.csv",
        help="Custom path to CSV dataset file (default: data/users.csv).",
    )
    parser.add_argument(
        "--template",
        type=str,
        default="templates/email_template.html",
        help="Custom path to Jinja2 HTML email template (default: templates/email_template.html).",
    )
    parser.add_argument(
        "--subject",
        type=str,
        default="Order Update & Exclusive Offer for {{ name }}",
        help="Email subject template with optional Jinja placeholders (default: Order Update for {{ name }}).",
    )
    return parser.parse_args()

def sanitize_filename(name: str) -> str:
    """Sanitize string for safe filesystem filename."""
    clean = re.sub(r'[^a-zA-Z0-9_-]', '_', name.strip().lower())
    return re.sub(r'_+', '_', clean).strip('_')

def run_dry_run_mode(valid_users: List[Dict[str, Any]], invalid_users: List[Dict[str, Any]], builder: EmailBuilder, subject_template: str) -> None:
    """
    Execute Dry-Run Preview Mode:
    - Renders personalized HTML templates
    - Saves rendered HTML files into preview/ folder
    - Prints formatted console summary table (Name | Email | Template Status)
    - Zero network calls / zero email sends
    """
    preview_dir = os.path.abspath("preview")
    os.makedirs(preview_dir, exist_ok=True)

    print("\n" + "=" * 80)
    print("                      DRY-RUN PREVIEW & TEMPLATE STATUS                      ")
    print("=" * 80)
    header_line = f"{'NAME':<20} | {'EMAIL':<30} | {'TEMPLATE STATUS':<25}"
    print(header_line)
    print("-" * 80)

    for user in valid_users:
        user_name = user.get("name", "User")
        user_email = user.get("email", "unknown@example.com")

        is_ok, status_msg = builder.check_template_status(user)
        
        # Render HTML body
        try:
            html_content = builder.render(user)
            filename = f"{sanitize_filename(user_name)}.html"
            file_path = os.path.join(preview_dir, filename)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html_content)
        except Exception as e:
            is_ok = False
            status_msg = f"Render Error: {str(e)}"

        status_display = "OK" if is_ok else f"ERROR: {status_msg}"
        print(f"{user_name[:20]:<20} | {user_email[:30]:<30} | {status_display:<25}")

    for inv_user in invalid_users:
        user_name = inv_user.get("name", "User")
        user_email = inv_user.get("email", "invalid_email")
        print(f"{user_name[:20]:<20} | {user_email[:30]:<30} | {'SKIPPED (Invalid Email)':<25}")

    print("=" * 80)
    print(f"\n[+] Rendered HTML preview files saved to directory: {preview_dir}\n")

def run_test_send_mode(target_email: str, valid_users: List[Dict[str, Any]], builder: EmailBuilder, subject_template: str) -> None:
    """
    Execute Single Test-Send Mode:
    - Overrides recipient email address of first CSV row to target_email
    - Sends exactly one real email to test rendering and SMTP connection
    """
    if not valid_users:
        app_logger.error("No valid user records found in CSV dataset for test-send.")
        sys.exit(1)

    first_user = valid_users[0].copy()
    user_name = first_user.get("name", "Test User")
    first_user["email"] = target_email  # Override recipient email

    app_logger.info(f"Initiating single test-send to: {target_email} using data for '{user_name}'...")

    try:
        sender = UnifiedEmailSender()
        rendered_subject = builder.jinja_env.from_string(subject_template).render(**first_user)
        
        msg, html_body, plain_body = builder.build_message(
            user_data=first_user,
            subject=rendered_subject,
            from_name=config.FROM_NAME,
            from_email=config.FROM_EMAIL,
        )

        result = execute_with_retry(
            sender.send_email,
            msg,
            html_content=html_body,
            plain_text=plain_body,
            max_retries=config.RETRY_LIMIT,
            base_delay=2.0,
        )

        status = result.get("status", "FAILED")
        error_msg = result.get("error", "")

        log_email_delivery(user_name, target_email, status, error_msg)

        if result.get("success", False):
            print("\n" + "=" * 70)
            print("  TEST SEND SUCCESSFUL!")
            print("=" * 70)
            print(f"  Recipient : {target_email}")
            print(f"  Subject   : {rendered_subject}")
            print(f"  Backend   : {config.EMAIL_PROVIDER.upper()}")
            print(f"  Status    : {status}")
            print("=" * 70 + "\n")
        else:
            print("\n" + "=" * 70)
            print("  TEST SEND FAILED!")
            print("=" * 70)
            print(f"  Recipient : {target_email}")
            print(f"  Error     : {error_msg}")
            print("=" * 70 + "\n")

    except SMTPAuthError as auth_err:
        print("\n" + "=" * 70)
        print("  SMTP AUTHENTICATION ERROR")
        print("=" * 70)
        print(f"  {str(auth_err)}")
        print("  Stopping execution. Please check your credentials in .env")
        print("=" * 70 + "\n")
        sys.exit(1)
    except Exception as e:
        app_logger.error(f"Unexpected error during test send: {str(e)}")
        sys.exit(1)

def run_bulk_send_mode(valid_users: List[Dict[str, Any]], invalid_users: List[Dict[str, Any]], builder: EmailBuilder, subject_template: str) -> None:
    """
    Execute Bulk Send Mode (--now):
    - Loops through all valid recipients with tqdm progress bar
    - Sends real emails via configured provider with retry backoff
    - Stops immediately if SMTP authentication fails
    - Appends all results to logs/email_log.csv
    - Prints final summary and log file path
    """
    try:
        sender = UnifiedEmailSender()
    except Exception as e:
        app_logger.error(f"Failed to initialize sender backend: {str(e)}")
        sys.exit(1)

    stats: Dict[str, int] = {
        "total": len(valid_users) + len(invalid_users),
        "success": 0,
        "retried": 0,
        "failed": 0,
        "skipped": len(invalid_users),
    }

    # Log skipped invalid records in CSV log
    for inv_user in invalid_users:
        log_email_delivery(
            name=inv_user.get("name", "Unknown"),
            recipient_email=inv_user.get("email", "INVALID_EMAIL"),
            status="SKIPPED",
            error_message="Invalid email regex pattern",
        )

    print(f"\nProcessing {len(valid_users)} recipients via [{config.EMAIL_PROVIDER.upper()}]...\n")

    for user in tqdm(valid_users, desc="Bulk Email Sending", unit="email"):
        user_name = user.get("name", "User")
        recipient_email = user["email"]

        try:
            rendered_subject = builder.jinja_env.from_string(subject_template).render(**user)
            
            msg, html_body, plain_body = builder.build_message(
                user_data=user,
                subject=rendered_subject,
                from_name=config.FROM_NAME,
                from_email=config.FROM_EMAIL,
            )

            result = execute_with_retry(
                sender.send_email,
                msg,
                html_content=html_body,
                plain_text=plain_body,
                max_retries=config.RETRY_LIMIT,
                base_delay=2.0,
            )

            status = result.get("status", "FAILED")
            error_msg = result.get("error", "")

            if status == "SUCCESS":
                stats["success"] += 1
            elif status == "RETRIED_SUCCESS":
                stats["retried"] += 1
            else:
                stats["failed"] += 1

            log_email_delivery(user_name, recipient_email, status, error_msg)
            time.sleep(config.SEND_DELAY_SECONDS)

        except SMTPAuthError as auth_err:
            print("\n" + "=" * 70)
            print("  FATAL SMTP AUTHENTICATION FAILURE")
            print("=" * 70)
            print(f"  {str(auth_err)}")
            print("  Halting bulk dispatch to prevent repeated authentication rejections.")
            print("=" * 70 + "\n")
            log_email_delivery(user_name, recipient_email, "FAILED", str(auth_err))
            stats["failed"] += 1
            break

        except Exception as e:
            err_msg = f"Unexpected processing exception: {str(e)}"
            app_logger.error(f"Error processing recipient {recipient_email}: {err_msg}")
            stats["failed"] += 1
            log_email_delivery(user_name, recipient_email, "FAILED", err_msg)

    print_run_summary(stats)

def main():
    args = parse_args()

    # 1. Startup Environment Validation (bypassed for --dry-run)
    try:
        config.validate(dry_run=args.dry_run)
    except ValueError as e:
        sys.exit(1)

    # 2. Load and validate CSV recipients
    try:
        valid_users, invalid_users = load_users(args.csv)
    except Exception as e:
        app_logger.error(f"Fatal error reading CSV dataset: {str(e)}")
        sys.exit(1)

    # 3. Initialize Email Builder
    try:
        builder = EmailBuilder(args.template)
    except Exception as e:
        app_logger.error(f"Fatal error initializing email template builder: {str(e)}")
        sys.exit(1)

    # 4. Mode Execution Control
    if args.dry_run:
        run_dry_run_mode(valid_users, invalid_users, builder, args.subject)
    elif args.test_send:
        run_test_send_mode(args.test_send, valid_users, builder, args.subject)
    elif args.schedule:
        app_logger.info(f"Scheduling daily dispatches at {args.schedule}...")
        schedule_daily_job(
            lambda: run_bulk_send_mode(valid_users, invalid_users, builder, args.subject),
            args.schedule,
        )
    elif args.now:
        run_bulk_send_mode(valid_users, invalid_users, builder, args.subject)
    else:
        print("\n[!] No run mode specified. Use --dry-run, --test-send <EMAIL>, --now, or --schedule HH:MM.")
        print("    Running --dry-run by default...\n")
        run_dry_run_mode(valid_users, invalid_users, builder, args.subject)

if __name__ == "__main__":
    main()
