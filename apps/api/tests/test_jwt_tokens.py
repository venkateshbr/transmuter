from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from joserfc.errors import ExpiredTokenError, JoseError

from app.core.jwt_tokens import decode_token, encode_token

SECRET = "jwt-test-secret-that-is-at-least-32-characters"
ALGORITHM = "HS256"


def test_token_round_trip_normalizes_datetime_and_validates_claims() -> None:
    expires_at = datetime.now(UTC) + timedelta(minutes=5)

    token = encode_token(
        {"sub": "user-1", "tenant_id": "tenant-1", "exp": expires_at},
        SECRET,
        ALGORITHM,
    )

    claims = decode_token(token, SECRET, ALGORITHM)

    assert claims["sub"] == "user-1"
    assert claims["tenant_id"] == "tenant-1"
    assert claims["exp"] == int(expires_at.timestamp())


def test_token_rejects_expired_claim() -> None:
    token = encode_token(
        {"sub": "user-1", "exp": datetime.now(UTC) - timedelta(seconds=1)},
        SECRET,
        ALGORITHM,
    )

    with pytest.raises(ExpiredTokenError):
        decode_token(token, SECRET, ALGORITHM)


@pytest.mark.parametrize(
    ("secret", "algorithm", "message"),
    [
        ("short", ALGORITHM, "JWT secret must be at least 32 characters"),
        ("\u00e9" * 16, ALGORITHM, "JWT secret must be at least 32 characters"),
        (SECRET, "none", "JWT algorithm must be HS256, HS384, or HS512"),
        (SECRET, "RS256", "JWT algorithm must be HS256, HS384, or HS512"),
    ],
)
def test_token_rejects_weak_secret_and_non_hmac_algorithms(
    secret: str,
    algorithm: str,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        encode_token({"sub": "user-1"}, secret, algorithm)


@pytest.mark.parametrize(
    ("token_factory", "verification_secret", "decode_algorithm"),
    [
        (lambda: "not-a-jwt", SECRET, ALGORITHM),
        (lambda: encode_token({"sub": "user-1"}, SECRET, ALGORITHM), SECRET, "HS512"),
        (
            lambda: encode_token({"sub": "user-1"}, SECRET, ALGORITHM),
            f"{SECRET}-different",
            ALGORITHM,
        ),
    ],
)
def test_token_rejects_malformed_algorithm_confusion_and_bad_signature(
    token_factory: Callable[[], str],
    verification_secret: str,
    decode_algorithm: str,
) -> None:
    with pytest.raises(JoseError):
        decode_token(token_factory(), verification_secret, decode_algorithm)
