"""
Small generic helpers used across routes.
"""

from datetime import datetime

from app.extensions import db
from app.models import Booking


def generate_booking_number(prefix="AXIS-GH"):
    """
    Generate a booking number such as AXIS-GH-2026-0001.

    The running sequence resets implicitly per year because we count how
    many bookings already exist for the current year and add 1. This is
    simple and sufficient for an internal company tool; for very high
    concurrency a DB sequence table would be preferable.
    """
    year = datetime.utcnow().year
    year_prefix = f"{prefix}-{year}-"
    count = Booking.query.filter(Booking.booking_number.like(f"{year_prefix}%")).count()
    next_number = count + 1
    return f"{year_prefix}{next_number:04d}"
