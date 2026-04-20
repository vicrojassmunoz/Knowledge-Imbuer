import html
import logging
import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import httpx
import resend

from src.config import (
    TELEGRAM_TOKEN,
    TELEGRAM_CHAT_ID,
    EMAIL_TO,
    EMAIL_FROM
)
from src.fetcher import NewsItem

logger = logging.getLogger(__name__)

# TODO: Interface it

# Telegram

def _format_telegram(items: list[NewsItem]) -> str:
    lines = ["<b>Knowledge Imbuer — Daily Digest</b>\n"]

    for i, item in enumerate(items,1 ):
        lines.append(
            f"{i}. <a href='{item.url}'>{html.escape(item.title)}</a>\n"
            f"<i>{html.escape(item.one_liner)}</i>\n"
            f"<code>{item.source}</code>\n"
        )

    return "\n".join(lines)

def send_telegram(items: list[NewsItem]) -> bool:
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": _format_telegram(items),
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        response = httpx.post(url, json=payload, timeout=10)

        response.raise_for_status()
        logger.info(f"Telegram notification sent - {len(items)} items")
        return True

    except Exception as e:
        logger.error(f"Failed to send telegram notification - {e}")
        return False



# Email

def _format_email(items: list[NewsItem]) -> str:
    rows = ""
    for i, item in enumerate(items,1 ):
        rows += f"""
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #eee;">
                <strong>{i}. <a href="{item.url}" style="color: #0066cc;">{item.title}</a></strong><br>
                <span style="color: #555; font-size: 13px;">{item.one_liner}</span><br>
                <span style="color: #999; font-size: 11px;">{item.source}</span>
            </td>
        </tr>
        """

    return f"""
    <html><body style="font-family: Arial, sans-serif; max-width: 600px; margin: auto;">
        <h2 style="color: #333;">Knowledge Imbuer — Daily Digest</h2>
        <table width="100%" cellpadding="0" cellspacing="0">{rows}</table>
        <p style="color: #999; font-size: 11px; margin-top: 20px;">
            Powered by Athena
        </p>
    </body></html>        
    """

def send_email(items: list[NewsItem]) -> bool:
    try:
        params = {
            "from": EMAIL_FROM,
            "to": EMAIL_TO,
            "subject": f"Knowledge Imbuer — {len(items)} items worth your time",
            "html": _format_email(items),
        }

        resend.Emails.send(params)
        logger.info(f"Email sent to {EMAIL_TO} — {len(items)} items")
        return True

    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


def notify_all(items: list[NewsItem]) -> bool:
    if not items:
        logger.info("No items to notify")
        return True

    telegram = send_telegram(items)
    email = send_email(items)

    return telegram and email

