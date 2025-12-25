import logging
from typing import List, Dict, Optional
from datetime import datetime
from jinja2 import Template
from dotenv import load_dotenv
import os

# Import SMTP modules for email sending
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()

from infrastructure.config import (
    EMAIL_SMTP_SERVER,
    EMAIL_SMTP_PORT,
    EMAIL_USERNAME,
    EMAIL_PASSWORD,
    EMAIL_FROM,
    EMAIL_TO
)

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.from_email = EMAIL_FROM
        self.to_emails = EMAIL_TO  # Now a list of email addresses

        # Use SMTP for email sending
        self.smtp_server = EMAIL_SMTP_SERVER
        self.smtp_port = EMAIL_SMTP_PORT
        self.username = EMAIL_USERNAME
        self.password = EMAIL_PASSWORD
        print("Using SMTP for email sending")

    def send_signal_notification(self, new_signals: List[Dict], scrape_date: str):
        """
        Send email notification for new signal companies

        Args:
            new_signals: List of dicts with company info (name, logo_url, score, etc.)
            scrape_date: The date when products were scraped
        """
        if not new_signals:
            logger.info("No new signals to notify about")
            return

        subject = f"New Signal Companies Detected - {scrape_date}"

        # Create HTML content
        html_content = self._create_signal_email_html(new_signals, scrape_date)

        # Send email to all recipients
        for to_email in self.to_emails:
            self._send_email(subject, html_content, to_email)

        logger.info(f"Sent signal notification email for {len(new_signals)} companies on {scrape_date} to {len(self.to_emails)} recipients")

    def _create_signal_email_html(self, new_signals: List[Dict], scrape_date: str) -> str:
        try:
            date_obj = datetime.strptime(scrape_date, "%Y-%m-%d")
            formatted_date = date_obj.strftime("%B %d, %Y")
        except:
            formatted_date = scrape_date
        html_template = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Signal Companies Alert</title>
<style>
    body {
        font-family: Arial, sans-serif;
        background-color: #f4f6f8;
        padding: 20px;
        margin: 0;
    }
    .container {
        max-width: 600px;
        margin: 0 auto;
        background: #ffffff;
        padding: 20px;
        border-radius: 8px;
    }
    .header {
        text-align: center;
        border-bottom: 2px solid #2563eb;
        padding-bottom: 15px;
        margin-bottom: 20px;
    }
    .header h2 {
        margin: 0;
        color: #2563eb;
    }
    .count {
        text-align: center;
        background: #e3f2fd;
        padding: 8px;
        border-radius: 6px;
        font-weight: bold;
        margin-bottom: 20px;
        color: #1976d2;
    }
    .card {
        border: 1px solid #d1d5db;
        border-radius: 6px;
        padding: 14px;
        background: #f9fafb;
        text-align: center;
        cursor: pointer;
        transition: all 0.2s ease;
        text-decoration: none;
        color: inherit;
        display: block;
    }
    .card:hover {
        background: #f3f4f6;
        border-color: #2563eb;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transform: translateY(-1px);
    }
    .logo {
        width: 48px;
        height: 48px;
        border-radius: 6px;
        background: #2563eb;
        color: #ffffff;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        font-weight: bold;
        margin: 0 auto 8px;
    }
    .name {
        font-weight: bold;
        margin-bottom: 6px;
    }
    .score {
        color: #16a34a;
        font-weight: bold;
        font-size: 14px;
    }
    .footer {
        text-align: center;
        font-size: 12px;
        color: #6b7280;
        margin-top: 25px;
        border-top: 1px solid #e5e7eb;
        padding-top: 15px;
    }
</style>
</head>

<body>
<div class="container">

<div class="header">
    <h2>🚀 Signal Companies Alert</h2>
    <p>New companies showing strong signals detected</p>
</div>

<div class="count">
    {{ signal_count }} signal companies · {{ formatted_date }}
</div>

<table width="100%" cellpadding="10" cellspacing="0" role="presentation">
<tr>
{% for signal in new_signals %}
    <td width="33%" valign="top">
        {% if signal.product_metadata and signal.product_metadata.get('product_hunt') and signal.product_metadata['product_hunt'].get('website') %}
        <a href="{{ signal.product_metadata['product_hunt']['website'] }}" class="card" target="_blank" rel="noopener noreferrer">
        {% else %}
        <div class="card">
        {% endif %}
            {% if signal.logo_url %}
                <img src="{{ signal.logo_url }}" width="48" height="48" style="border-radius:6px;">
            {% else %}
                <div class="logo">{{ signal.company_name[0].upper() }}</div>
            {% endif %}
            <div class="name">{{ signal.company_name }}</div>
            <div class="score">Score: {{ signal.score }}/100</div>
            {% if signal.launch_date %}
            <div style="font-size:12px; color:#6b7280;">
                {{ signal.launch_date }}
            </div>
            {% endif %}
        {% if signal.product_metadata and signal.product_metadata.get('product_hunt') and signal.product_metadata['product_hunt'].get('website') %}
        </a>
        {% else %}
        </div>
        {% endif %}
    </td>

    {% if loop.index % 3 == 0 %}
</tr><tr>
    {% endif %}
{% endfor %}
</tr>
</table>

<div class="footer">
    This email was automatically generated by the Signal Detector system.
</div>

</div>
</body>
</html>
"""
        return Template(html_template).render(
            new_signals=new_signals,
            signal_count=len(new_signals),
            formatted_date=formatted_date
        )

    def _send_email(self, subject: str, html_content: str, to_email: str):
        """Send email using SMTP"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to_email

            # Attach HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)

            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.username, self.password)
            server.sendmail(self.from_email, to_email, msg.as_string())
            server.quit()

            logger.info(f"Email sent successfully to {to_email} via SMTP")

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            raise
