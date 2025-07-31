import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
import tempfile
import os
import time

# Use a temporary SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///" + tempfile.mkstemp()[1]
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the get_db dependency
@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    db_path = SQLALCHEMY_DATABASE_URL.replace("sqlite:///", "")
    for _ in range(5):
        try:
            os.remove(db_path)
            break
        except PermissionError:
            time.sleep(0.2)

@pytest.fixture(scope="module")
def client():
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c


def test_user_crud_flow(client):
    # 1. Signup
    user_data = {
        "username": "testuser",
        "first_name": "Test",
        "last_name": "User",
        "email": "testuser@example.com",
        "password": "testpass123"
    }
    resp = client.post("/users/", json=user_data)
    assert resp.status_code == 201
    user = resp.json()
    assert user["username"] == user_data["username"]
    assert user["email"] == user_data["email"]
    user_id = user["id"]

    # 2. Duplicate username/email
    resp2 = client.post("/users/", json=user_data)
    assert resp2.status_code == 400
    assert "Username already registered" in resp2.text or "Email already registered" in resp2.text

    # 3. Signin (via /auth/signin)
    signin_data = {"login": "testuser", "password": "testpass123"}
    resp3 = client.post("/auth/signin", json=signin_data)
    assert resp3.status_code == 200
    assert "access_token" in resp3.json()

    # 4. Update user
    update_data = {
        "first_name": "Updated",
        "last_name": "User2",
        "username": "testuser2",
        "email": "testuser2@example.com",
        "password": "newpass456"
    }
    resp4 = client.put(f"/users/{user_id}", json=update_data)
    assert resp4.status_code == 200
    updated = resp4.json()
    assert updated["first_name"] == "Updated"
    assert updated["username"] == "testuser2"
    assert updated["email"] == "testuser2@example.com"

    # 5. Delete user
    resp5 = client.delete(f"/users/{user_id}")
    assert resp5.status_code == 204

    # 6. Confirm user is deleted
    resp6 = client.get(f"/users/{user_id}")
    assert resp6.status_code == 404

def test_family_group_signup_and_invites(client):
    # 1. Family group signup with invitees
    family_data = {
        "username": "familyadmin",
        "first_name": "Family",
        "last_name": "Admin",
        "email": "familyadmin@example.com",
        "password": "adminpass123",
        "family_invitees": [
            {
                "first_name": "Spouse",
                "last_name": "One",
                "email": "spouse1@example.com",
                "role": "spouse"
            },
            {
                "first_name": "Child",
                "last_name": "One",
                "email": "child1@example.com",
                "role": "child"
            }
        ]
    }
    resp = client.post("/users/", json=family_data)
    assert resp.status_code == 201
    user = resp.json()
    assert user["username"] == family_data["username"]
    assert user["email"] == family_data["email"]
    user_id = user["id"]
    assert user["family_group_id"] is not None
    family_group_id = user["family_group_id"]

    # Ensure the family group is committed and visible
    _ = client.get(f"/users/{user_id}")

    # 2. Check that invitations were created (via /family/invite endpoint or direct DB query)
    new_invite_data = {
        "family_group_id": family_group_id,
        "invitees": [
            {
                "first_name": "Grandparent",
                "last_name": "One",
                "email": "grandparent1@example.com",
                "role": "grandparent"
            }
        ]
    }
    resp2 = client.post("/family/invite", json=new_invite_data)
    assert resp2.status_code == 200
    invites = resp2.json()
    assert any(inv["email"] == "grandparent1@example.com" for inv in invites)
    token = [inv["token"] for inv in invites if inv["email"] == "grandparent1@example.com"][0]

    # 3. Accept an invitation (get invite details for pre-population)
    resp3 = client.get(f"/family/invite/accept/{token}")
    assert resp3.status_code == 200
    invite_details = resp3.json()
    assert invite_details["first_name"] == "Grandparent"
    assert invite_details["last_name"] == "One"
    assert invite_details["email"] == "grandparent1@example.com"
    assert invite_details["role"] == "grandparent"
    assert invite_details["inviter"] == "Family Admin"

    # 4. Register invitee with username and password
    register_data = {
        "token": token,
        "username": "grandparentuser",
        "password": "grandparentpass"
    }
    resp4 = client.post("/family/register-invitee", json=register_data)
    assert resp4.status_code == 200
    new_user = resp4.json()
    assert new_user["email"] == "grandparent1@example.com"
    assert new_user["family_group_id"] == family_group_id
    assert new_user["username"] == "grandparentuser"

    # 5. Try to register with the same username (should fail)
    register_data2 = {
        "token": token,
        "username": "grandparentuser",
        "password": "anotherpass"
    }
    resp5 = client.post("/family/register-invitee", json=register_data2)
    assert resp5.status_code == 404 or resp5.status_code == 400

    # 6. Try to accept the same invitation again (should fail)
    resp6 = client.get(f"/family/invite/accept/{token}")
    assert resp6.status_code == 404 