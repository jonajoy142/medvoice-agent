import os

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.rbac import CurrentUser, writable_hospital_id
from app.main import app
from app.api.v1.routes_saas import _redirect


def user(role="hospital_admin", hospital_id="h1"):
    return CurrentUser(
        staff_user_id="s1",
        supabase_user_id="u1",
        email="admin@example.com",
        full_name="Admin",
        role=role,
        hospital_id=hospital_id,
        hospital_name="Hospital",
        hospital_status="active",
    )


def test_role_redirects():
    assert _redirect("super_admin") == "/admin"
    assert _redirect("hospital_admin") == "/dashboard"
    assert _redirect("staff") == "/dashboard"


def test_hospital_user_cannot_select_other_tenant():
    with pytest.raises(HTTPException):
        writable_hospital_id(user("hospital_admin", "h1"), "h2")


def test_super_admin_must_specify_hospital_for_writes_without_membership():
    with pytest.raises(HTTPException):
        writable_hospital_id(user("super_admin", None), None)


def test_supabase_integration_login_is_gated():
    if os.getenv("RUN_SUPABASE_INTEGRATION_TESTS") != "true":
        pytest.skip("Set RUN_SUPABASE_INTEGRATION_TESTS=true with Supabase credentials to run this test.")
    client = TestClient(app)
    response = client.post("/api/v1/auth/login", json={"email": os.environ["SEED_HOSPITAL_ADMIN_EMAIL"], "password": os.environ["SEED_DEFAULT_PASSWORD"]})
    assert response.status_code == 200
    assert response.json()["profile"]["role"] in {"hospital_admin", "staff", "super_admin"}
