"""
WTForms definitions used across the application. Centralising them here
keeps routes thin and validation logic consistent and reusable.
"""

from datetime import date

from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SelectField, SelectMultipleField, IntegerField,
    TextAreaField, DateField, BooleanField, SubmitField, widgets
)
from wtforms.validators import (
    DataRequired, Email, Length, EqualTo, Regexp, NumberRange, Optional, ValidationError
)


GRADE_CHOICES = [(g, g) for g in ["A", "B", "C", "D", "E"]]
GENDER_CHOICES = [("Male", "Male"), ("Female", "Female")]
ROLE_CHOICES = [("Employee", "Employee"), ("Admin", "Admin"), ("HOD", "HOD")]

MOBILE_REGEX = r"^[0-9+\-\s]{7,15}$"
PINCODE_REGEX = r"^[0-9]{4,10}$"


class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


# ---------------------------------------------------------------------------
# Auth forms
# ---------------------------------------------------------------------------
class LoginForm(FlaskForm):
    email = StringField("Email ID", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")


class ForgotPasswordForm(FlaskForm):
    email = StringField("Registered Email ID", validators=[DataRequired(), Email()])
    submit = SubmitField("Send Reset Link")


class ResetPasswordForm(FlaskForm):
    password = PasswordField(
        "New Password",
        validators=[DataRequired(), Length(min=8, message="Password must be at least 8 characters.")],
    )
    confirm_password = PasswordField(
        "Confirm New Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    submit = SubmitField("Reset Password")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current Password", validators=[DataRequired()])
    new_password = PasswordField(
        "New Password",
        validators=[DataRequired(), Length(min=8, message="Password must be at least 8 characters.")],
    )
    confirm_password = PasswordField(
        "Confirm New Password",
        validators=[DataRequired(), EqualTo("new_password", message="Passwords must match.")],
    )
    submit = SubmitField("Change Password")


# ---------------------------------------------------------------------------
# User Master form
# ---------------------------------------------------------------------------
class UserForm(FlaskForm):
    employee_code = StringField("Employee ID", validators=[DataRequired(), Length(max=20)])
    name = StringField("Employee Name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email ID", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField(
        "Password",
        validators=[Optional(), Length(min=8, message="Password must be at least 8 characters.")],
    )
    mobile_number = StringField(
        "Mobile Number", validators=[DataRequired(), Regexp(MOBILE_REGEX, message="Enter a valid mobile number.")]
    )
    grade = SelectField("Grade", choices=GRADE_CHOICES, validators=[DataRequired()])
    gender = SelectField("Gender", choices=GENDER_CHOICES, validators=[DataRequired()])
    hod_name = StringField("HOD Name", validators=[Optional(), Length(max=120)])
    hod_email = StringField("HOD Email ID", validators=[Optional(), Email(), Length(max=120)])
    roles = MultiCheckboxField("Role(s)", choices=ROLE_CHOICES, validators=[DataRequired()])
    is_active_user = BooleanField("Active", default=True)
    submit = SubmitField("Save User")


# ---------------------------------------------------------------------------
# Guest House Master form
# ---------------------------------------------------------------------------
class GuestHouseForm(FlaskForm):
    city = StringField("City", validators=[DataRequired(), Length(max=80)])
    name = StringField("Guest House Name", validators=[DataRequired(), Length(max=150)])
    address = TextAreaField("Address", validators=[DataRequired()])
    pincode = StringField("Pincode", validators=[DataRequired(), Regexp(PINCODE_REGEX, message="Enter a valid pincode.")])
    number_of_rooms = IntegerField("Number of Rooms", validators=[DataRequired(), NumberRange(min=1, max=500)])
    capacity_per_room = IntegerField("Capacity per Room", validators=[DataRequired(), NumberRange(min=1, max=10)])
    gender_accommodated = MultiCheckboxField(
        "Gender Accommodated", choices=GENDER_CHOICES, validators=[DataRequired()]
    )
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save Guest House")


# ---------------------------------------------------------------------------
# Room Master form
# ---------------------------------------------------------------------------
class RoomForm(FlaskForm):
    room_number = StringField("Room Number", validators=[DataRequired(), Length(max=20)])
    capacity = IntegerField("Capacity", validators=[DataRequired(), NumberRange(min=1, max=10)])
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save Room")


# ---------------------------------------------------------------------------
# Booking forms
# ---------------------------------------------------------------------------
class AvailabilityCheckForm(FlaskForm):
    city = SelectField("City", validators=[DataRequired()])
    guest_house_id = SelectField("Guest House", validators=[DataRequired()], coerce=int)
    check_in_date = DateField("Check-in Date", validators=[DataRequired()], format="%Y-%m-%d")
    check_out_date = DateField("Check-out Date", validators=[DataRequired()], format="%Y-%m-%d")
    purpose_of_visit = TextAreaField("Purpose of Visit", validators=[DataRequired(), Length(max=500)])
    remarks = TextAreaField("Remarks", validators=[Optional(), Length(max=500)])
    submit_check = SubmitField("Check Availability")
    submit_booking = SubmitField("Submit Booking Request")

    def validate_check_out_date(self, field):
        if self.check_in_date.data and field.data:
            if field.data <= self.check_in_date.data:
                raise ValidationError("Check-out date must be after check-in date.")

    def validate_check_in_date(self, field):
        if field.data and field.data < date.today():
            raise ValidationError("You cannot book a past date.")


class CancelBookingForm(FlaskForm):
    cancellation_reason = TextAreaField(
        "Cancellation Reason", validators=[DataRequired(), Length(max=500)]
    )
    submit = SubmitField("Cancel Booking")


class HODRejectForm(FlaskForm):
    rejection_reason = TextAreaField(
        "Rejection Reason", validators=[DataRequired(), Length(max=500)]
    )
    submit = SubmitField("Reject")


class AdminCancelForm(FlaskForm):
    reason = TextAreaField("Reason for Cancellation/Modification", validators=[DataRequired(), Length(max=500)])
    submit = SubmitField("Cancel Booking")


class ReportFilterForm(FlaskForm):
    from_date = DateField("From Date", validators=[Optional()], format="%Y-%m-%d")
    to_date = DateField("To Date", validators=[Optional()], format="%Y-%m-%d")
    city = StringField("City", validators=[Optional()])
    guest_house_id = SelectField("Guest House", validators=[Optional()], coerce=int)
    employee_email = StringField("Employee Email", validators=[Optional()])
    status = SelectField(
        "Status",
        choices=[("", "All")] + [(s, s) for s in
            ["Pending HOD Approval", "Approved", "Rejected", "Confirmed",
             "Cancellation Requested", "Cancelled"]],
        validators=[Optional()],
    )
    report_type = SelectField(
        "Report Type",
        choices=[
            ("date_wise", "Date-wise Booking Report"),
            ("city_wise", "City-wise Booking Report"),
            ("guesthouse_occupancy", "Guest House-wise Occupancy Report"),
            ("employee_history", "Employee-wise Booking History"),
            ("cancelled", "Cancelled Booking Report"),
            ("pending_approval", "Pending Approval Report"),
        ],
    )
    submit = SubmitField("Generate Report")
    export = SubmitField("Export to Excel")
