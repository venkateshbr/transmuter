from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from joserfc import jwt
from joserfc.jwk import OctKey
from joserfc.jwt import JWTClaimsRegistry

ALLOWED_HMAC_ALGORITHMS = frozenset({"HS256", "HS384", "HS512"})


def encode_token(claims: dict[str, Any], secret: str, algorithm: str) -> str:
    """Encode a signed JWT with one explicitly allowed HMAC algorithm."""
    return jwt.encode(
        {"alg": algorithm},
        _normalize_datetime_claims(claims),
        _symmetric_key(secret, algorithm),
        algorithms=[algorithm],
    )


def decode_token(token: str, secret: str, algorithm: str) -> dict[str, Any]:
    """Verify a signed JWT and validate its registered time-based claims."""
    decoded = jwt.decode(
        token,
        _symmetric_key(secret, algorithm),
        algorithms=[algorithm],
    )
    JWTClaimsRegistry().validate(decoded.claims)
    return decoded.claims


def _symmetric_key(secret: str, algorithm: str) -> OctKey:
    if algorithm not in ALLOWED_HMAC_ALGORITHMS:
        raise ValueError("JWT algorithm must be HS256, HS384, or HS512")
    if len(secret) < 32:
        raise ValueError("JWT secret must be at least 32 characters")
    return OctKey.import_key(secret)


def _normalize_datetime_claims(claims: dict[str, Any]) -> dict[str, Any]:
    normalized = claims.copy()
    for name, value in normalized.items():
        if isinstance(value, datetime):
            timestamp = value if value.tzinfo else value.replace(tzinfo=UTC)
            normalized[name] = int(timestamp.timestamp())
    return normalized
