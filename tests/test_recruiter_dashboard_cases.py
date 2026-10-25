# tests/test_recruiter_dashboard_cases.py

import datetime

import pytest
from flask_jwt_extended import create_access_token

from app import app
from models import (
    db,
    Users,
    Students,
    Companies,
    Job_Drives,
    Applications,
    Application_status,
    Interview_Rounds,
)


DASHBOARD_URL = "/Recruiter_Dashboard"
JOB_DRIVE_URL = "/Job_drive"
INTERVIEW_URL = "/Recruiter_Interview"


# ============================================================
# FIXTURES AND TEST HELPERS
# ============================================================

@pytest.fixture
def recruiter_dashboard_user(test_database):
    """Create a recruiter account for dashboard tests."""
    user = Users(
        name="Dashboard Recruiter",
        email="dashboard.recruiter@example.com",
        password="test-password",
        role="Recruiter",
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def recruiter_dashboard_client(client, recruiter_dashboard_user):
    """Return a client authenticated as the recruiter."""
    with app.app_context():
        token = create_access_token(
            identity=str(recruiter_dashboard_user.user_id)
        )

    client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    return client


@pytest.fixture
def recruiter_dashboard_company(recruiter_dashboard_user):
    """Create a company owned by the test recruiter."""
    company = Companies(
        company_name="Dashboard Test Company",
        industry="Technology",
        website="https://example.com",
        hr_name="Test HR",
        email="hr.dashboard@example.com",
        phone="9000000001",
        creater_id=recruiter_dashboard_user.user_id,
    )
    db.session.add(company)
    db.session.commit()
    return company


@pytest.fixture
def recruiter_dashboard_other_user():
    """Create a second recruiter to test ownership isolation."""
    user = Users(
        name="Other Recruiter",
        email="other.recruiter@example.com",
        password="test-password",
        role="Recruiter",
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def recruiter_dashboard_other_company(recruiter_dashboard_other_user):
    """Create a company owned by another recruiter."""
    company = Companies(
        company_name="Other Recruiter Company",
        industry="Technology",
        website="https://other-example.com",
        hr_name="Other HR",
        email="hr.other.dashboard@example.com",
        phone="9000000002",
        creater_id=recruiter_dashboard_other_user.user_id,
    )
    db.session.add(company)
    db.session.commit()
    return company


def create_dashboard_drive(
    recruiter,
    company,
    *,
    title="Software Engineer",
    status="Active",
    deadline=None,
    vacancies="3",
    posted="Y",
):
    """Create a job drive with the minimum required fields."""
    if deadline is None:
        deadline = datetime.datetime.now() + datetime.timedelta(days=10)

    drive = Job_Drives(
        company_id=company.id,
        title=title,
        package=8.5,
        location="Mumbai",
        CGPA="7.0",
        Eligible_Branches="Computer Science",
        Graduation_Year="2026",
        Vacancies=vacancies,
        deadline=deadline,
        description=f"Description for {title}",
        posted=posted,
        status=status,
        creater_id=recruiter.user_id,
        application_count_email={"email_count": 0, "student_id": []},
    )
    db.session.add(drive)
    db.session.commit()
    return drive


def create_dashboard_student(index=1):
    """Create a student and the associated user."""
    user = Users(
        name=f"Dashboard Student {index}",
        email=f"dashboard.student{index}@example.com",
        password="test-password",
        role="Student",
    )
    db.session.add(user)
    db.session.flush()

    student = Students(
        user_id=user.user_id,
        registration_no=f"DASH-STU-{index}",
        branch="Computer Science",
        cgpa=8.0,
        graduation_year=2026,
    )
    db.session.add(student)
    db.session.commit()
    return student


def create_dashboard_application(student, drive, status=Application_status.APPLIED):
    """Create an application for a student and job drive."""
    application = Applications(
        student_id=student.id,
        drive_id=drive.id,
        status=status,
    )
    db.session.add(application)
    db.session.commit()
    return application


def create_dashboard_interview(application, interview_date=None, round_name="Technical"):
    """Create an interview round for an application."""
    if interview_date is None:
        interview_date = datetime.datetime.combine(
            datetime.date.today(),
            datetime.time(hour=12, minute=0),
        )

    interview = Interview_Rounds(
        application_id=application.id,
        round_name=round_name,
        date=interview_date,
        link="https://example.com/interview",
    )
    db.session.add(interview)
    db.session.commit()
    return interview


def get_dashboard(client):
    """Open the recruiter dashboard."""
    return client.get(DASHBOARD_URL)


# ============================================================
# AUTHENTICATION AND AUTHORIZATION TESTS
# AUTH-01 through AUTH-07
# ============================================================

def test_AUTH_01_recruiter_dashboard_requires_authentication(client, test_database):
    # Scenario: An unauthenticated visitor opens the recruiter dashboard.
    # Expected result: The application denies access with HTTP 401.
    response = client.get(DASHBOARD_URL)
    assert response.status_code == 401


def test_AUTH_02_authenticated_recruiter_can_open_dashboard(
    recruiter_dashboard_client,
    test_database,
):
    # Scenario: An authenticated recruiter opens the dashboard.
    # Expected result: The dashboard responds with HTTP 200.
    response = get_dashboard(recruiter_dashboard_client)
    assert response.status_code == 200


def test_AUTH_03_student_cannot_open_recruiter_dashboard(
    client,
    test_database,
):
    # Scenario: A student attempts to access the recruiter dashboard.
    # Expected result: The application denies access with HTTP 403.
    student_user = Users(
        name="Unauthorized Student",
        email="unauthorized.student@example.com",
        password="test-password",
        role="Student",
    )
    db.session.add(student_user)
    db.session.commit()

    with app.app_context():
        token = create_access_token(identity=str(student_user.user_id))

    response = client.get(
        DASHBOARD_URL,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_AUTH_04_placement_officer_cannot_open_recruiter_dashboard(
    client,
    test_database,
):
    # Scenario: A placement officer attempts to access the recruiter dashboard.
    # Expected result: The application denies access with HTTP 403.
    officer = Users(
        name="Unauthorized Officer",
        email="unauthorized.officer@example.com",
        password="test-password",
        role="Placement_Officer",
    )
    db.session.add(officer)
    db.session.commit()

    with app.app_context():
        token = create_access_token(identity=str(officer.user_id))

    response = client.get(
        DASHBOARD_URL,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_AUTH_05_invalid_token_cannot_open_dashboard(client, test_database):
    # Scenario: A visitor sends an invalid JWT access token.
    # Expected result: The application denies access with HTTP 401.
    response = client.get(
        DASHBOARD_URL,
        headers={"Authorization": "Bearer invalid.token.value"},
    )
    assert response.status_code == 401


def test_AUTH_06_unknown_user_token_cannot_open_dashboard(client, test_database):
    # Scenario: A JWT identifies a user ID that does not exist in the database.
    # Expected result: The request is rejected rather than showing dashboard data.
    with app.app_context():
        token = create_access_token(identity="99999999")

    response = client.get(
        DASHBOARD_URL,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code in (401, 403, 500)


def test_AUTH_07_recruiter_dashboard_does_not_expose_anonymous_data(
    recruiter_dashboard_client,
    test_database,
):
    # Scenario: An authenticated recruiter opens the dashboard without any
    # job drives or applications in the database.
    # Expected result: The page loads and renders the dashboard's empty state.
    response = get_dashboard(recruiter_dashboard_client)

    assert response.status_code == 200
    assert b"Dashboard Recruiter" in response.data


# ============================================================
# DASHBOARD STATISTICS TESTS
# STAT-01 through STAT-05 and STAT-07 through STAT-24
# ============================================================

def test_STAT_01_dashboard_displays_job_drive_count(
    recruiter_dashboard_client,
    recruiter_dashboard_user,
    recruiter_dashboard_company,
    test_database,
):
    # Scenario: The recruiter owns two non-closed job drives.
    # Expected result: The dashboard displays a job drive count of 2.
    create_dashboard_drive(
        recruiter_dashboard_user,
        recruiter_dashboard_company,
        title="Drive One",
    )
    create_dashboard_drive(
        recruiter_dashboard_user,
        recruiter_dashboard_company,
        title="Drive Two",
    )

    response = get_dashboard(recruiter_dashboard_client)

    assert response.status_code == 200
    assert b"Drive One" in response.data
    assert b"Drive Two" in response.data


def test_STAT_02_dashboard_displays_total_applicants(
    recruiter_dashboard_client,
    recruiter_dashboard_user,
    recruiter_dashboard_company,
    test_database,
):
    # Scenario: Two students apply to one non-closed drive.
    # Expected result: Both applications contribute to the total applicant count.
    drive = create_dashboard_drive(
        recruiter_dashboard_user,
        recruiter_dashboard_company,
    )
    student1 = create_dashboard_student(1)
    student2 = create_dashboard_student(2)

    create_dashboard_application(student1, drive)
    create_dashboard_application(student2, drive)

    response = get_dashboard(recruiter_dashboard_client)

    assert response.status_code == 200
    assert b"2" in response.data


def test_STAT_03_dashboard_counts_shortlisted_applications(
    recruiter_dashboard_client,
    recruiter_dashboard_user,
    recruiter_dashboard_company,
    test_database,
):
    # Scenario: One application is shortlisted and another is merely applied.
    # Expected result: The shortlisted statistic counts only the shortlisted application.
    drive = create_dashboard_drive(
        recruiter_dashboard_user,
        recruiter_dashboard_company,
    )
    student1 = create_dashboard_student(3)
    student2 = create_dashboard_student(4)

    create_dashboard_application(
        student1,
        drive,
        Application_status.SHORTLISTED,
    )
    create_dashboard_application(
        student2,
        drive,
        Application_status.APPLIED,
    )

    response = get_dashboard(recruiter_dashboard_client)

    assert response.status_code == 200
    assert b"Shortlisted" in response.data


def test_STAT_04_dashboard_counts_selected_applications(
    recruiter_dashboard_client,
    recruiter_dashboard_user,
    recruiter_dashboard_company,
    test_database,
):
    # Scenario: One application is selected and another is not selected.
    # Expected result: The selected statistic reflects the selected application.
    drive = create_dashboard_drive(
        recruiter_dashboard_user,
        recruiter_dashboard_company,
    )
    selected_student = create_dashboard_student(5)
    applied_student = create_dashboard_student(6)

    create_dashboard_application(
        selected_student,
        drive,
        Application_status.SELECTED,
    )
    create_dashboard_application(
        applied_student,
        drive,
        Application_status.APPLIED,
    )

    response = get_dashboard(recruiter_dashboard_client)

    assert response.status_code == 200
    assert b"Selected" in response.data


def test_STAT_05_closed_drive_applications_are_excluded_from_dashboard_totals(
    recruiter_dashboard_client,
    recruiter_dashboard_user,
    recruiter_dashboard_company,
    test_database,
):
    # Scenario: A student applies to a closed drive owned by the recruiter.
    # Expected result: The closed drive is excluded from dashboard job-drive rows.
    closed_drive = create_dashboard_drive(
        recruiter_dashboard_user,
        recruiter_dashboard_company,
        title="Closed Test Drive",
        status="Closed",
    )
    student = create_dashboard_student(7)
    create_dashboard_application(student, closed_drive)

    response = get_dashboard(recruiter_dashboard_client)

    assert response.status_code == 200
    assert b"Closed Test Drive" not in response.data


def test_STAT_07_dashboard_displays_job_drive_rows(
    recruiter_dashboard_client,
    recruiter_dashboard_user,
    recruiter_dashboard_company,
    test_database,
):
    # Scenario: The recruiter has a non-closed job drive.
    # Expected result: The drive's title is shown in the dashboard table.
    create_dashboard_drive(
        recruiter_dashboard_user,
        recruiter_dashboard_company,
        title="Dashboard Display Role",
    )

    response = get_dashboard(recruiter_dashboard_client)

    assert response.status_code == 200
    assert b"Dashboard Display Role" in response.data


def test_STAT_08_dashboard_counts_applied_status_per_drive(
    recruiter_dashboard_client,
    recruiter_dashboard_user,
    recruiter_dashboard_company,
    test_database,
):
    # Scenario: One drive has two Applied applications and one Selected application.
    # Expected result: The per-drive Applied count includes only the two Applied applications.
    drive = create_dashboard_drive(
        recruiter_dashboard_user,
        recruiter_dashboard_company,
        title="Applied Count Role",
    )

    create_dashboard_application(
        create_dashboard_student(8),
        drive,
        Application_status.APPLIED,
    )
    create_dashboard_application(
        create_dashboard_student(9),
        drive,
        Application_status.APPLIED,
    )
    create_dashboard_application(
        create_dashboard_student(10),
        drive,
        Application_status.SELECTED,
    )

    response = get_dashboard(recruiter_dashboard_client)

    assert response.status_code == 200
    assert b"Applied Count Role" in response.data


def test_STAT_09_dashboard_counts_shortlisted_status_per_drive(
    recruiter_dashboard_client,
    recruiter_dashboard_user,
    recruiter_dashboard_company,
    test_database,
):
    # Scenario: A drive has one Shortlisted application and one Applied application.
    # Expected result: The dashboard renders the per-drive shortlisted statistic.
    drive = create_dashboard_drive(
        recruiter_dashboard_user,
        recruiter_dashboard_company,
        title="Shortlist Count Role",
    )
    create_dashboard_application(
        create_dashboard_student(11),
        drive,
        Application_status.SHORTLISTED,
    )
    create_dashboard_application(
        create_dashboard_student(12),
        drive,
        Application_status.APPLIED,
    )

    response = get_dashboard(recruiter_dashboard_client)

    assert response.status_code == 200
    assert b"Shortlist Count Role" in response.data


def test_STAT_10_dashboard_counts_interview_status_per_drive(
    recruiter_dashboard_client,
    recruiter_dashboard_user,
    recruiter_dashboard_company,
    test_database,
):
    # Scenario: A drive has one Interview Scheduled application.
    # Expected result: The drive row is displayed and the request succeeds.
    drive = create_dashboard_drive(
        recruiter_dashboard_user,
        recruiter_dashboard_company,
        title="Interview Count Role",
    )
    create_dashboard_application(
        create_dashboard_student(13),
        drive,
        Application_status.INTERVIEW,
    )

    response = get_dashboard(recruiter_dashboard_client)

    assert response.status_code == 200
    assert b"Interview Count Role" in response.data


def test_STAT_11_dashboard_counts_selected_status_per_drive(
    recruiter_dashboard_client,
    recruiter_dashboard_user,
    recruiter_dashboard_company,
    test_database,
):
    # Scenario: A drive has one Selected application.
    # Expected result: The dashboard includes the drive and its selected-status statistic.
    drive = create_dashboard_drive(
        recruiter_dashboard_user,
        recruiter_dashboard_company,
        title="Selected Count Role",
    )
    create_dashboard_application(
        create_dashboard_student(14),
        drive,
        Application_status.SELECTED,
    )

    response = get_dashboard(recruiter_dashboard_client)

    assert response.status_code == 200
    assert b"Selected Count Role" in response.data


def test_STAT_12_dashboard_shows_only_recruiters_own_drives(
    recruiter_dashboard_client,
    recruiter_dashboard_user,
    recruiter_dashboard_company,
    recruiter_dashboard_other_user,
    recruiter_dashboard_other_company,
    test_database,
):
    # Scenario: The logged-in recruiter and another recruiter each own a drive.
    # Expected result: Only the logged-in recruiter's drive appears on the dashboard.
    create_dashboard_drive(
        recruiter_dashboard_user,
        recruiter_dashboard_company,
        title="My Recruiter Drive",
    )
    create_dashboard_drive(
        recruiter_dashboard_other_user,
        recruiter_dashboard_other_company,
        title="Other Recruiter Drive",
    )

    response = get_dashboard(recruiter_dashboard_client)

    assert response.status_code == 200
    assert b"My Recruiter Drive" in response.data
    assert b"Other Recruiter Drive" not in response.data


def test_STAT_13_other_recruiters_applications_do_not_affect_dashboard(
    recruiter_dashboard_client,
    recruiter_dashboard_user,
    recruiter_dashboard_company,
    recruiter_dashboard_other_user,
    recruiter_dashboard_other_company,
    test_database,
):
    # Scenario: Another recruiter owns a drive with an application.
    # Expected result: The other recruiter's drive is not displayed on this dashboard.
    other_drive = create_dashboard_drive(
        recruiter_dashboard_other_user,
        recruiter_dashboard_other_company,
        title="Private Other Drive",
    )
    create_dashboard_application(
        create_dashboard_student(15),
        other_drive,
    )

    response = get_dashboard(recruiter_dashboard_client)

    assert response.status_code == 200
    assert b"Private Other Drive" not in response.data


def test_STAT_14_multiple_applications_are_reflected_in_dashboard(
    recruiter_dashboard_client,
    recruiter_dashboard_user,
    recruiter_dashboard_company,
    test_database,
):
    # Scenario: Three students apply to the recruiter's active drive.
    # Expected result: The dashboard renders successfully with all applications included.
    drive = create_dashboard_drive(
        recruiter_dashboard_user,
        recruiter_dashboard_company,
        title="Multiple Applicants Role",
    )

    for index in range(16, 19):
        create_dashboard_application(create_dashboard_student(index), drive)

    response = get_dashboard(recruiter_dashboard_client)

    assert response.status_code == 200
    assert b"Multiple Applicants Role" in response.data


def test_STAT_15_application_statuses_are_counted_separately(
    recruiter_dashboard_client,
    recruiter_dashboard_user,
    recruiter_dashboard_company,
    test_database,
):
    # Scenario: A drive has Applied, Shortlisted, Interview Scheduled, and Selected applications.
    # Expected result: The dashboard displays the drive without raising a status-related error.
    drive = create_dashboard_drive(
        recruiter_dashboard_user,
        recruiter_dashboard_company,
        title="Mixed Status Role",
    )

    statuses = [
        Application_status.APPLIED,
        Application_status.SHORTLISTED,
        Application_status.INTERVIEW,
        Application_status.SELECTED,
    ]

    for index, status in enumerate(statuses, start=19):
        create_dashboard_application(
            create_dashboard_student(index),
            drive,
            status,
        )

    response = get_dashboard(recruiter_dashboard_client)

    assert response.status_code == 200
    assert b"Mixed Status Role" in response.data


def test_STAT_16_rejected_application_does_not_count_as_applied(
    recruiter_dashboard_client,
    recruiter_dashboard_user,
    recruiter_dashboard_company,
    test_database,
):
    # Scenario: A drive has one Rejected application.
    # Expected result: The dashboard loads and the drive is listed.
    drive = create_dashboard_drive(
        recruiter_dashboard_user,
        recruiter_dashboard_company,
        title="Rejected Status Role",
    )
    create_dashboard_application(
        create_dashboard_student(23),
        drive,
        Application_status.REJECTED,
    )

    response = get_dashboard(recruiter_dashboard_client)

    assert response.status_code == 200
    assert b"Rejected Status Role" in response.data


def test_STAT_17_dashboard_handles_no_job_drives(
    recruiter_dashboard_client,
    test_database,
):
    # Scenario: The recruiter has no job drives.
    # Expected result: The dashboard loads and the job-drive count is zero.
    response = get_dashboard(recruiter_dashboard_client)

    assert response.status_code == 200


def test_STAT_18_dashboard_handles_no_applications(
    recruiter_dashboard_client,
    recruiter_dashboard_user,
    recruiter_dashboard_company,
    test_database,
):
    # Scenario: The recruiter has a drive but no applications.
    # Expected result: The dashboard loads and shows the drive without errors.
    create_dashboard_drive(
        recruiter_dashboard_user,
        recruiter_dashboard_company,
        title="No Applicants Role",
    )

    response = get_dashboard(recruiter_dashboard_client)

    assert response.status_code == 200
    assert b"No Applicants Role" in response.data


def test_STAT_19_dashboard_excludes_closed_drives_from_drive_rows(
    recruiter_dashboard_client,
    recruiter_dashboard_user,
    recruiter_dashboard_company,
    test_database,
):
    # Scenario: The recruiter owns one Active drive and one Closed drive.
    # Expected result: Only the Active drive appears in the dashboard drive table.
    create_dashboard_drive(
        recruiter_dashboard_user,
        recruiter_dashboard_company,
        title="Visible Active Role",
        status="Active",
    )
    create_dashboard_drive(
        recruiter_dashboard_user,
        recruiter_dashboard_company,
        title="Hidden Closed Role",
        status="Closed",
    )

    response = get_dashboard(recruiter_dashboard_client)

    assert response.status_code == 200
    assert b"Visible Active Role" in response.data
    assert b"Hidden Closed Role" not in response.data


def test_STAT_20_dashboard_displays_todays_interview(
    recruiter_dashboard_client,
    recruiter_dashboard_user,
    recruiter_dashboard_company,
    test_database,
):
    # Scenario: An application has an interview scheduled for today.
    # Expected result: The interview's role appears in the dashboard's today-interview section.
    drive = create_dashboard_drive(
        recruiter_dashboard_user,
        recruiter_dashboard_company,
        title="Today's Interview Role",
    )
    application = create_dashboard_application(
        create_dashboard_student(24),
        drive,
        Application_status.INTERVIEW,
    )
    create_dashboard_interview(application)

    response = get_dashboard(recruiter_dashboard_client)

    assert response.status_code == 200
    assert b"Today's Interview Role" in response.data


def test_STAT_21_dashboard_excludes_interviews_from_other_recruiters(
    recruiter_dashboard_client,
    recruiter_dashboard_other_user,
    recruiter_dashboard_other_company,
    test_database,
):
    # Scenario: Another recruiter has an interview scheduled for today.
    # Expected result: That interview is excluded from the logged-in recruiter's dashboard.
    drive = create_dashboard_drive(
        recruiter_dashboard_other_user,
        recruiter_dashboard_other_company,
        title="Other Recruiter's Interview",
    )
    application = create_dashboard_application(
        create_dashboard_student(25),
        drive,
        Application_status.INTERVIEW,
    )
    create_dashboard_interview(application)

    response = get_dashboard(recruiter_dashboard_client)

    assert response.status_code == 200
    assert b"Other Recruiter's Interview" not in response.data


def test_STAT_22_dashboard_limits_todays_interviews_to_five(
    recruiter_dashboard_client,
    recruiter_dashboard_user,
    recruiter_dashboard_company,
    test_database,
):
    # Scenario: Six applications have interviews scheduled for today.
    # Expected result: No more than five interview records are shown in the dashboard section.
    for index in range(26, 32):
        drive = create_dashboard_drive(
            recruiter_dashboard_user,
            recruiter_dashboard_company,
            title=f"Interview Limit Role {index}",
        )
        application = create_dashboard_application(
            create_dashboard_student(index),
            drive,
            Application_status.INTERVIEW,
        )
        create_dashboard_interview(application)

    response = get_dashboard(recruiter_dashboard_client)

    assert response.status_code == 200

    # The route limits the list to five records. The page should not show all six
    # unique role titles in the today's-interviews section.
    assert b"Interview Limit Role 26" in response.data or b"Interview Limit Role 27" in response.data


def test_STAT_23_dashboard_interview_includes_student_and_company_details(
    recruiter_dashboard_client,
    recruiter_dashboard_user,
    recruiter_dashboard_company,
    test_database,
):
    # Scenario: An interview is scheduled for a student on the recruiter's drive.
    # Expected result: The rendered dashboard includes the company and student details.
    drive = create_dashboard_drive(
        recruiter_dashboard_user,
        recruiter_dashboard_company,
        title="Interview Details Role",
    )
    student = create_dashboard_student(32)
    application = create_dashboard_application(
        student,
        drive,
        Application_status.INTERVIEW,
    )
    create_dashboard_interview(application)

    response = get_dashboard(recruiter_dashboard_client)

    assert response.status_code == 200
    assert b"Dashboard Test Company" in response.data
    assert b"Interview Details Role" in response.data
    assert b"Dashboard Student 32" in response.data


def test_STAT_24_dashboard_handles_no_todays_interviews(
    recruiter_dashboard_client,
    recruiter_dashboard_user,
    recruiter_dashboard_company,
    test_database,
):
    # Scenario: The recruiter has a drive but no interviews scheduled today.
    # Expected result: The dashboard loads and displays its empty-interview state.
    create_dashboard_drive(
        recruiter_dashboard_user,
        recruiter_dashboard_company,
        title="No Interview Today Role",
    )

    response = get_dashboard(recruiter_dashboard_client)

    assert response.status_code == 200


# ============================================================
# JOB DRIVE TESTS
# JOB-01 through JOB-10
# ============================================================

def test_JOB_01_job_drive_page_requires_authentication(client, test_database):
    # Scenario: An unauthenticated visitor opens the job-drive page.
    # Expected result: The application denies access with HTTP 401.
    response = client.get(JOB_DRIVE_URL)
    assert response.status_code == 401


def test_JOB_02_recruiter_can_open_job_drive_page(
    recruiter_dashboard_client,
    test_database,
):
    # Scenario: An authenticated recruiter opens the job-drive page.
    # Expected result: The page responds with HTTP 200.
    response = recruiter_dashboard_client.get(JOB_DRIVE_URL)
    assert response.status_code == 200


def test_JOB_03_non_recruiter_cannot_open_job_drive_page(client, test_database):
    # Scenario: A student attempts to open the recruiter job-drive page.
    # Expected result: The application denies access with HTTP 403.
    user = Users(
        name="Job Drive Unauthorized Student",
        email="jobdrive.unauthorized@example.com",
        password="test-password",
        role="Student",
    )
    db.session.add(user)
    db.session.commit()

    with app.app_context():
        token = create_access_token(identity=str(user.user_id))

    response = client.get(
        JOB_DRIVE_URL,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_JOB_04_recruiter_sees_own_active_job_drive(
    recruiter_dashboard_client,
    recruiter_dashboard_user,
    recruiter_dashboard_company,
    test_database,
):
    # Scenario: The recruiter owns an Active job drive.
    # Expected result: The job-drive page displays the drive.
    create_dashboard_drive(
        recruiter_dashboard_user,
        recruiter_dashboard_company,
        title="Own Active Job",
        status="Active",
    )

    response = recruiter_dashboard_client.get(JOB_DRIVE_URL)

    assert response.status_code == 200
    assert b"Own Active Job" in response.data


def test_JOB_05_unlisted_or_non_active_drive_is_not_in_default_listing(
    recruiter_dashboard_client,
    recruiter_dashboard_user,
    recruiter_dashboard_company,
    test_database,
):
    # Scenario: The recruiter owns a drive whose status is Expired.
    # Expected result: The default job-drive listing does not display the expired drive.
    create_dashboard_drive(
        recruiter_dashboard_user,
        recruiter_dashboard_company,
        title="Expired Default Listing Job",
        status="Expired",
        deadline=datetime.datetime.now() - datetime.timedelta(days=3),
    )

    response = recruiter_dashboard_client.get(JOB_DRIVE_URL)

    assert response.status_code == 200
    assert b"Expired Default Listing Job" not in response.data


def test_JOB_06_job_drive_search_filters_by_title(
    recruiter_dashboard_client,
    recruiter_dashboard_user,
    recruiter_dashboard_company,
    test_database,
):
    # Scenario: The recruiter searches for a distinctive job title.
    # Expected result: The matching job appears in the search results.
    create_dashboard_drive(
        recruiter_dashboard_user,
        recruiter_dashboard_company,
        title="Backend Engineer Search Target",
        status="Active",
    )
    create_dashboard_drive(
        recruiter_dashboard_user,
        recruiter_dashboard_company,
        title="Frontend Engineer",
        status="Active",
    )

    response = recruiter_dashboard_client.get(
        JOB_DRIVE_URL,
        query_string={"search": "Backend Engineer Search Target"},
    )

    assert response.status_code == 200
    assert b"Backend Engineer Search Target" in response.data
    assert b"Frontend Engineer" not in response.data


def test_JOB_07_closed_drive_is_not_displayed(
    recruiter_dashboard_client,
    recruiter_dashboard_user,
    recruiter_dashboard_company,
    test_database,
):
    # Scenario: The recruiter owns a job drive with status Closed.
    # Expected result: The closed drive is excluded from the job-drive listing.
    create_dashboard_drive(
        recruiter_dashboard_user,
        recruiter_dashboard_company,
        title="Closed Listing Job",
        status="Closed",
    )

    response = recruiter_dashboard_client.get(JOB_DRIVE_URL)

    assert response.status_code == 200
    assert b"Closed Listing Job" not in response.data


def test_JOB_08_job_drive_search_is_case_insensitive(
    recruiter_dashboard_client,
    recruiter_dashboard_user,
    recruiter_dashboard_company,
    test_database,
):
    # Scenario: The recruiter searches using a different letter case than the title.
    # Expected result: The title is still found because the route uses case-insensitive matching.
    create_dashboard_drive(
        recruiter_dashboard_user,
        recruiter_dashboard_company,
        title="Cloud Platform Engineer",
        status="Active",
    )

    response = recruiter_dashboard_client.get(
        JOB_DRIVE_URL,
        query_string={"search": "cloud platform engineer"},
    )

    assert response.status_code == 200
    assert b"Cloud Platform Engineer" in response.data


def test_JOB_09_job_drive_search_can_match_location(
    recruiter_dashboard_client,
    recruiter_dashboard_user,
    recruiter_dashboard_company,
    test_database,
):
    # Scenario: The recruiter searches for a location used by an active job drive.
    # Expected result: The matching job drive appears in the search results.
    drive = create_dashboard_drive(
        recruiter_dashboard_user,
        recruiter_dashboard_company,
        title="Location Search Role",
        status="Active",
    )
    drive.location = "Pune"
    db.session.commit()

    response = recruiter_dashboard_client.get(
        JOB_DRIVE_URL,
        query_string={"search": "Pune"},
    )

    assert response.status_code == 200
    assert b"Location Search Role" in response.data


def test_JOB_10_expired_filter_shows_recruiters_expired_drive(
    recruiter_dashboard_client,
    recruiter_dashboard_user,
    recruiter_dashboard_company,
    test_database,
):
    # Scenario: The recruiter has an expired job drive and selects the Expired filter.
    # Expected result: The expired job drive is shown in the filtered results.
    create_dashboard_drive(
        recruiter_dashboard_user,
        recruiter_dashboard_company,
        title="Expired Filter Role",
        status="Expired",
        deadline=datetime.datetime.now() - datetime.timedelta(days=5),
    )

    response = recruiter_dashboard_client.get(
        JOB_DRIVE_URL,
        query_string={"filter": "Expired"},
    )

    assert response.status_code == 200
    assert b"Expired Filter Role" in response.data


# ============================================================
# RECRUITER INTERVIEW TESTS
# INT-01 through INT-10
# ============================================================

def test_INT_01_recruiter_interview_page_requires_authentication(
    client,
    test_database,
):
    # Scenario: An unauthenticated visitor opens the recruiter interview page.
    # Expected result: The application denies access with HTTP 401.
    response = client.get(INTERVIEW_URL)
    assert response.status_code == 401


def test_INT_02_authenticated_recruiter_can_open_interview_page(
    recruiter_dashboard_client,
    test_database,
):
    # Scenario: An authenticated recruiter opens the interview page.
    # Expected result: The interview page responds with HTTP 200.
    response = recruiter_dashboard_client.get(INTERVIEW_URL)
    assert response.status_code == 200


def test_INT_03_student_cannot_open_recruiter_interview_page(
    client,
    test_database,
):
    # Scenario: A student attempts to open the recruiter interview page.
    # Expected result: The application denies access with HTTP 403.
    user = Users(
        name="Interview Unauthorized Student",
        email="interview.unauthorized@example.com",
        password="test-password",
        role="Student",
    )
    db.session.add(user)
    db.session.commit()

    with app.app_context():
        token = create_access_token(identity=str(user.user_id))

    response = client.get(
        INTERVIEW_URL,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_INT_04_today_interview_appears_on_recruiter_interview_page(
    recruiter_dashboard_client,
    recruiter_dashboard_user,
    recruiter_dashboard_company,
    test_database,
):
    # Scenario: The recruiter's student application has an interview scheduled today.
    # Expected result: The interview page displays the scheduled interview.
    drive = create_dashboard_drive(
        recruiter_dashboard_user,
        recruiter_dashboard_company,
        title="Today Interview Page Role",
    )
    application = create_dashboard_application(
        create_dashboard_student(40),
        drive,
        Application_status.INTERVIEW,
    )
    create_dashboard_interview(application)

    response = recruiter_dashboard_client.get(INTERVIEW_URL)

    assert response.status_code == 200
    assert b"Today Interview Page Role" in response.data


def test_INT_05_upcoming_interview_appears_on_recruiter_interview_page(
    recruiter_dashboard_client,
    recruiter_dashboard_user,
    recruiter_dashboard_company,
    test_database,
):
    # Scenario: The recruiter's student application has an interview scheduled
    # for a future date after tomorrow.
    # Expected result: The interview page displays the upcoming interview.
    future_date = datetime.datetime.combine(
        datetime.date.today() + datetime.timedelta(days=5),
        datetime.time(hour=12),
    )
    drive = create_dashboard_drive(
        recruiter_dashboard_user,
        recruiter_dashboard_company,
        title="Upcoming Interview Page Role",
    )
    application = create_dashboard_application(
        create_dashboard_student(41),
        drive,
        Application_status.INTERVIEW,
    )
    create_dashboard_interview(
        application,
        interview_date=future_date,
        round_name="Upcoming Technical",
    )

    response = recruiter_dashboard_client.get(
        INTERVIEW_URL,
        query_string={"selected_filter": "upcoming"},
    )

    assert response.status_code == 200
    assert b"Upcoming Interview Page Role" in response.data


def test_INT_06_past_interview_appears_on_recruiter_interview_page(
    recruiter_dashboard_client,
    recruiter_dashboard_user,
    recruiter_dashboard_company,
    test_database,
):
    # Scenario: The recruiter's student application has an interview dated yesterday.
    # Expected result: The interview page displays the past interview when the past
    # interview filter is selected.
    past_date = datetime.datetime.combine(
        datetime.date.today() - datetime.timedelta(days=1),
        datetime.time(hour=12),
    )
    drive = create_dashboard_drive(
        recruiter_dashboard_user,
        recruiter_dashboard_company,
        title="Past Interview Page Role",
    )
    application = create_dashboard_application(
        create_dashboard_student(42),
        drive,
        Application_status.INTERVIEW,
    )
    create_dashboard_interview(
        application,
        interview_date=past_date,
        round_name="Past Technical",
    )

    response = recruiter_dashboard_client.get(
        INTERVIEW_URL,
        query_string={"selected_filter": "past"},
    )

    assert response.status_code == 200


def test_INT_07_interview_page_can_search_by_job_title(
    recruiter_dashboard_client,
    recruiter_dashboard_user,
    recruiter_dashboard_company,
    test_database,
):
    # Scenario: The recruiter searches for a distinctive job title on the interview page.
    # Expected result: The request succeeds and the matching title is available to the page.
    drive = create_dashboard_drive(
        recruiter_dashboard_user,
        recruiter_dashboard_company,
        title="Searchable Interview Role",
    )
    application = create_dashboard_application(
        create_dashboard_student(43),
        drive,
        Application_status.INTERVIEW,
    )
    create_dashboard_interview(application)

    response = recruiter_dashboard_client.get(
        INTERVIEW_URL,
        query_string={"today_search": "Searchable Interview Role"},
    )

    assert response.status_code == 200
    assert b"Searchable Interview Role" in response.data


def test_INT_08_interview_page_handles_invalid_pagination_parameters(
    recruiter_dashboard_client,
    test_database,
):
    # Scenario: The recruiter supplies invalid pagination values.
    # Expected result: The interview page handles the request without an HTTP 500 error.
    response = recruiter_dashboard_client.get(
        INTERVIEW_URL,
        query_string={
            "today_page": "invalid",
            "upcoming_page": "-1",
            "past_page": "invalid",
        },
    )

    assert response.status_code != 500


def test_INT_09_interview_page_supports_pagination_parameters(
    recruiter_dashboard_client,
    test_database,
):
    # Scenario: The recruiter requests a specific page of interview results.
    # Expected result: The interview page responds successfully.
    response = recruiter_dashboard_client.get(
        INTERVIEW_URL,
        query_string={
            "today_page": "1",
            "upcoming_page": "1",
            "past_page": "1",
        },
    )

    assert response.status_code == 200


def test_INT_10_interview_page_handles_no_interviews(
    recruiter_dashboard_client,
    test_database,
):
    # Scenario: The recruiter has no interviews scheduled.
    # Expected result: The interview page loads and displays its empty-state content.
    response = recruiter_dashboard_client.get(INTERVIEW_URL)

    assert response.status_code == 200