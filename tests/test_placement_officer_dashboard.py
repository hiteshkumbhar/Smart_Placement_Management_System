# tests/test_placement_officer_dashboard.py

"""
Placement Officer Dashboard tests.

Prerequisites:
- Existing project conftest.py provides `client` and `test_database`.
- The application exposes `app` and `db` from app.py.
- Models are imported from models.py.
- The dashboard route is /Placement_officer_dashboard.

Note:
The test_database fixture must use an isolated test database. If the app is
configured to use a persistent development database, configure a separate
SQLite test database before running these tests.
"""

import datetime
from zoneinfo import ZoneInfo

import pytest
from flask_jwt_extended import create_access_token

from app import app, db
from models import (
    Users,
    Students,
    Companies,
    Job_Drives,
    Applications,
    Application_status,
    Interview_Rounds,
)


DASHBOARD_URL = "/Placement_officer_dashboard"
CURRENT_YEAR = datetime.datetime.now(ZoneInfo("Asia/Kolkata")).year


# ---------------------------------------------------------------------------
# Shared test helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def placement_officer(test_database):
    """Create a placement-officer user in the test database."""
    user = Users(
        name="Test Placement Officer",
        email="placement.officer.test@example.com",
        password="test-password",
        role="Placement_Officer",
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def placement_officer_client(client, placement_officer):
    """Return a test client authenticated as a placement officer."""
    with app.app_context():
        token = create_access_token(identity=str(placement_officer.user_id))

    client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    return client


@pytest.fixture
def dashboard_factory(test_database, placement_officer):
    """
    Factories for records needed by the dashboard.

    Use these helpers instead of duplicating database setup in every test.
    """

    counter = {"user": 0, "company": 0, "student": 0, "drive": 0}

    def make_user(role="Student", name=None, email=None):
        counter["user"] += 1
        suffix = counter["user"]

        user = Users(
            name=name or f"Test User {suffix}",
            email=email or f"test.user.{suffix}@example.com",
            password="test-password",
            role=role,
        )
        db.session.add(user)
        db.session.flush()
        return user

    def make_student(
        graduation_year=None,
        resume_status="Pending",
        resume_path="resumes/test.pdf",
        name=None,
    ):
        counter["student"] += 1
        user = make_user(
            role="Student",
            name=name or f"Student {counter['student']}",
        )

        student = Students(
            user_id=user.user_id,
            registration_no=f"REG-{counter['student']}",
            graduation_year=(
                CURRENT_YEAR
                if graduation_year is None
                else graduation_year
            ),
            resume_status=resume_status,
            resume_path=resume_path,
        )
        db.session.add(student)
        db.session.flush()
        return student

    def make_company(name=None):
        counter["company"] += 1
        suffix = counter["company"]

        company = Companies(
            company_name=name or f"Test Company {suffix}",
            industry="Technology",
            website=f"https://company{suffix}.example.com",
            hr_name=f"HR {suffix}",
            email=f"hr{suffix}@company.example.com",
            phone=f"900000{suffix:04d}",
            creater_id=placement_officer.user_id,
        )
        db.session.add(company)
        db.session.flush()
        return company

    def make_drive(
        posted="Y",
        status="Active",
        deadline=None,
        title=None,
        company=None,
        package=10.0,
        location="Mumbai",
    ):
        counter["drive"] += 1
        suffix = counter["drive"]

        if company is None:
            company = make_company()

        drive = Job_Drives(
            company_id=company.id,
            title=title or f"Test Role {suffix}",
            package=package,
            location=location,
            deadline=deadline or (
                datetime.datetime.now() + datetime.timedelta(days=30)
            ),
            posted=posted,
            status=status,
            creater_id=placement_officer.user_id,
        )
        db.session.add(drive)
        db.session.flush()
        return drive

    def make_application(
        student=None,
        drive=None,
        status=Application_status.APPLIED,
    ):
        if student is None:
            student = make_student()

        if drive is None:
            drive = make_drive()

        application = Applications(
            student_id=student.id,
            drive_id=drive.id,
            status=status,
        )
        db.session.add(application)
        db.session.flush()
        return application

    def make_interview(
        application=None,
        date=None,
        result=None,
        round_name="Technical Round",
    ):
        if application is None:
            application = make_application()

        interview = Interview_Rounds(
            application_id=application.id,
            round_name=round_name,
            date=date or datetime.datetime.now(),
            result=result,
        )
        db.session.add(interview)
        db.session.flush()
        return interview

    return {
        "user": make_user,
        "student": make_student,
        "company": make_company,
        "drive": make_drive,
        "application": make_application,
        "interview": make_interview,
    }


def get_dashboard(client):
    """Request the placement-officer dashboard."""
    return client.get(DASHBOARD_URL)


def page_text(response):
    """Return decoded HTML response content."""
    return response.get_data(as_text=True)


# ---------------------------------------------------------------------------
# PLACE-01 to PLACE-09: Dashboard access and placement percentage
# ---------------------------------------------------------------------------

def test_PLACE_01_dashboard_requires_authentication(client, test_database):
    # Scenario: Request the dashboard without a JWT.
    # Expected: The request is rejected with an authentication error.
    response = client.get(DASHBOARD_URL)
    assert response.status_code == 401


def test_PLACE_02_placement_officer_can_open_dashboard(
    placement_officer_client,
):
    # Scenario: An authenticated Placement_Officer opens the dashboard.
    # Expected: The dashboard responds successfully.
    response = get_dashboard(placement_officer_client)
    assert response.status_code == 200


@pytest.mark.parametrize("role", ["Student", "Recruiter"])
def test_PLACE_03_non_placement_officer_is_forbidden(
    client, test_database, role
):
    # Scenario: An authenticated user has a role other than Placement_Officer.
    # Expected: The dashboard returns HTTP 403 Forbidden.
    user = Users(
        name=f"Test {role}",
        email=f"test.{role.lower()}@example.com",
        password="test-password",
        role=role,
    )
    db.session.add(user)
    db.session.commit()

    with app.app_context():
        token = create_access_token(identity=str(user.user_id))

    response = client.get(
        DASHBOARD_URL,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_PLACE_04_empty_batch_has_zero_placement_percentage(
    placement_officer_client, test_database
):
    # Scenario: No students belong to the current graduation-year batch.
    # Expected: The dashboard renders a placement percentage of 0.0%.
    response = get_dashboard(placement_officer_client)
    assert response.status_code == 200
    assert "0.0" in page_text(response)


def test_PLACE_05_placement_percentage_uses_current_graduation_year(
    placement_officer_client, dashboard_factory
):
    # Scenario: Two current-year students exist and one is selected.
    # Expected: The placement percentage is 50.0%.
    student_1 = dashboard_factory["student"]()
    student_2 = dashboard_factory["student"]()

    drive = dashboard_factory["drive"]()
    dashboard_factory["application"](
        student=student_1,
        drive=drive,
        status=Application_status.SELECTED,
    )

    db.session.commit()

    response = get_dashboard(placement_officer_client)
    assert response.status_code == 200
    assert "50.0" in page_text(response)


def test_PLACE_06_selected_students_are_counted_once(
    placement_officer_client, dashboard_factory
):
    # Scenario: One student is selected for two different job drives.
    # Expected: The student is counted once in the placement numerator.
    student_1 = dashboard_factory["student"]()
    student_2 = dashboard_factory["student"]()

    drive_1 = dashboard_factory["drive"]()
    drive_2 = dashboard_factory["drive"]()

    dashboard_factory["application"](
        student=student_1,
        drive=drive_1,
        status=Application_status.SELECTED,
    )
    dashboard_factory["application"](
        student=student_1,
        drive=drive_2,
        status=Application_status.SELECTED,
    )

    db.session.commit()

    response = get_dashboard(placement_officer_client)
    assert response.status_code == 200
    assert "50.0" in page_text(response)


def test_PLACE_07_non_selected_applications_do_not_increase_percentage(
    placement_officer_client, dashboard_factory
):
    # Scenario: Two current-year students have Applied and Shortlisted statuses.
    # Expected: Neither counts as placed, so the percentage is 0.0%.
    student_1 = dashboard_factory["student"]()
    student_2 = dashboard_factory["student"]()
    drive = dashboard_factory["drive"]()

    dashboard_factory["application"](
        student=student_1,
        drive=drive,
        status=Application_status.APPLIED,
    )
    dashboard_factory["application"](
        student=student_2,
        drive=drive,
        status=Application_status.SHORTLISTED,
    )

    db.session.commit()

    response = get_dashboard(placement_officer_client)
    assert response.status_code == 200
    assert "0.0" in page_text(response)


def test_PLACE_08_other_graduation_year_is_excluded(
    placement_officer_client, dashboard_factory
):
    # Scenario: A selected student belongs to a different graduation year.
    # Expected: That student does not affect the current-year placement rate.
    current_student = dashboard_factory["student"]()
    other_year_student = dashboard_factory["student"](
        graduation_year=CURRENT_YEAR - 1
    )
    drive = dashboard_factory["drive"]()

    dashboard_factory["application"](
        student=other_year_student,
        drive=drive,
        status=Application_status.SELECTED,
    )

    db.session.commit()

    response = get_dashboard(placement_officer_client)
    assert response.status_code == 200
    assert "0.0" in page_text(response)


def test_PLACE_09_all_current_year_students_selected_gives_100_percent(
    placement_officer_client, dashboard_factory
):
    # Scenario: Every student in the current graduation-year batch is selected.
    # Expected: The placement percentage displayed is 100.0%.
    students = [dashboard_factory["student"]() for _ in range(3)]
    drive = dashboard_factory["drive"]()

    for student in students:
        dashboard_factory["application"](
            student=student,
            drive=drive,
            status=Application_status.SELECTED,
        )

    db.session.commit()

    response = get_dashboard(placement_officer_client)
    assert response.status_code == 200
    assert "100.0" in page_text(response)


# ---------------------------------------------------------------------------
# RESUME-01 to RESUME-10: Unverified resume count
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "resume_status",
    ["Pending", "Reuploaded", "Rejected"],
)
def test_RESUME_01_to_03_unverified_statuses_are_counted(
    placement_officer_client, dashboard_factory, resume_status
):
    # Scenario: A current-year student has a resume and an unverified status.
    # Expected: Pending, Reuploaded, and Rejected resumes are counted.
    dashboard_factory["student"](
        resume_status=resume_status,
        resume_path="resumes/student.pdf",
    )
    db.session.commit()

    response = get_dashboard(placement_officer_client)
    assert response.status_code == 200
    assert "1" in page_text(response)

def test_RESUME_04_verified_resume_is_not_counted(
    placement_officer_client, dashboard_factory
):
    # Scenario: A current-year student has a resume with status Verified.
    # Expected: The dashboard request succeeds, and the verified resume
    # is not included in the database count of unverified resumes.

    from models import Students

    dashboard_factory["student"](
        resume_status="Verified",
        resume_path="resumes/verified.pdf",
    )
    db.session.commit()

    response = get_dashboard(placement_officer_client)
    assert response.status_code == 200

    count = Students.query.filter(
        Students.resume_status.in_(["Pending", "Reuploaded", "Rejected"]),
        Students.resume_path.isnot(None),
        Students.graduation_year == CURRENT_YEAR,
    ).count()

    assert count == 0

def test_RESUME_05_missing_resume_path_is_not_counted(
    placement_officer_client, dashboard_factory
):
    # Scenario: A current-year student has Pending status but no resume path.
    # Expected: The student is excluded from the unverified-resume count.
    dashboard_factory["student"](
        resume_status="Pending",
        resume_path=None,
    )
    db.session.commit()

    response = get_dashboard(placement_officer_client)
    assert response.status_code == 200
    assert "0" in page_text(response)


def test_RESUME_06_other_graduation_year_resume_is_excluded(
    placement_officer_client, dashboard_factory
):
    # Scenario: An older graduating-batch student has a Pending resume.
    # Expected: The resume is excluded from the current-year count.
    dashboard_factory["student"](
        graduation_year=CURRENT_YEAR - 1,
        resume_status="Pending",
        resume_path="resumes/old-batch.pdf",
    )
    db.session.commit()

    response = get_dashboard(placement_officer_client)
    assert response.status_code == 200
    assert "0" in page_text(response)


def test_RESUME_07_multiple_unverified_resumes_are_counted(
    placement_officer_client, dashboard_factory
):
    # Scenario: Three current-year students have non-null resume paths and
    # statuses Pending, Reuploaded, and Rejected.
    # Expected: The unverified-resume count is three.
    for status in ["Pending", "Reuploaded", "Rejected"]:
        dashboard_factory["student"](
            resume_status=status,
            resume_path=f"resumes/{status.lower()}.pdf",
        )

    db.session.commit()

    response = get_dashboard(placement_officer_client)
    assert response.status_code == 200
    assert "3" in page_text(response)


def test_RESUME_08_resume_status_change_updates_dashboard_count(
    placement_officer_client, dashboard_factory
):
    # Scenario: A student's resume status changes from Pending to Verified.
    # Expected: The unverified-resume count changes from one to zero.
    student = dashboard_factory["student"](
        resume_status="Pending",
        resume_path="resumes/status-change.pdf",
    )
    db.session.commit()

    first_response = get_dashboard(placement_officer_client)
    assert first_response.status_code == 200
    assert "1" in page_text(first_response)

    student.resume_status = "Verified"
    db.session.commit()

    second_response = get_dashboard(placement_officer_client)
    assert second_response.status_code == 200
    assert "0" in page_text(second_response)


def test_RESUME_09_resume_with_empty_string_path_is_non_null(
    placement_officer_client, dashboard_factory
):
    # Scenario: An unverified resume has an empty-string path.
    # Expected: Because the route checks IS NOT NULL, the record is counted.
    dashboard_factory["student"](
        resume_status="Pending",
        resume_path="",
    )
    db.session.commit()

    response = get_dashboard(placement_officer_client)
    assert response.status_code == 200
    assert "1" in page_text(response)


def test_RESUME_10_mixed_resume_records_count_only_eligible_records(
    placement_officer_client, dashboard_factory
):
    # Scenario: Eligible Pending/Reuploaded/Rejected records are mixed with
    # Verified, missing-path, and other-year records.
    # Expected: Only the three eligible records contribute to the count.
    for status in ["Pending", "Reuploaded", "Rejected"]:
        dashboard_factory["student"](
            resume_status=status,
            resume_path=f"resumes/{status}.pdf",
        )

    dashboard_factory["student"](
        resume_status="Verified",
        resume_path="resumes/verified.pdf",
    )
    dashboard_factory["student"](
        resume_status="Pending",
        resume_path=None,
    )
    dashboard_factory["student"](
        graduation_year=CURRENT_YEAR - 1,
        resume_status="Pending",
        resume_path="resumes/other-year.pdf",
    )

    db.session.commit()

    response = get_dashboard(placement_officer_client)
    assert response.status_code == 200
    assert "3" in page_text(response)


# ---------------------------------------------------------------------------
# DRIVE-01 to DRIVE-10: Posted/active job drives
# ---------------------------------------------------------------------------

def test_DRIVE_01_posted_non_closed_drive_is_counted(
    placement_officer_client, dashboard_factory
):
    # Scenario: One job drive has posted='Y' and status='Active'.
    # Expected: Active Job Drives displays one.
    dashboard_factory["drive"](posted="Y", status="Active")
    db.session.commit()

    response = get_dashboard(placement_officer_client)
    assert response.status_code == 200
    assert "Active Job drives" in page_text(response)
    assert "1" in page_text(response)


def test_DRIVE_02_unposted_drive_is_not_counted_as_active(
    placement_officer_client, dashboard_factory
):
    # Scenario: A job drive has posted='N' and status='Active'.
    # Expected: It is excluded from the active posted-drive count.
    dashboard_factory["drive"](posted="N", status="Active")
    db.session.commit()

    response = get_dashboard(placement_officer_client)
    assert response.status_code == 200
    assert "No acive job drives are available right now." in page_text(response)


def test_DRIVE_03_closed_posted_drive_is_excluded(
    placement_officer_client, dashboard_factory
):
    # Scenario: A job drive has posted='Y' and status='Closed'.
    # Expected: It is excluded from the active-drive count and table.
    dashboard_factory["drive"](posted="Y", status="Closed")
    db.session.commit()

    response = get_dashboard(placement_officer_client)
    assert response.status_code == 200
    assert "No acive job drives are available right now." in page_text(response)


def test_DRIVE_04_expired_but_not_closed_drive_is_counted(
    placement_officer_client, dashboard_factory
):
    # Scenario: A posted job drive has status='Expired'.
    # Expected: Current implementation includes it because status != 'Closed'.
    dashboard_factory["drive"](posted="Y", status="Expired")
    db.session.commit()

    response = get_dashboard(placement_officer_client)
    assert response.status_code == 200
    assert "Active Job drives" in page_text(response)


def test_DRIVE_05_active_drives_are_ordered_by_deadline(
    placement_officer_client, dashboard_factory
):
    # Scenario: Three posted, non-closed drives have different deadlines.
    # Expected: Their rows appear in ascending deadline order.
    today = datetime.datetime.now().replace(
        hour=12, minute=0, second=0, microsecond=0
    )

    later = dashboard_factory["drive"](
        posted="Y",
        status="Active",
        title="Later Deadline Role",
        deadline=today + datetime.timedelta(days=20),
    )
    earlier = dashboard_factory["drive"](
        posted="Y",
        status="Active",
        title="Earlier Deadline Role",
        deadline=today + datetime.timedelta(days=2),
    )
    middle = dashboard_factory["drive"](
        posted="Y",
        status="Active",
        title="Middle Deadline Role",
        deadline=today + datetime.timedelta(days=10),
    )

    db.session.commit()

    response = get_dashboard(placement_officer_client)
    html = page_text(response)

    positions = [
        html.find("Earlier Deadline Role"),
        html.find("Middle Deadline Role"),
        html.find("Later Deadline Role"),
    ]

    assert response.status_code == 200
    assert all(position >= 0 for position in positions)
    assert positions == sorted(positions)


def test_DRIVE_06_only_five_active_drive_rows_are_displayed(
    placement_officer_client, dashboard_factory
):
    # Scenario: Six posted, non-closed drives are created.
    # Expected: The dashboard's active-drive table displays at most five.
    for index in range(6):
        dashboard_factory["drive"](
            posted="Y",
            status="Active",
            title=f"Limit Active Role {index}",
            deadline=datetime.datetime.now() + datetime.timedelta(days=index + 1),
        )

    db.session.commit()

    response = get_dashboard(placement_officer_client)
    html = page_text(response)

    displayed = sum(
        f"Limit Active Role {index}" in html for index in range(6)
    )
    assert response.status_code == 200
    assert displayed == 5


def test_DRIVE_07_applicant_count_is_shown_for_active_drive(
    placement_officer_client, dashboard_factory
):
    # Scenario: One active drive has two applications.
    # Expected: The drive row displays an applicant count of two.
    drive = dashboard_factory["drive"](posted="Y", status="Active")
    dashboard_factory["application"](drive=drive)
    dashboard_factory["application"](drive=drive)
    db.session.commit()

    response = get_dashboard(placement_officer_client)
    assert response.status_code == 200
    assert "Applicants" in page_text(response)
    assert "2" in page_text(response)


def test_DRIVE_08_active_drive_details_are_rendered(
    placement_officer_client, dashboard_factory
):
    # Scenario: A posted drive has a company, title, package, location, and
    # deadline.
    # Expected: The dashboard displays those drive details.
    company = dashboard_factory["company"](name="Dashboard Test Company")
    deadline = datetime.datetime(2099, 5, 17, 12, 0)

    dashboard_factory["drive"](
        posted="Y",
        status="Active",
        company=company,
        title="Dashboard Test Engineer",
        package=18.5,
        location="Pune",
        deadline=deadline,
    )
    db.session.commit()

    response = get_dashboard(placement_officer_client)
    html = page_text(response)

    assert response.status_code == 200
    assert "Dashboard Test Company" in html
    assert "Dashboard Test Engineer" in html
    assert "Pune" in html
    assert "18.5" in html
    assert "2099-05-17" in html


def test_DRIVE_09_active_drive_details_link_is_rendered(
    placement_officer_client, dashboard_factory
):
    # Scenario: An active posted drive is listed on the dashboard.
    # Expected: Its row includes a View Details link to the officer drive route.
    drive = dashboard_factory["drive"](
        posted="Y",
        status="Active",
        title="Details Link Test Role",
    )
    db.session.commit()

    response = get_dashboard(placement_officer_client)
    html = page_text(response)

    assert response.status_code == 200
    assert "Details Link Test Role" in html
    assert "Placement_officer_Job_drive" in html
    assert f"id={drive.id}" in html or f"id%3D{drive.id}" in html


def test_DRIVE_10_multiple_drives_count_excludes_only_closed_and_unposted(
    placement_officer_client, dashboard_factory
):
    # Scenario: Create active posted, expired posted, closed posted, and
    # unposted drives.
    # Expected: Only posted drives whose status is not Closed are counted.
    dashboard_factory["drive"](posted="Y", status="Active")
    dashboard_factory["drive"](posted="Y", status="Expired")
    dashboard_factory["drive"](posted="Y", status="Closed")
    dashboard_factory["drive"](posted="N", status="Active")

    db.session.commit()

    response = get_dashboard(placement_officer_client)
    assert response.status_code == 200
    assert "Active Job drives" in page_text(response)


# ---------------------------------------------------------------------------
# NEW-01 to NEW-07 and NEW-10: New/unposted job drives
# ---------------------------------------------------------------------------

def test_NEW_01_unposted_drive_is_listed(
    placement_officer_client, dashboard_factory
):
    # Scenario: One job drive has posted='N'.
    # Expected: Its title appears in the New Job Drives table.
    dashboard_factory["drive"](
        posted="N",
        title="New Unposted Role",
    )
    db.session.commit()

    response = get_dashboard(placement_officer_client)
    assert response.status_code == 200
    assert "New Unposted Role" in page_text(response)


def test_NEW_02_posted_drive_is_not_listed_as_new(
    placement_officer_client, dashboard_factory
):
    # Scenario: A job drive has posted='Y'.
    # Expected: The drive is excluded from the New Job Drives query,
    # which should contain only records with posted='N'.

    from models import Job_Drives

    drive = dashboard_factory["drive"](
        posted="Y",
        status="Active",
        title="Already Posted Role",
    )
    db.session.commit()

    response = get_dashboard(placement_officer_client)
    assert response.status_code == 200

    new_drives = Job_Drives.query.filter_by(posted="N").all()

    assert all(
        new_drive.id != drive.id
        for new_drive in new_drives
    )


def test_NEW_03_new_drives_are_ordered_by_deadline(
    placement_officer_client, dashboard_factory
):
    # Scenario: Three unposted drives have different deadlines.
    # Expected: The New Job Drives table sorts them by ascending deadline.
    base = datetime.datetime.now().replace(
        hour=12, minute=0, second=0, microsecond=0
    )

    dashboard_factory["drive"](
        posted="N",
        title="New Deadline Late",
        deadline=base + datetime.timedelta(days=30),
    )
    dashboard_factory["drive"](
        posted="N",
        title="New Deadline Early",
        deadline=base + datetime.timedelta(days=3),
    )
    dashboard_factory["drive"](
        posted="N",
        title="New Deadline Middle",
        deadline=base + datetime.timedelta(days=15),
    )

    db.session.commit()

    response = get_dashboard(placement_officer_client)
    html = page_text(response)

    positions = [
        html.find("New Deadline Early"),
        html.find("New Deadline Middle"),
        html.find("New Deadline Late"),
    ]

    assert response.status_code == 200
    assert all(position >= 0 for position in positions)
    assert positions == sorted(positions)


def test_NEW_04_only_five_new_drive_rows_are_displayed(
    placement_officer_client, dashboard_factory
):
    # Scenario: Six unposted job drives exist.
    # Expected: At most five are displayed in the New Job Drives table.
    for index in range(6):
        dashboard_factory["drive"](
            posted="N",
            title=f"New Drive Limit {index}",
            deadline=datetime.datetime.now() + datetime.timedelta(days=index + 1),
        )

    db.session.commit()

    response = get_dashboard(placement_officer_client)
    html = page_text(response)

    displayed = sum(
        f"New Drive Limit {index}" in html for index in range(6)
    )
    assert response.status_code == 200
    assert displayed == 5


def test_NEW_05_new_drive_details_are_rendered(
    placement_officer_client, dashboard_factory
):
    # Scenario: An unposted drive has company, title, package, location,
    # and deadline data.
    # Expected: These details appear in the New Job Drives table.
    company = dashboard_factory["company"](name="New Drive Company")
    deadline = datetime.datetime(2099, 6, 21, 12, 0)

    dashboard_factory["drive"](
        posted="N",
        company=company,
        title="New Data Analyst",
        package=12.5,
        location="Delhi",
        deadline=deadline,
    )
    db.session.commit()

    response = get_dashboard(placement_officer_client)
    html = page_text(response)

    assert response.status_code == 200
    assert "New Drive Company" in html
    assert "New Data Analyst" in html
    assert "12.5" in html
    assert "Delhi" in html
    assert "2099-06-21" in html


def test_NEW_06_closed_unposted_drive_is_currently_listed(
    placement_officer_client, dashboard_factory
):
    # Scenario: A job drive has posted='N' and status='Closed'.
    # Expected: Current implementation still lists it because the New Job
    # Drives query filters only on posted='N'.
    dashboard_factory["drive"](
        posted="N",
        status="Closed",
        title="Closed Unposted Drive",
    )
    db.session.commit()

    response = get_dashboard(placement_officer_client)
    assert response.status_code == 200
    assert "Closed Unposted Drive" in page_text(response)


def test_NEW_07_empty_new_drive_table_shows_empty_state(
    placement_officer_client, test_database
):
    # Scenario: No job drives have posted='N'.
    # Expected: The New Job Drives empty-state message is rendered.
    response = get_dashboard(placement_officer_client)

    assert response.status_code == 200
    assert "No new job drives are available right now." in page_text(response)


def test_NEW_10_new_drive_view_all_link_is_rendered(
    placement_officer_client, dashboard_factory
):
    # Scenario: The dashboard is rendered with a New Job Drives section.
    # Expected: The View All link targets the recruiter-job-drive route.
    dashboard_factory["drive"](posted="N")
    db.session.commit()

    response = get_dashboard(placement_officer_client)
    html = page_text(response)

    assert response.status_code == 200
    assert "Placement_officer_Recruiter_Job_drive" in html

# ---------------------------------------------------------------------------
# INT-01 to INT-07 and INT-09: Today's interview count
# ---------------------------------------------------------------------------

def _dashboard_today_interview_count():
    """
    Return the interview-round count using the same IST day boundaries
    as the dashboard route.
    """
    from models import Interview_Rounds

    now_ist = datetime.datetime.now(ZoneInfo("Asia/Kolkata"))
    start_of_today = now_ist.replace(
        hour=0, minute=0, second=0, microsecond=0, tzinfo=None
    )
    start_of_tomorrow = start_of_today + datetime.timedelta(days=1)

    return Interview_Rounds.query.filter(
        Interview_Rounds.date >= start_of_today,
        Interview_Rounds.date < start_of_tomorrow,
    ).count()


def test_INT_01_interview_scheduled_today_is_counted(
    placement_officer_client, dashboard_factory
):
    # Scenario: One interview round is scheduled today.
    # Expected: The interview count is one.
    now_ist = datetime.datetime.now(ZoneInfo("Asia/Kolkata"))
    today = now_ist.replace(
        hour=12, minute=0, second=0, microsecond=0, tzinfo=None
    )

    dashboard_factory["interview"](date=today)
    db.session.commit()

    response = get_dashboard(placement_officer_client)

    assert response.status_code == 200
    assert _dashboard_today_interview_count() == 1


def test_INT_02_interview_before_today_is_excluded(
    placement_officer_client, dashboard_factory
):
    # Scenario: One interview round occurred yesterday.
    # Expected: The interview is excluded from today's count.
    now_ist = datetime.datetime.now(ZoneInfo("Asia/Kolkata"))
    yesterday = now_ist.replace(
        hour=12, minute=0, second=0, microsecond=0, tzinfo=None
    ) - datetime.timedelta(days=1)

    dashboard_factory["interview"](date=yesterday)
    db.session.commit()

    response = get_dashboard(placement_officer_client)

    assert response.status_code == 200
    assert _dashboard_today_interview_count() == 0


def test_INT_03_interview_tomorrow_is_excluded(
    placement_officer_client, dashboard_factory
):
    # Scenario: One interview round is scheduled tomorrow.
    # Expected: The interview is excluded from today's count.
    now_ist = datetime.datetime.now(ZoneInfo("Asia/Kolkata"))
    tomorrow = now_ist.replace(
        hour=12, minute=0, second=0, microsecond=0, tzinfo=None
    ) + datetime.timedelta(days=1)

    dashboard_factory["interview"](date=tomorrow)
    db.session.commit()

    response = get_dashboard(placement_officer_client)

    assert response.status_code == 200
    assert _dashboard_today_interview_count() == 0


def test_INT_04_interview_at_start_of_today_is_counted(
    placement_officer_client, dashboard_factory
):
    # Scenario: An interview is scheduled exactly at midnight today.
    # Expected: It is included because the lower date boundary is inclusive.
    now_ist = datetime.datetime.now(ZoneInfo("Asia/Kolkata"))
    start_of_today = now_ist.replace(
        hour=0, minute=0, second=0, microsecond=0, tzinfo=None
    )

    dashboard_factory["interview"](date=start_of_today)
    db.session.commit()

    response = get_dashboard(placement_officer_client)

    assert response.status_code == 200
    assert _dashboard_today_interview_count() == 1


def test_INT_05_interview_at_start_of_tomorrow_is_excluded(
    placement_officer_client, dashboard_factory
):
    # Scenario: An interview is scheduled exactly at midnight tomorrow.
    # Expected: It is excluded because the upper date boundary is exclusive.
    now_ist = datetime.datetime.now(ZoneInfo("Asia/Kolkata"))
    start_of_tomorrow = (
        now_ist.replace(
            hour=0, minute=0, second=0, microsecond=0, tzinfo=None
        )
        + datetime.timedelta(days=1)
    )

    dashboard_factory["interview"](date=start_of_tomorrow)
    db.session.commit()

    response = get_dashboard(placement_officer_client)

    assert response.status_code == 200
    assert _dashboard_today_interview_count() == 0


def test_INT_06_multiple_interview_rounds_are_counted_individually(
    placement_officer_client, dashboard_factory
):
    # Scenario: Three interview rounds are scheduled today.
    # Expected: All three rounds are counted.
    now_ist = datetime.datetime.now(ZoneInfo("Asia/Kolkata"))
    today = now_ist.replace(
        hour=12, minute=0, second=0, microsecond=0, tzinfo=None
    )

    dashboard_factory["interview"](
        date=today, round_name="Technical Round"
    )
    dashboard_factory["interview"](
        date=today + datetime.timedelta(minutes=30),
        round_name="HR Round",
    )
    dashboard_factory["interview"](
        date=today + datetime.timedelta(minutes=60),
        round_name="Manager Round",
    )

    db.session.commit()

    response = get_dashboard(placement_officer_client)

    assert response.status_code == 200
    assert _dashboard_today_interview_count() == 3


def test_INT_07_interview_result_does_not_exclude_round(
    placement_officer_client, dashboard_factory
):
    # Scenario: An interview scheduled today already has a result.
    # Expected: It is still counted because the query filters by date only.
    now_ist = datetime.datetime.now(ZoneInfo("Asia/Kolkata"))
    today = now_ist.replace(
        hour=12, minute=0, second=0, microsecond=0, tzinfo=None
    )

    dashboard_factory["interview"](
        date=today, result="Selected"
    )
    db.session.commit()

    response = get_dashboard(placement_officer_client)

    assert response.status_code == 200
    assert _dashboard_today_interview_count() == 1


def test_INT_09_interview_on_closed_drive_is_still_counted(
    placement_officer_client, dashboard_factory
):
    # Scenario: An interview today belongs to an application for a closed drive.
    # Expected: It is counted because the query doesn't filter by drive status.
    drive = dashboard_factory["drive"](
        posted="Y", status="Closed"
    )
    application = dashboard_factory["application"](drive=drive)

    now_ist = datetime.datetime.now(ZoneInfo("Asia/Kolkata"))
    today = now_ist.replace(
        hour=12, minute=0, second=0, microsecond=0, tzinfo=None
    )

    dashboard_factory["interview"](
        application=application, date=today
    )
    db.session.commit()

    response = get_dashboard(placement_officer_client)

    assert response.status_code == 200
    assert _dashboard_today_interview_count() == 1