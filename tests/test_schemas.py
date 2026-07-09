import pytest
from pydantic import ValidationError

from app.schemas.requests.users import LoginUserRequest, RegisterUserRequest


def test_valid_registration():
    req = RegisterUserRequest(
        email="user@example.com", username="cinemafan", password="longenough"
    )
    assert req.username == "cinemafan"


def test_registration_rejects_short_password():
    with pytest.raises(ValidationError):
        RegisterUserRequest(email="user@example.com", username="fan", password="short")


def test_registration_rejects_bad_email():
    with pytest.raises(ValidationError):
        RegisterUserRequest(email="not-an-email", username="fan", password="longenough")


@pytest.mark.parametrize("username", ["has space", "sym!bol", "coma,"])
def test_registration_rejects_special_username(username):
    with pytest.raises(ValidationError):
        RegisterUserRequest(
            email="user@example.com", username=username, password="longenough"
        )


def test_registration_allows_underscore_username():
    req = RegisterUserRequest(
        email="user@example.com", username="cool_fan_99", password="longenough"
    )
    assert req.username == "cool_fan_99"


def test_login_request_minimal():
    req = LoginUserRequest(contact="user@example.com", password="x")
    assert req.contact == "user@example.com"


def test_review_rating_bounds():
    from api.v1.users.users import ReviewCreateRequest

    assert ReviewCreateRequest(rating=1).rating == 1
    assert ReviewCreateRequest(rating=10).rating == 10
    with pytest.raises(ValidationError):
        ReviewCreateRequest(rating=0)
    with pytest.raises(ValidationError):
        ReviewCreateRequest(rating=11)
