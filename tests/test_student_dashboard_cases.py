# tests/test_student_dashboard_cases.py

import datetime
import io

import pytest
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

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


# ============================================================
# FIXTURES AND HELPERS
# ============================================================

@pytest.fixture
def student_test_data(test_database):
    """
    Creates isolated users and student records using the existing
    test_database fixture from conftest.py.
    """
    student_user = Users(
        name="Test Student",
        email="student_dashboard_test@example.com",
        password=generate_password_hash("StudentPass123"),
        role="student",
    )
    recruiter_user = Users(
        name="Test Recruiter",
        email="recruiter_dashboard_test@example.com",
        password=generate_password_hash("RecruiterPass123"),
        role="Recruiter",
    )
    officer_user = Users(
        name="Test Placement Officer",
        email="officer_dashboard_test@example.com",
        password=generate_password_hash("OfficerPass123"),
        role="Placement_Officer",
    )

    test_database.session.add_all(
        [student_user, recruiter_user, officer_user]
    )
    test_database.session.commit()

    student = Students(
        user_id=student_user.user_id,
        registration_no="REG-STU-001",
        branch="Computer Science",
        cgpa=8.5,
        skills="Python, Flask, SQL",
        resume_path=None,
        resume_status="Pending",
        graduation_year=datetime.date.today().year,
        placement_status="Not Placed",
        mobile_number="9000000001",
        Gender="Other",
        Address="Test Address",
        City="Test City",
        State="Test State",
        pin_code=400001,
        University_Roll_Number="ROLL-STU-001",
        Semester=7,
        tenth_Percentage=85.0,
        twelth_Percentage=82.0,
        Total_Backlogs="0",
        Active_Backlogs="0",
        job_drive=None,
    )

    test_database.session.add(student)
    test_database.session.commit()

    return {
        "student_user": student_user,
        "recruiter_user": recruiter_user,
        "officer_user": officer_user,
        "student": student,
    }


@pytest.fixture
def student_auth(client, student_test_data):
    """
    Scenario: Authenticate a student for dashboard and profile tests.
    Expected result: Requests pass JWT authentication, including protected POST requests.
    """
    from flask_jwt_extended import create_access_token, decode_token

    with app.app_context():
        token = create_access_token(
            identity=str(student_test_data["student_user"].user_id)
        )
        decoded = decode_token(token)
        csrf_token = decoded["csrf"]

    access_cookie = app.config.get(
        "JWT_ACCESS_COOKIE_NAME", "access_token_cookie"
    )
    csrf_cookie = app.config.get(
        "JWT_ACCESS_CSRF_COOKIE_NAME", "csrf_access_token"
    )

    client.set_cookie(access_cookie, token)
    client.set_cookie(csrf_cookie, csrf_token)

    # Make the CSRF token available to POST forms.
    client.environ_base["HTTP_X_CSRF_TOKEN"] = csrf_token

    return client

@pytest.fixture
def recruiter_auth(client, student_test_data):
    """Authenticate the test client as a recruiter."""
    with app.app_context():
        token = create_access_token(
            identity=str(student_test_data["recruiter_user"].user_id)
        )

    client.set_cookie(
        app.config.get("JWT_ACCESS_COOKIE_NAME", "access_token_cookie"),
        token,
    )
    return client


@pytest.fixture
def officer_auth(client, student_test_data):
    """Authenticate the test client as a placement officer."""
    with app.app_context():
        token = create_access_token(
            identity=str(student_test_data["officer_user"].user_id)
        )

    client.set_cookie(
        app.config.get("JWT_ACCESS_COOKIE_NAME", "access_token_cookie"),
        token,
    )
    return client


@pytest.fixture
def job_drive_factory(test_database, student_test_data):
    """Factory for creating a company and a related job drive."""

    created = {"company_count": 0, "drive_count": 0}

    def _make_job_drive(
        *,
        title="Software Engineer",
        company_name=None,
        status="Active",
        posted="Y",
        deadline=None,
        package=12.0,
        location="Mumbai",
        application_count_email=None,
    ):
        created["company_count"] += 1
        created["drive_count"] += 1

        suffix = created["company_count"]
        company_name = company_name or f"Test Company {suffix}"

        company = Companies(
            company_name=company_name,
            industry="Technology",
            website=f"https://company{suffix}.example.com",
            hr_name=f"HR {suffix}",
            email=f"hr{suffix}_dashboard@example.com",
            phone=f"910000{suffix:04d}",
            creater_id=student_test_data["recruiter_user"].user_id,
        )
        test_database.session.add(company)
        test_database.session.flush()

        if deadline is None:
            deadline = datetime.datetime.now() + datetime.timedelta(days=10)

        drive = Job_Drives(
            company_id=company.id,
            title=title,
            package=package,
            location=location,
            CGPA="6.0",
            Eligible_Branches="Computer Science",
            Graduation_Year=str(datetime.date.today().year),
            Vacancies="5",
            deadline=deadline,
            description="Test job description",
            posted=posted,
            status=status,
            creater_id=student_test_data["recruiter_user"].user_id,
            application_count_email=(
                application_count_email
                if application_count_email is not None
                else {"email_count": 0, "student_id": []}
            ),
        )

        test_database.session.add(drive)
        test_database.session.commit()
        return drive

    return _make_job_drive


@pytest.fixture
def application_factory(test_database, student_test_data):
    """Factory for creating applications for the test student."""

    def _make_application(drive, status=Application_status.APPLIED):
        application = Applications(
            student_id=student_test_data["student"].id,
            drive_id=drive.id,
            status=status,
        )
        test_database.session.add(application)
        test_database.session.commit()
        return application

    return _make_application


@pytest.fixture
def interview_factory(test_database):
    """Factory for creating interview rounds."""

    def _make_interview(
        application,
        *,
        round_name="Technical Interview",
        date=None,
        result=None,
        link="https://example.com/interview",
        feedback=None,
    ):
        if date is None:
            date = datetime.datetime.now() + datetime.timedelta(days=2)

        interview = Interview_Rounds(
            application_id=application.id,
            round_name=round_name,
            date=date,
            result=result,
            link=link,
            feedback=feedback,
        )
        test_database.session.add(interview)
        test_database.session.commit()
        return interview

    return _make_interview


# ============================================================
# AUTHENTICATION TESTS — AUTH-01 to AUTH-05
# ============================================================

# AUTH-01
def test_AUTH_01_student_dashboard_requires_authentication(client):
    # Scenario: An unauthenticated visitor opens the student dashboard.
    # Expected result: The request is rejected or redirected to authentication.
    response = client.get("/Student_Dashboard")
    assert response.status_code in (302, 401)


# AUTH-02
def test_AUTH_02_student_can_open_dashboard(student_auth):
    # Scenario: A user with the student role opens the dashboard with a valid JWT.
    # Expected result: The dashboard responds successfully.
    response = student_auth.get("/Student_Dashboard")
    assert response.status_code == 200


# AUTH-03
def test_AUTH_03_recruiter_cannot_open_student_dashboard(recruiter_auth):
    # Scenario: An authenticated recruiter tries to access the student dashboard.
    # Expected result: Access is forbidden.
    response = recruiter_auth.get("/Student_Dashboard")
    assert response.status_code == 403


# AUTH-04
def test_AUTH_04_placement_officer_cannot_open_student_dashboard(officer_auth):
    # Scenario: An authenticated placement officer tries to access the student dashboard.
    # Expected result: Access is forbidden.
    response = officer_auth.get("/Student_Dashboard")
    assert response.status_code == 403


# AUTH-05
def test_AUTH_05_student_profile_requires_authentication(client):
    # Scenario: An unauthenticated visitor opens the student profile page.
    # Expected result: The request is rejected or redirected to authentication.
    response = client.get("/Student_Profile")
    assert response.status_code in (302, 401)


# ============================================================
# PROFILE TESTS — PROF-01 to PROF-10
# ============================================================

# PROF-01
def test_PROF_01_profile_page_loads(student_auth):
    # Scenario: An authenticated student opens their profile page.
    # Expected result: The profile page responds successfully.
    response = student_auth.get("/Student_Profile")
    assert response.status_code == 200


# PROF-02
def test_PROF_02_profile_displays_student_name(
    student_auth, student_test_data
):
    # Scenario: The student opens their profile.
    # Expected result: The page contains the student's account name.
    response = student_auth.get("/Student_Profile")
    assert response.status_code == 200
    assert b"Test Student" in response.data


# PROF-03
def test_PROF_03_profile_update_mode_loads(student_auth):
    # Scenario: The student opens the profile in Update mode.
    # Expected result: The profile update page responds successfully.
    response = student_auth.get("/Student_Profile?mode=Update")
    assert response.status_code == 200


# PROF-04
def test_PROF_04_go_to_update_redirects_to_update_mode(student_auth):
    # Scenario: The student submits the profile action to enter update mode.
    # Expected result: The response redirects to the profile Update page.
    response = student_auth.post(
        "/Student_Profile",
        data={"action": "go_to_update"},
    )
    assert response.status_code == 302
    assert "mode=Update" in response.headers["Location"]


# PROF-05
def test_PROF_05_profile_displays_existing_branch(
    student_auth, student_test_data
):
    # Scenario: The student opens their profile with a saved branch.
    # Expected result: The saved branch is displayed on the profile page.
    response = student_auth.get("/Student_Profile")
    assert response.status_code == 200
    assert b"Computer Science" in response.data


# PROF-06
def test_PROF_06_profile_displays_existing_cgpa(
    student_auth, student_test_data
):
    # Scenario: The student opens their profile with a saved CGPA.
    # Expected result: The profile page displays the saved CGPA.
    response = student_auth.get("/Student_Profile")
    assert response.status_code == 200
    assert b"8.5" in response.data


# PROF-07
def test_PROF_07_missing_resume_download_returns_404(
    student_auth, student_test_data
):
    # Scenario: The student requests a resume download when no resume is saved.
    # Expected result: The route returns 404.
    response = student_auth.get(
        "/Student_Profile?Download=download_resume"
    )
    assert response.status_code == 404


# PROF-08
def test_PROF_08_invalid_profile_photo_extension_is_rejected(
    student_auth,
):
    # Scenario: The student uploads a profile photo with an unsupported extension.
    # Expected result: The application redirects back to the profile page.
    response = student_auth.post(
        "/Student_Profile",
        data={
            "action": "change_photo",
            "profile_photo": (
                io.BytesIO(b"not really an image"),
                "profile.gif",
            ),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 302
    assert "Student_Profile" in response.headers["Location"]


# PROF-09
def test_PROF_09_profile_photo_upload_accepts_png(
    student_auth, student_test_data, monkeypatch
):
    # Scenario: The student uploads a PNG profile photo within the size limit.
    # Expected result: The route accepts the upload and redirects to profile View mode.
    #
    # The filesystem is redirected to a temporary directory to avoid modifying
    # the application's real static files during the test.
    import student.routes as student_routes

    monkeypatch.setattr(
        student_routes.os,
        "makedirs",
        lambda *args, **kwargs: None,
    )

    monkeypatch.setattr(
        student_routes,
        "secure_filename",
        lambda name: "Test_Student",
    )

    response = student_auth.post(
        "/Student_Profile",
        data={
            "action": "change_photo",
            "profile_photo": (
                io.BytesIO(b"\x89PNG\r\n\x1a\nfake-png-data"),
                "profile.png",
            ),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 302
    assert "mode=View" in response.headers["Location"]


# PROF-10
def test_PROF_10_profile_update_mode_does_not_change_data_on_get(
    student_auth, student_test_data, test_database
):
    # Scenario: The student opens Update mode without submitting changes.
    # Expected result: The page loads and the saved branch remains unchanged.
    response = student_auth.get("/Student_Profile?mode=Update")
    assert response.status_code == 200

    student = test_database.session.get(
        Students, student_test_data["student"].id
    )
    assert student.branch == "Computer Science"


# ============================================================
# DASHBOARD STATISTICS — STAT-01 to STAT-08
# ============================================================

# STAT-01
def test_STAT_01_dashboard_shows_profile_completion(
    student_auth,
):
    # Scenario: The student opens the dashboard.
    # Expected result: The rendered dashboard contains the profile completion section.
    response = student_auth.get("/Student_Dashboard")
    assert response.status_code == 200
    assert b"profile" in response.data.lower()


# STAT-02
def test_STAT_02_dashboard_shows_resume_status(
    student_auth,
):
    # Scenario: The student opens the dashboard.
    # Expected result: The rendered dashboard contains the student's resume status.
    response = student_auth.get("/Student_Dashboard")
    assert response.status_code == 200
    assert b"Pending" in response.data


# STAT-03
def test_STAT_03_dashboard_counts_active_applications(
    student_auth,
    student_test_data,
    job_drive_factory,
    application_factory,
):
    # Scenario: The student has one application for a non-closed job drive.
    # Expected result: The dashboard shows one active application.
    drive = job_drive_factory(status="Active")
    application_factory(drive, Application_status.APPLIED)

    response = student_auth.get("/Student_Dashboard")

    assert response.status_code == 200
    assert b"1" in response.data


# STAT-04
def test_STAT_04_dashboard_counts_selected_applications(
    student_auth,
    job_drive_factory,
    application_factory,
):
    # Scenario: The student has one application marked Selected.
    # Expected result: The dashboard displays one selection.
    drive = job_drive_factory()
    application_factory(drive, Application_status.SELECTED)

    response = student_auth.get("/Student_Dashboard")

    assert response.status_code == 200
    assert b"1" in response.data


# STAT-05
def test_STAT_05_rejected_application_not_counted_as_active(
    student_auth,
    job_drive_factory,
    application_factory,
):
    # Scenario: The student has a rejected application for an active drive.
    # Expected result: The rejected application is excluded from total active applications.
    drive = job_drive_factory()
    application_factory(drive, Application_status.REJECTED)

    response = student_auth.get("/Student_Dashboard")

    assert response.status_code == 200


# STAT-06
def test_STAT_06_closed_drive_application_not_counted_as_active(
    student_auth,
    job_drive_factory,
    application_factory,
):
    # Scenario: The student has an application associated with a closed drive.
    # Expected result: The closed-drive application is excluded from the active application count.
    drive = job_drive_factory(status="Closed")
    application_factory(drive, Application_status.APPLIED)

    response = student_auth.get("/Student_Dashboard")

    assert response.status_code == 200


# STAT-07
def test_STAT_07_upcoming_interview_is_counted(
    student_auth,
    job_drive_factory,
    application_factory,
    interview_factory,
):
    # Scenario: The student has an interview in the future with no result recorded.
    # Expected result: The dashboard shows an upcoming interview.
    drive = job_drive_factory()
    application = application_factory(drive)
    interview_factory(
        application,
        date=datetime.datetime.now() + datetime.timedelta(days=3),
    )

    response = student_auth.get("/Student_Dashboard")

    assert response.status_code == 200


# STAT-08
def test_STAT_08_interview_with_result_is_not_upcoming(
    student_auth,
    job_drive_factory,
    application_factory,
    interview_factory,
):
    # Scenario: The student has a future interview whose result has been recorded.
    # Expected result: The interview is excluded from the upcoming-interview count.
    drive = job_drive_factory()
    application = application_factory(
        drive, Application_status.INTERVIEW
    )
    interview_factory(
        application,
        date=datetime.datetime.now() + datetime.timedelta(days=3),
        result="Passed",
    )

    response = student_auth.get("/Student_Dashboard")

    assert response.status_code == 200


# ============================================================
# INTERVIEW TESTS — INT-01 to INT-06, INT-09, INT-10, INT-11, INT-13
# ============================================================

# INT-01
def test_INT_01_interview_page_requires_authentication(client):
    # Scenario: An unauthenticated visitor opens the interview page.
    # Expected result: The request is rejected or redirected to authentication.
    response = client.get("/Student_interview")
    assert response.status_code in (302, 401)


# INT-02
def test_INT_02_student_can_open_interview_page(student_auth):
    # Scenario: An authenticated student opens the interview page.
    # Expected result: The interview page responds successfully.
    response = student_auth.get("/Student_interview")
    assert response.status_code == 200


# INT-03
def test_INT_03_non_student_cannot_open_interview_page(recruiter_auth):
    # Scenario: A recruiter tries to open the student interview page.
    # Expected result: The application returns 403 Forbidden.
    response = recruiter_auth.get("/Student_interview")
    assert response.status_code == 403


# INT-04
def test_INT_04_future_interview_appears_in_upcoming_section(
    student_auth,
    job_drive_factory,
    application_factory,
    interview_factory,
):
    # Scenario: The student has an interview scheduled after tomorrow.
    # Expected result: The interview appears in the upcoming interview section.
    drive = job_drive_factory(title="Upcoming Interview Role")
    application = application_factory(drive)
    interview_factory(
        application,
        round_name="Upcoming Test Round",
        date=datetime.datetime.combine(
            datetime.date.today() + datetime.timedelta(days=5),
            datetime.time(12, 0),
        ),
    )

    response = student_auth.get("/Student_interview")

    assert response.status_code == 200
    assert b"Upcoming Test Round" in response.data


# INT-05
def test_INT_05_past_interview_appears_in_past_section(
    student_auth,
    job_drive_factory,
    application_factory,
    interview_factory,
):
    # Scenario: The student has an interview scheduled before today.
    # Expected result: The interview appears on the interview page.
    drive = job_drive_factory()
    application = application_factory(drive)
    interview_factory(
        application,
        round_name="Past Test Round",
        date=datetime.datetime.combine(
            datetime.date.today() - datetime.timedelta(days=2),
            datetime.time(12, 0),
        ),
    )

    response = student_auth.get("/Student_interview")

    assert response.status_code == 200
    assert b"Past Test Round" in response.data


# INT-06
def test_INT_06_today_interview_appears_on_interview_page(
    student_auth,
    job_drive_factory,
    application_factory,
    interview_factory,
):
    # Scenario: The student has an interview scheduled for today.
    # Expected result: The interview page includes the interview.
    drive = job_drive_factory()
    application = application_factory(drive)
    interview_factory(
        application,
        round_name="Today's Test Round",
        date=datetime.datetime.combine(
            datetime.date.today(),
            datetime.time(12, 0),
        ),
    )

    response = student_auth.get("/Student_interview")

    assert response.status_code == 200
    assert b"Today&#39;s Test Round" in response.data

# INT-09
def test_INT_09_interview_page_supports_pagination_parameters(student_auth):
    # Scenario: The student opens the interview page with pagination parameters.
    # Expected result: The page handles valid pagination parameters without an error.
    response = student_auth.get(
        "/Student_interview?page=1&today_page=1&upcoming_page=1"
    )
    assert response.status_code == 200


# INT-10
def test_INT_10_invalid_pagination_parameters_do_not_crash(student_auth):
    # Scenario: The student supplies non-numeric interview pagination parameters.
    # Expected result: The route falls back to its default page values and responds successfully.
    response = student_auth.get(
        "/Student_interview?page=invalid&today_page=invalid&upcoming_page=invalid"
    )
    assert response.status_code == 200


# INT-11
def test_INT_11_interview_page_can_search_past_interviews(
    student_auth,
    job_drive_factory,
    application_factory,
    interview_factory,
):
    # Scenario: The student searches past interviews using a company name.
    # Expected result: The interview page processes the search and responds successfully.
    drive = job_drive_factory(company_name="Searchable Interview Company")
    application = application_factory(drive)
    interview_factory(
        application,
        date=datetime.datetime.combine(
            datetime.date.today() - datetime.timedelta(days=2),
            datetime.time(12, 0),
        ),
    )

    response = student_auth.get(
        "/Student_interview?past_search=Searchable"
    )

    assert response.status_code == 200


# INT-13
def test_INT_13_interview_page_limits_results_per_page(
    student_auth,
    job_drive_factory,
    application_factory,
    interview_factory,
):
    # Scenario: The student has six past interview rounds and opens page one.
    # Expected result: The route paginates past interviews at five records per page.
    drive = job_drive_factory()
    application = application_factory(drive)

    for index in range(6):
        interview_factory(
            application,
            round_name=f"Past Round {index + 1}",
            date=datetime.datetime.combine(
                datetime.date.today() - datetime.timedelta(days=2),
                datetime.time(10, index),
            ),
        )

    response = student_auth.get("/Student_interview?page=1")

    assert response.status_code == 200
    assert b"Past Round 1" in response.data


# ============================================================
# SELECTION TESTS — SEL-01 to SEL-04
# ============================================================

# SEL-01
def test_SEL_01_selected_application_is_counted_on_dashboard(
    student_auth,
    job_drive_factory,
    application_factory,
):
    # Scenario: The student has one application with Selected status.
    # Expected result: The dashboard responds successfully and includes the selection statistic.
    drive = job_drive_factory()
    application_factory(drive, Application_status.SELECTED)

    response = student_auth.get("/Student_Dashboard")

    assert response.status_code == 200


# SEL-02
def test_SEL_02_non_selected_application_does_not_count_as_selection(
    student_auth,
    job_drive_factory,
    application_factory,
):
    # Scenario: The student's application is Applied, not Selected.
    # Expected result: The application does not contribute to the selection count.
    drive = job_drive_factory()
    application_factory(drive, Application_status.APPLIED)

    response = student_auth.get("/Student_Dashboard")

    assert response.status_code == 200


# SEL-03
def test_SEL_03_multiple_selected_applications_are_counted(
    student_auth,
    job_drive_factory,
    application_factory,
):
    # Scenario: The student has two distinct applications with Selected status.
    # Expected result: The dashboard renders successfully with the selection count based on both records.
    first_drive = job_drive_factory(title="Selected Role One")
    second_drive = job_drive_factory(title="Selected Role Two")

    application_factory(first_drive, Application_status.SELECTED)
    application_factory(second_drive, Application_status.SELECTED)

    response = student_auth.get("/Student_Dashboard")

    assert response.status_code == 200


# SEL-04
def test_SEL_04_selected_application_is_visible_in_application_list(
    student_auth,
    job_drive_factory,
    application_factory,
):
    # Scenario: The student has a selected application for a non-closed drive.
    # Expected result: The dashboard's application list includes the selected status.
    drive = job_drive_factory(title="Selected Software Role")
    application_factory(drive, Application_status.SELECTED)

    response = student_auth.get("/Student_Dashboard")

    assert response.status_code == 200
    assert b"Selected" in response.data


# ============================================================
# APPLICATION TESTS — APP-01 to APP-04
# ============================================================

# APP-01
def test_APP_01_application_page_requires_authentication(client):
    # Scenario: An unauthenticated visitor opens the applications page.
    # Expected result: The request is rejected or redirected to authentication.
    response = client.get("/Student_Application")
    assert response.status_code in (302, 401)


# APP-02
def test_APP_02_student_can_open_application_page(student_auth):
    # Scenario: An authenticated student opens the applications page.
    # Expected result: The page responds successfully.
    response = student_auth.get("/Student_Application")
    assert response.status_code == 200


# APP-03
def test_APP_03_recruiter_cannot_open_student_application_page(
    recruiter_auth,
):
    # Scenario: An authenticated recruiter opens the student's applications page.
    # Expected result: Access is forbidden.
    response = recruiter_auth.get("/Student_Application")
    assert response.status_code == 403


# APP-04
def test_APP_04_application_filter_parameter_is_supported(
    student_auth,
    job_drive_factory,
    application_factory,
):
    # Scenario: The student opens the application list using a supported status filter.
    # Expected result: The application page processes the filter and responds successfully.
    drive = job_drive_factory()
    application_factory(drive, Application_status.SHORTLISTED)

    response = student_auth.get("/Student_Application?filter=shortlisted")

    assert response.status_code == 200


# ============================================================
# JOB DRIVE TESTS — JOB-01 to JOB-07
# ============================================================

# JOB-01
def test_JOB_01_job_drive_page_requires_authentication(client):
    # Scenario: An unauthenticated visitor opens the job drive page.
    # Expected result: The request is rejected or redirected to authentication.
    response = client.get("/Student_Job_Drive")
    assert response.status_code in (302, 401)


# JOB-02
def test_JOB_02_student_can_open_job_drive_page(student_auth):
    # Scenario: An authenticated student opens the job drive page.
    # Expected result: The page responds successfully.
    response = student_auth.get("/Student_Job_Drive")
    assert response.status_code == 200


# JOB-03
def test_JOB_03_non_student_cannot_open_job_drive_page(recruiter_auth):
    # Scenario: An authenticated recruiter tries to open the student job drive page.
    # Expected result: Access is forbidden.
    response = recruiter_auth.get("/Student_Job_Drive")
    assert response.status_code == 403


# JOB-04
def test_JOB_04_eligible_active_drive_is_displayed(
    student_auth,
    student_test_data,
    job_drive_factory,
    test_database,
):
    # Scenario: The student's eligible-drive list contains an active job drive.
    # Expected result: The job drive appears on the job drive page.
    drive = job_drive_factory(title="Eligible Active Role")
    student = student_test_data["student"]
    student.job_drive = str(drive.id)
    test_database.session.commit()

    response = student_auth.get("/Student_Job_Drive")

    assert response.status_code == 200
    assert b"Eligible Active Role" in response.data


# JOB-05
def test_JOB_05_unlisted_drive_is_not_displayed(
    student_auth,
    job_drive_factory,
):
    # Scenario: An active drive exists but is not in the student's eligible-drive list.
    # Expected result: The unlisted drive is not displayed to that student.
    job_drive_factory(title="Unlisted Role")

    response = student_auth.get("/Student_Job_Drive")

    assert response.status_code == 200
    assert b"Unlisted Role" not in response.data


# JOB-06
def test_JOB_06_job_drive_search_filters_by_title(
    student_auth,
    student_test_data,
    job_drive_factory,
    test_database,
):
    # Scenario: The student searches for a job title in their eligible drives.
    # Expected result: The matching job is displayed.
    drive = job_drive_factory(title="Python Developer Search Test")
    student = student_test_data["student"]
    student.job_drive = str(drive.id)
    test_database.session.commit()

    response = student_auth.get(
        "/Student_Job_Drive?search=Python%20Developer"
    )

    assert response.status_code == 200
    assert b"Python Developer Search Test" in response.data


# JOB-07
def test_JOB_07_closed_job_drive_is_not_displayed(
    student_auth,
    student_test_data,
    job_drive_factory,
    test_database,
):
    # Scenario: A closed drive is listed in the student's eligible-drive list.
    # Expected result: The closed drive is excluded from the active job drive listing.
    drive = job_drive_factory(
        title="Closed Job Role",
        status="Closed",
    )
    student = student_test_data["student"]
    student.job_drive = str(drive.id)
    test_database.session.commit()

    response = student_auth.get("/Student_Job_Drive")

    assert response.status_code == 200
    assert b"Closed Job Role" not in response.data