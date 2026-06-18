"""
Email notification utility.

All outgoing email content is generated here so that templates for the
various notifications (forgot password, booking submitted, HOD approval/
rejection, booking confirmation, admin notification, cancellation) live in
one place.

SMTP settings are read from Config (environment variables / .env file).
When MAIL_SUPPRESS_SEND is True (the default for local development), the
Flask-Mail SUPPRESS_SEND option means messages are not actually delivered
- they are simply logged, which is convenient when no real SMTP server is
configured.
"""

from flask import current_app, render_template_string
from flask_mail import Message

from app.extensions import mail


def _send(subject, recipients, html_body):
    if not recipients:
        return
    msg = Message(subject=subject, recipients=recipients, html=html_body)
    try:
        mail.send(msg)
    except Exception as exc:  # pragma: no cover - best effort, never block the request
        current_app.logger.warning("Failed to send email '%s' to %s: %s", subject, recipients, exc)


def send_password_reset_email(user, reset_url):
    html = render_template_string(
        """
        <p>Dear {{ user.name }},</p>
        <p>We received a request to reset your password for the Axis Solutions Ltd
        Guest House Booking System.</p>
        <p><a href="{{ reset_url }}">Click here to reset your password</a></p>
        <p>This link will expire in {{ expiry }} minutes. If you did not request this,
        please ignore this email.</p>
        <p>Regards,<br>Axis Solutions Ltd - Guest House Booking System</p>
        """,
        user=user, reset_url=reset_url,
        expiry=current_app.config.get("PASSWORD_RESET_EXPIRY_MINUTES", 30),
    )
    _send("Password Reset Request - Axis Guest House Booking", [user.email], html)


def send_booking_submitted_to_hod(booking, approve_url, reject_url):
    html = render_template_string(
        """
        <p>Dear {{ b.hod_email }},</p>
        <p>{{ b.employee_name }} ({{ b.employee_email }}) has submitted a guest house
        booking request that requires your approval.</p>
        <table border="0" cellpadding="4">
        <tr><td><b>Booking No.</b></td><td>{{ b.booking_number }}</td></tr>
        <tr><td><b>Employee ID</b></td><td>{{ b.employee_id }}</td></tr>
        <tr><td><b>City</b></td><td>{{ b.city }}</td></tr>
        <tr><td><b>Guest House</b></td><td>{{ b.guest_house_name }}</td></tr>
        <tr><td><b>Room Number</b></td><td>{{ b.room_number }}</td></tr>
        <tr><td><b>Check-in</b></td><td>{{ b.check_in_date }}</td></tr>
        <tr><td><b>Check-out</b></td><td>{{ b.check_out_date }}</td></tr>
        <tr><td><b>Purpose</b></td><td>{{ b.purpose_of_visit }}</td></tr>
        </table>
        <p>
          <a href="{{ approve_url }}">Login to Approve</a> &nbsp;|&nbsp;
          <a href="{{ reject_url }}">Login to Reject</a>
        </p>
        <p>Please log in to the application to take action.</p>
        """,
        b=booking, approve_url=approve_url, reject_url=reject_url,
    )
    _send(f"Booking Approval Required - {booking.booking_number}", [booking.hod_email], html)


def send_booking_confirmation_to_employee(booking):
    html = render_template_string(
        """
        <p>Dear {{ b.employee_name }},</p>
        <p>Your guest house booking has been <b>Confirmed</b> by your HOD.</p>
        <table border="0" cellpadding="4">
        <tr><td><b>Booking No.</b></td><td>{{ b.booking_number }}</td></tr>
        <tr><td><b>Guest House</b></td><td>{{ b.guest_house_name }}</td></tr>
        <tr><td><b>Room Number</b></td><td>{{ b.room_number }}</td></tr>
        <tr><td><b>Check-in</b></td><td>{{ b.check_in_date }}</td></tr>
        <tr><td><b>Check-out</b></td><td>{{ b.check_out_date }}</td></tr>
        </table>
        <p>You may print your booking confirmation from "My Booking Status" in the
        application.</p>
        <p>Regards,<br>Axis Solutions Ltd - Guest House Booking System</p>
        """,
        b=booking,
    )
    _send(f"Booking Confirmed - {booking.booking_number}", [booking.employee_email], html)


def send_booking_details_to_admin(booking, admin_email):
    html = render_template_string(
        """
        <p>A guest house booking has been confirmed. Details below:</p>
        <table border="0" cellpadding="4">
        <tr><td><b>Booking No.</b></td><td>{{ b.booking_number }}</td></tr>
        <tr><td><b>Employee Name</b></td><td>{{ b.employee_name }}</td></tr>
        <tr><td><b>Employee ID</b></td><td>{{ b.employee_id }}</td></tr>
        <tr><td><b>Mobile</b></td><td>{{ b.mobile_number }}</td></tr>
        <tr><td><b>Grade</b></td><td>{{ b.grade }}</td></tr>
        <tr><td><b>Gender</b></td><td>{{ b.gender }}</td></tr>
        <tr><td><b>City</b></td><td>{{ b.city }}</td></tr>
        <tr><td><b>Guest House</b></td><td>{{ b.guest_house_name }}</td></tr>
        <tr><td><b>Address</b></td><td>{{ b.guest_house.address }}, {{ b.guest_house.pincode }}</td></tr>
        <tr><td><b>Room Number</b></td><td>{{ b.room_number }}</td></tr>
        <tr><td><b>Check-in</b></td><td>{{ b.check_in_date }}</td></tr>
        <tr><td><b>Check-out</b></td><td>{{ b.check_out_date }}</td></tr>
        <tr><td><b>HOD</b></td><td>{{ b.hod_email }}</td></tr>
        <tr><td><b>Purpose</b></td><td>{{ b.purpose_of_visit }}</td></tr>
        </table>
        """,
        b=booking,
    )
    _send(f"Booking Confirmed - {booking.booking_number}", [admin_email], html)


def send_booking_rejection_to_employee(booking):
    html = render_template_string(
        """
        <p>Dear {{ b.employee_name }},</p>
        <p>Your guest house booking request <b>{{ b.booking_number }}</b> has been
        <b>Rejected</b> by your HOD.</p>
        <p><b>Reason:</b> {{ b.hod_rejection_reason }}</p>
        <p>You may submit a new booking request from the application if required.</p>
        """,
        b=booking,
    )
    _send(f"Booking Rejected - {booking.booking_number}", [booking.employee_email], html)


def send_cancellation_notification(booking, admin_email):
    recipients = [e for e in [admin_email, booking.hod_email] if e]
    html = render_template_string(
        """
        <p>The following guest house booking has been cancelled:</p>
        <table border="0" cellpadding="4">
        <tr><td><b>Booking No.</b></td><td>{{ b.booking_number }}</td></tr>
        <tr><td><b>Employee</b></td><td>{{ b.employee_name }} ({{ b.employee_email }})</td></tr>
        <tr><td><b>Guest House</b></td><td>{{ b.guest_house_name }}</td></tr>
        <tr><td><b>Room Number</b></td><td>{{ b.room_number }}</td></tr>
        <tr><td><b>Check-in</b></td><td>{{ b.check_in_date }}</td></tr>
        <tr><td><b>Check-out</b></td><td>{{ b.check_out_date }}</td></tr>
        <tr><td><b>Cancelled By</b></td><td>{{ b.cancelled_by }}</td></tr>
        <tr><td><b>Reason</b></td><td>{{ b.cancellation_reason }}</td></tr>
        </table>
        """,
        b=booking,
    )
    _send(f"Booking Cancelled - {booking.booking_number}", recipients, html)
