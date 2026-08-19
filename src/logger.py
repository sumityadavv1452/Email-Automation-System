"""
Application logging and CSV delivery audit trail logger module.
"""

import os
import csv
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Dict, Any

# Ensure logs directory exists
LOGS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
os.makedirs(LOGS_DIR, exist_ok=True)

APP_LOG_PATH = os.path.join(LOGS_DIR, "app.log")
CSV_LOG_PATH = os.path.join(LOGS_DIR, "email_log.csv")

def setup_logger(name: str = "email_automation") -> logging.Logger:
    """Set up and return application logger with console and rotating file handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if logger.hasHandlers():
        return logger

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # Rotating File Handler (max 5MB, keep 3 backups)
    file_handler = RotatingFileHandler(
        APP_LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_format = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)

    return logger

app_logger = setup_logger()

def log_email_delivery(name: str, recipient_email: str, status: str, error_message: str = "") -> None:
    """
    Append an email send attempt result to logs/email_log.csv.
    CSV Schema: timestamp, name, recipient_email, status, error_message
    """
    file_exists = os.path.exists(CSV_LOG_PATH)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        with open(CSV_LOG_PATH, mode="a", newline="", encoding="utf-8") as csv_file:
            fieldnames = ["timestamp", "name", "recipient_email", "status", "error_message"]
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

            if not file_exists or os.path.getsize(CSV_LOG_PATH) == 0:
                writer.writeheader()

            writer.writerow({
                "timestamp": timestamp,
                "name": name,
                "recipient_email": recipient_email,
                "status": status,
                "error_message": error_message,
            })
    except Exception as e:
        app_logger.error(f"Failed to write to CSV log file: {str(e)}")

def print_run_summary(stats: Dict[str, int]) -> None:
    """Print clean summary statistics and log file path after email execution."""
    total = stats.get("total", 0)
    success = stats.get("success", 0)
    retried = stats.get("retried", 0)
    failed = stats.get("failed", 0)
    skipped = stats.get("skipped", 0)

    summary = f"""
==================================================
              DISPATCH RUN SUMMARY                
==================================================
 Total Processed  : {total}
 Successfully Sent: {success} (X sent)
 Retried & Sent   : {retried} (Z retried)
 Permanent Failed : {failed} (Y failed)
 Skipped (Invalid): {skipped}
--------------------------------------------------
 Audit Log File   : {CSV_LOG_PATH}
==================================================
"""
    app_logger.info(summary)
