import re


def normalize_phone(phone: str | None) -> str | None:
    """Return a stable digit-only phone number for matching across channels."""
    if not phone:
        return None
    digits = re.sub(r"\D+", "", str(phone))
    return digits or None
