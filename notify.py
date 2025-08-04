import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from logger import get_logger

# Set up logger
logger = get_logger('notify', 'logs/notify.log')

def send_email(subject, message, to_email="your-email@example.com"):
    """Send email notification"""
    try:
        msg = MIMEMultipart()
        msg['From'] = "your-email@example.com"
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(message, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login("your-email@example.com", "your-app-password")
        text = msg.as_string()
        server.sendmail("your-email@example.com", to_email, text)
        server.quit()
        
        logger.info(f"Email sent: {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False 