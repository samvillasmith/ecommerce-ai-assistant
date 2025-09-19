# backend/services/price.py
from typing import Any, Optional

def format_price(value: Any, currency: str = "$") -> Optional[str]:
    """
    Permanent normalization for your current dataset:
    - DB stores integers like 3999, 5499, 10999 → interpret as cents → $39.99, $54.99, $109.99
    - If given floats/str digits, handle them too
    - Returns None if value is None/unparsable
    """
    if value is None:
        return None

    try:
        # handle numeric & numeric strings
        if isinstance(value, str):
            if value.strip().replace(".", "", 1).isdigit():
                value = float(value) if "." in value else int(value)
            else:
                return None

        # If value looks like whole cents (e.g., 5999), render as dollars.cents
        if isinstance(value, int):
            # treat ALL ints >= 100 as cents (fits your data)
            dollars = value / 100.0
            return f"{currency}{dollars:,.2f}"

        if isinstance(value, float):
            # assume already dollars — standardize to $X,XXX.XX
            return f"{currency}{value:,.2f}"

        return None
    except Exception:
        return None
