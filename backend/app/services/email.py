from email.message import EmailMessage
from pathlib import Path
import logging
import mimetypes
import smtplib

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    def is_configured(self) -> bool:
        return bool(settings.smtp_host and settings.smtp_from_email)

    def send_proposal(
        self,
        *,
        recipient_email: str,
        subject: str,
        body: str,
        attachment_path: str | None = None,
    ) -> dict:
        if not self.is_configured():
            logger.warning("Proposal email send skipped because SMTP is not configured.")
            return {"status": "skipped", "reason": "missing_smtp_config"}

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
        message["To"] = recipient_email
        message.set_content(body)

        if attachment_path:
            path = Path(attachment_path)
            if path.exists() and path.is_file():
                content_type, _encoding = mimetypes.guess_type(path.name)
                main_type, sub_type = (content_type or "application/pdf").split("/", 1)
                message.add_attachment(
                    path.read_bytes(),
                    maintype=main_type,
                    subtype=sub_type,
                    filename=path.name,
                )

        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
                if settings.smtp_use_tls:
                    smtp.starttls()
                if settings.smtp_user and settings.smtp_password:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(message)
            return {"status": "sent", "reference": "smtp"}
        except (OSError, smtplib.SMTPException):
            logger.exception("Failed to send proposal email.")
            return {"status": "error", "reason": "email_send_failed"}
