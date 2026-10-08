import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app

logger = logging.getLogger(__name__)

def send_otp_email(to_email: str, otp_code: str, purpose: str = "Registration"):
    """
    Sends a 6-digit OTP code to the recipient email.
    If OTP_MOCK_MODE is enabled or SMTP credentials are not configured,
    logs the OTP securely to console/logs for local development.
    """
    mock_mode = current_app.config.get('OTP_MOCK_MODE', True)
    mail_username = current_app.config.get('MAIL_USERNAME')
    mail_password = current_app.config.get('MAIL_PASSWORD')
    mail_server = current_app.config.get('MAIL_SERVER')
    mail_port = current_app.config.get('MAIL_PORT', 587)
    mail_sender = current_app.config.get('MAIL_DEFAULT_SENDER')
    if not mail_sender or 'noreply@dairymitra.com' in mail_sender:
        mail_sender = mail_username or 'noreply@dairymitra.com'

    purpose_titles = {
        'REGISTER': 'Account Registration',
        'FORGOT_PASSWORD': 'Password Reset',
        'VERIFY_EMAIL': 'Email Verification'
    }
    title = purpose_titles.get(purpose.upper(), 'Verification')

    subject = f"DairyMitra - Your {title} OTP Code: {otp_code}"
    
    # HTML Content
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
        <h2 style="color: #2E7D32; text-align: center;">DairyMitra</h2>
        <p style="font-size: 16px; color: #333;">Hello,</p>
        <p style="font-size: 14px; color: #555;">Use the following 6-digit OTP to complete your <strong>{title}</strong>:</p>
        <div style="text-align: center; margin: 30px 0;">
            <span style="display: inline-block; font-size: 32px; font-weight: bold; letter-spacing: 6px; color: #1B5E20; background: #E8F5E9; padding: 12px 24px; border-radius: 6px; border: 1px dashed #2E7D32;">
                {otp_code}
            </span>
        </div>
        <p style="font-size: 12px; color: #777;">This code is valid for 10 minutes. Do NOT share this code with anyone.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;" />
        <p style="font-size: 11px; color: #999; text-align: center;">DairyMitra - Smart Dairy & Farm Management Platform</p>
    </div>
    """

    if mock_mode or not mail_username or not mail_password:
        logger.info(f"\n[MOCK EMAIL DISPATCH] To: {to_email} | Subject: {subject} | OTP: {otp_code}\n")
        print(f"\n=======================================================\n[DAIRYMITRA EMAIL OTP]\nTo: {to_email}\nPurpose: {purpose}\nOTP: {otp_code}\n=======================================================\n")
        return True

    # Real SMTP Dispatch
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = mail_sender
        msg['To'] = to_email

        part1 = MIMEText(f"Your DairyMitra {title} OTP is {otp_code}. Valid for 10 minutes.", 'plain')
        part2 = MIMEText(html_content, 'html')

        msg.attach(part1)
        msg.attach(part2)

        with smtplib.SMTP(mail_server, mail_port) as server:
            if current_app.config.get('MAIL_USE_TLS', True):
                server.starttls()
            server.login(mail_username, mail_password)
            server.sendmail(mail_sender, [to_email], msg.as_string())
        
        return True
    except Exception as e:
        logger.error(f"Failed to dispatch email to {to_email}: {str(e)}")
        # In case of network error, do not crash; return False
        return False
