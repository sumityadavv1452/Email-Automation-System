"""
CSV Data Loader and Email Regex Validation module.
"""

import os
import re
from typing import List, Dict, Any, Tuple
import pandas as pd
from src.logger import app_logger

# Standard RFC 5322 pattern simplified for email regex validation
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

def validate_email(email: str) -> bool:
    """Validate email address string against regex."""
    if not isinstance(email, str):
        return False
    return bool(EMAIL_REGEX.match(email.strip()))

def load_users(csv_path: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Read user dataset from CSV using pandas.
    
    Validates required columns ('name', 'email') and validates email format.
    
    Returns:
        Tuple containing:
            - valid_users: List of user dicts for valid emails
            - invalid_users: List of user dicts skipped due to validation failure
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found at path: {csv_path}")

    app_logger.info(f"Loading user data from CSV: {csv_path}")
    try:
        # Read CSV, keeping missing values as empty strings
        df = pd.read_csv(csv_path, dtype=str).fillna("")
    except Exception as e:
        app_logger.error(f"Error reading CSV file '{csv_path}': {str(e)}")
        raise

    # Normalize column names by trimming spaces and converting to lowercase
    df.columns = [col.strip() for col in df.columns]

    # Required columns check
    required_cols = {"name", "email"}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        raise ValueError(f"CSV file '{csv_path}' is missing required columns: {missing_cols}")

    valid_users: List[Dict[str, Any]] = []
    invalid_users: List[Dict[str, Any]] = []

    for index, row in df.iterrows():
        user_dict = {col: str(row[col]).strip() for col in df.columns}
        user_email = user_dict.get("email", "")
        
        if validate_email(user_email):
            valid_users.append(user_dict)
        else:
            app_logger.warning(
                f"Skipping row {index + 2}: Invalid email format '{user_email}' for user '{user_dict.get('name')}'"
            )
            invalid_users.append(user_dict)

    app_logger.info(
        f"Data loaded successfully. Valid users: {len(valid_users)}, Skipped invalid rows: {len(invalid_users)}"
    )
    return valid_users, invalid_users

def get_users(csv_path: str = "data/users.csv") -> List[Dict[str, Any]]:
    """Helper convenience function returning valid users."""
    valid_users, _ = load_users(csv_path)
    return valid_users
