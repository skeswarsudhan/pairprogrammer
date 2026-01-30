"""Email utilities for sending emails to users."""
import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import logging

from dotenv import load_dotenv

load_dotenv()

# Email configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER)
FROM_NAME = os.getenv("FROM_NAME", "Pair Programmer")
LOGO_URL = os.getenv("LOGO_URL", "")

logger = logging.getLogger(__name__)


def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None
) -> bool:
    """
    Send an email to the specified address.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML body of the email
        text_content: Plain text version (optional)
    
    Returns:
        True if email was sent successfully, False otherwise
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP credentials not configured. Email not sent.")
        return False
    
    try:
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
        message["To"] = to_email
        
        # Add plain text version
        if text_content:
            part1 = MIMEText(text_content, "plain")
            message.attach(part1)
        
        # Add HTML version
        part2 = MIMEText(html_content, "html")
        message.attach(part2)
        
        # Create secure connection and send
        context = ssl.create_default_context()
        
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(FROM_EMAIL, to_email, message.as_string())
        
        logger.info(f"Email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        return False


def send_welcome_email(to_email: str, username: str, logo_url: Optional[str] = None) -> bool:
    """
    Send a welcome email to a newly registered user.
    
    Args:
        to_email: User's email address
        username: User's username
        logo_url: Optional URL to the logo image
    
    Returns:
        True if email was sent successfully, False otherwise
    """
    subject = "Welcome to Pair Programmer"
    
    # Logo section - uses LOGO_URL from environment or parameter
    # To add your logo: set LOGO_URL in .env to your hosted logo URL
    effective_logo_url = logo_url or LOGO_URL
    logo_section = ""
    if effective_logo_url:
        logo_section = f'<img src="{effective_logo_url}" alt="Pair Programmer" style="max-width: 120px; height: auto; margin-bottom: 20px; border-radius: 8px;">'
    else:
        # Text-based logo fallback
        logo_section = '<div style="font-size: 24px; font-weight: 700; letter-spacing: 2px;">PAIR PROGRAMMER</div>'
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700&display=swap" rel="stylesheet">
    </head>
    <body style="font-family: 'Open Sans', Arial, sans-serif; line-height: 1.7; max-width: 600px; margin: 0 auto; padding: 0;">
        
        <!-- Outer container -->
        <div style="padding: 40px 20px;">
            
            
            <!-- Main content card -->
            <div style="padding: 40px 30px; margin-top: 30px; border-radius: 8px; border: 1px solid #888888;">
                
                <h1 style="margin: 0 0 20px 0; font-size: 26px; font-weight: 600; text-align: center;">
                    Welcome Aboard
                </h1>
                
                <div style="width: 60px; height: 2px; background: #888888; margin: 0 auto 30px auto;"></div>
                
                <p style="font-size: 16px; margin-bottom: 25px;">
                    Hi <strong>{username}</strong>,
                </p>
                
                <p style="margin-bottom: 25px;">
                    Welcome to Pair Programmer - your collaborative coding companion in the vast universe of development.
                </p>
                
                <p style="margin-bottom: 15px;">Here's what you can do:</p>
                
                <ul style="padding-left: 20px; margin-bottom: 30px;">
                    <li style="margin-bottom: 12px;"><strong>Code together</strong> in real-time with other coders</li>
                    <li style="margin-bottom: 12px;"><strong>AI extension</strong> to get assistance from AI while you are struck</li>
                    <li style="margin-bottom: 12px;"><strong>Create private rooms</strong> for secure collaboration</li>
                </ul>
                
                <div style="text-align: center; margin: 35px 0;">
                    <a href="#" style="background: #555555; color: #ffffff; padding: 14px 35px; text-decoration: none; border-radius: 4px; font-weight: 600; display: inline-block; letter-spacing: 0.5px;">
                        Start Coding
                    </a>
                </div>
                
                <p style="font-size: 14px; margin-top: 30px; color: #666666;">
                    If you have any questions, feel free to reach out to me at <a href="mailto:skeswarsudhan@gmail.com">skeswarsudhan@gmail.com</a>.
                </p>
                
            </div>
            
            <!-- Footer -->
            <div style="text-align: center; padding: 30px 0; margin-top: 20px;">
                <p style="font-size: 11px; margin: 0; color: #888888;">
                    You're receiving this email because you registered for a Pair Programmer account.
                </p>
            </div>
            
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
    Welcome to Pair Programmer
    
    Hi {username},
    
    Welcome to Pair Programmer - your collaborative coding companion.
    
    Here's what you can do:
    - Code together in real-time with other coders
    - AI extension to get assistance from AI while you are struck
    - Create private rooms for secure collaboration

    
    If you have any questions, feel free to reach out to me at skeswarsudhan@gmail.com.
    
    — SK Eswar Sudhan
    """
    
    return send_email(to_email, subject, html_content, text_content)
