from datetime import datetime
from unittest.mock import patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from app.utils.security import get_password_hash
from tests.MockDataBase import MockDatabase, MockInsertOneResult  # Import MockDatabase from the test_utils file


# Test cases
@pytest.mark.asyncio
async def test_signup(test_client: TestClient, mock_db: MockDatabase):
    payload = {
        "email": "testuser@example.com",
        "password": "testpassword",
        "full_name": "Test User",
        "is_company": True,
        "promo": True
    }

    # Mock asynchronous behavior for find_one and insert_one
    mock_db.add_collection_mock(
        "Registered_users",
        "find_one",
        return_value=None  # Simulate no user exists with this email
    )

    mock_db.add_collection_mock(
        "Registered_users",
        "insert_one",
        return_value=MockInsertOneResult(inserted_id="mock_id")  # Simulate user insertion
    )

    with patch("app.api.v2.endpoints.auth.send_email") as mock_send_email:
        mock_send_email.return_value = None  # Mock the email sending process
        # Send a POST request to the signup endpoint using the async client
        response = test_client.post("/api/v2/signup", json=payload)

        # Check that the response status code is 201 (Created)
        assert response.status_code == 201

        # Get the JSON data from the response and validate the fields
        data = response.json()
        assert data["email"] == payload["email"]
        assert data["full_name"] == payload["full_name"]
        assert data["is_company"] == payload["is_company"]
        assert data["promo"] == payload["promo"]

        # Ensure a company ID was generated for the user
        assert data["company_id"] is not None
        mock_send_email.assert_called_once_with(
            "testuser@example.com",
            "Email Verification",
            mock_send_email.call_args[0][2]  # Check email body if necessary
        )


@pytest.mark.asyncio
async def test_signup_same_email(test_client: TestClient, mock_db: MockDatabase):
    payload = {
        "email": "testuser@example.com",
        "password": "testpassword",
        "full_name": "Test User",
        "is_company": False,
        "promo": True
    }

    # Mock asynchronous behavior for find_one and insert_one
    mock_db.add_collection_mock(
        "Registered_users",
        "find_one",
        return_value=MockInsertOneResult(inserted_id="mock_id")  # Simulate no user exists with this email
    )

    with patch("app.api.v2.endpoints.auth.send_email") as mock_send_email:
        mock_send_email.return_value = None  # Mock the email sending process
        # Send a POST request to the signup endpoint using the async client
        response = test_client.post("/api/v2/signup", json=payload)

        # Check that the response status code is 201 (Created)
        assert response.status_code == 400

        data = response.json()
        assert data["detail"] == "Email already registered"


@pytest.mark.asyncio
async def test_login(test_client: TestClient, mock_db: MockDatabase):
    mock_user_data = {
        "_id": ObjectId("665c71cbae7ecb3d1ea81dc1"),
        "email": "testuser@example.com",
        "hashed_password": get_password_hash("testpassword"),
        "is_active": True,
        "is_verified": True,
        "full_name": "John Doe",
        "date_joined": datetime(2024, 10, 5, 12, 34, 56, 789000),
        "is_company": False,
        "company_id": None,
        "promo": False
    }

    # Mocking database behavior for user find_one
    mock_db.add_collection_mock("Registered_users",
                                "find_one",
                                return_value=mock_user_data)

    # Attempt to login with correct credentials
    payload = {
        "username": "testuser@example.com",
        "password": "testpassword"
    }
    response = test_client.post("/api/v2/login", data=payload)
    print(response.json())
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data

    # Store the token for future use
    global access_token
    access_token = data["access_token"]


@pytest.mark.asyncio
async def test_login_password_unset_unverified(test_client: TestClient, mock_db: MockDatabase):
    mock_user_data = {
        "_id": ObjectId("665c71cbae7ecb3d1ea81dc1"),
        "email": "testuser@example.com",
        "is_active": True,
        "is_verified": True,
        "full_name": "John Doe",
        "date_joined": datetime(2024, 10, 5, 12, 34, 56, 789000),
        "is_company": False,
        "company_id": None,
        "promo": False
    }
    mock_unverified = {
        "_id": ObjectId("665c71cbae7ecb3d1ea81dc1"),
        "email": "testuser@example.com",
        "hashed_password": get_password_hash("testpassword"),
        "is_active": True,
        "is_verified": False,
        "full_name": "John Doe",
        "date_joined": datetime(2024, 10, 5, 12, 34, 56, 789000),
        "is_company": False,
        "company_id": None,
        "promo": False
    }
    # Mocking database behavior for user find_one
    mock_db.add_collection_mock("Registered_users",
                                "find_one",
                                return_value=mock_user_data)

    # Attempt to login with correct credentials
    payload = {
        "username": "testuser@example.com",
        "password": "testpassword"
    }
    response = test_client.post("/api/v2/login", data=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "Password not set for this user"

    mock_db.add_collection_mock("Registered_users",
                                "find_one",
                                return_value=mock_unverified)
    response = test_client.post("/api/v2/login", data=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "Email not verified"


@pytest.mark.asyncio
async def test_login_incorrect_password_email(test_client: TestClient, mock_db: MockDatabase):
    mock_user_data_incorrect_password = {
        "_id": ObjectId("665c71cbae7ecb3d1ea81dc1"),
        "email": "testuser@example.com",
        "hashed_password": get_password_hash("1234"),
        "is_verified": True,
    }
    mock_user_data_incorrect_email = {
    }
    # Mocking database behavior for user find_one
    mock_db.add_collection_mock(
        "Registered_users",
        "find_one",
        return_value=mock_user_data_incorrect_password)

    # Attempt to login with correct credentials
    payload = {
        "username": "testuser@example.com",
        "password": "testpassword"
    }
    response = test_client.post("/api/v2/login", data=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "Incorrect email or password"
    mock_db.add_collection_mock(
        "Registered_users",
        "find_one",
        return_value=mock_user_data_incorrect_email)
    response = test_client.post("/api/v2/login", data=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "Incorrect email or password"

def mock_decode_access_token(token: str):
    if token == "valid_token":
        return {"user_id": "60d21b4667d0d8992e610c85"}  # Valid user ID
    elif token == "invalid_token":
        return None
    elif token == "token_without_user_id":
        return {}
    else:
        return None

# @pytest.mark.asyncio
# async def test_verify_email(client, mock_db: MockDatabase):
#     # Mocking database behavior
#     mock_db.add_collection_mock("Users", "find_one", return_value={
#         "_id": ObjectId(),
#         "email": "testuser@example.com",
#         "is_active": False,
#         "is_verified": False
#     })
#
#     # Retrieve the user from the mock database
#     user = await mock_db.mock_db_instance["Users"].find_one({"email": "testuser@example.com"})
#     assert user is not None
#
#     # Generate a verification token
#     token_data = {"user_id": str(user["_id"])}
#     verification_token = create_access_token(token_data, expires_delta=timedelta(hours=24))
#
#     response = await client.get(f"/api/v2/verify-email?token={verification_token}")
#     assert response.status_code == 200
#     data = response.json()
#     assert data["message"] == "Email verified successfully"
#
#     # Verify that the user's is_active and is_verified fields are updated
#     mock_db.add_collection_mock("Users", "find_one", return_value={
#         "_id": ObjectId(),
#         "email": "testuser@example.com",
#         "is_active": True,
#         "is_verified": True
#     })
#
#     updated_user = await mock_db.mock_db_instance["Users"].find_one({"email": "testuser@example.com"})
#     assert updated_user["is_active"] == True
#     assert updated_user["is_verified"] == True
#

# @pytest.mark.asyncio
# async def test_protected_route(client):
#     # Access protected route with the token
#     headers = {"Authorization": f"Bearer {access_token}"}
#     response = await client.get("/api/v2/me", headers=headers)
#     assert response.status_code == 200
#     data = response.json()
#     assert data["email"] == "testuser@example.com"
#
# @pytest.mark.asyncio
# async def test_forgot_password(client, mock_db: MockDatabase):
#     with patch("app.services.email.send_email", side_effect=mock_send_email):
#         response = await client.post("/api/v2/forgot-password", params={"email": "testuser@example.com"})
#         assert response.status_code == 200
#         data = response.json()
#         assert data["message"] == "Password reset email sent"
#
# @pytest.mark.asyncio
# async def test_reset_password(client, mock_db: MockDatabase):
#     # Mocking database behavior for user find_one
#     mock_db.add_collection_mock("Users", "find_one", return_value={
#         "_id": ObjectId(),
#         "email": "testuser@example.com"
#     })
#
#     # Retrieve the user from the mock database
#     user = await mock_db.mock_db_instance["Users"].find_one({"email": "testuser@example.com"})
#     assert user is not None
#
#     # Generate a reset token
#     token_data = {"user_id": str(user["_id"])}
#     reset_token = create_access_token(token_data, expires_delta=timedelta(hours=1))
#
#     # Reset the password
#     new_password = "newtestpassword"
#     response = await client.post(
#         "/api/v2/auth/reset-password",
#         json={"token": reset_token, "new_password": new_password}
#     )
#     assert response.status_code == 200
#     data = response.json()
#     assert data["message"] == "Password reset successful"
#
#     # Attempt to login with the new password
#     payload = {
#         "username": "testuser@example.com",
#         "password": new_password
#     }
#     response = await client.post("/api/v2/login", data=payload)
#     assert response.status_code == 200
#     data = response.json()
#     assert "access_token" in data
#
# @pytest.mark.asyncio
# async def test_logout(client):
#     # Since logout is stateless, we can just call the endpoint
#     response = await client.post("/api/v2/logout")
#     assert response.status_code == 200
#     data = response.json()
#     assert data["message"] == "Logout successful"
