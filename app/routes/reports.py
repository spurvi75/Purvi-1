"""
Admin reports: date-wise, city-wise, guest house occupancy, employee
history, cancelled bookings, pending approvals - with filters and Excel
export.
"""

from flask import Blueprint, render_template, request, send_file
from flask_login import login_required

from app.models import Booking, BookingStatus, GuestHouse
from app.forms import ReportFilterForm
from app.utils.decorators import roles_required
from app.utils.export_utils import export_bookings_to_excel

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


@reports_bp.before_request
@login_required
@roles_required("Admin")
def restrict_to_admin():
    pass


def _apply_filters(query, form):
    if form.from_date.data:
        query = query.filter(Booking.check_in_date >= form.from_date.data)
    if form.to_date.data:
        query = query.filter(Booking.check_out_date <= form.to_date.data)
    if form.city.data:
        query = query.filter(Booking.city.ilike(f"%{form.city.data.strip()}%"))
    if form.guest_house_id.data:
        query = query.filter(Booking.guest_house_id == form.guest_house_id.data)
    if form.employee_email.data:
        query = query.filter(Booking.employee_email.ilike(f"%{form.employee_email.data.strip()}%"))
    if form.status.data:
        query = query.filter(Booking.booking_status == form.status.data)
    return query


def _report_specific_query(report_type, query):
    if report_type == "cancelled":
        query = query.filter(Booking.booking_status.in_(
            [BookingStatus.CANCELLED, BookingStatus.REJECTED]))
    elif report_type == "pending_approval":
        query = query.filter(Booking.booking_status == BookingStatus.PENDING_HOD_APPROVAL)
    return query


@reports_bp.route("/", methods=["GET", "POST"])
def index():
    form = ReportFilterForm()
    form.guest_house_id.choices = [(0, "All Guest Houses")] + [
        (gh.id, f"{gh.name} ({gh.city})") for gh in GuestHouse.query.order_by(GuestHouse.name).all()
    ]
    if not form.report_type.data:
        form.report_type.data = "date_wise"

    bookings = []
    generated = False

    if request.method == "POST" and form.validate_on_submit():
        query = Booking.query
        query = _apply_filters(query, form)
        query = _report_specific_query(form.report_type.data, query)
        bookings = query.order_by(Booking.check_in_date.desc()).all()
        generated = True

        if form.export.data:
            buffer = export_bookings_to_excel(
                bookings, title=dict(form.report_type.choices).get(form.report_type.data, "Booking Report")
            )
            return send_file(
                buffer, as_attachment=True, download_name="axis_guesthouse_report.xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    return render_template("reports/reports.html", form=form, bookings=bookings, generated=generated)
