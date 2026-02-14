"""Tests for JWT authentication — register, login, protected endpoints."""

import pytest
from httpx import AsyncClient


async def test_register(client: AsyncClient):
    """Test user registration."""
    resp = await client.post("/api/auth/register", json={
        "email": "test@example.com",
        "name": "Test User",
        "password": "securepass123",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "test@example.com"
    assert data["user"]["name"] == "Test User"
    assert data["user"]["role"] == "user"


async def test_register_duplicate_email(client: AsyncClient):
    """Test that duplicate email registration is rejected."""
    await client.post("/api/auth/register", json={
        "email": "dup@example.com",
        "name": "First User",
        "password": "pass123",
    })
    resp = await client.post("/api/auth/register", json={
        "email": "dup@example.com",
        "name": "Second User",
        "password": "pass456",
    })
    assert resp.status_code == 409


async def test_login_success(client: AsyncClient):
    """Test successful login."""
    await client.post("/api/auth/register", json={
        "email": "login@example.com",
        "name": "Login User",
        "password": "mypassword",
    })
    resp = await client.post("/api/auth/login", json={
        "email": "login@example.com",
        "password": "mypassword",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "login@example.com"


async def test_login_wrong_password(client: AsyncClient):
    """Test login with wrong password."""
    await client.post("/api/auth/register", json={
        "email": "wrong@example.com",
        "name": "Wrong User",
        "password": "correct",
    })
    resp = await client.post("/api/auth/login", json={
        "email": "wrong@example.com",
        "password": "incorrect",
    })
    assert resp.status_code == 401


async def test_login_nonexistent_email(client: AsyncClient):
    """Test login with nonexistent email."""
    resp = await client.post("/api/auth/login", json={
        "email": "nobody@example.com",
        "password": "anything",
    })
    assert resp.status_code == 401


async def test_get_me_authenticated(client: AsyncClient):
    """Test /me endpoint with valid token."""
    resp = await client.post("/api/auth/register", json={
        "email": "me@example.com",
        "name": "Me User",
        "password": "pass123",
    })
    token = resp.json()["access_token"]

    resp = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@example.com"


async def test_get_me_no_token(client: AsyncClient):
    """Test /me endpoint without token returns 401."""
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


async def test_get_me_invalid_token(client: AsyncClient):
    """Test /me endpoint with invalid token returns 401."""
    resp = await client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert resp.status_code == 401
