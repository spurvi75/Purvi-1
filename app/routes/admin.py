"""
Admin routes: dashboard, Guest House Master, Room Master, User Master,
Booking Requests / Approved / Cancelled views, manual cancel/modify.
"""

from datetime import date, datetime

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user

from app.extensions import db
from app.models import User, GuestHouse, Room, Booking, BookingStatus, AuditLog
from app.forms import UserForm, GuestHouseForm, RoomForm, AdminCancelForm
from app.utils.decorators import roles_required
from app.utils.email_utils import send_cancellation_notification
from app.utils.availability import room_booking_history

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.before_request
@login_required
@roles_required("Admin")
def restrict_to_admin():
    pass


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@admin_bp.route("/dashboard")
def dashboard():
    today = date.today()
    cards = {
        "total_guest_houses": GuestHouse.query.filter_by(is_active=True).count(),
        "total_rooms": Room.query.filter_by(is_active=True).count(),
        "today_checkins": Booking.query.filter(
            Booking.check_in_date == today,
            Booking.booking_status.in_(BookingStatus.ACTIVE_STATUSES)).count(),
        "today_checkouts": Booking.query.filter(
            Booking.check_out_date == today,
            Booking.booking_status.in_(BookingStatus.ACTIVE_STATUSES)).count(),
        "pending_approvals": Booking.query.filter_by(
            booking_status=BookingStatus.PENDING_HOD_APPROVAL).count(),
        "confirmed_bookings": Booking.query.filter_by(
            booking_status=BookingStatus.CONFIRMED).count(),
    }
    recent_bookings = Booking.query.order_by(Booking.created_date.desc()).limit(8).all()
    return render_template("admin/dashboard.html", cards=cards, recent_bookings=recent_bookings)


# ---------------------------------------------------------------------------
# Guest House Master
# ---------------------------------------------------------------------------
@admin_bp.route("/guesthouses")
def guesthouse_list():
    search = request.args.get("q", "").strip()
    query = GuestHouse.query
    if search:
        query = query.filter(
            db.or_(GuestHouse.name.ilike(f"%{search}%"), GuestHouse.city.ilike(f"%{search}%"))
        )
    guesthouses = query.order_by(GuestHouse.city.asc(), GuestHouse.name.asc()).all()
    return render_template("admin/guesthouse_list.html", guesthouses=guesthouses, search=search)


@admin_bp.route("/guesthouses/new", methods=["GET", "POST"])
def guesthouse_new():
    form = GuestHouseForm()
    if form.validate_on_submit():
        gh = GuestHouse(
            city=form.city.data.strip(),
            name=form.name.data.strip(),
            address=form.address.data.strip(),
            pincode=form.pincode.data.strip(),
            number_of_rooms=form.number_of_rooms.data,
            capacity_per_room=form.capacity_per_room.data,
            gender_accommodated=",".join(form.gender_accommodated.data),
            is_active=form.is_active.data,
        )
        db.session.add(gh)
        db.session.commit()

        # Auto-create rooms according to "Number of Rooms"
        for i in range(1, form.number_of_rooms.data + 1):
            room = Room(
                guest_house_id=gh.id,
                room_number=f"R{i:03d}",
                capacity=form.capacity_per_room.data,
                is_active=True,
            )
            db.session.add(room)
        db.session.commit()

        AuditLog.log(current_user.email, "CREATE", "GuestHouse", gh.id, f"Created {gh.name}")
        flash(f"Guest house '{gh.name}' created with {form.number_of_rooms.data} rooms.", "success")
        return redirect(url_for("admin.guesthouse_list"))
    return render_template("admin/guesthouse_form.html", form=form, mode="new")


@admin_bp.route("/guesthouses/<int:gh_id>/edit", methods=["GET", "POST"])
def guesthouse_edit(gh_id):
    gh = GuestHouse.query.get_or_404(gh_id)
    form = GuestHouseForm(obj=gh)
    if request.method == "GET":
        form.gender_accommodated.data = gh.gender_list()
    if form.validate_on_submit():
        gh.city = form.city.data.strip()
        gh.name = form.name.data.strip()
        gh.address = form.address.data.strip()
        gh.pincode = form.pincode.data.strip()
        gh.number_of_rooms = form.number_of_rooms.data
        gh.capacity_per_room = form.capacity_per_room.data
        gh.gender_accommodated = ",".join(form.gender_accommodated.data)
        gh.is_active = form.is_active.data
        gh.modified_date = datetime.utcnow()
        db.session.commit()
        AuditLog.log(current_user.email, "UPDATE", "GuestHouse", gh.id, f"Updated {gh.name}")
        flash("Guest house updated successfully.", "success")
        return redirect(url_for("admin.guesthouse_list"))
    return render_template("admin/guesthouse_form.html", form=form, mode="edit", gh=gh)


@admin_bp.route("/guesthouses/<int:gh_id>/toggle-active", methods=["POST"])
def guesthouse_toggle_active(gh_id):
    gh = GuestHouse.query.get_or_404(gh_id)
    gh.is_active = not gh.is_active
    db.session.commit()
    AuditLog.log(current_user.email, "ACTIVATE" if gh.is_active else "DEACTIVATE",
                 "GuestHouse", gh.id, gh.name)
    flash(f"Guest house '{gh.name}' is now {'Active' if gh.is_active else 'Inactive'}.", "info")
    return redirect(url_for("admin.guesthouse_list"))


@admin_bp.route("/guesthouses/<int:gh_id>/delete", methods=["POST"])
def guesthouse_delete(gh_id):
    gh = GuestHouse.query.get_or_404(gh_id)
    if Booking.query.filter_by(guest_house_id=gh.id).count() > 0:
        flash("Cannot delete: this guest house has existing bookings. Deactivate it instead.", "warning")
        return redirect(url_for("admin.guesthouse_list"))
    db.session.delete(gh)
    db.session.commit()
    AuditLog.log(current_user.email, "DELETE", "GuestHouse", gh_id, gh.name)
    flash("Guest house deleted.", "info")
    return redirect(url_for("admin.guesthouse_list"))


# ---------------------------------------------------------------------------
# Room Master
# ---------------------------------------------------------------------------
@admin_bp.route("/guesthouses/<int:gh_id>/rooms")
def room_list(gh_id):
    gh = GuestHouse.query.get_or_404(gh_id)
    rooms = Room.query.filter_by(guest_house_id=gh_id).order_by(Room.room_number.asc()).all()
    return render_template("admin/room_list.html", gh=gh, rooms=rooms)


@admin_bp.route("/guesthouses/<int:gh_id>/rooms/new", methods=["GET", "POST"])
def room_new(gh_id):
    gh = GuestHouse.query.get_or_404(gh_id)
    form = RoomForm()
    if form.validate_on_submit():
        room = Room(
            guest_house_id=gh.id,
            room_number=form.room_number.data.strip(),
            capacity=form.capacity.data,
            is_active=form.is_active.data,
        )
        db.session.add(room)
        db.session.commit()
        AuditLog.log(current_user.email, "CREATE", "Room", room.id, f"{gh.name} - {room.room_number}")
        flash("Room added.", "success")
        return redirect(url_for("admin.room_list", gh_id=gh.id))
    return render_template("admin/room_form.html", form=form, gh=gh, mode="new")


@admin_bp.route("/rooms/<int:room_id>/edit", methods=["GET", "POST"])
def room_edit(room_id):
    room = Room.query.get_or_404(room_id)
    gh = room.guest_house
    form = RoomForm(obj=room)
    if form.validate_on_submit():
        room.room_number = form.room_number.data.strip()
        room.capacity = form.capacity.data
        room.is_active = form.is_active.data
        db.session.commit()
        AuditLog.log(current_user.email, "UPDATE", "Room", room.id, room.room_number)
        flash("Room updated.", "success")
        return redirect(url_for("admin.room_list", gh_id=gh.id))
    return render_template("admin/room_form.html", form=form, gh=gh, mode="edit", room=room)


@admin_bp.route("/rooms/<int:room_id>/toggle-active", methods=["POST"])
def room_toggle_active(room_id):
    room = Room.query.get_or_404(room_id)
    room.is_active = not room.is_active
    db.session.commit()
    AuditLog.log(current_user.email, "ACTIVATE" if room.is_active else "DEACTIVATE",
                 "Room", room.id, room.room_number)
    flash(f"Room '{room.room_number}' is now {'Active' if room.is_active else 'Inactive'}.", "info")
    return redirect(url_for("admin.room_list", gh_id=room.guest_house_id))


@admin_bp.route("/rooms/<int:room_id>/history")
def room_history(room_id):
    room = Room.query.get_or_404(room_id)
    bookings = room_booking_history(room_id)
    return render_template("admin/room_history.html", room=room, bookings=bookings)


# ---------------------------------------------------------------------------
# User Master
# ---------------------------------------------------------------------------
@admin_bp.route("/users")
def user_list():
    search = request.args.get("q", "").strip()
    query = User.query
    if search:
        query = query.filter(
            db.or_(User.name.ilike(f"%{search}%"), User.email.ilike(f"%{search}%"),
                   User.employee_code.ilike(f"%{search}%"))
        )
    users = query.order_by(User.name.asc()).all()
    return render_template("admin/user_list.html", users=users, search=search)


@admin_bp.route("/users/new", methods=["GET", "POST"])
def user_new():
    form = UserForm()
    if form.validate_on_submit():
        if not form.password.data:
            flash("Password is required for a new user.", "danger")
            return render_template("admin/user_form.html", form=form, mode="new")
        if User.query.filter_by(email=form.email.data.strip().lower()).first():
            flash("A user with this email already exists.", "danger")
            return render_template("admin/user_form.html", form=form, mode="new")

        user = User(
            employee_code=form.employee_code.data.strip(),
            name=form.name.data.strip(),
            email=form.email.data.strip().lower(),
            mobile_number=form.mobile_number.data.strip(),
            grade=form.grade.data,
            gender=form.gender.data,
            hod_name=form.hod_name.data.strip() if form.hod_name.data else None,
            hod_email=form.hod_email.data.strip().lower() if form.hod_email.data else None,
            roles=",".join(form.roles.data),
            is_active_user=form.is_active_user.data,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        AuditLog.log(current_user.email, "CREATE", "User", user.id, user.email)
        flash(f"User '{user.name}' created.", "success")
        return redirect(url_for("admin.user_list"))
    return render_template("admin/user_form.html", form=form, mode="new")


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
def user_edit(user_id):
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)
    if request.method == "GET":
        form.roles.data = user.role_list()
        form.password.data = ""
    if form.validate_on_submit():
        existing = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if existing and existing.id != user.id:
            flash("Another user with this email already exists.", "danger")
            return render_template("admin/user_form.html", form=form, mode="edit", user=user)

        user.employee_code = form.employee_code.data.strip()
        user.name = form.name.data.strip()
        user.email = form.email.data.strip().lower()
        user.mobile_number = form.mobile_number.data.strip()
        user.grade = form.grade.data
        user.gender = form.gender.data
        user.hod_name = form.hod_name.data.strip() if form.hod_name.data else None
        user.hod_email = form.hod_email.data.strip().lower() if form.hod_email.data else None
        user.roles = ",".join(form.roles.data)
        user.is_active_user = form.is_active_user.data
        if form.password.data:
            user.set_password(form.password.data)
        user.modified_date = datetime.utcnow()
        db.session.commit()
        AuditLog.log(current_user.email, "UPDATE", "User", user.id, user.email)
        flash("User updated successfully.", "success")
        return redirect(url_for("admin.user_list"))
    return render_template("admin/user_form.html", form=form, mode="edit", user=user)


@admin_bp.route("/users/<int:user_id>/toggle-active", methods=["POST"])
def user_toggle_active(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot deactivate your own account.", "warning")
        return redirect(url_for("admin.user_list"))
    user.is_active_user = not user.is_active_user
    db.session.commit()
    AuditLog.log(current_user.email, "ACTIVATE" if user.is_active_user else "DEACTIVATE",
                 "User", user.id, user.email)
    flash(f"User '{user.name}' is now {'Active' if user.is_active_user else 'Inactive'}.", "info")
    return redirect(url_for("admin.user_list"))


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
def user_delete(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot delete your own account.", "warning")
        return redirect(url_for("admin.user_list"))
    if Booking.query.filter_by(employee_id=user.id).count() > 0:
        flash("Cannot delete: this user has existing bookings. Deactivate instead.", "warning")
        return redirect(url_for("admin.user_list"))
    db.session.delete(user)
    db.session.commit()
    AuditLog.log(current_user.email, "DELETE", "User", user_id, user.email)
    flash("User deleted.", "info")
    return redirect(url_for("admin.user_list"))


# ---------------------------------------------------------------------------
# Bookings - view all / approved / cancelled, manual cancel
# ---------------------------------------------------------------------------
@admin_bp.route("/bookings")
def bookings_all():
    status_filter = request.args.get("status", "")
    query = Booking.query
    if status_filter:
        query = query.filter_by(booking_status=status_filter)
    bookings = query.order_by(Booking.created_date.desc()).all()
    return render_template("admin/bookings.html", bookings=bookings, status_filter=status_filter,
                            all_statuses=BookingStatus.ALL, page_title="All Booking Requests")


@admin_bp.route("/bookings/approved")
def bookings_approved():
    bookings = Booking.query.filter(
        Booking.booking_status.in_([BookingStatus.APPROVED, BookingStatus.CONFIRMED])
    ).order_by(Booking.created_date.desc()).all()
    return render_template("admin/bookings.html", bookings=bookings, status_filter="",
                            all_statuses=BookingStatus.ALL, page_title="Approved / Confirmed Bookings")


@admin_bp.route("/bookings/cancelled")
def bookings_cancelled():
    bookings = Booking.query.filter(
        Booking.booking_status.in_([BookingStatus.CANCELLED, BookingStatus.REJECTED])
    ).order_by(Booking.created_date.desc()).all()
    return render_template("admin/bookings.html", bookings=bookings, status_filter="",
                            all_statuses=BookingStatus.ALL, page_title="Cancelled / Rejected Bookings")


@admin_bp.route("/bookings/<int:booking_id>")
def booking_detail(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    cancel_form = AdminCancelForm()
    return render_template("admin/booking_detail.html", booking=booking, cancel_form=cancel_form)


@admin_bp.route("/bookings/<int:booking_id>/cancel", methods=["POST"])
def booking_cancel(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    form = AdminCancelForm()
    if form.validate_on_submit():
        booking.booking_status = BookingStatus.CANCELLED
        booking.cancelled_by = f"Admin: {current_user.email}"
        booking.cancellation_date = datetime.utcnow()
        booking.cancellation_reason = form.reason.data
        booking.admin_remarks = form.reason.data
        db.session.commit()
        AuditLog.log(current_user.email, "CANCEL", "Booking", booking.id, form.reason.data)
        send_cancellation_notification(booking, current_app.config.get("ADMIN_NOTIFICATION_EMAIL"))
        flash(f"Booking {booking.booking_number} cancelled.", "success")
    else:
        flash("Cancellation reason is required.", "danger")
    return redirect(url_for("admin.booking_detail", booking_id=booking.id))


# ---------------------------------------------------------------------------
# Audit Log
# ---------------------------------------------------------------------------
@admin_bp.route("/audit-log")
def audit_log():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(500).all()
    return render_template("admin/audit_log.html", logs=logs)
