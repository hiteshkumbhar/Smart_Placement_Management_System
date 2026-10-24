import pytest
from app import app, db


@pytest.fixture
def client():
    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
    )

    with app.test_client() as test_client:
        yield test_client


@pytest.fixture
def test_database():
    """Create a fresh database for each test."""
    with app.app_context():
        db.create_all()

        yield db

        db.session.remove()
        db.drop_all()


@pytest.fixture
def mock_notifications(monkeypatch):
    """Prevent real notification delivery during tests."""
    # Replace this with the actual notification function
    # used by your application's registration route.
    #
    # Example:
    # monkeypatch.setattr(
    #     "app.send_email",
    #     lambda *args, **kwargs: None
    # )
    pass
