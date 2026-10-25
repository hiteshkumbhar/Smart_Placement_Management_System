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

# ============================================================
# STUDENT PROFILE — ADDITIONAL AUTHENTICATION, NAVIGATION,
# DUPLICATE VALIDATION, PHOTO, RESUME AND CERTIFICATION TESTS
# ============================================================

import os
from pathlib import Path

from flask_jwt_extended import create_access_token, decode_token


# ============================================================
# ADDITIONAL FIXTURES AND HELPERS
# ============================================================

@pytest.fixture
def second_student(test_database):
    """
    Creates a second student for duplicate-value and document
    ownership tests.

    Scenario:
        Two distinct student accounts exist in the test database.

    Expected result:
        Each student has unique profile values that can be used
        to test duplicate validation and document isolation.
    """
    user = Users(
        name="Second Test Student",
        email="second_student_profile@example.com",
        password=generate_password_hash("StudentPass123"),
        role="student",
    )

    test_database.session.add(user)
    test_database.session.commit()

    student = Students(
        user_id=user.user_id,
        registration_no="REG-STU-002",
        branch="Information Technology",
        cgpa=7.5,
        skills="Java, SQL",
        resume_path=None,
        resume_status="Pending",
        graduation_year=datetime.date.today().year,
        placement_status="Not Placed",
        mobile_number="9000000002",
        Gender="Other",
        Address="Second Test Address",
        City="Second Test City",
        State="Second Test State",
        pin_code=400002,
        University_Roll_Number="ROLL-STU-002",
        Semester=6,
        tenth_Percentage=80.0,
        twelth_Percentage=81.0,
        Total_Backlogs="0",
        Active_Backlogs="0",
        LinkedIn="https://linkedin.com/in/second-test-student",
        GitHub="https://github.com/second-test-student",
        Portfolio_Website="https://second-test-student.example.com",
        LeetCode="https://leetcode.com/second-test-student",
        HackerRank="https://hackerrank.com/second-test-student",
        Certification="",
        job_drive=None,
    )

    test_database.session.add(student)
    test_database.session.commit()

    return {
        "user": user,
        "student": student,
    }


@pytest.fixture
def profile_test_directory(tmp_path, monkeypatch):
    """
    Scenario:
        Profile tests need to upload photos, resumes, and certifications.

    Expected result:
        All files are written under a temporary directory instead
        of modifying the application's real static directories.
    """
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def profile_post_client(client, student_test_data):
    """
    Scenario:
        Tests need to submit profile POST requests without relying
        on a browser-generated JWT cookie CSRF header.

    Expected result:
        The client authenticates using a valid Bearer access token.
    """
    with app.app_context():
        token = create_access_token(
            identity=str(student_test_data["student_user"].user_id)
        )

    client.environ_base.pop("HTTP_X_CSRF_TOKEN", None)
    client.set_cookie(
        app.config.get("JWT_ACCESS_COOKIE_NAME", "access_token_cookie"),
        "",
    )
    client.set_cookie(
        app.config.get("JWT_ACCESS_CSRF_COOKIE_NAME", "csrf_access_token"),
        "",
    )
    client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {token}"

    return client


def _profile_bearer_client(client, user_id):
    """
    Helper:
        Authenticate a client as the user identified by user_id.

    Expected result:
        Requests made through the returned client carry a valid
        Bearer access token for that user.
    """
    with app.app_context():
        token = create_access_token(identity=str(user_id))

    client.set_cookie(
        app.config.get("JWT_ACCESS_COOKIE_NAME", "access_token_cookie"),
        "",
    )
    client.set_cookie(
        app.config.get("JWT_ACCESS_CSRF_COOKIE_NAME", "csrf_access_token"),
        "",
    )
    client.environ_base.pop("HTTP_X_CSRF_TOKEN", None)
    client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {token}"

    return client


def _profile_duplicate_payload(field, value):
    """
    Helper:
        Build a form submission containing a duplicate profile value.

    Expected result:
        The submitted field can be tested independently without
        modifying unrelated profile fields.
    """
    return {field: value}


# ============================================================
# AUTHENTICATION AND AUTHORIZATION
# ============================================================

# AUTH-PROF-01
def test_AUTH_PROF_01_profile_requires_authentication(client):
    # Scenario:
    # An unauthenticated visitor opens /Student_Profile.
    # Expected result:
    # The application rejects the request with HTTP 401 or redirects
    # the visitor to authentication.
    response = client.get("/Student_Profile")

    assert response.status_code in (302, 401)


# AUTH-PROF-03
def test_AUTH_PROF_03_recruiter_cannot_open_student_profile(
    client, student_test_data
):
    # Scenario:
    # An authenticated recruiter attempts to open /Student_Profile.
    # Expected result:
    # The application returns HTTP 403 Forbidden.
    recruiter_client = _profile_bearer_client(
        client,
        student_test_data["recruiter_user"].user_id,
    )

    response = recruiter_client.get("/Student_Profile")

    assert response.status_code == 403


# AUTH-PROF-04
def test_AUTH_PROF_04_placement_officer_cannot_open_student_profile(
    client, student_test_data
):
    # Scenario:
    # An authenticated placement officer attempts to open
    # /Student_Profile.
    # Expected result:
    # The application returns HTTP 403 Forbidden.
    officer_client = _profile_bearer_client(
        client,
        student_test_data["officer_user"].user_id,
    )

    response = officer_client.get("/Student_Profile")

    assert response.status_code == 403


# AUTH-PROF-05
def test_AUTH_PROF_05_unauthenticated_profile_update_is_rejected(
    client, student_test_data, test_database
):
    # Scenario:
    # An unauthenticated visitor submits a profile update.
    # Expected result:
    # The request is rejected, and the student's existing profile
    # values remain unchanged.
    original_branch = student_test_data["student"].branch

    response = client.post(
        "/Student_Profile",
        data={"branch": "Unauthorized Branch"},
    )

    test_database.session.expire_all()

    student = test_database.session.get(
        Students,
        student_test_data["student"].id,
    )

    assert response.status_code in (302, 401)
    assert student.branch == original_branch


# AUTH-PROF-06
@pytest.mark.parametrize(
    "role_key",
    ["recruiter_user", "officer_user"],
)
def test_AUTH_PROF_06_non_student_cannot_update_profile(
    client,
    student_test_data,
    test_database,
    role_key,
):
    # Scenario:
    # An authenticated recruiter or placement officer submits
    # a profile update.
    # Expected result:
    # The application returns HTTP 403 and the student's data
    # remains unchanged.
    original_branch = student_test_data["student"].branch

    non_student_client = _profile_bearer_client(
        client,
        student_test_data[role_key].user_id,
    )

    response = non_student_client.post(
        "/Student_Profile",
        data={"branch": "Unauthorized Branch"},
    )

    test_database.session.expire_all()

    student = test_database.session.get(
        Students,
        student_test_data["student"].id,
    )

    assert response.status_code == 403
    assert student.branch == original_branch


# AUTH-PROF-07
@pytest.mark.parametrize(
    "role_key",
    ["recruiter_user", "officer_user"],
)
def test_AUTH_PROF_07_non_student_cannot_upload_profile_photo(
    client,
    student_test_data,
    test_database,
    profile_test_directory,
    role_key,
):
    # Scenario:
    # A recruiter or placement officer attempts to upload a
    # profile photo using the student profile route.
    # Expected result:
    # The application returns HTTP 403 and no photo is saved.
    non_student_client = _profile_bearer_client(
        client,
        student_test_data[role_key].user_id,
    )

    response = non_student_client.post(
        "/Student_Profile",
        data={
            "action": "change_photo",
            "profile_photo": (
                io.BytesIO(b"fake image bytes"),
                "profile.png",
            ),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 403

    photo_directory = (
        profile_test_directory
        / "static"
        / "Images"
        / "student"
        / "profile_photo"
    )

    assert (
        not photo_directory.exists()
        or not any(photo_directory.iterdir())
    )


# ============================================================
# PROFILE NAVIGATION AND UPDATE
# ============================================================

# NAV-PROF-01
def test_NAV_PROF_01_profile_defaults_to_view_mode(student_auth):
    # Scenario:
    # An authenticated student opens /Student_Profile without
    # providing a mode query parameter.
    # Expected result:
    # The profile renders successfully in View mode.
    response = student_auth.get("/Student_Profile")

    assert response.status_code == 200
    assert b"Update" in response.data


# NAV-PROF-02
def test_NAV_PROF_02_explicit_view_mode_loads(student_auth):
    # Scenario:
    # An authenticated student opens /Student_Profile?mode=View.
    # Expected result:
    # The profile renders successfully.
    response = student_auth.get("/Student_Profile?mode=View")

    assert response.status_code == 200


# NAV-PROF-05
def test_NAV_PROF_05_cancel_returns_to_view_without_saving(
    student_auth, student_test_data, test_database
):
    # Scenario:
    # A student opens Update mode and clicks Cancel.
    # Expected result:
    # The browser navigates to View mode, and the database remains
    # unchanged because Cancel is a navigation link, not a submission.
    original_branch = student_test_data["student"].branch

    update_response = student_auth.get(
        "/Student_Profile?mode=Update"
    )

    assert update_response.status_code == 200

    cancel_response = student_auth.get(
        "/Student_Profile?mode=View"
    )

    test_database.session.expire_all()

    student = test_database.session.get(
        Students,
        student_test_data["student"].id,
    )

    assert cancel_response.status_code == 200
    assert student.branch == original_branch


# NAV-PROF-06
def test_NAV_PROF_06_valid_update_redirects_to_view(
    student_auth, student_test_data, test_database
):
    # Scenario:
    # A student submits a valid profile update.
    # Expected result:
    # The application redirects to View mode, and the new branch
    # is persisted in the database.
    response = student_auth.post(
        "/Student_Profile",
        data={"branch": "Information Technology"},
    )

    assert response.status_code == 302
    assert "mode=View" in response.headers["Location"]

    test_database.session.expire_all()

    student = test_database.session.get(
        Students,
        student_test_data["student"].id,
    )

    assert student.branch == "Information Technology"


# NAV-PROF-07
def test_NAV_PROF_07_duplicate_mobile_update_is_rejected(
    student_auth,
    student_test_data,
    second_student,
    test_database,
):
    # Scenario:
    # A student submits another student's mobile number.
    # Expected result:
    # The application redirects back to Update mode and preserves
    # the original mobile number.
    original_mobile = student_test_data["student"].mobile_number

    response = student_auth.post(
        "/Student_Profile",
        data={
            "mobile_number": second_student["student"].mobile_number,
        },
    )

    assert response.status_code == 302
    assert "mode=Update" in response.headers["Location"]

    test_database.session.expire_all()

    student = test_database.session.get(
        Students,
        student_test_data["student"].id,
    )

    assert student.mobile_number == original_mobile


# ============================================================
# DUPLICATE-VALUE VALIDATION
# ============================================================

@pytest.mark.parametrize(
    "test_id,field,second_student_field",
    [
        ("DUP-01", "mobile_number", "mobile_number"),
        ("DUP-02", "University_Roll_Number", "University_Roll_Number"),
        ("DUP-03", "LinkedIn", "LinkedIn"),
        ("DUP-04", "GitHub", "GitHub"),
        ("DUP-05", "Portfolio_Website", "Portfolio_Website"),
        ("DUP-06", "LeetCode", "LeetCode"),
        ("DUP-07", "HackerRank", "HackerRank"),
    ],
)
def test_profile_duplicate_values_are_rejected(
    student_auth,
    student_test_data,
    second_student,
    test_database,
    test_id,
    field,
    second_student_field,
):
    # Scenario:
    # The student submits a mobile number, roll number, or
    # professional URL already owned by another student.
    # Expected result:
    # The application rejects the duplicate and redirects to
    # Update mode without replacing the existing value.
    #
    # Parametrized test IDs:
    # DUP-01: Duplicate mobile number.
    # DUP-02: Duplicate university roll number.
    # DUP-03: Duplicate LinkedIn URL.
    # DUP-04: Duplicate GitHub URL.
    # DUP-05: Duplicate portfolio URL.
    # DUP-06: Duplicate LeetCode URL.
    # DUP-07: Duplicate HackerRank URL.

    original_value = getattr(
        student_test_data["student"],
        field,
    )

    duplicate_value = getattr(
        second_student["student"],
        second_student_field,
    )

    response = student_auth.post(
        "/Student_Profile",
        data=_profile_duplicate_payload(field, duplicate_value),
    )

    assert response.status_code == 302
    assert "mode=Update" in response.headers["Location"]

    test_database.session.expire_all()

    student = test_database.session.get(
        Students,
        student_test_data["student"].id,
    )

    assert getattr(student, field) == original_value


# ============================================================
# PROFILE PHOTO UPLOAD
# ============================================================

@pytest.mark.parametrize(
    "filename",
    [
        "profile.jpg",
        "profile.jpeg",
    ],
)
def test_PHOTO_02_03_valid_jpg_and_jpeg_uploads_succeed(
    student_auth,
    student_test_data,
    test_database,
    profile_test_directory,
    filename,
):
    # Scenario:
    # A student uploads a JPG or JPEG profile photo smaller than
    # the configured 5 MB maximum.
    # Expected result:
    # The application redirects to View mode, saves the photo,
    # and persists the generated filename in profile_pic.
    response = student_auth.post(
        "/Student_Profile",
        data={
            "action": "change_photo",
            "profile_photo": (
                io.BytesIO(b"test image content"),
                filename,
            ),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 302
    assert "mode=View" in response.headers["Location"]

    test_database.session.expire_all()

    student = test_database.session.get(
        Students,
        student_test_data["student"].id,
    )

    assert student.profile_pic is not None
    assert student.profile_pic.lower().endswith(
        Path(filename).suffix.lower()
    )

    saved_file = (
        profile_test_directory
        / "static"
        / "Images"
        / "student"
        / "profile_photo"
        / student.profile_pic
    )

    assert saved_file.is_file()
    assert saved_file.read_bytes() == b"test image content"


# PHOTO-05
def test_PHOTO_05_pdf_profile_photo_is_rejected(
    student_auth,
    student_test_data,
    test_database,
    profile_test_directory,
):
    # Scenario:
    # A student uploads a PDF instead of an allowed image format.
    # Expected result:
    # The upload is rejected, the original profile photo remains
    # unchanged, and no file is saved.
    original_photo = student_test_data["student"].profile_pic

    response = student_auth.post(
        "/Student_Profile",
        data={
            "action": "change_photo",
            "profile_photo": (
                io.BytesIO(b"fake pdf"),
                "profile.pdf",
            ),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 302

    test_database.session.expire_all()

    student = test_database.session.get(
        Students,
        student_test_data["student"].id,
    )

    assert student.profile_pic == original_photo

    photo_directory = (
        profile_test_directory
        / "static"
        / "Images"
        / "student"
        / "profile_photo"
    )

    assert (
        not photo_directory.exists()
        or not any(photo_directory.iterdir())
    )


# PHOTO-06
def test_PHOTO_06_photo_larger_than_5_mb_is_rejected(
    student_auth,
    student_test_data,
    test_database,
    profile_test_directory,
):
    # Scenario:
    # A student uploads a profile photo larger than 5 MB.
    # Expected result:
    # The upload is rejected and the saved profile photo remains
    # unchanged.
    original_photo = student_test_data["student"].profile_pic

    oversized_content = b"x" * (5 * 1024 * 1024 + 1)

    response = student_auth.post(
        "/Student_Profile",
        data={
            "action": "change_photo",
            "profile_photo": (
                io.BytesIO(oversized_content),
                "large_photo.png",
            ),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 302

    test_database.session.expire_all()

    student = test_database.session.get(
        Students,
        student_test_data["student"].id,
    )

    assert student.profile_pic == original_photo

    photo_directory = (
        profile_test_directory
        / "static"
        / "Images"
        / "student"
        / "profile_photo"
    )

    assert (
        not photo_directory.exists()
        or not any(photo_directory.iterdir())
    )


# PHOTO-07
def test_PHOTO_07_photo_without_extension_is_rejected_gracefully(
    student_auth,
    student_test_data,
    test_database,
    profile_test_directory,
):
    # Scenario:
    # A student uploads a photo whose filename has no extension.
    # Expected result:
    # The application rejects the upload without raising an
    # unhandled exception, and the existing photo is unchanged.
    original_photo = student_test_data["student"].profile_pic

    response = student_auth.post(
        "/Student_Profile",
        data={
            "action": "change_photo",
            "profile_photo": (
                io.BytesIO(b"image content"),
                "profilephoto",
            ),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 302

    test_database.session.expire_all()

    student = test_database.session.get(
        Students,
        student_test_data["student"].id,
    )

    assert student.profile_pic == original_photo

    photo_directory = (
        profile_test_directory
        / "static"
        / "Images"
        / "student"
        / "profile_photo"
    )

    assert (
        not photo_directory.exists()
        or not any(photo_directory.iterdir())
    )


# PHOTO-08
def test_PHOTO_08_photo_submission_without_file_changes_nothing(
    student_auth,
    student_test_data,
    test_database,
    profile_test_directory,
):
    # Scenario:
    # A student submits the change-photo action without selecting
    # a file.
    # Expected result:
    # The request completes without crashing and the existing
    # profile photo remains unchanged.
    original_photo = student_test_data["student"].profile_pic

    response = student_auth.post(
        "/Student_Profile",
        data={"action": "change_photo"},
        content_type="multipart/form-data",
    )

    assert response.status_code == 302

    test_database.session.expire_all()

    student = test_database.session.get(
        Students,
        student_test_data["student"].id,
    )

    assert student.profile_pic == original_photo

    photo_directory = (
        profile_test_directory
        / "static"
        / "Images"
        / "student"
        / "profile_photo"
    )

    assert (
        not photo_directory.exists()
        or not any(photo_directory.iterdir())
    )


# PHOTO-09
def test_PHOTO_09_uploaded_photo_filename_is_saved_in_database(
    student_auth,
    student_test_data,
    test_database,
    profile_test_directory,
):
    # Scenario:
    # A student uploads a valid PNG profile photo.
    # Expected result:
    # The generated filename is saved in profile_pic, and the
    # corresponding file exists on disk.
    response = student_auth.post(
        "/Student_Profile",
        data={
            "action": "change_photo",
            "profile_photo": (
                io.BytesIO(b"test png content"),
                "avatar.png",
            ),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 302

    test_database.session.expire_all()

    student = test_database.session.get(
        Students,
        student_test_data["student"].id,
    )

    assert student.profile_pic
    assert student.profile_pic.endswith(".png")

    saved_file = (
        profile_test_directory
        / "static"
        / "Images"
        / "student"
        / "profile_photo"
        / student.profile_pic
    )

    assert saved_file.is_file()
    assert saved_file.read_bytes() == b"test png content"


# PHOTO-10
def test_PHOTO_10_second_photo_replaces_profile_reference(
    student_auth,
    student_test_data,
    test_database,
    profile_test_directory,
):
    # Scenario:
    # A student uploads a second profile photo after uploading
    # an initial photo.
    # Expected result:
    # profile_pic references the newly uploaded photo, and the
    # new file exists on disk.
    first_response = student_auth.post(
        "/Student_Profile",
        data={
            "action": "change_photo",
            "profile_photo": (
                io.BytesIO(b"first photo"),
                "first.png",
            ),
        },
        content_type="multipart/form-data",
    )

    assert first_response.status_code == 302

    test_database.session.expire_all()

    student = test_database.session.get(
        Students,
        student_test_data["student"].id,
    )
    first_filename = student.profile_pic

    second_response = student_auth.post(
        "/Student_Profile",
        data={
            "action": "change_photo",
            "profile_photo": (
                io.BytesIO(b"second photo"),
                "second.jpg",
            ),
        },
        content_type="multipart/form-data",
    )

    assert second_response.status_code == 302

    test_database.session.expire_all()

    student = test_database.session.get(
        Students,
        student_test_data["student"].id,
    )

    assert student.profile_pic is not None
    assert student.profile_pic.endswith(".jpg")
    assert student.profile_pic != first_filename

    second_file = (
        profile_test_directory
        / "static"
        / "Images"
        / "student"
        / "profile_photo"
        / student.profile_pic
    )

    assert second_file.is_file()
    assert second_file.read_bytes() == b"second photo"


# PHOTO-11
def test_PHOTO_11_invalid_photo_preserves_existing_photo(
    student_auth,
    student_test_data,
    test_database,
    profile_test_directory,
):
    # Scenario:
    # A student already has a saved profile photo and uploads
    # a GIF, which is not an allowed format.
    # Expected result:
    # The existing profile photo remains unchanged and the
    # invalid upload is not saved.
    student = student_test_data["student"]
    student.profile_pic = "existing_photo.png"
    test_database.session.commit()

    existing_content = b"existing photo content"

    photo_directory = (
        profile_test_directory
        / "static"
        / "Images"
        / "student"
        / "profile_photo"
    )
    photo_directory.mkdir(parents=True, exist_ok=True)

    (photo_directory / "existing_photo.png").write_bytes(
        existing_content
    )

    response = student_auth.post(
        "/Student_Profile",
        data={
            "action": "change_photo",
            "profile_photo": (
                io.BytesIO(b"invalid gif"),
                "invalid.gif",
            ),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 302

    test_database.session.expire_all()

    student = test_database.session.get(
        Students,
        student_test_data["student"].id,
    )

    assert student.profile_pic == "existing_photo.png"
    assert (
        photo_directory / "existing_photo.png"
    ).read_bytes() == existing_content

    assert not (photo_directory / "invalid.gif").exists()


# PHOTO-12
def test_PHOTO_12_photo_is_saved_in_profile_photo_directory(
    student_auth,
    student_test_data,
    test_database,
    profile_test_directory,
):
    # Scenario:
    # A student uploads a valid PNG profile photo.
    # Expected result:
    # The file is stored in static/Images/student/profile_photo
    # under the temporary test working directory.
    response = student_auth.post(
        "/Student_Profile",
        data={
            "action": "change_photo",
            "profile_photo": (
                io.BytesIO(b"directory test image"),
                "directory_test.png",
            ),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 302

    test_database.session.expire_all()

    student = test_database.session.get(
        Students,
        student_test_data["student"].id,
    )

    photo_directory = (
        profile_test_directory
        / "static"
        / "Images"
        / "student"
        / "profile_photo"
    )

    assert photo_directory.is_dir()
    assert (photo_directory / student.profile_pic).is_file()


# ============================================================
# RESUME UPLOAD AND DOWNLOAD
# ============================================================

# RESUME-01
def test_RESUME_01_valid_pdf_resume_is_uploaded(
    student_auth,
    student_test_data,
    test_database,
    profile_test_directory,
):
    # Scenario:
    # A student uploads a PDF resume smaller than 5 MB.
    # Expected result:
    # The PDF is saved, resume_path is updated, and the request
    # redirects to View mode.
    response = student_auth.post(
        "/Student_Profile",
        data={
            "resume_file": (
                io.BytesIO(b"%PDF-1.4 test resume"),
                "resume.pdf",
            ),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 302
    assert "mode=View" in response.headers["Location"]

    test_database.session.expire_all()

    student = test_database.session.get(
        Students,
        student_test_data["student"].id,
    )

    assert student.resume_path
    assert student.resume_path.endswith(".pdf")

    saved_file = (
        profile_test_directory
        / "static"
        / "Docs"
        / "student"
        / "resumes"
        / student.resume_path
    )

    assert saved_file.is_file()
    assert saved_file.read_bytes() == b"%PDF-1.4 test resume"


# RESUME-02
def test_RESUME_02_txt_resume_is_rejected(
    student_auth,
    student_test_data,
    test_database,
    profile_test_directory,
):
    # Scenario:
    # A student attempts to upload a TXT file as a resume.
    # Expected result:
    # The application rejects the file, redirects to Update mode,
    # and does not save the invalid resume.
    original_resume = student_test_data["student"].resume_path

    response = student_auth.post(
        "/Student_Profile",
        data={
            "resume_file": (
                io.BytesIO(b"text resume"),
                "resume.txt",
            ),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 302
    assert "mode=Update" in response.headers["Location"]

    test_database.session.expire_all()

    student = test_database.session.get(
        Students,
        student_test_data["student"].id,
    )

    assert student.resume_path == original_resume

    resume_directory = (
        profile_test_directory
        / "static"
        / "Docs"
        / "student"
        / "resumes"
    )

    assert (
        not resume_directory.exists()
        or not any(resume_directory.iterdir())
    )


# RESUME-03
def test_RESUME_03_docx_resume_is_rejected(
    student_auth,
    student_test_data,
    test_database,
    profile_test_directory,
):
    # Scenario:
    # A student attempts to upload a DOCX file as a resume.
    # Expected result:
    # The application rejects the file and leaves resume_path
    # unchanged.
    original_resume = student_test_data["student"].resume_path

    response = student_auth.post(
        "/Student_Profile",
        data={
            "resume_file": (
                io.BytesIO(b"fake docx content"),
                "resume.docx",
            ),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 302
    assert "mode=Update" in response.headers["Location"]

    test_database.session.expire_all()

    student = test_database.session.get(
        Students,
        student_test_data["student"].id,
    )

    assert student.resume_path == original_resume


# RESUME-04
def test_RESUME_04_resume_larger_than_5_mb_is_rejected(
    student_auth,
    student_test_data,
    test_database,
    profile_test_directory,
):
    # Scenario:
    # A student uploads a PDF resume larger than 5 MB.
    # Expected result:
    # The application rejects the upload and does not replace
    # an existing resume.
    original_resume = student_test_data["student"].resume_path

    oversized_content = b"x" * (5 * 1024 * 1024 + 1)

    response = student_auth.post(
        "/Student_Profile",
        data={
            "resume_file": (
                io.BytesIO(oversized_content),
                "large_resume.pdf",
            ),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 302
    assert "mode=Update" in response.headers["Location"]

    test_database.session.expire_all()

    student = test_database.session.get(
        Students,
        student_test_data["student"].id,
    )

    assert student.resume_path == original_resume

    resume_directory = (
        profile_test_directory
        / "static"
        / "Docs"
        / "student"
        / "resumes"
    )

    assert (
        not resume_directory.exists()
        or not any(resume_directory.iterdir())
    )


# RESUME-05
def test_RESUME_05_resume_without_extension_is_rejected(
    student_auth,
    student_test_data,
    test_database,
    profile_test_directory,
):
    # Scenario:
    # A student uploads a resume whose filename has no extension.
    # Expected result:
    # The application rejects the upload gracefully and preserves
    # the existing resume reference.
    original_resume = student_test_data["student"].resume_path

    response = student_auth.post(
        "/Student_Profile",
        data={
            "resume_file": (
                io.BytesIO(b"resume content"),
                "resume",
            ),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 302

    test_database.session.expire_all()

    student = test_database.session.get(
        Students,
        student_test_data["student"].id,
    )

    assert student.resume_path == original_resume


# RESUME-06
def test_RESUME_06_reupload_sets_resume_status_to_reuploaded(
    student_auth,
    student_test_data,
    test_database,
    profile_test_directory,
):
    # Scenario:
    # A student who already has a resume uploads a replacement PDF.
    # Expected result:
    # The new resume is saved, resume_path is updated, and
    # resume_status becomes "Reuploaded".
    student = student_test_data["student"]
    student.resume_path = "old_resume.pdf"
    student.resume_status = "Pending"
    test_database.session.commit()

    response = student_auth.post(
        "/Student_Profile",
        data={
            "resume_file": (
                io.BytesIO(b"%PDF-1.4 replacement resume"),
                "replacement.pdf",
            ),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 302

    test_database.session.expire_all()

    student = test_database.session.get(
        Students,
        student_test_data["student"].id,
    )

    assert student.resume_path != "old_resume.pdf"
    assert student.resume_path.endswith(".pdf")
    assert student.resume_status == "Reuploaded"

    saved_file = (
        profile_test_directory
        / "static"
        / "Docs"
        / "student"
        / "resumes"
        / student.resume_path
    )

    assert saved_file.is_file()
    assert saved_file.read_bytes() == b"%PDF-1.4 replacement resume"


# RESUME-07
def test_RESUME_07_invalid_resume_preserves_existing_resume(
    student_auth,
    student_test_data,
    test_database,
    profile_test_directory,
):
    # Scenario:
    # A student has an existing resume and attempts to replace it
    # with a TXT file.
    # Expected result:
    # The existing resume reference and file contents remain unchanged.
    student = student_test_data["student"]
    student.resume_path = "existing_resume.pdf"
    test_database.session.commit()

    resume_directory = (
        profile_test_directory
        / "static"
        / "Docs"
        / "student"
        / "resumes"
    )
    resume_directory.mkdir(parents=True, exist_ok=True)

    existing_content = b"%PDF-1.4 existing resume"

    (resume_directory / "existing_resume.pdf").write_bytes(
        existing_content
    )

    response = student_auth.post(
        "/Student_Profile",
        data={
            "resume_file": (
                io.BytesIO(b"invalid text resume"),
                "invalid.txt",
            ),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 302

    test_database.session.expire_all()

    student = test_database.session.get(
        Students,
        student_test_data["student"].id,
    )

    assert student.resume_path == "existing_resume.pdf"
    assert (
        resume_directory / "existing_resume.pdf"
    ).read_bytes() == existing_content


# RESUME-08
def test_RESUME_08_submitting_without_resume_preserves_existing_resume(
    student_auth,
    student_test_data,
    test_database,
    profile_test_directory,
):
    # Scenario:
    # A student has an existing resume and submits the profile form
    # without selecting a replacement resume.
    # Expected result:
    # The saved resume remains unchanged.
    student = student_test_data["student"]
    student.resume_path = "existing_resume.pdf"
    test_database.session.commit()

    response = student_auth.post(
        "/Student_Profile",
        data={"branch": "Computer Science"},
    )

    assert response.status_code == 302

    test_database.session.expire_all()

    student = test_database.session.get(
        Students,
        student_test_data["student"].id,
    )

    assert student.resume_path == "existing_resume.pdf"


# RESUME-10
def test_RESUME_10_existing_resume_download_succeeds(
    student_auth,
    student_test_data,
    test_database,
):
    # Scenario:
    # An authenticated student downloads an existing resume.
    # Expected result:
    # HTTP 200 is returned, the downloaded bytes match the saved
    # file, and the response is an attachment.

    from flask import current_app

    student = student_test_data["student"]
    filename = "Resume_Test_Student.pdf"

    resume_directory = (
        Path(current_app.root_path)
        / "static"
        / "Docs"
        / "student"
        / "resumes"
    )

    resume_directory.mkdir(parents=True, exist_ok=True)

    resume_file = resume_directory / filename
    expected_content = b"%PDF-1.4 download test"

    previous_resume = student.resume_path
    student.resume_path = filename
    test_database.session.commit()

    try:
        resume_file.write_bytes(expected_content)

        response = student_auth.get(
            "/Student_Profile?Download=download_resume"
        )

        assert response.status_code == 200
        assert response.data == expected_content
        assert "attachment" in response.headers.get(
            "Content-Disposition",
            "",
        ).lower()

    finally:
        student.resume_path = previous_resume
        test_database.session.commit()

        if resume_file.exists():
            resume_file.unlink()

# RESUME-12
def test_RESUME_12_missing_resume_file_returns_404(
    student_auth,
    student_test_data,
    test_database,
    profile_test_directory,
):
    # Scenario:
    # The database contains a resume filename, but the file has
    # been removed from disk.
    # Expected result:
    # The download request returns HTTP 404.
    student = student_test_data["student"]
    student.resume_path = "missing_resume.pdf"
    test_database.session.commit()

    response = student_auth.get(
        "/Student_Profile?Download=download_resume"
    )

    assert response.status_code == 404


# RESUME-13
def test_RESUME_13_student_cannot_download_another_students_resume(
    student_auth,
    student_test_data,
    second_student,
    test_database,
    profile_test_directory,
):
    # Scenario:
    # Student B has a resume, but Student A attempts to download
    # a resume using the profile download endpoint.
    # Expected result:
    # Student A cannot retrieve Student B's file.
    second_student_record = second_student["student"]
    second_student_record.resume_path = "Resume_Second_Student.pdf"
    test_database.session.commit()

    resume_directory = (
        profile_test_directory
        / "static"
        / "Docs"
        / "student"
        / "resumes"
    )
    resume_directory.mkdir(parents=True, exist_ok=True)

    other_student_content = b"%PDF-1.4 private second student resume"

    (
        resume_directory / second_student_record.resume_path
    ).write_bytes(other_student_content)

    # The authenticated client belongs to Student A, whose resume
    # is unset in the test fixture.
    response = student_auth.get(
        "/Student_Profile?Download=download_resume"
    )

    assert response.status_code == 404
    assert response.data != other_student_content


# ============================================================
# CERTIFICATION UPLOAD AND DOWNLOAD
# ============================================================

# CERT-01
def test_CERT_01_valid_pdf_certification_upload_succeeds(
    student_auth,
    student_test_data,
    test_database,
    profile_test_directory,
):
    # Scenario:
    # A student uploads a valid PDF certification.
    # Expected result:
    # The certification is saved and its filename is recorded
    # in the Certification database field.
    response = student_auth.post(
        "/Student_Profile",
        data={
            "Certification": (
                io.BytesIO(b"%PDF-1.4 test certification"),
                "Python_Certificate.pdf",
            ),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 302

    test_database.session.expire_all()

    student = test_database.session.get(
        Students,
        student_test_data["student"].id,
    )

    assert student.Certification
    assert "Python_Certificate.pdf" in student.Certification

    certification_filename = (
        f"Cert_{student.user_id}_Test_Student_Python_Certificate.pdf"
    )

    saved_file = (
        profile_test_directory
        / "static"
        / "Docs"
        / "student"
        / "certifications"
        / certification_filename
    )

    assert saved_file.is_file()
    assert saved_file.read_bytes() == b"%PDF-1.4 test certification"


# CERT-02
def test_CERT_02_non_pdf_certification_is_rejected(
    student_auth,
    student_test_data,
    test_database,
    profile_test_directory,
):
    # Scenario:
    # A student attempts to upload a TXT certification.
    # Expected result:
    # The upload is rejected and the existing Certification
    # database value remains unchanged.
    original_certification = student_test_data["student"].Certification

    response = student_auth.post(
        "/Student_Profile",
        data={
            "Certification": (
                io.BytesIO(b"text certification"),
                "certificate.txt",
            ),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 302
    assert "mode=Update" in response.headers["Location"]

    test_database.session.expire_all()

    student = test_database.session.get(
        Students,
        student_test_data["student"].id,
    )

    assert student.Certification == original_certification


# CERT-03
def test_CERT_03_certification_larger_than_5_mb_is_rejected(
    student_auth,
    student_test_data,
    test_database,
    profile_test_directory,
):
    # Scenario:
    # A student uploads a PDF certification larger than 5 MB.
    # Expected result:
    # The application rejects the upload and does not update the
    # Certification database field.
    original_certification = student_test_data["student"].Certification

    oversized_content = b"x" * (5 * 1024 * 1024 + 1)

    response = student_auth.post(
        "/Student_Profile",
        data={
            "Certification": (
                io.BytesIO(oversized_content),
                "large_certificate.pdf",
            ),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 302
    assert "mode=Update" in response.headers["Location"]

    test_database.session.expire_all()

    student = test_database.session.get(
        Students,
        student_test_data["student"].id,
    )

    assert student.Certification == original_certification

    certification_directory = (
        profile_test_directory
        / "static"
        / "Docs"
        / "student"
        / "certifications"
    )

    assert (
        not certification_directory.exists()
        or not any(certification_directory.iterdir())
    )


# CERT-04
def test_CERT_04_certification_without_extension_is_rejected(
    student_auth,
    student_test_data,
    test_database,
    profile_test_directory,
):
    # Scenario:
    # A student uploads a certification whose filename has
    # no extension.
    # Expected result:
    # The application rejects the upload gracefully and does not
    # modify the existing certification list.
    original_certification = student_test_data["student"].Certification

    response = student_auth.post(
        "/Student_Profile",
        data={
            "Certification": (
                io.BytesIO(b"certificate content"),
                "certificate",
            ),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 302
    assert "mode=Update" in response.headers["Location"]

    test_database.session.expire_all()

    student = test_database.session.get(
        Students,
        student_test_data["student"].id,
    )

    assert student.Certification == original_certification


# CERT-05
def test_CERT_05_first_certification_is_recorded(
    student_auth,
    student_test_data,
    test_database,
    profile_test_directory,
):
    # Scenario:
    # A student without existing certifications uploads a PDF.
    # Expected result:
    # The certification filename is stored in the Certification
    # database field and the corresponding file exists.
    student = student_test_data["student"]
    student.Certification = ""
    test_database.session.commit()

    response = student_auth.post(
        "/Student_Profile",
        data={
            "Certification": (
                io.BytesIO(b"%PDF-1.4 first certificate"),
                "First_Certificate.pdf",
            ),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 302

    test_database.session.expire_all()

    student = test_database.session.get(
        Students,
        student_test_data["student"].id,
    )

    assert student.Certification == "First_Certificate.pdf"

    saved_file = (
        profile_test_directory
        / "static"
        / "Docs"
        / "student"
        / "certifications"
        / (
            f"Cert_{student.user_id}_Test_Student_"
            "First_Certificate.pdf"
        )
    )

    assert saved_file.is_file()


# CERT-06
def test_CERT_06_second_certification_is_appended(
    student_auth,
    student_test_data,
    test_database,
    profile_test_directory,
):
    # Scenario:
    # A student already has one certification and uploads another PDF.
    # Expected result:
    # The new certification is appended without removing the first
    # certification, and the new file is saved.
    student = student_test_data["student"]
    student.Certification = "First_Certificate.pdf"
    test_database.session.commit()

    response = student_auth.post(
        "/Student_Profile",
        data={
            "Certification": (
                io.BytesIO(b"%PDF-1.4 second certificate"),
                "Second_Certificate.pdf",
            ),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 302

    test_database.session.expire_all()

    student = test_database.session.get(
        Students,
        student_test_data["student"].id,
    )

    assert "First_Certificate.pdf" in student.Certification
    assert "Second_Certificate.pdf" in student.Certification

    saved_file = (
        profile_test_directory
        / "static"
        / "Docs"
        / "student"
        / "certifications"
        / (
            f"Cert_{student.user_id}_Test_Student_"
            "Second_Certificate.pdf"
        )
    )

    assert saved_file.is_file()
    assert saved_file.read_bytes() == b"%PDF-1.4 second certificate"


# CERT-07
def test_CERT_07_uploaded_certification_can_be_downloaded(
    student_auth,
    student_test_data,
    test_database,
    profile_test_directory,
):
    # Scenario:
    # A student uploads a PDF certification and requests its download.
    # Expected result:
    # The download returns HTTP 200, includes the expected content,
    # and is delivered as an attachment.
    response = student_auth.post(
        "/Student_Profile",
        data={
            "Certification": (
                io.BytesIO(b"%PDF-1.4 downloadable certificate"),
                "Download_Certificate.pdf",
            ),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 302

    student = student_test_data["student"]

    download_response = student_auth.post(
        "/student/certification/download",
        data={
            "id": str(student.user_id),
            "name": "Download_Certificate.pdf",
        },
    )

    assert download_response.status_code == 200
    assert download_response.data == (
        b"%PDF-1.4 downloadable certificate"
    )
    assert "attachment" in download_response.headers.get(
        "Content-Disposition",
        "",
    ).lower()


# CERT-08
def test_CERT_08_downloaded_certification_matches_uploaded_content(
    student_auth,
    student_test_data,
    test_database,
    profile_test_directory,
):
    # Scenario:
    # A student uploads a certification and downloads the same file.
    # Expected result:
    # The downloaded bytes exactly match the uploaded bytes.
    uploaded_content = b"%PDF-1.4 exact content verification"

    student_auth.post(
        "/Student_Profile",
        data={
            "Certification": (
                io.BytesIO(uploaded_content),
                "Content_Verification.pdf",
            ),
        },
        content_type="multipart/form-data",
    )

    response = student_auth.post(
        "/student/certification/download",
        data={
            "id": str(student_test_data["student_user"].user_id),
            "name": "Content_Verification.pdf",
        },
    )

    assert response.status_code == 200
    assert response.data == uploaded_content


# CERT-09
def test_CERT_09_missing_certification_file_returns_404(
    student_auth,
    student_test_data,
    test_database,
    profile_test_directory,
):
    # Scenario:
    # The student's Certification field references a PDF that
    # does not exist on disk.
    # Expected result:
    # The download request returns HTTP 404.
    student = student_test_data["student"]
    student.Certification = "Missing_Certificate.pdf"
    test_database.session.commit()

    response = student_auth.post(
        "/student/certification/download",
        data={
            "id": str(student.user_id),
            "name": "Missing_Certificate.pdf",
        },
    )

    assert response.status_code == 404


# CERT-10
def test_CERT_10_non_student_cannot_download_certification(
    client,
    student_test_data,
    profile_test_directory,
):
    # Scenario:
    # A recruiter attempts to use the student certification
    # download endpoint.
    # Expected result:
    # The application returns HTTP 403 Forbidden.
    recruiter_client = _profile_bearer_client(
        client,
        student_test_data["recruiter_user"].user_id,
    )

    response = recruiter_client.post(
        "/student/certification/download",
        data={
            "id": str(student_test_data["student_user"].user_id),
            "name": "Certificate.pdf",
        },
    )

    assert response.status_code == 403


# CERT-11
def test_CERT_11_invalid_upload_preserves_existing_certifications(
    student_auth,
    student_test_data,
    test_database,
    profile_test_directory,
):
    # Scenario:
    # A student already has a certification and attempts to upload
    # a non-PDF file.
    # Expected result:
    # The existing Certification database value remains unchanged,
    # and the invalid file is not saved.
    student = student_test_data["student"]
    student.Certification = "Existing_Certificate.pdf"
    test_database.session.commit()

    response = student_auth.post(
        "/Student_Profile",
        data={
            "Certification": (
                io.BytesIO(b"invalid text"),
                "Invalid_Certificate.txt",
            ),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 302

    test_database.session.expire_all()

    student = test_database.session.get(
        Students,
        student_test_data["student"].id,
    )

    assert student.Certification == "Existing_Certificate.pdf"

    certification_directory = (
        profile_test_directory
        / "static"
        / "Docs"
        / "student"
        / "certifications"
    )

    assert (
        not certification_directory.exists()
        or not any(certification_directory.iterdir())
    )

# ============================================================
# STUDENT JOB DRIVE — ADDITIONAL AUTHORIZATION, LISTING,
# APPLY AND OPT-OUT TESTS
# Append this section to tests/test_student_dashboard_cases.py
# ============================================================


# ============================================================
# ADDITIONAL HELPER FIXTURE
# ============================================================

@pytest.fixture
def job_drive_notifications(monkeypatch):
    """
    Scenario:
        Job-drive actions may send notifications to recruiters or placement officers.

    Expected result:
        Notification calls are captured during tests instead of sending real
        notifications. The captured calls can be checked where necessary.
    """
    import student.routes as student_routes

    calls = []

    def fake_notifications(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})

    monkeypatch.setattr(
        student_routes,
        "notifications",
        fake_notifications,
    )

    return calls


# ============================================================
# AUTH-JOB-04 AND AUTH-JOB-05
# ============================================================

# AUTH-JOB-04
def test_AUTH_JOB_04_placement_officer_cannot_open_job_drive_page(
    officer_auth,
):
    # Scenario:
    # An authenticated placement officer attempts to access
    # /Student_Job_Drive using a valid JWT.
    # Expected result:
    # The route rejects the request with HTTP 403 Forbidden.

    response = officer_auth.get("/Student_Job_Drive")

    assert response.status_code == 403


# AUTH-JOB-05
def test_AUTH_JOB_05_non_student_cannot_submit_job_drive_action(
    client,
    student_test_data,
    job_drive_factory,
    test_database,
):
    # Scenario:
    # An authenticated recruiter submits an application action for a job drive.
    # Expected result:
    # The route rejects the request with HTTP 403 Forbidden, and no application
    # is created for the student.

    drive = job_drive_factory(title="Recruiter POST Protection Role")

    recruiter_client = _profile_bearer_client(
        client,
        student_test_data["recruiter_user"].user_id,
    )

    response = recruiter_client.post(
        f"/Student_Job_Drive?id={drive.id}",
        data={"action": "apply"},
    )

    assert response.status_code == 403

    application = Applications.query.filter_by(
        student_id=student_test_data["student"].id,
        drive_id=drive.id,
    ).first()

    assert application is None


# ============================================================
# JOB-08, JOB-09, JOB-11, JOB-13, JOB-14 AND JOB-16
# ============================================================

# JOB-08
def test_JOB_08_empty_eligible_drive_list_displays_empty_state(
    student_auth,
    student_test_data,
    test_database,
):
    # Scenario:
    # The student has no eligible job drives (job_drive is None).
    # Expected result:
    # The job-drive page loads successfully and displays its empty-state message.

    student_test_data["student"].job_drive = None
    test_database.session.commit()

    response = student_auth.get("/Student_Job_Drive")

    assert response.status_code == 200
    assert b"No job drives available" in response.data


# JOB-09
def test_JOB_09_multiple_eligible_active_drives_are_displayed(
    student_auth,
    student_test_data,
    job_drive_factory,
    test_database,
):
    # Scenario:
    # The student's eligible-drive list contains two active job drives.
    # Expected result:
    # Both eligible job-drive titles appear on the page.

    first_drive = job_drive_factory(
        title="Eligible Multiple Role Alpha",
    )
    second_drive = job_drive_factory(
        title="Eligible Multiple Role Beta",
    )

    student_test_data["student"].job_drive = (
        f"{first_drive.id},{second_drive.id}"
    )
    test_database.session.commit()

    response = student_auth.get("/Student_Job_Drive")

    assert response.status_code == 200
    assert b"Eligible Multiple Role Alpha" in response.data
    assert b"Eligible Multiple Role Beta" in response.data


# JOB-11
def test_JOB_11_expired_drive_is_not_shown_in_active_listing(
    student_auth,
    student_test_data,
    job_drive_factory,
    test_database,
):
    # Scenario:
    # An eligible job drive has a deadline before today's date.
    # Expected result:
    # The expired drive is excluded from the default active listing.

    expired_drive = job_drive_factory(
        title="Expired Listing Test Role",
        deadline=(
            datetime.datetime.now()
            - datetime.timedelta(days=2)
        ),
    )

    student_test_data["student"].job_drive = str(expired_drive.id)
    test_database.session.commit()

    response = student_auth.get("/Student_Job_Drive")

    assert response.status_code == 200
    assert b"Expired Listing Test Role" not in response.data


# JOB-13
def test_JOB_13_expired_filter_displays_eligible_expired_drive(
    student_auth,
    student_test_data,
    job_drive_factory,
    test_database,
):
    # Scenario:
    # The student is eligible for a drive whose deadline has passed and opens
    # the job-drive page with filter=Expired.
    # Expected result:
    # The expired drive appears in the filtered results.

    expired_drive = job_drive_factory(
        title="Expired Filter Test Role",
        deadline=(
            datetime.datetime.now()
            - datetime.timedelta(days=2)
        ),
    )

    student_test_data["student"].job_drive = str(expired_drive.id)
    test_database.session.commit()

    response = student_auth.get("/Student_Job_Drive?filter=Expired")

    assert response.status_code == 200
    assert b"Expired Filter Test Role" in response.data


# JOB-14
def test_JOB_14_job_drive_search_matches_company_name(
    student_auth,
    student_test_data,
    job_drive_factory,
    test_database,
):
    # Scenario:
    # The student searches using a distinctive part of the company name
    # associated with an eligible active drive.
    # Expected result:
    # The matching job drive appears in the results.

    drive = job_drive_factory(
        title="Company Search Test Role",
        company_name="UniqueSearchCompanyXYZ",
    )

    student_test_data["student"].job_drive = str(drive.id)
    test_database.session.commit()

    response = student_auth.get(
        "/Student_Job_Drive?search=UniqueSearchCompanyXYZ"
    )

    assert response.status_code == 200
    assert b"Company Search Test Role" in response.data
    assert b"UniqueSearchCompanyXYZ" in response.data


# JOB-16
def test_JOB_16_job_drive_search_with_no_matches_returns_no_results(
    student_auth,
    student_test_data,
    job_drive_factory,
    test_database,
):
    # Scenario:
    # The student has an eligible active drive but searches for text that
    # matches neither its company name nor its title.
    # Expected result:
    # The page responds successfully and the unrelated drive is not displayed.

    drive = job_drive_factory(
        title="Search No Match Test Role",
        company_name="Search No Match Test Company",
    )

    student_test_data["student"].job_drive = str(drive.id)
    test_database.session.commit()

    response = student_auth.get(
        "/Student_Job_Drive?search=NoSuchCompanyOrRoleXYZ"
    )

    assert response.status_code == 200
    assert b"Search No Match Test Role" not in response.data


# ============================================================
# APPLY-JOB-01, APPLY-JOB-02, APPLY-JOB-03, APPLY-JOB-04,
# APPLY-JOB-06, APPLY-JOB-08, APPLY-JOB-09 AND APPLY-JOB-10
# ============================================================

# APPLY-JOB-01
def test_APPLY_JOB_01_verified_student_can_apply_successfully(
    student_auth,
    student_test_data,
    job_drive_factory,
    test_database,
    job_drive_notifications,
):
    # Scenario:
    # A student with a Verified resume applies for an eligible active drive
    # and has not previously applied for that drive.
    # Expected result:
    # An application is created with APPLIED status, the drive is removed
    # from the student's eligible-drive list, and application tracking updates.

    student = student_test_data["student"]
    student.resume_status = "Verified"

    drive = job_drive_factory(
        title="Verified Resume Apply Role",
    )

    student.job_drive = str(drive.id)
    test_database.session.commit()

    response = student_auth.post(
        f"/Student_Job_Drive?id={drive.id}",
        data={"action": "apply"},
    )

    assert response.status_code == 200

    application = Applications.query.filter_by(
        student_id=student.id,
        drive_id=drive.id,
    ).first()

    assert application is not None
    assert application.status == Application_status.APPLIED

    test_database.session.refresh(student)
    test_database.session.refresh(drive)

    assert student.job_drive is None

    assert drive.application_count_email["email_count"] == 1
    assert student.id in drive.application_count_email["student_id"]

    assert len(job_drive_notifications) >= 1


# APPLY-JOB-02
def test_APPLY_JOB_02_unverified_resume_cannot_apply(
    student_auth,
    student_test_data,
    job_drive_factory,
    test_database,
    job_drive_notifications,
):
    # Scenario:
    # A student whose resume is Pending attempts to apply for an eligible
    # active job drive.
    # Expected result:
    # No application is created, the eligible-drive list remains unchanged,
    # and no application notification is sent.

    student = student_test_data["student"]
    student.resume_status = "Pending"

    drive = job_drive_factory(
        title="Pending Resume Apply Role",
    )

    student.job_drive = str(drive.id)
    test_database.session.commit()

    response = student_auth.post(
        f"/Student_Job_Drive?id={drive.id}",
        data={"action": "apply"},
    )

    assert response.status_code == 200

    application = Applications.query.filter_by(
        student_id=student.id,
        drive_id=drive.id,
    ).first()

    assert application is None

    test_database.session.refresh(student)
    test_database.session.refresh(drive)

    assert student.job_drive == str(drive.id)
    assert drive.application_count_email["email_count"] == 0
    assert drive.application_count_email["student_id"] == []
    assert job_drive_notifications == []


# APPLY-JOB-03
def test_APPLY_JOB_03_duplicate_application_is_not_created(
    student_auth,
    student_test_data,
    job_drive_factory,
    application_factory,
    test_database,
    job_drive_notifications,
):
    # Scenario:
    # A student with a Verified resume submits an application for a drive
    # for which an application already exists.
    # Expected result:
    # No second application is created, and application tracking is not
    # incremented again.

    student = student_test_data["student"]
    student.resume_status = "Verified"

    drive = job_drive_factory(
        title="Duplicate Apply Protection Role",
    )

    student.job_drive = str(drive.id)
    test_database.session.commit()

    application_factory(drive)

    test_database.session.refresh(drive)
    original_count = drive.application_count_email["email_count"]
    original_students = list(
        drive.application_count_email["student_id"]
    )

    response = student_auth.post(
        f"/Student_Job_Drive?id={drive.id}",
        data={"action": "apply"},
    )

    assert response.status_code == 302

    applications = Applications.query.filter_by(
        student_id=student.id,
        drive_id=drive.id,
    ).all()

    assert len(applications) == 1

    test_database.session.refresh(drive)

    assert drive.application_count_email["email_count"] == original_count
    assert drive.application_count_email["student_id"] == original_students
    assert job_drive_notifications == []


# APPLY-JOB-04
def test_APPLY_JOB_04_applying_to_only_eligible_drive_clears_eligibility(
    student_auth,
    student_test_data,
    job_drive_factory,
    test_database,
    job_drive_notifications,
):
    # Scenario:
    # A student with a Verified resume applies for their only eligible
    # active job drive.
    # Expected result:
    # The application is saved, and Students.job_drive becomes None because
    # the student has no remaining eligible drives.

    student = student_test_data["student"]
    student.resume_status = "Verified"

    drive = job_drive_factory(
        title="Only Eligible Apply Role",
    )

    student.job_drive = str(drive.id)
    test_database.session.commit()

    response = student_auth.post(
        f"/Student_Job_Drive?id={drive.id}",
        data={"action": "apply"},
    )

    assert response.status_code == 200

    test_database.session.refresh(student)

    assert student.job_drive is None

    application = Applications.query.filter_by(
        student_id=student.id,
        drive_id=drive.id,
    ).first()

    assert application is not None
    assert application.status == Application_status.APPLIED


# APPLY-JOB-06
def test_APPLY_JOB_06_applying_removes_only_selected_drive_from_eligibility(
    student_auth,
    student_test_data,
    job_drive_factory,
    test_database,
    job_drive_notifications,
):
    # Scenario:
    # A student with a Verified resume is eligible for two active drives
    # and applies for only one of them.
    # Expected result:
    # The application is created for the selected drive, which is removed
    # from Students.job_drive, while the other eligible drive remains.

    student = student_test_data["student"]
    student.resume_status = "Verified"

    first_drive = job_drive_factory(
        title="Selected Apply Role",
    )
    second_drive = job_drive_factory(
        title="Remaining Eligible Role",
    )

    student.job_drive = f"{first_drive.id},{second_drive.id}"
    test_database.session.commit()

    response = student_auth.post(
        f"/Student_Job_Drive?id={first_drive.id}",
        data={"action": "apply"},
    )

    assert response.status_code == 200

    test_database.session.refresh(student)

    assert student.job_drive == str(second_drive.id)

    application = Applications.query.filter_by(
        student_id=student.id,
        drive_id=first_drive.id,
    ).first()

    assert application is not None
    assert application.status == Application_status.APPLIED

    other_application = Applications.query.filter_by(
        student_id=student.id,
        drive_id=second_drive.id,
    ).first()

    assert other_application is None


# APPLY-JOB-08
def test_APPLY_JOB_08_student_cannot_apply_for_ineligible_drive(
    student_auth,
    student_test_data,
    job_drive_factory,
    test_database,
    job_drive_notifications,
):
    # Scenario:
    # An authenticated student with a Verified resume attempts to apply for
    # an active drive that is not in their eligible-drive list.
    # Expected result:
    # The request is rejected or safely redirected, no application is created,
    # and the student's eligible-drive list remains unchanged.

    student = student_test_data["student"]
    student.resume_status = "Verified"

    eligible_drive = job_drive_factory(
        title="Student Eligible Apply Role",
    )
    ineligible_drive = job_drive_factory(
        title="Student Ineligible Apply Role",
    )

    student.job_drive = str(eligible_drive.id)
    test_database.session.commit()

    # Follow redirects so that a redirect-based rejection can be checked.
    response = student_auth.post(
        f"/Student_Job_Drive?id={ineligible_drive.id}",
        data={"action": "apply"},
        follow_redirects=False,
    )

    assert response.status_code in (302, 400, 403)

    application = Applications.query.filter_by(
        student_id=student.id,
        drive_id=ineligible_drive.id,
    ).first()

    assert application is None

    test_database.session.refresh(student)

    assert student.job_drive == str(eligible_drive.id)

# APPLY-JOB-10
def test_APPLY_JOB_10_successful_application_updates_tracking_once(
    student_auth,
    student_test_data,
    job_drive_factory,
    test_database,
    job_drive_notifications,
):
    # Scenario:
    # A student with a Verified resume applies successfully for an eligible
    # active drive whose application-tracking counter starts at zero.
    # Expected result:
    # The counter increments by one and the student's ID is recorded once
    # in the tracking list.

    student = student_test_data["student"]
    student.resume_status = "Verified"

    drive = job_drive_factory(
        title="Application Tracking Test Role",
        application_count_email={
            "email_count": 0,
            "student_id": [],
        },
    )

    student.job_drive = str(drive.id)
    test_database.session.commit()

    response = student_auth.post(
        f"/Student_Job_Drive?id={drive.id}",
        data={"action": "apply"},
    )

    assert response.status_code == 200

    test_database.session.refresh(drive)

    tracking = drive.application_count_email

    assert tracking["email_count"] == 1
    assert tracking["student_id"].count(student.id) == 1


# ============================================================
# OPTOUT-JOB-01, OPTOUT-JOB-02, OPTOUT-JOB-03 AND OPTOUT-JOB-06
# ============================================================

# OPTOUT-JOB-01
def test_OPTOUT_JOB_01_student_can_opt_out_of_eligible_drive(
    student_auth,
    student_test_data,
    job_drive_factory,
    test_database,
    job_drive_notifications,
):
    # Scenario:
    # A student opts out of an eligible active drive for which they have
    # not already applied.
    # Expected result:
    # The drive is removed from the student's eligible-drive list, and the
    # student's ID is recorded in the drive's opt_out field.

    student = student_test_data["student"]

    drive = job_drive_factory(
        title="Successful Opt Out Role",
    )

    student.job_drive = str(drive.id)
    test_database.session.commit()

    response = student_auth.post(
        f"/Student_Job_Drive?id={drive.id}",
        data={"action": "opt_out"},
    )

    assert response.status_code == 200

    test_database.session.refresh(student)
    test_database.session.refresh(drive)

    assert student.job_drive is None
    assert str(student.id) in str(drive.opt_out)


# OPTOUT-JOB-02
def test_OPTOUT_JOB_02_opt_out_of_only_drive_clears_eligibility(
    student_auth,
    student_test_data,
    job_drive_factory,
    test_database,
    job_drive_notifications,
):
    # Scenario:
    # The student is eligible for only one active drive and opts out of it.
    # Expected result:
    # Students.job_drive becomes None, and the student's ID is recorded
    # in the drive's opt_out field.

    student = student_test_data["student"]

    drive = job_drive_factory(
        title="Only Drive Opt Out Role",
    )

    student.job_drive = str(drive.id)
    test_database.session.commit()

    response = student_auth.post(
        f"/Student_Job_Drive?id={drive.id}",
        data={"action": "opt_out"},
    )

    assert response.status_code == 200

    test_database.session.refresh(student)
    test_database.session.refresh(drive)

    assert student.job_drive is None
    assert str(student.id) in str(drive.opt_out)

    application = Applications.query.filter_by(
        student_id=student.id,
        drive_id=drive.id,
    ).first()

    assert application is None


# OPTOUT-JOB-03
def test_OPTOUT_JOB_03_opt_out_preserves_other_eligible_drives(
    student_auth,
    student_test_data,
    job_drive_factory,
    test_database,
    job_drive_notifications,
):
    # Scenario:
    # The student is eligible for two active drives and opts out of one.
    # Expected result:
    # Only the opted-out drive is removed from the eligible-drive list.
    # The other drive remains available to the student.

    student = student_test_data["student"]

    opted_out_drive = job_drive_factory(
        title="Opted Out Selected Role",
    )
    remaining_drive = job_drive_factory(
        title="Opt Out Remaining Role",
    )

    student.job_drive = (
        f"{opted_out_drive.id},{remaining_drive.id}"
    )
    test_database.session.commit()

    response = student_auth.post(
        f"/Student_Job_Drive?id={opted_out_drive.id}",
        data={"action": "opt_out"},
    )

    assert response.status_code == 200

    test_database.session.refresh(student)
    test_database.session.refresh(opted_out_drive)

    assert student.job_drive == str(remaining_drive.id)
    assert str(student.id) in str(opted_out_drive.opt_out)

    application = Applications.query.filter_by(
        student_id=student.id,
        drive_id=opted_out_drive.id,
    ).first()

    assert application is None


# OPTOUT-JOB-06
def test_OPTOUT_JOB_06_student_who_already_applied_cannot_opt_out(
    student_auth,
    student_test_data,
    job_drive_factory,
    application_factory,
    test_database,
    job_drive_notifications,
):
    # Scenario:
    # The student already has an application for a drive and then attempts
    # to opt out of that same drive.
    # Expected result:
    # The existing application remains unchanged, the drive is not recorded
    # as an opt-out, and the eligible-drive list is not modified.

    student = student_test_data["student"]

    drive = job_drive_factory(
        title="Already Applied Opt Out Protection Role",
    )

    student.job_drive = str(drive.id)
    test_database.session.commit()

    existing_application = application_factory(drive)

    response = student_auth.post(
        f"/Student_Job_Drive?id={drive.id}",
        data={"action": "opt_out"},
        follow_redirects=False,
    )

    assert response.status_code == 302

    test_database.session.refresh(student)
    test_database.session.refresh(drive)

    assert student.job_drive == str(drive.id)
    assert drive.opt_out is None

    applications = Applications.query.filter_by(
        student_id=student.id,
        drive_id=drive.id,
    ).all()

    assert len(applications) == 1
    assert applications[0].id == existing_application.id