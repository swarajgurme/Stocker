"""
ML Utilities - Validation
Input validation for ML pipelines
"""

import logging
from datetime import datetime, timedelta
from typing import Tuple

logger = logging.getLogger(__name__)

VALID_STORES = {"S001", "S002", "S003", "S004", "S005"}
VALID_PRODUCTS = {
    "Air Filter", "Alternator", "Battery", "Brake Pad", "Coolant",
    "Disc Rotor", "Engine Oil", "Fans", "Fuse", "LED",
    "Radiator", "Rearview Mirror", "Resistors", "Sensor",
    "Sideview Mirror", "Spark Plugs", "Thermostat", "Water Pump",
    "Windshield", "Wires"
}


def validate_input(
    store_id: str,
    product_name: str,
    start_date_str: str,
    end_date_str: str,
    horizon_days: int = 365
) -> Tuple[bool, str]:
    """
    Validate all forecast input parameters (legacy name for test compatibility)

    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    # Store validation
    if not store_id or store_id not in VALID_STORES:
        return False, f"Invalid Store ID: {store_id}. Valid options: {sorted(VALID_STORES)}"

    # Product validation
    if not product_name or product_name not in VALID_PRODUCTS:
        return False, f"Invalid Product Name: {product_name}. Valid options: {sorted(VALID_PRODUCTS)}"

    # Date format validation
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        return False, "Invalid date format. Use YYYY-MM-DD (e.g., 2024-01-01)"

    # Date range validation
    if start_date > end_date:
        return False, "Start date must be before end date"

    max_range = 730  # Max 2 years
    if (end_date - start_date).days > max_range:
        return False, f"Date range cannot exceed {max_range} days (2 years)"

    # Horizon validation (if provided)
    if horizon_days is not None:
        if horizon_days < 1 or horizon_days > 365:
            return False, "Horizon must be between 1 and 365 days"

    return True, ""
