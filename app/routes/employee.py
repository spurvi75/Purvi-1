"""
Employee routes: dashboard, guest house booking (availability check +
submit), my booking status / history, cancellation, print confirmation.
"""

from datetime import date, datetime

from flask import (
    Blueprint, render_template, redirect, url_for, flash, request,
    current_app, send_file, jsonify
)
from flask_login import login_required, current_user

from app.extensions import db
from app.models import GuestHouse, Booking, BookingStatus
from app.forms import AvailabilityCheckForm, CancelBookingForm
from app.utils.decorators import roles_required
from app.utils.availability import check_availability
from app.utils.helpers import generate_booking_number
from app.utils.email_utils import (
    send_booking_submitted_to_hod, send_cancellation_notification
)
from app.utils.pdf_utils import generate_booking_confirmation_pdf

employee_bp = Blueprint("employee", __name__, url_prefix="/employee")


@employee_bp.before_request
@login_required
@roles_required("Employee", "Admin", "HOD")
def restrict_to_logged_in():
    # Every role includes basic "Employee" self-service capability
    # (an Admin or HOD can also personally book guest houses).
    pass


@employee_bp.route("/dashboard")
def dashboard():
    my_bookings = Booking.query.filter_by(employee_id=current_user.id).order_by(
        Booking.created_date.desc()
    ).limit(5).all()
    return render_template("employee/dashboard.html", my_bookings=my_bookings)


def _populate_city_and_gh_choices(form):
    cities = sorted({gh.city for gh in GuestHouse.query.filter_by(is_active=True).all()})
    form.city.choices = [("", "-- Select City --")] + [(c, c) for c in cities]

    selected_city = form.city.data
    if selected_city:
        ghs = GuestHouse.query.filter_by(is_active=True, city=selected_city).all()
    else:
        ghs = []
    form.guest_house_id.choices = [(0, "-- Select Guest House --")] + [
        (gh.id, f"{gh.name} ({gh.address[:40]})") for gh in ghs
    ]


@employee_bp.route("/booking", methods=["GET", "POST"])
def booking():
    form = AvailabilityCheckForm()
    # Repopulate city select based on submitted value (for validation) before validate_on_submit
    form.city.choices = [("", "-- Select City --")] + [
        (c, c) for c in sorted({gh.city for gh in GuestHouse.query.filter_by(is_active=True).all()})
    ]
    if request.method == "POST" and form.city.data:
        ghs = GuestHouse.query.filter_by(is_active=True, city=form.city.data).all()
        form.guest_house_id.choices = [(0, "-- Select Guest House --")] + [
            (gh.id, f"{gh.name} ({gh.address[:40]})") for gh in ghs
        ]
    else:
        form.guest_house_id.choices = [(0, "-- Select Guest House --")]

    result = None
    guest_house = None

    if request.method == "POST":
        if form.guest_house_id.data:
            guest_house = GuestHouse.query.get(form.guest_house_id.data)

        if form.validate_on_submit() and guest_house:
            if form.submit_check.data:
                result = check_availability(
                    guest_house.id, current_user.gender, current_user.grade,
                    form.check_in_date.data, form.check_out_date.data,
                )
            elif form.submit_booking.data:
                # Re-verify availability server-side before committing
                # (defends against stale/duplicate submissions).
                result = check_availability(
                    guest_house.id, current_user.gender, current_user.grade,
                    form.check_in_date.data, form.check_out_date.data,
                )
                if not result["available"]:
                    flash(result["message"], "danger")
                else:
                    room = result["room"]
                    booking_obj = Booking(
                        booking_number=generate_booking_number(
                            current_app.config.get("BOOKING_NUMBER_PREFIX", "AXIS-GH")
                        ),
                        employee_id=current_user.id,
                        employee_name=current_user.name,
                        employee_email=current_user.email,
                        mobile_number=current_user.mobile_number,
                        grade=current_user.grade,
                        gender=current_user.gender,
                        hod_email=current_user.hod_email,
                        city=guest_house.city,
                        guest_house_id=guest_house.id,
                        guest_house_name=guest_house.name,
                        room_id=room.id,
                        room_number=room.room_number,
                        check_in_date=form.check_in_date.data,
                        check_out_date=form.check_out_date.data,
                        purpose_of_visit=form.purpose_of_visit.data,
                        remarks=form.remarks.data,
                        booking_status=BookingStatus.PENDING_HOD_APPROVAL,
                        hod_approval_status="Pending",
                    )
                    db.session.add(booking_obj)
                    db.session.commit()

                    if booking_obj.hod_email:
                        approve_url = url_for("hod.pending_approvals", _external=True)
                        send_booking_submitted_to_hod(booking_obj, approve_url, approve_url)
                    else:
                        flash(
                            "Note: No HOD email is configured on your profile; "
                            "please contact Admin to set your HOD for approval routing.",
                            "warning",
                        )

                    flash(
                        "Your guest house booking request has been submitted to your HOD for approval.",
                        "success",
                    )
                    return redirect(url_for("employee.my_bookings"))

    return render_template(
        "employee/booking.html", form=form, result=result, guest_house=guest_house, today=date.today()
    )


@employee_bp.route("/booking/guesthouses-for-city")
def guesthouses_for_city():
    """Small JSON endpoint used by the booking page to refresh the guest
    house dropdown via JS when the city selection changes (progressive
    enhancement; the page also works correctly via full form re-submit)."""
    city = request.args.get("city", "")
    ghs = GuestHouse.query.filter_by(is_active=True, city=city).all() if city else []
    return jsonify([
        {"id": gh.id, "name": gh.name, "address": gh.address, "pincode": gh.pincode,
         "gender": gh.gender_accommodated}
        for gh in ghs
    ])


@employee_bp.route("/my-bookings")
def my_bookings():
    bookings = Booking.query.filter_by(employee_id=current_user.id).order_by(
        Booking.created_date.desc()
    ).all()
    return render_template("employee/my_bookings.html", bookings=bookings)


@employee_bp.route("/booking/<int:booking_id>/confirmation")
def booking_confirmation(booking_id):
    booking_obj = Booking.query.get_or_404(booking_id)
    if booking_obj.employee_id != current_user.id and not current_user.is_admin:
        flash("You can only view your own bookings.", "danger")
        return redirect(url_for("employee.my_bookings"))
    return render_template("employee/booking_confirmation.html", booking=booking_obj)


@employee_bp.route("/booking/<int:booking_id>/confirmation/pdf")
def booking_confirmation_pdf(booking_id):
    booking_obj = Booking.query.get_or_404(booking_id)
    if booking_obj.employee_id != current_user.id and not current_user.is_admin:
        flash("You can only view your own bookings.", "danger")
        return redirect(url_for("employee.my_bookings"))
    buffer = generate_booking_confirmation_pdf(
        booking_obj, current_app.config.get("COMPANY_NAME", "Axis Solutions Ltd.")
    )
    return send_file(
        buffer, mimetype="application/pdf", as_attachment=True,
        download_name=f"{booking_obj.booking_number}.pdf",
    )


@employee_bp.route("/booking/<int:booking_id>/cancel", methods=["GET", "POST"])
def cancel_booking(booking_id):
    booking_obj = Booking.query.get_or_404(booking_id)
    if booking_obj.employee_id != current_user.id:
        flash("You can only cancel your own bookings.", "danger")
        return redirect(url_for("employee.my_bookings"))

    if booking_obj.booking_status not in (
        BookingStatus.PENDING_HOD_APPROVAL, BookingStatus.APPROVED, BookingStatus.CONFIRMED
    ):
        flash("This booking cannot be cancelled.", "warning")
        return redirect(url_for("employee.my_bookings"))

    form = CancelBookingForm()
    if form.validate_on_submit():
        booking_obj.booking_status = BookingStatus.CANCELLED
        booking_obj.cancelled_by = f"Employee: {current_user.email}"
        booking_obj.cancellation_date = datetime.utcnow()
        booking_obj.cancellation_reason = form.cancellation_reason.data
        db.session.commit()

        send_cancellation_notification(
            booking_obj, current_app.config.get("ADMIN_NOTIFICATION_EMAIL")
        )
        flash(f"Booking {booking_obj.booking_number} has been cancelled. The room is now available again.", "success")
        return redirect(url_for("employee.my_bookings"))

    return render_template("employee/cancel_booking.html", booking=booking_obj, form=form)
