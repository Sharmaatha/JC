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
        """Create HTML email content for signal notifications"""

        # Convert scrape_date to readable format
        try:
            date_obj = datetime.strptime(scrape_date, "%Y-%m-%d")
            formatted_date = date_obj.strftime("%B %d, %Y")
        except:
            formatted_date = scrape_date

        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Signal Companies Alert</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            background-color: #f8f9fa;
            padding: 20px;
        }
        .container {
            background-color: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .header {
            text-align: center;
            border-bottom: 3px solid #007bff;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        .header h1 {
            color: #007bff;
            margin: 0;
            font-size: 28px;
        }
        .signal-card {
            border: 2px solid #28a745;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
            background-color: #f8fff9;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        .signal-item {
            border: 1px solid #dee2e6;
            border-radius: 6px;
            padding: 15px;
            background-color: white;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        .company-logo {
            width: 60px;
            height: 60px;
            border-radius: 8px;
            object-fit: cover;
            margin-right: 15px;
            border: 2px solid #dee2e6;
        }
        .company-info {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
        }
        .company-details h3 {
            margin: 0 0 5px 0;
            color: #28a745;
            font-size: 20px;
        }
        .score-badge {
            display: inline-block;
            background-color: #28a745;
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 14px;
            margin-bottom: 8px;
        }
        .launch-date {
            color: #6c757d;
            font-size: 12px;
            font-weight: 500;
        }
        .date-info {
            color: #6c757d;
            font-size: 14px;
            margin-top: 10px;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #dee2e6;
            color: #6c757d;
            font-size: 12px;
        }
        .signal-count {
            background-color: #e3f2fd;
            color: #1976d2;
            padding: 10px;
            border-radius: 5px;
            text-align: center;
            margin-bottom: 20px;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Signal Companies Alert</h1>
            <p>Exciting new companies showing strong signal indicators!</p>
        </div>

        <div class="signal-count">
            {{ signal_count }} new signal companies detected for {{ formatted_date }}
        </div>

        <div class="signal-card">
            {% for signal in new_signals %}
            <div class="signal-item">
                <div class="company-info">
                    {% if signal.logo_url %}
                    <img src="{{ signal.logo_url }}" alt="{{ signal.company_name }} logo" class="company-logo">
                    {% else %}
                    <div class="company-logo" style="background-color: #007bff; display: flex; align-items: center; justify-content: center; color: white; font-size: 24px; font-weight: bold;">
                        {{ signal.company_name[0].upper() }}
                    </div>
                    {% endif %}
                    <div class="company-details">
                        <h3>{{ signal.company_name }}</h3>
                        <span class="score-badge">Signal Score: {{ signal.score }}/100</span>
                        {% if signal.launch_date %}
                        <div class="launch-date">Launched: {{ signal.launch_date }}</div>
                        {% endif %}
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>

        <div class="footer">
            <p>This email was automatically generated by the Signal Detector system.</p>
            <p>Stay tuned for more signal insights!</p>
        </div>
    </div>
</body>
</html>
        """

        template = Template(html_template)
        return template.render(
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
