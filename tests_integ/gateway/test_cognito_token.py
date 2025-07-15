import base64
import json
import logging
import os
import urllib.parse

import pytest
import urllib3

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("token-test")


def test_cognito_token_methods():
    """Test different methods of getting a Cognito token."""

    # Get credentials from environment variables
    client_id = os.environ.get("TEST_COGNITO_CLIENT_ID", "")
    client_secret = os.environ.get("TEST_COGNITO_CLIENT_SECRET", "")
    token_endpoint = os.environ.get("TEST_COGNITO_TOKEN_ENDPOINT", "")
    scope = os.environ.get("TEST_COGNITO_SCOPE", "")

    # Skip test if environment variables not set
    if not all([client_id, client_secret, token_endpoint, scope]):
        pytest.skip(
            "Cognito test credentials not configured. Set TEST_COGNITO_CLIENT_ID, "
            "TEST_COGNITO_CLIENT_SECRET, TEST_COGNITO_TOKEN_ENDPOINT, and TEST_COGNITO_SCOPE"
        )

    http = urllib3.PoolManager()

    # Method 1: Basic Auth
    logger.info("Method 1: Using Basic Auth...")
    credentials = f"{client_id}:{client_secret}"
    encoded_creds = base64.b64encode(credentials.encode()).decode()

    try:
        response = http.request(
            "POST",
            token_endpoint,
            body=f"grant_type=client_credentials&scope={urllib.parse.quote(scope)}",
            headers={
                "Authorization": f"Basic {encoded_creds}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        logger.info("Status: %s", response.status)
        # Don't log the full response as it may contain sensitive tokens
        if response.status == 200:
            logger.info("Response contains token data (not shown for security)")
        else:
            logger.info("Response: %s", response.data.decode())
        assert response.status == 200, f"Expected 200, got {response.status}"

    except Exception as e:
        pytest.fail(f"Error making request with basic auth: {e}")

    logger.info("")

    # Method 2: Form fields
    logger.info("Method 2: Using form fields...")
    form_data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": scope,
    }

    encoded_data = urllib.parse.urlencode(form_data)
    response = http.request(
        "POST",
        token_endpoint,
        body=encoded_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    logger.info("Status: %s", response.status)
    # Don't log the full response as it contains tokens
    if response.status == 200:
        logger.info("Response contains token data (not shown for security)")
    else:
        logger.info("Response: %s", response.data.decode())
    assert response.status == 200, f"Expected 200, got {response.status}"

    # Verify token structure
    token_data = json.loads(response.data.decode())
    assert "access_token" in token_data, "Response should contain access_token"
    assert "token_type" in token_data, "Response should contain token_type"
    assert token_data["token_type"].lower() == "bearer", "Token type should be Bearer"


if __name__ == "__main__":
    # For running directly
    test_cognito_token_methods()
