import os
import smtplib
import pytest


NETWORK_TESTS = os.getenv("RUN_NETWORK_TESTS")


@pytest.mark.skipif(not NETWORK_TESTS, reason="Network tests disabled")
def test_smtp_starttls() -> None:
    """Verify that the Gmail SMTP STARTTLS endpoint is reachable."""
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
        server.starttls()


@pytest.mark.skipif(not NETWORK_TESTS, reason="Network tests disabled")
def test_smtp_ssl() -> None:
    """Verify that the Gmail SMTP SSL endpoint is reachable."""
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10):
        pass


