import os
import logging
import requests
from datetime import datetime
from app import db
from models import NotificationLog, SystemSettings
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

def send_whatsapp_message(to_number, message, application_id=None):
    """Send WhatsApp message using Twilio WhatsApp API"""
    try:
        import os
        from twilio.rest import Client
        
        # Force use environment variables directly
        account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        
        if not account_sid or not auth_token:
            logger.error("Twilio credentials not found in environment")
            logger.info(f"WhatsApp message (would send to {to_number}): {message}")
            log_notification(
                application_id=application_id,
                channel='whatsapp',
                recipient=to_number,
                message=message,
                status='pending',
                error_message='Credentials not configured'
            )
            return False
        
        # Use sandbox number for reliable messaging
        from_number = "whatsapp:+14155238886" 
        to_whatsapp = f"whatsapp:{to_number}"
        
        client = Client(account_sid, auth_token)
        
        message_obj = client.messages.create(
            body=message,
            from_=from_number,
            to=to_whatsapp
        )
        
        logger.info(f"WhatsApp message sent successfully to {to_number}, SID: {message_obj.sid}")
        log_notification(
            application_id=application_id,
            channel='whatsapp',
            recipient=to_number,
            message=message,
            status='sent'
        )
        return True
            
    except Exception as e:
        logger.error(f"Error sending WhatsApp message via Twilio: {e}")
        # For debugging, log what message would be sent
        logger.info(f"WhatsApp message (failed to send to {to_number}): {message}")
        log_notification(
            application_id=application_id,
            channel='whatsapp',
            recipient=to_number,
            message=message,
            status='failed',
            error_message=str(e)
        )
        return False

def send_email(to_email, subject, message, application_id=None):
    """Send email using SMTP"""
    try:
        # Get credentials from system settings first, fallback to environment variables
        smtp_server = SystemSettings.get_setting('smtp_server') or os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(SystemSettings.get_setting('smtp_port') or os.environ.get('SMTP_PORT', '587'))
        smtp_username = SystemSettings.get_setting('smtp_username') or os.environ.get('SMTP_USERNAME')
        smtp_password = SystemSettings.get_setting('smtp_password') or os.environ.get('SMTP_PASSWORD')
        from_email = SystemSettings.get_setting('from_email') or os.environ.get('FROM_EMAIL', smtp_username)
        
        if not smtp_username or not smtp_password:
            logger.error("Email credentials not configured in system settings")
            return False
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(message, 'plain'))
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        
        # Log the notification
        log_notification(
            application_id=application_id,
            channel='email',
            recipient=to_email,
            message=message,
            status='sent'
        )
        
        logger.info(f"Email sent to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        log_notification(
            application_id=application_id,
            channel='email',
            recipient=to_email,
            message=message,
            status='failed',
            error_message=str(e)
        )
        return False

def send_sms(to_number, message, application_id=None):
    """Send SMS using Twilio"""
    try:
        from twilio.rest import Client
        
        # Get credentials from system settings first, fallback to environment variables
        account_sid = SystemSettings.get_setting('twilio_account_sid') or os.environ.get('TWILIO_ACCOUNT_SID')
        auth_token = SystemSettings.get_setting('twilio_auth_token') or os.environ.get('TWILIO_AUTH_TOKEN')
        from_number = SystemSettings.get_setting('twilio_phone_number') or os.environ.get('TWILIO_PHONE_NUMBER')
        
        if not account_sid or not auth_token or not from_number:
            logger.error("Twilio credentials not configured in system settings")
            return False
        
        client = Client(account_sid, auth_token)
        
        sms_message = client.messages.create(
            body=message,
            from_=from_number,
            to=to_number
        )
        
        # Log the notification
        log_notification(
            application_id=application_id,
            channel='sms',
            recipient=to_number,
            message=message,
            status='sent'
        )
        
        logger.info(f"SMS sent to {to_number}, SID: {sms_message.sid}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending SMS: {e}")
        log_notification(
            application_id=application_id,
            channel='sms',
            recipient=to_number,
            message=message,
            status='failed',
            error_message=str(e)
        )
        return False

def send_bulk_notification(applications, message, channels=['whatsapp']):
    """Send bulk notifications to multiple applications"""
    results = {'sent': 0, 'failed': 0}
    
    for application in applications:
        success = False
        
        for channel in channels:
            try:
                if channel == 'whatsapp' and application.whatsapp_number:
                    success = send_whatsapp_message(
                        application.whatsapp_number, 
                        message, 
                        application.id
                    )
                elif channel == 'email' and application.email:
                    success = send_email(
                        application.email,
                        f"Update: {application.internship.title}",
                        message,
                        application.id
                    )
                elif channel == 'sms' and application.phone_number:
                    success = send_sms(
                        application.phone_number, 
                        message, 
                        application.id
                    )
                
                if success:
                    results['sent'] += 1
                    break  # Success on one channel, don't try others
                    
            except Exception as e:
                logger.error(f"Error sending {channel} notification to application {application.id}: {e}")
        
        if not success:
            results['failed'] += 1
    
    return results

def log_notification(application_id, channel, recipient, message, status, error_message=None):
    """Log notification attempt to database"""
    try:
        notification_log = NotificationLog(
            application_id=application_id,
            channel=channel,
            recipient=recipient,
            message=message,
            status=status,
            sent_at=datetime.utcnow() if status == 'sent' else None,
            error_message=error_message
        )
        
        db.session.add(notification_log)
        db.session.commit()
        
    except Exception as e:
        logger.error(f"Error logging notification: {e}")
        db.session.rollback()
