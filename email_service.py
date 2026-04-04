"""
email_service.py — Send lead notification via Gmail SMTP
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def send_lead_email(lead_data: dict) -> tuple[bool, str]:
    """
    Sends a lead notification email using Gmail SMTP + TLS.
    Returns (success: bool, message: str).
    """
    email_user = os.environ.get("EMAIL_USER", "")
    email_pass = os.environ.get("EMAIL_PASS", "")

    if not email_user or not email_pass:
        msg = "EMAIL_USER or EMAIL_PASS environment variable is not set."
        logger.error(msg)
        return False, msg

    name      = lead_data.get("name", "—")
    email     = lead_data.get("email", "—")
    phone     = lead_data.get("phone", "—")
    timestamp = lead_data.get("timestamp", "—")

    subject = f"🚀 New Lead: {name}"

    # Plain-text body
    text_body = f"""
New lead captured via AI Chatbot
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Name      : {name}
Email     : {email}
Phone     : {phone}
Timestamp : {timestamp}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    # HTML body
    html_body = f"""
<!DOCTYPE html>
<html>
<body style="font-family:DM Sans,Arial,sans-serif;background:#0d0d0f;color:#e8e6e0;padding:32px;">
  <div style="max-width:480px;margin:0 auto;background:#111114;border:1px solid #222228;
              border-radius:16px;padding:32px;">
    <h2 style="color:#7c7cf0;font-family:monospace;margin-top:0;">🚀 New Lead Captured</h2>
    <table style="width:100%;border-collapse:collapse;">
      <tr><td style="padding:10px 0;color:#888;width:110px;">Name</td>
          <td style="padding:10px 0;font-weight:600;">{name}</td></tr>
      <tr><td style="padding:10px 0;color:#888;">Email</td>
          <td style="padding:10px 0;"><a href="mailto:{email}" style="color:#7c7cf0;">{email}</a></td></tr>
      <tr><td style="padding:10px 0;color:#888;">Phone</td>
          <td style="padding:10px 0;">{phone}</td></tr>
      <tr><td style="padding:10px 0;color:#888;">Timestamp</td>
          <td style="padding:10px 0;font-family:monospace;font-size:0.85em;">{timestamp}</td></tr>
    </table>
  </div>
  <p style="text-align:center;color:#444;font-size:0.8em;margin-top:16px;">
    AI Chatbot · Lead Notification
  </p>
</body>
</html>
"""

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = email_user
        msg["To"]      = email_user  # send to yourself; change if needed

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(email_user, email_pass)
            server.sendmail(email_user, email_user, msg.as_string())

        logger.info("Lead email sent to %s", email_user)
        return True, "Email sent successfully."

    except smtplib.SMTPAuthenticationError:
        msg = "SMTP authentication failed. Check EMAIL_USER / EMAIL_PASS (use App Password)."
        logger.error(msg)
        return False, msg
    except smtplib.SMTPException as e:
        msg = f"SMTP error: {str(e)}"
        logger.error(msg)
        return False, msg
    except Exception as e:
        msg = f"Email unexpected error: {str(e)}"
        logger.error(msg)
        return False, msg
