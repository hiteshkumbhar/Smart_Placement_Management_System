import pytest
from flask import url_for
from flask_jwt_extended import decode_token
from werkzeug.security import generate_password_hash
from app import app
from models import Users, Students

@pytest.fixture
def login_users(test_database):
    users = {
        "student": Users(
            name="Test Student",
            email="student_test@example.com",
            password=generate_password_hash("StudentPass123"),
            role="student",
        ),
        "recruiter": Users(
            name="Test Recruiter",
            email="recruiter_test@example.com",
            password=generate_password_hash("RecruiterPass123"),
            role="Recruiter",
        ),
        "placement_officer": Users(
            name="Test Placement Officer",
            email="officer_test@example.com",
            password=generate_password_hash("OfficerPass123"),
            role="Placement_Officer",
        ),
    }

    test_database.session.add_all(users.values())
    test_database.session.commit()

    # Create a student profile linked to the student user.
    student_profile = Students(
        user_id=users["student"].user_id,
        resume_status="Pending",
    )

    test_database.session.add(student_profile)
    test_database.session.commit()

    return users

def login(client, endpoint, email, password):
    """Submit credentials to the selected login endpoint."""
    return client.post(
        endpoint,
        data={
            "email": email,
            "pass": password,
        },
        follow_redirects=False,
    )


def get_cookie_value(response, cookie_name):
    """Extract a cookie value from the response headers."""
    for header in response.headers.getlist("Set-Cookie"):
        if header.startswith(f"{cookie_name}="):
            return header.split(";", 1)[0].split("=", 1)[1]

    return None


# ---------------------------------------------------------
# Verify that all login pages load successfully
# ---------------------------------------------------------

@pytest.mark.parametrize(
    "endpoint",
    [
        "/Student_login",
        "/Recruiter_login",
        "/Placement_Officer_login",
    ],
    ids=[
        "student_login_page",
        "recruiter_login_page",
        "placement_officer_login_page",
    ],
)
def test_login_pages_return_200(client, endpoint):
    response = client.get(endpoint)
    assert response.status_code == 200

# ---------------------------------------------------------
# Successful login for each role
# ---------------------------------------------------------

@pytest.mark.parametrize(
    "role, endpoint, dashboard_endpoint",
    [
        (
            "student",
            "/Student_login",
            "student.Student_Dashboard",
        ),
        (
            "recruiter",
            "/Recruiter_login",
            "Recruiter.Recruiter_Dashboard",
        ),
        (
            "placement_officer",
            "/Placement_Officer_login",
            "Placement_officer.Placement_officer_dashboard",
        ),
    ],
    ids=[
        "student_successful_login",
        "recruiter_successful_login",
        "placement_officer_successful_login",
    ],
)
def test_successful_login_redirects_to_correct_dashboard(
    client,
    login_users,
    role,
    endpoint,
    dashboard_endpoint,
):
    user = login_users[role]

    password = {
        "student": "StudentPass123",
        "recruiter": "RecruiterPass123",
        "placement_officer": "OfficerPass123",
    }[role]

    response = login(
        client,
        endpoint,
        user.email,
        password,
    )

    expected_location = url_for(dashboard_endpoint)

    assert response.status_code == 302
    assert response.headers["Location"].endswith(expected_location)


# ---------------------------------------------------------
# Verify access and refresh JWT cookies
# ---------------------------------------------------------

def test_successful_login_sets_access_token_cookie(
    client,
    login_users,
):
    user = login_users["student"]

    response = login(
        client,
        "/Student_login",
        user.email,
        "StudentPass123",
    )

    access_cookie_name = app.config["JWT_ACCESS_COOKIE_NAME"]

    access_token = get_cookie_value(
        response,
        access_cookie_name,
    )

    assert response.status_code == 302
    assert access_token is not None
    assert access_token != ""


def test_successful_login_sets_refresh_token_cookie(
    client,
    login_users,
):
    user = login_users["student"]

    response = login(
        client,
        "/Student_login",
        user.email,
        "StudentPass123",
    )

    refresh_cookie_name = app.config["JWT_REFRESH_COOKIE_NAME"]

    refresh_token = get_cookie_value(
        response,
        refresh_cookie_name,
    )

    assert response.status_code == 302
    assert refresh_token is not None
    assert refresh_token != ""


# ---------------------------------------------------------
# Verify that the access token identifies the correct user
# ---------------------------------------------------------

def test_access_token_contains_correct_user_identity(
    client,
    login_users,
):
    user = login_users["student"]

    response = login(
        client,
        "/Student_login",
        user.email,
        "StudentPass123",
    )

    access_cookie_name = app.config["JWT_ACCESS_COOKIE_NAME"]

    access_token = get_cookie_value(
        response,
        access_cookie_name,
    )

    assert access_token is not None

    decoded_token = decode_token(access_token)

    assert decoded_token["sub"] == str(user.user_id)


# ---------------------------------------------------------
# Login with an email that does not exist
# ---------------------------------------------------------

def test_login_rejects_unknown_email(client, test_database):
    response = login(
        client,
        "/Student_login",
        "unknown_user@example.com",
        "SomePassword123",
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith(
        url_for("Student_login")
    )

    with client.session_transaction() as session:
        assert any(
            message == "User does not exist"
            for category, message in session.get("_flashes", [])
        )


# ---------------------------------------------------------
# Login with an incorrect password
# ---------------------------------------------------------

def test_login_rejects_incorrect_password(
    client,
    login_users,
):
    user = login_users["student"]

    response = login(
        client,
        "/Student_login",
        user.email,
        "IncorrectPassword123",
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith(
        url_for("Student_login")
    )

    with client.session_transaction() as session:
        assert any(
            message == "Wrong username or password"
            for category, message in session.get("_flashes", [])
        )


# ---------------------------------------------------------
# Prevent users from logging in through the wrong role
# ---------------------------------------------------------

@pytest.mark.parametrize(
    "endpoint, user_role",
    [
        ("/Student_login", "recruiter"),
        ("/Student_login", "placement_officer"),
        ("/Recruiter_login", "student"),
        ("/Recruiter_login", "placement_officer"),
        ("/Placement_Officer_login", "student"),
        ("/Placement_Officer_login", "recruiter"),
    ],
)
def test_user_cannot_login_through_wrong_role(
    client,
    login_users,
    endpoint,
    user_role,
):
    user = login_users[user_role]

    password = {
        "student": "StudentPass123",
        "recruiter": "RecruiterPass123",
        "placement_officer": "OfficerPass123",
    }[user_role]

    response = login(
        client,
        endpoint,
        user.email,
        password,
    )

    assert response.status_code == 302

    # The wrong-role login must not redirect to an authenticated dashboard.
    assert response.headers["Location"].endswith(endpoint)

    access_cookie_name = app.config["JWT_ACCESS_COOKIE_NAME"]
    refresh_cookie_name = app.config["JWT_REFRESH_COOKIE_NAME"]

    assert get_cookie_value(response, access_cookie_name) is None
    assert get_cookie_value(response, refresh_cookie_name) is None

    with client.session_transaction() as session:
        assert any(
            message == "User does not exist"
            for category, message in session.get("_flashes", [])
        )


# ---------------------------------------------------------
# Prevent unauthenticated access to protected dashboards
# ---------------------------------------------------------

@pytest.mark.parametrize(
    "dashboard_endpoint",
    [
        "student.Student_Dashboard",
        "Recruiter.Recruiter_Dashboard",
        "Placement_officer.Placement_officer_dashboard",
    ],
)
def test_unauthenticated_user_cannot_access_dashboard(
    client,
    dashboard_endpoint,
):
    with client.application.test_request_context():
        dashboard_url = url_for(dashboard_endpoint)

    response = client.get(
        dashboard_url,
        follow_redirects=False,
    )

    assert response.status_code in (401, 403)


# ---------------------------------------------------------
# Prevent one role from accessing another role's dashboard
# ---------------------------------------------------------

@pytest.mark.parametrize(
    "login_role, login_endpoint, password, dashboard_endpoint",
    [
        (
            "recruiter",
            "/Recruiter_login",
            "RecruiterPass123",
            "student.Student_Dashboard",
        ),
        (
            "student",
            "/Student_login",
            "StudentPass123",
            "Recruiter.Recruiter_Dashboard",
        ),
        (
            "student",
            "/Student_login",
            "StudentPass123",
            "Placement_officer.Placement_officer_dashboard",
        ),
        (
            "placement_officer",
            "/Placement_Officer_login",
            "OfficerPass123",
            "student.Student_Dashboard",
        ),
    ],
)
def test_user_cannot_access_another_roles_dashboard(
    client,
    login_users,
    login_role,
    login_endpoint,
    password,
    dashboard_endpoint,
):
    user = login_users[login_role]

    login_response = login(
        client,
        login_endpoint,
        user.email,
        password,
    )

    assert login_response.status_code == 302

    response = client.get(
        url_for(dashboard_endpoint),
        follow_redirects=False,
    )

    assert response.status_code == 403


# ---------------------------------------------------------
# Failed login must not create authentication cookies
# ---------------------------------------------------------

def test_failed_login_does_not_set_authentication_cookies(
    client,
    login_users,
):
    user = login_users["student"]

    response = login(
        client,
        "/Student_login",
        user.email,
        "WrongPassword123",
    )

    assert response.status_code == 302

    access_cookie_name = app.config["JWT_ACCESS_COOKIE_NAME"]
    refresh_cookie_name = app.config["JWT_REFRESH_COOKIE_NAME"]

    assert get_cookie_value(response, access_cookie_name) is None
    assert get_cookie_value(response, refresh_cookie_name) is None


# ---------------------------------------------------------
# Verify that successful login permits access to a protected page
# ---------------------------------------------------------

def test_successful_login_allows_access_to_student_dashboard(
    client,
    login_users,
):
    user = login_users["student"]

    login_response = login(
        client,
        "/Student_login",
        user.email,
        "StudentPass123",
    )

    assert login_response.status_code == 302

    dashboard_response = client.get(
        url_for("student.Student_Dashboard"),
        follow_redirects=False,
    )

    assert dashboard_response.status_code not in (401, 403)