from http import HTTPStatus

from core.exceptions import (
    BadRequestException,
    CustomException,
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
)


def test_default_custom_exception_is_500():
    assert int(CustomException.code) == HTTPStatus.INTERNAL_SERVER_ERROR


def test_bad_request_code():
    assert int(BadRequestException.code) == 400


def test_not_found_code():
    assert int(NotFoundException.code) == 404


def test_unauthorized_code():
    assert int(UnauthorizedException.code) == 401


def test_forbidden_code():
    assert int(ForbiddenException.code) == 403


def test_custom_message_override():
    exc = BadRequestException("Seats already booked")
    assert exc.message == "Seats already booked"


def test_default_message_used_when_none():
    exc = NotFoundException()
    assert exc.message  # non-empty default
