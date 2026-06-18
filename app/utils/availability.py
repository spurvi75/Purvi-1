"""
Core room availability and allocation logic.

This module implements the rules described in the specification:

1. Only bookings with status in BookingStatus.ACTIVE_STATUSES
   (Pending HOD Approval, Approved, Confirmed) block a room. Rejected and
   Cancelled bookings are ignored.
2. Two date ranges overlap if:
       existing.check_in  <  requested.check_out   AND
       existing.check_out >  requested.check_in
3. Guest House "Gender Accommodated" must include the employee's gender.
4. Grade A/B employees require single (exclusive) occupancy of a room:
       - A room already holding any overlapping booking cannot be given
         to a Grade A/B employee.
       - A room already exclusively held by a Grade A/B occupant (for
         overlapping dates) cannot be given to anyone else.
5. Gender separation: a room with an overlapping Male occupant cannot
   take a Female occupant and vice-versa.
6. Capacity: total overlapping occupants in a room must stay within the
   room's capacity.

The main entry point is `find_available_room`, which returns the first
suitable Room object, or None if no room satisfies all the rules.
"""

from app.extensions import db
from app.models import Room, Booking, BookingStatus, GuestHouse


def _overlapping_bookings_for_room(room_id, check_in, check_out, exclude_booking_id=None):
    """Return all *active* bookings for a room that overlap the given date range."""
    query = Booking.query.filter(
        Booking.room_id == room_id,
        Booking.booking_status.in_(BookingStatus.ACTIVE_STATUSES),
        Booking.check_in_date < check_out,
        Booking.check_out_date > check_in,
    )
    if exclude_booking_id:
        query = query.filter(Booking.id != exclude_booking_id)
    return query.all()


def is_single_occupancy_grade(grade):
    return grade in {"A", "B"}


def room_is_suitable(room, gender, grade, check_in, check_out, exclude_booking_id=None):
    """
    Check whether `room` can accommodate a booking for an employee of the
    given `gender` and `grade` for the [check_in, check_out) date range.

    Returns (bool suitable, str reason_if_not).
    """
    if not room.is_active:
        return False, "Room is inactive."

    overlapping = _overlapping_bookings_for_room(
        room.id, check_in, check_out, exclude_booking_id=exclude_booking_id
    )

    # Rule: Grade A/B requesting employee needs the room completely empty
    # for the overlapping period.
    if is_single_occupancy_grade(grade):
        if overlapping:
            return False, "Room already has occupant(s); Grade A/B requires single occupancy."
    else:
        # Rule: if room already exclusively held by a Grade A/B occupant for
        # overlapping dates, nobody else can be added.
        if any(is_single_occupancy_grade(b.grade) for b in overlapping):
            return False, "Room is exclusively blocked for a Grade A/B occupant."

        # Rule: gender separation - existing occupants must all share the
        # same gender as the requesting employee.
        existing_genders = {b.gender for b in overlapping}
        if existing_genders and existing_genders != {gender}:
            return False, "Room already occupied by the opposite gender for overlapping dates."

        # Rule: capacity check.
        if len(overlapping) >= room.capacity:
            return False, "Room capacity already full for the selected dates."

    return True, ""


def find_available_room(guest_house, gender, grade, check_in, check_out, exclude_booking_id=None):
    """
    Find the first suitable active room in `guest_house` for an employee of
    `gender` / `grade` over [check_in, check_out).

    Returns the Room instance, or None if no room is available. Also
    returns None immediately if the guest house's gender-accommodation
    rule excludes the requesting gender.
    """
    if not guest_house.is_active:
        return None

    if not guest_house.accommodates(gender):
        return None

    rooms = (
        Room.query.filter_by(guest_house_id=guest_house.id, is_active=True)
        .order_by(Room.room_number.asc())
        .all()
    )

    for room in rooms:
        suitable, _ = room_is_suitable(
            room, gender, grade, check_in, check_out, exclude_booking_id=exclude_booking_id
        )
        if suitable:
            return room

    return None


def check_availability(guest_house_id, gender, grade, check_in, check_out, exclude_booking_id=None):
    """
    High level helper used by routes. Returns a dict describing the
    availability outcome, suitable for rendering in templates.
    """
    guest_house = GuestHouse.query.get(guest_house_id)
    if guest_house is None:
        return {"available": False, "message": "Selected guest house not found.", "room": None}

    if not guest_house.is_active:
        return {"available": False, "message": "Selected guest house is not active.", "room": None}

    if not guest_house.accommodates(gender):
        return {
            "available": False,
            "message": (
                f"This guest house does not accommodate {gender} employees. "
                "Please choose an alternate guest house."
            ),
            "room": None,
        }

    room = find_available_room(guest_house, gender, grade, check_in, check_out,
                                exclude_booking_id=exclude_booking_id)
    if room is None:
        return {
            "available": False,
            "message": (
                "Guest house is fully booked for selected dates. "
                "Please check alternate dates or alternate location."
            ),
            "room": None,
        }

    return {"available": True, "message": "Room available.", "room": room}


def room_booking_history(room_id):
    """Return all bookings (any status) ever made for a room, most recent first."""
    return (
        Booking.query.filter_by(room_id=room_id)
        .order_by(Booking.created_date.desc())
        .all()
    )
