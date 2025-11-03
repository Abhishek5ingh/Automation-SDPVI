from email.message import EmailMessage

from src.email.parser import extract_otp_from_email, extract_otp_from_text


def test_extract_otp_from_text_with_default_regex():
    assert extract_otp_from_text("Your code is 123456. Do not share.") == "123456"


def test_extract_otp_from_text_without_match():
    assert extract_otp_from_text("No code here.") is None


def test_extract_otp_from_email():
    message = EmailMessage()
    message.set_content("OTP: 654321")
    assert extract_otp_from_email(message) == "654321"
