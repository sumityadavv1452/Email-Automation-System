"""
Exponential backoff retry handler module for network calls and email sends.
"""

import time
from typing import Callable, Dict, Any
from src.logger import app_logger

def execute_with_retry(
    send_func: Callable[..., Dict[str, Any]],
    *args,
    max_retries: int = 3,
    base_delay: float = 2.0,
    **kwargs
) -> Dict[str, Any]:
    """
    Executes an email send operation with exponential backoff retries.

    Args:
        send_func: Callable function executing the email dispatch.
        max_retries: Maximum retry attempts (default 3).
        base_delay: Base delay in seconds for exponential backoff (2^attempt).

    Returns:
        Result dictionary containing 'success', 'status', and 'error' keys.
    """
    total_attempts = max_retries + 1
    last_error = ""

    for attempt in range(1, total_attempts + 1):
        result = send_func(*args, **kwargs)

        if result.get("success", False):
            if attempt > 1:
                result["status"] = "RETRIED_SUCCESS"
                app_logger.info(f"Send succeeded on retry attempt #{attempt - 1}")
            return result

        last_error = result.get("error", "Unknown send failure")

        if attempt < total_attempts:
            delay = base_delay * (2 ** (attempt - 1))
            app_logger.warning(
                f"Send attempt #{attempt} failed: {last_error}. Retrying in {delay:.1f}s..."
            )
            time.sleep(delay)
        else:
            app_logger.error(
                f"Permanent send failure after {max_retries} retries. Final error: {last_error}"
            )

    return {
        "success": False,
        "status": "FAILED",
        "error": f"Failed after {max_retries} retries: {last_error}",
    }
