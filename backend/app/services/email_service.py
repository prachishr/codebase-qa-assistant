import smtplib
from email.message import EmailMessage

from backend.app.core.config import settings


def send_password_reset_email(
    to_email: str,
    username: str,
    reset_link: str,
) -> bool:
    """
    Send a password reset email using configured SMTP settings.
    Returns True if emailed, or False if SMTP is not configured (logs link in dev).
    """
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        print("\n========== PASSWORD RESET (SMTP NOT CONFIGURED) ==========")
        print(f"User: {username} <{to_email}>")
        print(f"Reset Link (expires in {settings.PASSWORD_RESET_EXPIRE_MINUTES} min): {reset_link}")
        print("==========================================================\n")
        return False

    sender = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
    smtp_password = settings.SMTP_PASSWORD.replace(" ", "").strip()

    message = EmailMessage()
    message["Subject"] = "Reset your Codebase QA Assistant password"
    message["From"] = sender
    message["To"] = to_email

    message.set_content(
        f"Hi {username},\n\n"
        f"Use the link below to reset your password (valid for {settings.PASSWORD_RESET_EXPIRE_MINUTES} minutes):\n\n"
        f"{reset_link}\n\n"
        "If you did not request a password reset, you can ignore this email.\n"
    )

    message.add_alternative(
        f"""
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #1e293b;">
            <h2>Reset your password</h2>
            <p>Hi {username},</p>
            <p>Click the button below to set a new password for your <strong>Codebase QA Assistant</strong> account. This link expires in {settings.PASSWORD_RESET_EXPIRE_MINUTES} minutes.</p>
            <p style="margin: 24px 0;">
              <a href="{reset_link}" style="background:#7c3aed;color:#ffffff;padding:12px 20px;border-radius:8px;text-decoration:none;font-weight:600;">
                Reset Password
              </a>
            </p>
            <p style="font-size:12px;color:#64748b;">Or copy and paste this link:<br>{reset_link}</p>
            <p style="font-size:12px;color:#64748b;">If you did not request this, you can safely ignore this email.</p>
          </body>
        </html>
        """,
        subtype="html",
    )

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as server:
        server.starttls()
        server.login(settings.SMTP_USER, smtp_password)
        server.send_message(message)

    return True
