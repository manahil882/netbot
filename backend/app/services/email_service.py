import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def send_verification_email(to_email: str, code: str) -> None:
    """Send a signup verification code via Resend, or log it in dev mode."""
    subject = "Your NetBot verification code"
    text = (
        f"Your NetBot verification code is {code}.\n\n"
        f"It expires in {settings.EMAIL_OTP_EXPIRE_MINUTES} minutes.\n"
        "If you did not request this, you can ignore this email."
    )
    html = (
        f"<p>Your NetBot verification code is:</p>"
        f"<p style='font-size:24px;font-weight:700;letter-spacing:4px'>{code}</p>"
        f"<p>It expires in {settings.EMAIL_OTP_EXPIRE_MINUTES} minutes.</p>"
    )

    if not settings.RESEND_API_KEY:
        logger.warning(
            "RESEND_API_KEY not set — verification code for %s is %s (dev only)",
            to_email,
            code,
        )
        return

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": settings.EMAIL_FROM,
                "to": [to_email],
                "subject": subject,
                "text": text,
                "html": html,
            },
        )
        if response.status_code >= 400:
            logger.error("Resend failed: %s %s", response.status_code, response.text)
            raise RuntimeError("Could not send verification email")
