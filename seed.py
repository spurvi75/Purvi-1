"""
Seed script - creates database tables and inserts sample data so the
application can be tested immediately:

    python seed.py

This creates:
  - 1 Admin user
  - 1 HOD user
  - 2 Employee users (one Grade C male, one Grade A female) reporting to the HOD
  - 2 Guest Houses (with rooms auto-created) in two different cities

Default test passwords are printed at the end. Change them after first login
in a real deployment.
"""

from app import create_app
from app.extensions import db
from app.models import User, GuestHouse, Room

app = create_app()

with app.app_context():
    db.create_all()

    if User.query.filter_by(email="admin@axisindia.in").first() is None:
        admin = User(
            employee_code="EMP0001",
            name="System Administrator",
            email="admin@axisindia.in",
            mobile_number="9876500001",
            grade="A",
            gender="Male",
            roles="Admin",
            is_active_user=True,
        )
        admin.set_password("Admin@123")
        db.session.add(admin)

    if User.query.filter_by(email="hod@axisindia.in").first() is None:
        hod = User(
            employee_code="EMP0002",
            name="Rajesh Kumar (HOD)",
            email="hod@axisindia.in",
            mobile_number="9876500002",
            grade="A",
            gender="Male",
            roles="HOD",
            is_active_user=True,
        )
        hod.set_password("Hod@1234")
        db.session.add(hod)

    db.session.commit()

    if User.query.filter_by(email="employee1@axisindia.in").first() is None:
        emp1 = User(
            employee_code="EMP0003",
            name="Suresh Patel",
            email="employee1@axisindia.in",
            mobile_number="9876500003",
            grade="C",
            gender="Male",
            hod_name="Rajesh Kumar",
            hod_email="hod@axisindia.in",
            roles="Employee",
            is_active_user=True,
        )
        emp1.set_password("Employee@123")
        db.session.add(emp1)

    if User.query.filter_by(email="employee2@axisindia.in").first() is None:
        emp2 = User(
            employee_code="EMP0004",
            name="Priya Sharma",
            email="employee2@axisindia.in",
            mobile_number="9876500004",
            grade="A",
            gender="Female",
            hod_name="Rajesh Kumar",
            hod_email="hod@axisindia.in",
            roles="Employee",
            is_active_user=True,
        )
        emp2.set_password("Employee@123")
        db.session.add(emp2)

    db.session.commit()

    if GuestHouse.query.filter_by(name="Axis Ahmedabad Guest House").first() is None:
        gh1 = GuestHouse(
            city="Ahmedabad",
            name="Axis Ahmedabad Guest House",
            address="Plot 12, GIDC Estate, Ahmedabad",
            pincode="380015",
            number_of_rooms=3,
            capacity_per_room=2,
            gender_accommodated="Male,Female",
            is_active=True,
        )
        db.session.add(gh1)
        db.session.commit()
        for i in range(1, 4):
            db.session.add(Room(guest_house_id=gh1.id, room_number=f"R{i:03d}",
                                 capacity=2, is_active=True))

    if GuestHouse.query.filter_by(name="Axis Mumbai Guest House").first() is None:
        gh2 = GuestHouse(
            city="Mumbai",
            name="Axis Mumbai Guest House",
            address="Tower B, Andheri East, Mumbai",
            pincode="400069",
            number_of_rooms=2,
            capacity_per_room=2,
            gender_accommodated="Male",
            is_active=True,
        )
        db.session.add(gh2)
        db.session.commit()
        for i in range(1, 3):
            db.session.add(Room(guest_house_id=gh2.id, room_number=f"R{i:03d}",
                                 capacity=2, is_active=True))

    db.session.commit()

print("Database initialized with sample data.")
print("-" * 60)
print("Default test users (change passwords after first login):")
print("  Admin     : admin@axisindia.in     / Admin@123")
print("  HOD       : hod@axisindia.in       / Hod@1234")
print("  Employee 1: employee1@axisindia.in / Employee@123  (Male, Grade C)")
print("  Employee 2: employee2@axisindia.in / Employee@123  (Female, Grade A)")
print("-" * 60)
print("Sample Guest Houses: Axis Ahmedabad Guest House (Male+Female, 3 rooms),")
print("                     Axis Mumbai Guest House (Male only, 2 rooms)")
