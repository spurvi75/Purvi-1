"""
Database models for the Axis Solutions Ltd Guest House Booking System.
"""

from datetime import datetime, timedelta
import secrets

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


# ---------------------------------------------------------------------------
# User Master
# ---------------------------------------------------------------------------
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    employee_code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    mobile_number = db.Column(db.String(15), nullable=False)
    grade = db.Column(db.String(5), nullable=False)
    gender = db.Column(db.String(10), nullable=False)  # Male / Female

    hod_name = db.Column(db.String(120))
    hod_email = db.Column(db.String(120))

    # Roles stored as comma separated string e.g. "Employee,HOD" so that a
    # single person can hold multiple roles as required by the spec.
    roles = db.Column(db.String(50), nullable=False, default="Employee")

    is_active_user = db.Column(db.Boolean, default=True, nullable=False)

    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    modified_date = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    bookings = db.relationship("Booking", backref="employee", lazy="dynamic",
                                foreign_keys="Booking.employee_id")

    # --- Password helpers ---------------------------------------------------
    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    # --- Role helpers --------------------------------------------------------
    def role_list(self):
        return [r.strip() for r in (self.roles or "").split(",") if r.strip()]

    def has_role(self, role):
        return role in self.role_list()

    @property
    def is_admin(self):
        return self.has_role("Admin")

    @property
    def is_hod(self):
        return self.has_role("HOD")

    @property
    def is_employee(self):
        return self.has_role("Employee")

    # Flask-Login requires this to be active to allow login
    @property
    def is_active(self):
        return self.is_active_user

    def __repr__(self):
        return f"<User {self.email}>"


# ---------------------------------------------------------------------------
# Guest House Master
# ---------------------------------------------------------------------------
class GuestHouse(db.Model):
    __tablename__ = "guest_houses"

    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(80), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    number_of_rooms = db.Column(db.Integer, nullable=False, default=0)
    capacity_per_room = db.Column(db.Integer, nullable=False, default=1)

    # Gender accommodated - stored as comma separated, e.g. "Male,Female"
    gender_accommodated = db.Column(db.String(20), nullable=False, default="Male,Female")

    is_active = db.Column(db.Boolean, default=True, nullable=False)

    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    modified_date = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    rooms = db.relationship("Room", backref="guest_house", lazy="dynamic",
                             cascade="all, delete-orphan")

    def accommodates(self, gender):
        return gender in self.gender_list()

    def gender_list(self):
        return [g.strip() for g in (self.gender_accommodated or "").split(",") if g.strip()]

    def __repr__(self):
        return f"<GuestHouse {self.name} ({self.city})>"


# ---------------------------------------------------------------------------
# Room Master
# ---------------------------------------------------------------------------
class Room(db.Model):
    __tablename__ = "rooms"

    id = db.Column(db.Integer, primary_key=True)
    guest_house_id = db.Column(db.Integer, db.ForeignKey("guest_houses.id"), nullable=False)
    room_number = db.Column(db.String(20), nullable=False)
    capacity = db.Column(db.Integer, nullable=False, default=1)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    bookings = db.relationship("Booking", backref="room", lazy="dynamic")

    __table_args__ = (
        db.UniqueConstraint("guest_house_id", "room_number", name="uq_room_per_guesthouse"),
    )

    def __repr__(self):
        return f"<Room {self.room_number} @GH{self.guest_house_id}>"


# ---------------------------------------------------------------------------
# Booking Request
# ---------------------------------------------------------------------------
class BookingStatus:
    DRAFT = "Draft"
    PENDING_HOD_APPROVAL = "Pending HOD Approval"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    CONFIRMED = "Confirmed"
    CANCELLATION_REQUESTED = "Cancellation Requested"
    CANCELLED = "Cancelled"

    ACTIVE_STATUSES = [PENDING_HOD_APPROVAL, APPROVED, CONFIRMED]
    ALL = [DRAFT, PENDING_HOD_APPROVAL, APPROVED, REJECTED, CONFIRMED,
           CANCELLATION_REQUESTED, CANCELLED]


class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    booking_number = db.Column(db.String(40), unique=True, nullable=False, index=True)

    employee_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Snapshot fields - captured at time of booking so historical record
    # remains correct even if the User Master record changes later.
    employee_name = db.Column(db.String(120), nullable=False)
    employee_email = db.Column(db.String(120), nullable=False)
    mobile_number = db.Column(db.String(15), nullable=False)
    grade = db.Column(db.String(5), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    hod_email = db.Column(db.String(120))

    city = db.Column(db.String(80), nullable=False)
    guest_house_id = db.Column(db.Integer, db.ForeignKey("guest_houses.id"), nullable=False)
    guest_house_name = db.Column(db.String(150), nullable=False)

    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False)
    room_number = db.Column(db.String(20), nullable=False)

    check_in_date = db.Column(db.Date, nullable=False)
    check_out_date = db.Column(db.Date, nullable=False)

    purpose_of_visit = db.Column(db.Text, nullable=False)
    remarks = db.Column(db.Text)

    booking_status = db.Column(db.String(30), nullable=False, default=BookingStatus.PENDING_HOD_APPROVAL)
    hod_approval_status = db.Column(db.String(30), default="Pending")
    hod_approval_date = db.Column(db.DateTime)
    hod_rejection_reason = db.Column(db.Text)

    admin_notification_status = db.Column(db.String(20), default="Pending")
    admin_remarks = db.Column(db.Text)

    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    modified_date = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    cancelled_by = db.Column(db.String(120))
    cancellation_date = db.Column(db.DateTime)
    cancellation_reason = db.Column(db.Text)

    guest_house = db.relationship("GuestHouse")

    def overlaps(self, check_in, check_out):
        """Standard date range overlap check."""
        return self.check_in_date < check_out and self.check_out_date > check_in

    def __repr__(self):
        return f"<Booking {self.booking_number} - {self.booking_status}>"


# ---------------------------------------------------------------------------
# Password Reset Tokens
# ---------------------------------------------------------------------------
class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    token = db.Column(db.String(128), unique=True, nullable=False, index=True)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)

    user = db.relationship("User")

    @staticmethod
    def generate_for_user(user, expiry_minutes=30):
        token = secrets.token_urlsafe(48)
        reset = PasswordResetToken(
            user_id=user.id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(minutes=expiry_minutes),
        )
        db.session.add(reset)
        db.session.commit()
        return reset

    def is_valid(self):
        return (not self.used) and datetime.utcnow() <= self.expires_at


# ---------------------------------------------------------------------------
# Audit Log (for admin master-data changes)
# ---------------------------------------------------------------------------
class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    performed_by = db.Column(db.String(120))
    action = db.Column(db.String(50))         # e.g. CREATE / UPDATE / DELETE / ACTIVATE / DEACTIVATE
    entity_type = db.Column(db.String(50))    # e.g. User / GuestHouse / Room / Booking
    entity_id = db.Column(db.Integer)
    details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def log(performed_by, action, entity_type, entity_id, details=""):
        entry = AuditLog(
            performed_by=performed_by,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
        )
        db.session.add(entry)
        db.session.commit()
