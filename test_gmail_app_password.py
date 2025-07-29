import os
import smtplib
import pytest

EMAIL = os.getenv("TEST_GMAIL_EMAIL")
APP_PASSWORD = os.getenv("TEST_GMAIL_APP_PASSWORD")

@pytest.mark.skipif(not EMAIL or not APP_PASSWORD, reason="Gmail credentials not provided")
def test_gmail_app_password() -> None:
    """Verify that the provided Gmail App Password works."""
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
        server.starttls()
        server.login(EMAIL, APP_PASSWORD)

