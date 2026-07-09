import logging
from collections.abc import Iterable
from email.message import EmailMessage
from typing import TypedDict

import aiosmtplib

from core.config import config

logger = logging.getLogger(__name__)


class EmailAttachment(TypedDict, total=False):
    filename: str
    content: bytes
    maintype: str
    subtype: str
    cid: str


async def send_email(
    to: str,
    subject: str,
    html_body: str,
    attachments: Iterable[EmailAttachment] | None = None,
) -> bool:
    if not config.EMAILS_ENABLED or not config.SMTP_HOST:
        logger.warning(
            "Email delivery disabled or SMTP not configured; skipping email to %s", to
        )
        return False

    message = EmailMessage()
    message["From"] = config.SMTP_FROM
    message["To"] = to
    message["Subject"] = subject
    message.set_content(
        "Thank you for your order. Your CinemaX tickets are attached — "
        "open this email in an HTML-capable client to view them."
    )
    message.add_alternative(html_body, subtype="html")

    html_part = message.get_payload()[1]

    for attachment in attachments or []:
        cid = attachment.get("cid")
        if cid:
            html_part.add_related(
                attachment["content"],
                maintype=attachment["maintype"],
                subtype=attachment["subtype"],
                cid=f"<{cid}>",
            )
        else:
            message.add_attachment(
                attachment["content"],
                maintype=attachment["maintype"],
                subtype=attachment["subtype"],
                filename=attachment["filename"],
            )

    try:
        await aiosmtplib.send(
            message,
            hostname=config.SMTP_HOST,
            port=config.SMTP_PORT,
            username=config.SMTP_USER,
            password=config.SMTP_PASSWORD,
            start_tls=config.SMTP_TLS,
        )
    except aiosmtplib.SMTPException:
        logger.exception("Failed to send email to %s", to)
        return False

    logger.info("Email sent to %s (subject=%s)", to, subject)
    return True
