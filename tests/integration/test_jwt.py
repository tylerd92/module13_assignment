import pytest
from app.auth.jwt import get_password_hash, verify_password
import asyncio
from datetime import timedelta, datetime, timezone
from jose import jwt as jose_jwt
from fastapi import HTTPException
from app.auth.jwt import decode_token, create_token, settings
from app.schemas.token import TokenType

def test_get_password_hash_returns_hash():
    password = "mysecretpassword"
    hashed = get_password_hash(password)
    assert isinstance(hashed, str)
    assert hashed != password
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$") or hashed.startswith("$2y$")

def test_get_password_hash_and_verify_password():
    password = "anotherpassword"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed)
    assert not verify_password("wrongpassword", hashed)

@pytest.mark.asyncio
async def test_decode_token_invalid_token_type(monkeypatch):
    async def fake_is_blacklisted(jti):
        return False
    monkeypatch.setattr("app.auth.redis.is_blacklisted", fake_is_blacklisted)

    user_id = "testuser"
    token = create_token(user_id, TokenType.REFRESH, expires_delta=timedelta(minutes=5))
    with pytest.raises(HTTPException) as exc:
        await decode_token(token, TokenType.ACCESS)
    assert exc.value.status_code == 401
    assert "Could not validate credentials" in exc.value.detail

@pytest.mark.asyncio
async def test_decode_token_expired_token(monkeypatch):
    async def fake_is_blacklisted(jti):
        return False
    monkeypatch.setattr("app.auth.redis.is_blacklisted", fake_is_blacklisted)

    user_id = "testuser"
    token = create_token(
        user_id,
        TokenType.ACCESS,
        expires_delta=timedelta(seconds=-1)  # Already expired
    )
    with pytest.raises(HTTPException) as exc:
        await decode_token(token, TokenType.ACCESS)
    assert exc.value.status_code == 401
    assert "Token has expired" in exc.value.detail

@pytest.mark.asyncio
async def test_decode_token_invalid_signature(monkeypatch):
    async def fake_is_blacklisted(jti):
        return False
    monkeypatch.setattr("app.auth.redis.is_blacklisted", fake_is_blacklisted)

    # Create a token with wrong secret
    user_id = "testuser"
    payload = {
        "sub": user_id,
        "type": TokenType.ACCESS.value,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        "iat": datetime.now(timezone.utc),
        "jti": "fakejti"
    }
    wrong_secret = "wrongsecret"
    token = jose_jwt.encode(payload, wrong_secret, algorithm=settings.ALGORITHM)
    with pytest.raises(HTTPException) as exc:
        await decode_token(token, TokenType.ACCESS)
    assert exc.value.status_code == 401
    assert "Could not validate credentials" in exc.value.detail
