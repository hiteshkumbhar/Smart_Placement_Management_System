import pytest
from werkzeug.security import check_password_hash, generate_password_hash
from models import Users, Students


@pytest.mark.registration
def test_register_page_returns_200(client):
    response = client.get("/Register")
    assert response.status_code == 200


@pytest.mark.registration
def test_register_duplicate_email(
    client, test_database, mock_notifications
):
    existing_user = Users(
        name="Existing User",
        email="existing@example.com",
        password=generate_password_hash("ExistingPassword123"),
        role="student",
    )

    test_database.session.add(existing_user)
    test_database.session.commit()

    response = client.post(
        "/Register",
        data={
            "Name": "Another User",
            "Email": "existing@example.com",
            "Role": "student",
            "Password": "Password123",
            "confirm_password": "Password123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"User already exists" in response.data


@pytest.mark.registration
def test_register_password_mismatch(
    client, test_database, mock_notifications
):
    """REG12: Different passwords should be rejected."""
    response = client.post(
        "/Register",
        data={
            "Name": "Test User",
            "Email": "mismatch@example.com",
            "Role": "student",
            "Password": "Password123",
            "confirm_password": "Different123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Passwords do not match" in response.data


@pytest.mark.registration
@pytest.mark.parametrize(
    "password",
    [
        "Ab123",
    ],
)
def test_register_password_too_short(
    client,
    test_database,
    mock_notifications,
    password,
):
    """REG13: Passwords shorter than six characters should be rejected."""
    response = client.post(
        "/Register",
        data={
            "Name": "Test User",
            "Email": "short@example.com",
            "Role": "student",
            "Password": password,
            "confirm_password": password,
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Password" in response.data


@pytest.mark.registration
@pytest.mark.parametrize(
    "password",
    [
        "A" * 21,
    ],
)
def test_register_password_too_long(
    client,
    test_database,
    mock_notifications,
    password,
):
    """REG14: Passwords longer than twenty characters should be rejected."""
    response = client.post(
        "/Register",
        data={
            "Name": "Test User",
            "Email": "long@example.com",
            "Role": "student",
            "Password": password,
            "confirm_password": password,
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Password" in response.data


@pytest.mark.registration
def test_register_successful_user(
    client, test_database, mock_notifications
):
    """REG15: A valid registration should create a user."""
    response = client.post(
        "/Register",
        data={
            "Name": "New User",
            "Email": "newuser@example.com",
            "Role": "student",
            "Password": "Password123",
            "confirm_password": "Password123",
        },
        follow_redirects=False,
    )

    assert response.status_code in (302, 303)

    user = Users.query.filter_by(
        email="newuser@example.com"
    ).first()

    assert user is not None
    assert user.name == "New User"
    assert user.role == "student"

    # The stored password should be hashed, not plaintext.
    assert user.password != "Password123"
    assert check_password_hash(user.password, "Password123")


@pytest.mark.registration
def test_register_student(
    client, test_database, mock_notifications
):
    """REG16: Student registration should create a student record."""
    client.post(
        "/Register",
        data={
            "Name": "Student User",
            "Email": "student@example.com",
            "Role": "student",
            "Password": "Password123",
            "confirm_password": "Password123",
        },
        follow_redirects=False,
    )

    user = Users.query.filter_by(
        email="student@example.com"
    ).first()

    assert user is not None
    assert user.role == "student"

    student = Students.query.filter_by(
        user_id=user.user_id
    ).first()

    assert student is not None


@pytest.mark.registration
def test_register_recruiter(
    client, test_database, mock_notifications
):
    """REG17: Recruiter registration should assign the recruiter role."""
    client.post(
        "/Register",
        data={
            "Name": "Recruiter User",
            "Email": "recruiter@example.com",
            "Role": "Recruiter",
            "Password": "Password123",
            "confirm_password": "Password123",
        },
        follow_redirects=False,
    )

    user = Users.query.filter_by(
        email="recruiter@example.com"
    ).first()

    assert user is not None
    assert user.role == "Recruiter"


@pytest.mark.registration
def test_register_placement_officer(
    client, test_database, mock_notifications
):
    """REG18: Placement Officer registration should assign the correct role."""
    client.post(
        "/Register",
        data={
            "Name": "Placement Officer",
            "Email": "officer@example.com",
            "Role": "Placement_Officer",
            "Password": "Password123",
            "confirm_password": "Password123",
        },
        follow_redirects=False,
    )

    user = Users.query.filter_by(
        email="officer@example.com"
    ).first()

    assert user is not None
    assert user.role == "Placement_Officer"