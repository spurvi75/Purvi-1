"""
PDF generation for booking confirmations, using ReportLab (pure Python,
no system dependencies, works reliably in any environment).
"""

import io

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def generate_booking_confirmation_pdf(booking, company_name="Axis Solutions Ltd."):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=20 * mm, bottomMargin=20 * mm, leftMargin=20 * mm, rightMargin=20 * mm
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleStyle", parent=styles["Title"], fontSize=18, textColor=colors.HexColor("#0d2c54")
    )
    sub_style = ParagraphStyle("SubStyle", parent=styles["Normal"], fontSize=11, textColor=colors.grey)
    section_style = ParagraphStyle(
        "SectionStyle", parent=styles["Heading2"], fontSize=12, textColor=colors.HexColor("#0d2c54")
    )

    elements = []
    elements.append(Paragraph(company_name, title_style))
    elements.append(Paragraph("Guest House Booking Confirmation", sub_style))
    elements.append(Spacer(1, 10 * mm))

    data = [
        ["Booking No.", booking.booking_number],
        ["Employee Name", booking.employee_name],
        ["Employee ID", str(booking.employee_id)],
        ["Mobile Number", booking.mobile_number],
        ["City", booking.city],
        ["Guest House", booking.guest_house_name],
        ["Address", f"{booking.guest_house.address}, {booking.guest_house.pincode}"],
        ["Room Number", booking.room_number],
        ["Check-in Date", booking.check_in_date.strftime("%d-%b-%Y")],
        ["Check-out Date", booking.check_out_date.strftime("%d-%b-%Y")],
        ["Purpose of Visit", booking.purpose_of_visit],
        ["Approved By (HOD)", booking.hod_email or "-"],
        ["Approval Date", booking.hod_approval_date.strftime("%d-%b-%Y %H:%M") if booking.hod_approval_date else "-"],
        ["Status", booking.booking_status],
    ]

    table = Table(data, colWidths=[55 * mm, 105 * mm])
    table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef2f7")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bbbbbb")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 10 * mm))

    elements.append(Paragraph("Important Instructions", section_style))
    instructions = [
        "Please carry a valid Company ID card during your stay.",
        "Check-in / check-out timings are as per guest house policy.",
        "Any damage to guest house property will be billed to the employee.",
        "This confirmation must be presented at the guest house reception.",
        "For any issues, contact the Admin department.",
    ]
    for instr in instructions:
        elements.append(Paragraph(f"&bull; {instr}", styles["Normal"]))

    doc.build(elements)
    buffer.seek(0)
    return buffer
