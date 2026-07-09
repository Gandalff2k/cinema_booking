from datetime import timedelta
from uuid import uuid4

import pytest

from core.security.jwt import (
    JWTDecodeError,
    JWTExpiredError,
    _encode_token,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from core.security.password import get_password_hash, verify_password


def test_access_token_roundtrip():
    uid = uuid4()
    token = create_access_token(uid)
    payload = decode_token(token)
    assert payload["sub"] == str(uid)
    assert payload["type"] == "access"


def test_refresh_token_type():
    payload = decode_token(create_refresh_token(uuid4()))
    assert payload["type"] == "refresh"


def test_decode_rejects_tampered_token():
    token = create_access_token(uuid4())
    with pytest.raises(JWTDecodeError):
        decode_token(token + "tampered")


def test_decode_rejects_garbage():
    with pytest.raises(JWTDecodeError):
        decode_token("not.a.jwt")


def test_decode_expired_token():
    token = _encode_token(str(uuid4()), timedelta(seconds=-10), "access")
    with pytest.raises(JWTExpiredError):
        decode_token(token)


def test_decode_expired_allowed_when_verify_off():
    token = _encode_token(str(uuid4()), timedelta(seconds=-10), "access")
    assert decode_token(token, verify_exp=False)["type"] == "access"


def test_password_hash_is_not_plaintext():
    hashed = get_password_hash("supersecret")
    assert hashed != "supersecret"
    assert len(hashed) > 20


@pytest.mark.parametrize("password", ["short1", "another-Pass9", "Ünïcodé123"])
def test_password_verify_roundtrip(password):
    hashed = get_password_hash(password)
    assert verify_password(password, hashed) is True
    assert verify_password(password + "x", hashed) is False


def test_two_hashes_of_same_password_differ():
    # bcrypt salts each hash independently.
    assert get_password_hash("same") != get_password_hash("same")
