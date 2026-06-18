"""
HOD routes: dashboard, pending approvals, approve/reject flow, approved /
rejected request history.
"""

from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, flash, current_app
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Booking, BookingStatus
from app.forms import HODRejectForm
from app.utils.decorators import roles_required
from app.utils.email_utils import (
    send_booking_confirmation_to_employee, send_booking_details_to_admin,
    send_booking_rejection_to_employee,
)

hod_bp = Blueprint("hod", __name__, url_prefix="/hod")


@hod_bp.before_request
@login_required
@roles_required("HOD")
def restrict_to_hod():
    pass


def _pending_for_current_hod():
    return Booking.query.filter_by(
        hod_email=current_user.email, booking_status=BookingStatus.PENDING_HOD_APPROVAL
    ).order_by(Booking.created_date.asc())


@hod_bp.route("/dashboard")
def dashboard():
    pending_count = _pending_for_current_hod().count()
    approved_count = Booking.query.filter_by(
        hod_email=current_user.email, booking_status=BookingStatus.CONFIRMED
    ).count()
    rejected_count = Booking.query.filter_by(
        hod_email=current_user.email, booking_status=BookingStatus.REJECTED
    ).count()
    recent_pending = _pending_for_current_hod().limit(5).all()
    return render_template(
        "hod/dashboard.html", pending_count=pending_count, approved_count=approved_count,
        rejected_count=rejected_count, recent_pending=recent_pending
    )


@hod_bp.route("/pending")
def pending_approvals():
    bookings = _pending_for_current_hod().all()
    return render_template("hod/pending.html", bookings=bookings)


@hod_bp.route("/approved")
def approved_requests():
    bookings = Booking.query.filter_by(
        hod_email=current_user.email, booking_status=BookingStatus.CONFIRMED
    ).order_by(Booking.hod_approval_date.desc()).all()
    return render_template("hod/approved.html", bookings=bookings)


@hod_bp.route("/rejected")
def rejected_requests():
    bookings = Booking.query.filter_by(
        hod_email=current_user.email, booking_status=BookingStatus.REJECTED
    ).order_by(Booking.modified_date.desc()).all()
    return render_template("hod/rejected.html", bookings=bookings)


@hod_bp.route("/bookings/<int:booking_id>")
def booking_detail(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.hod_email != current_user.email:
        flash("You may only act on requests routed to you.", "danger")
        return redirect(url_for("hod.pending_approvals"))
    reject_form = HODRejectForm()
    return render_template("hod/booking_detail.html", booking=booking, reject_form=reject_form)


@hod_bp.route("/bookings/<int:booking_id>/approve", methods=["POST"])
def approve(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.hod_email != current_user.email:
        flash("You may only act on requests routed to you.", "danger")
        return redirect(url_for("hod.pending_approvals"))

    if booking.booking_status != BookingStatus.PENDING_HOD_APPROVAL:
        flash("This request has already been actioned.", "warning")
        return redirect(url_for("hod.pending_approvals"))

    booking.booking_status = BookingStatus.CONFIRMED
    booking.hod_approval_status = "Approved"
    booking.hod_approval_date = datetime.utcnow()
    booking.admin_notification_status = "Sent"
    db.session.commit()

    send_booking_confirmation_to_employee(booking)
    send_booking_details_to_admin(booking, current_app.config.get("ADMIN_NOTIFICATION_EMAIL"))

    flash(f"Booking {booking.booking_number} approved and confirmed.", "success")
    return redirect(url_for("hod.pending_approvals"))


@hod_bp.route("/bookings/<int:booking_id>/reject", methods=["POST"])
def reject(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.hod_email != current_user.email:
        flash("You may only act on requests routed to you.", "danger")
        return redirect(url_for("hod.pending_approvals"))

    if booking.booking_status != BookingStatus.PENDING_HOD_APPROVAL:
        flash("This request has already been actioned.", "warning")
        return redirect(url_for("hod.pending_approvals"))

    form = HODRejectForm()
    if form.validate_on_submit():
        booking.booking_status = BookingStatus.REJECTED
        booking.hod_approval_status = "Rejected"
        booking.hod_approval_date = datetime.utcnow()
        booking.hod_rejection_reason = form.rejection_reason.data
        db.session.commit()

        send_booking_rejection_to_employee(booking)
        flash(f"Booking {booking.booking_number} rejected.", "info")
    else:
        flash("A rejection reason is required.", "danger")
    return redirect(url_for("hod.pending_approvals"))
