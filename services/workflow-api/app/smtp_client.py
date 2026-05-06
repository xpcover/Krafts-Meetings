"""SMTP delivery helpers for workflow-api."""

import asyncio
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Iterable

from app.config import Settings


class SmtpDeliveryError(Exception):
    """Raised when SMTP verification or delivery fails."""

    def __init__(self, message: str, retryable: bool | None = None):
        super().__init__(message)
        self.retryable = retryable


@dataclass(frozen=True)
class SmtpResult:
    status: str
    response: str


class SmtpClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def configured(self) -> bool:
        return bool(self.settings.smtp_host and self.settings.smtp_from_email)

    async def verify(self) -> SmtpResult:
        return await asyncio.to_thread(self._verify_sync)

    async def send(self, recipients: Iterable[str], subject: str, body: str) -> SmtpResult:
        recipient_list = [email for email in dict.fromkeys(recipients) if email]
        if not recipient_list:
            raise SmtpDeliveryError("No SMTP recipients provided")
        return await asyncio.to_thread(self._send_sync, recipient_list, subject, body)

    def _connect(self):
        mode = self.settings.smtp_tls_mode.lower()
        if mode == "ssl":
            server = smtplib.SMTP_SSL(self.settings.smtp_host, self.settings.smtp_port, timeout=20)
        else:
            server = smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=20)
        server.ehlo()
        if mode == "starttls":
            server.starttls()
            server.ehlo()
        if self.settings.smtp_username:
            server.login(self.settings.smtp_username, self.settings.smtp_password)
        return server

    @staticmethod
    def _error_from_exception(exc: Exception) -> SmtpDeliveryError:
        retryable = None
        if isinstance(exc, smtplib.SMTPResponseException):
            retryable = 400 <= exc.smtp_code < 500
        elif isinstance(exc, smtplib.SMTPAuthenticationError):
            retryable = False
        elif isinstance(exc, (OSError, smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError)):
            retryable = True
        return SmtpDeliveryError(str(exc), retryable=retryable)

    @staticmethod
    def _refused_recipients_error(refused: dict) -> SmtpDeliveryError:
        retryable = None
        codes = [value[0] for value in refused.values() if isinstance(value, tuple) and value]
        if codes:
            retryable = all(400 <= code < 500 for code in codes)
        return SmtpDeliveryError(f"SMTP refused recipients: {refused}", retryable=retryable)

    def _verify_sync(self) -> SmtpResult:
        if not self.configured:
            raise SmtpDeliveryError("SMTP_HOST and SMTP_FROM_EMAIL are required")
        try:
            with self._connect() as server:
                noop_code, noop_message = server.noop()
            if noop_code >= 400:
                raise SmtpDeliveryError(f"SMTP NOOP failed: {noop_code} {noop_message!r}")
            return SmtpResult(status="verified", response=f"SMTP verified with NOOP {noop_code}")
        except (OSError, smtplib.SMTPException) as exc:
            raise self._error_from_exception(exc) from exc

    def _send_sync(self, recipients: list[str], subject: str, body: str) -> SmtpResult:
        if not self.configured:
            raise SmtpDeliveryError("SMTP_HOST and SMTP_FROM_EMAIL are required")
        message = EmailMessage()
        message["From"] = self.settings.smtp_from_email
        message["To"] = ", ".join(recipients)
        message["Subject"] = subject
        message.set_content(body)
        try:
            with self._connect() as server:
                refused = server.send_message(message)
            if refused:
                raise self._refused_recipients_error(refused)
            return SmtpResult(status="sent", response="SMTP message accepted")
        except (OSError, smtplib.SMTPException) as exc:
            raise self._error_from_exception(exc) from exc
