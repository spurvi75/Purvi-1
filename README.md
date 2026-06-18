# Axis Solutions Ltd – Guest House Booking System

A complete, production-quality Flask web application for managing internal
company guest house bookings, with role-based access for **Admin**,
**Employee**, and **HOD/Approver**, full room-level availability logic
(gender separation, Grade A/B single-occupancy, capacity sharing, date
overlap), HOD approval workflow, email notifications, printable/PDF booking
confirmations, and Excel-exportable reports.

---

## 1. Technology Stack

- **Python 3.10+** / **Flask 3** (application factory pattern, blueprints)
- **Flask-SQLAlchemy** — ORM, works with SQLite out of the box and can be
  pointed at PostgreSQL/MySQL by changing one environment variable
- **Flask-Login** — session-based authentication
- **Flask-WTF / WTForms** — forms + CSRF protection
- **Flask-Mail** — email notifications (SMTP configurable, or suppressed
  for local dev)
- **openpyxl** — Excel report export
- **ReportLab** — PDF booking confirmation generation
- **Bootstrap 5 + Font Awesome 6** (via CDN) — responsive, professional UI

---

## 2. Folder Structure

```
axis_guesthouse/
├── app/
│   ├── __init__.py            # Application factory, blueprint registration
│   ├── extensions.py          # db, login_manager, csrf, mail singletons
│   ├── models.py              # User, GuestHouse, Room, Booking, etc.
│   ├── forms.py                # All WTForms forms
│   ├── routes/
│   │   ├── auth.py            # login / logout / forgot / reset / change password
│   │   ├── admin.py           # Guest House / Room / User masters, bookings, audit log
│   │   ├── employee.py        # Booking flow, my bookings, cancellation, confirmation
│   │   ├── hod.py             # Pending / approved / rejected approvals
│   │   └── reports.py         # Filtered reports + Excel export
│   ├── utils/
│   │   ├── availability.py    # << CORE room availability & allocation logic >>
│   │   ├── decorators.py      # roles_required() RBAC decorator
│   │   ├── email_utils.py     # All outgoing email templates/sending
│   │   ├── pdf_utils.py       # Booking confirmation PDF generation
│   │   ├── export_utils.py    # Excel report export
│   │   └── helpers.py         # Booking number generator
│   ├── templates/             # Jinja2 templates (auth/admin/employee/hod/reports)
│   └── static/css/style.css   # Axis branding stylesheet
├── config.py                  # Environment-driven configuration
├── run.py                     # App entry point
├── seed.py                    # Creates DB + sample test data
├── requirements.txt
├── .env.example
└── README.md                  # (this file)
```

---

## 3. Installation

```bash
# 1. Create and activate a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
# Edit .env with your SECRET_KEY, SMTP credentials, etc.
```

---

## 4. Create the Database & First Admin User

The `seed.py` script creates all database tables and inserts ready-to-use
sample data (1 Admin, 1 HOD, 2 Employees, 2 Guest Houses with rooms):

```bash
python seed.py
```

You should see output confirming the created users. If you'd rather start
with a completely empty database and create your own Admin manually, you
can instead run:

```bash
python -c "
from app import create_app
from app.extensions import db
from app.models import User
app = create_app()
with app.app_context():
    db.create_all()
    admin = User(employee_code='EMP0001', name='Admin', email='admin@axisindia.in',
                 mobile_number='9999999999', grade='A', gender='Male', roles='Admin')
    admin.set_password('ChangeMe@123')
    db.session.add(admin)
    db.session.commit()
    print('Admin created.')
"
```

---

## 5. Run the Application

```bash
python run.py
```

The app will be available at **http://127.0.0.1:5000**. You'll be
redirected to the login page automatically.

For production, run behind a proper WSGI server, e.g.:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 "run:app"
```

---

## 6. Default Test Users (created by seed.py)

| Role     | Email                       | Password       | Notes                       |
|----------|------------------------------|-----------------|------------------------------|
| Admin    | admin@axisindia.in           | Admin@123        |                              |
| HOD      | hod@axisindia.in             | Hod@1234         | Approves both employees below |
| Employee | employee1@axisindia.in       | Employee@123     | Male, Grade C (room sharing) |
| Employee | employee2@axisindia.in       | Employee@123     | Female, Grade A (single occupancy) |

**Please change these passwords immediately in any real deployment**
(use Change Password after logging in, or edit users via Admin → User Master).

---

## 7. Sample Guest House Data (created by seed.py)

| Guest House                  | City      | Rooms | Capacity/Room | Gender Accommodated |
|-------------------------------|-----------|-------|-----------------|------------------------|
| Axis Ahmedabad Guest House    | Ahmedabad | 3     | 2               | Male, Female           |
| Axis Mumbai Guest House       | Mumbai    | 2     | 2               | Male only               |

Rooms are auto-named `R001`, `R002`, ... and are auto-created whenever a
guest house is added (whether via `seed.py` or via Admin → Guest House
Master → Add Guest House, which creates rooms according to "Number of
Rooms").

---

## 8. Sample Booking Flow (walkthrough)

1. **Login** as `employee1@axisindia.in` / `Employee@123`.
2. Go to **Book Guest House**. Select **City = Ahmedabad** (the guest house
   dropdown refreshes automatically), then **Guest House = Axis Ahmedabad
   Guest House**.
3. Pick check-in/check-out dates (today or later) and enter a purpose of
   visit.
4. Click **Check Availability**. The system runs the full rule engine
   (gender match, Grade A/B exclusivity, gender separation, capacity) and
   shows the first suitable room, e.g. `R001`.
5. Click **Submit Booking Request**. The booking is created with status
   **Pending HOD Approval**, a booking number such as `AXIS-GH-2026-0001`
   is generated, and an email is sent to the employee's configured HOD.
6. **Logout**, then **login** as `hod@axisindia.in` / `Hod@1234`.
7. Go to **HOD Dashboard → Pending Approvals**. You'll see the new request.
   Click **Approve** (or open the request and **Reject** with a mandatory
   reason).
8. On approval: booking status becomes **Confirmed**, the employee gets a
   confirmation email, and the Admin notification email address (see
   `ADMIN_NOTIFICATION_EMAIL` in config) gets the full booking details.
9. **Login** again as the employee → **My Bookings** → the booking now
   shows **Confirmed** with a **Print** icon, which opens an HTML
   print-friendly confirmation page with a **Download PDF** button.
10. To test cancellation, click the **Cancel** icon on any
    Pending/Approved/Confirmed booking, enter a mandatory reason — the
    booking becomes **Cancelled** and the room is immediately available
    again for other employees.

### Testing the core availability rules

- **Gender separation**: log in as `employee2@axisindia.in` (Female, Grade
  A) and check availability for the same guest house/dates used above —
  she will be allocated a *different* room than the male employee
  (`R001` is occupied by a Male, so she gets `R002`).
- **Grade A/B single occupancy**: because `employee2` is Grade A, her room
  is then fully blocked for anyone else for those dates — no other
  employee (male or female) can be added to that room for an overlapping
  date range.
- **Capacity sharing**: log in as `employee1` again and check availability
  for the *same* dates/guest house — since `R001`'s capacity is 2 and
  currently holds 1 Male/Grade-C occupant, a second Male non-A/B employee
  can share it (allocated `R001` again).
- **Guest house gender restriction**: try booking the Mumbai guest house
  (Male only) as `employee2` (Female) — the system will correctly refuse
  with "This guest house does not accommodate Female employees."

All of the above rules were verified end-to-end during development by
running the live application and exercising each scenario via the actual
HTTP routes.

---

## 9. Configuring Email (SMTP)

All email settings are environment variables (see `.env.example`), read by
`config.py`:

```
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-smtp-username@example.com
MAIL_PASSWORD=your-smtp-app-password
MAIL_DEFAULT_SENDER=noreply@axisindia.in
MAIL_SUPPRESS_SEND=True
```

By default, `MAIL_SUPPRESS_SEND=True`, which means no real emails are sent
— Flask-Mail silently no-ops the send (useful so you can demo the whole
app without any SMTP server). Set it to `False` and fill in real SMTP
credentials to actually deliver:

- Forgot Password reset links
- Booking submitted → HOD notification
- HOD approval → employee confirmation + Admin notification
- HOD rejection → employee notification
- Cancellation → Admin + HOD notification

---

## 10. Switching from SQLite to PostgreSQL / MySQL

No code changes are required. Just set the `DATABASE_URL` environment
variable before running the app (and re-run `seed.py` or your own
table-creation step against the new database):

```bash
# PostgreSQL
export DATABASE_URL="postgresql://user:password@localhost:5432/axis_guesthouse"
pip install psycopg2-binary

# MySQL
export DATABASE_URL="mysql+pymysql://user:password@localhost:3306/axis_guesthouse"
pip install pymysql
```

Then:
```bash
python seed.py     # creates tables + sample data in the new database
python run.py
```

---

## 11. Role-Based Access Summary

| Area                          | Admin | HOD | Employee |
|--------------------------------|-------|-----|----------|
| Guest House / Room / User Master | ✅ | ❌ | ❌ |
| View all bookings, manual cancel | ✅ | ❌ | ❌ |
| Reports + Excel export          | ✅ | ❌ | ❌ |
| Audit Log                       | ✅ | ❌ | ❌ |
| Approve / Reject requests       | ❌ | ✅ (only requests routed to them) | ❌ |
| Book a guest house for self     | ✅ | ✅ | ✅ |
| View / cancel own bookings      | ✅ | ✅ | ✅ |

One user can hold multiple roles (e.g. `"Admin,HOD"` in the `roles` field),
and the navigation bar / access control adapts automatically.

---

## 12. Core Booking Rule Engine (`app/utils/availability.py`)

This is the most important part of the application, implementing every
rule from the specification:

1. Only bookings with status **Pending HOD Approval**, **Approved**, or
   **Confirmed** are considered "active" and block a room. Rejected and
   Cancelled bookings are ignored.
2. **Date overlap**: `existing.check_in < requested.check_out AND
   existing.check_out > requested.check_in`.
3. **Guest house gender rule**: the guest house's "Gender Accommodated"
   must include the employee's gender, or booking is refused outright.
4. **Grade A/B single occupancy**: a Grade A/B employee can only be
   allocated a room with zero overlapping occupants, and once allocated,
   that room is fully blocked from anyone else for the overlapping dates.
5. **Gender separation**: a room's overlapping occupants must all share
   the same gender — Male and Female are never mixed in the same room for
   overlapping dates.
6. **Capacity check**: for ordinary (non A/B) bookings, the number of
   overlapping occupants in a room must remain below the room's capacity.
7. **Room selection**: the first suitable *active* room in the guest
   house, ordered by room number, is allocated.

All of the above is unit-testable in isolation via
`check_availability(guest_house_id, gender, grade, check_in, check_out)`,
which is also re-verified server-side at the moment of final submission
(not just at "Check Availability" time) to defend against stale/duplicate
requests.

---

## 13. Extra Features Included

- Search/filter on Guest House, Room, and User master list pages
- Excel export for all report types (date-wise, city-wise, guest house
  occupancy, employee history, cancelled, pending approval)
- Audit log of every Admin master-data change (create/update/
  activate/deactivate/delete) and manual booking cancellation
- Room-level booking history page (Admin → Guest Houses → Rooms → History)
- Dashboard cards: active guest houses, active rooms, today's check-ins,
  today's check-outs, pending HOD approvals, confirmed bookings
- Admin remarks field captured on manual cancellations
- Auto-generated booking numbers, e.g. `AXIS-GH-2026-0001`
- Fully responsive Bootstrap 5 layout

---

## 14. Security Notes

- Passwords are hashed with Werkzeug's `generate_password_hash` /
  `check_password_hash` — never stored in plain text.
- All forms are CSRF-protected via Flask-WTF; raw (non-WTForms) action
  buttons include a manually-rendered `csrf_token` hidden field.
- Role-based access is enforced server-side via the `roles_required()`
  decorator on every blueprint (`before_request` + `@login_required` +
  `@roles_required(...)`), not just hidden in the UI.
- Password reset tokens are single-use and expire after
  `PASSWORD_RESET_EXPIRY_MINUTES` (default 30).
- Only active users can log in; only active guest houses/rooms are
  offered for booking.
- Employees can only view/cancel their own bookings; HODs can only act on
  requests routed to their own email.

---

## 15. Known Simplifications / Notes for Further Hardening

- Room numbers are auto-generated as `R001`, `R002`, ... when a guest
  house is created; editing "Number of Rooms" afterwards does **not**
  automatically add/remove rooms — manage rooms individually via Room
  Master for that guest house.
- The booking number sequence counts existing rows per year; for very high
  concurrent write volume in production, consider a dedicated DB sequence
  to fully eliminate any (very unlikely) race condition.
- `MAIL_SUPPRESS_SEND=True` by default so the app can be demoed/tested
  without a real SMTP server — flip it to `False` with real credentials
  before going live.
