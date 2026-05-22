import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib
from jinja2 import Environment, select_autoescape

from app.core.config import settings

logger = logging.getLogger(__name__)

_jinja = Environment(autoescape=select_autoescape(["html"]))

_ALERT_TEMPLATE = _jinja.from_string("""
<html><body>
<h2 style="color:#0f766e">Alert: {{ rule_name }}</h2>
<p><strong>Status:</strong> {{ status }}</p>
<p><strong>Value:</strong> {{ value }}</p>
<p><strong>Message:</strong> {{ message }}</p>
<hr/>
<small>WexaAI Analytics &mdash; {{ org_name }}</small>
</body></html>
""")

_REPORT_TEMPLATE = _jinja.from_string("""
<html><body>
<h2 style="color:#0f766e">Scheduled Report: {{ report_name }}</h2>
<p>Your report has been generated and is attached.</p>
<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse">
  <tr><th>Metric</th><th>Value</th></tr>
  {% for row in rows %}
  <tr><td>{{ row.label }}</td><td>{{ row.value }}</td></tr>
  {% endfor %}
</table>
<hr/>
<small>WexaAI Analytics &mdash; {{ org_name }}</small>
</body></html>
""")


async def send_email(to: list[str], subject: str, html: str) -> None:
    if not to:
        return
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = ", ".join(to)
    msg.attach(MIMEText(html, "html"))
    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user or None,
            password=settings.smtp_password or None,
            use_tls=settings.smtp_tls,
            start_tls=False,
        )
    except Exception:
        logger.exception("Failed to send email to %s", to)


async def send_alert_email(
    to: list[str],
    rule_name: str,
    status: str,
    value: float,
    message: str,
    org_name: str,
) -> None:
    html = _ALERT_TEMPLATE.render(
        rule_name=rule_name, status=status, value=value, message=message, org_name=org_name
    )
    await send_email(to, f"[WexaAI Alert] {rule_name} — {status}", html)


async def send_report_email(
    to: list[str],
    report_name: str,
    rows: list[dict],
    org_name: str,
) -> None:
    html = _REPORT_TEMPLATE.render(report_name=report_name, rows=rows, org_name=org_name)
    await send_email(to, f"[WexaAI Report] {report_name}", html)
