import os
import logging
from datetime import datetime
from app import app, db
from models import Application, Internship, WhatsAppMessage
from communication import send_whatsapp_message
from utils import save_media_file
import requests

logger = logging.getLogger(__name__)

# Conversation states
STATE_WAITING_FOR_APPLY = 'waiting_for_apply'
STATE_WAITING_FOR_NAME = 'waiting_for_name'
STATE_WAITING_FOR_EMAIL = 'waiting_for_email'
STATE_WAITING_FOR_PHONE = 'waiting_for_phone'
STATE_WAITING_FOR_COVER_LETTER = 'waiting_for_cover_letter'
STATE_WAITING_FOR_CV = 'waiting_for_cv'
STATE_COMPLETED = 'completed'

def handle_webhook(data):
    """Handle incoming WhatsApp webhook data"""
    try:
        if 'entry' not in data:
            return
        
        for entry in data['entry']:
            if 'changes' not in entry:
                continue
                
            for change in entry['changes']:
                if change.get('field') != 'messages':
                    continue
                
                value = change.get('value', {})
                
                # Handle incoming messages
                if 'messages' in value:
                    for message in value['messages']:
                        handle_incoming_message(message)
                
                # Handle message status updates
                if 'statuses' in value:
                    for status in value['statuses']:
                        handle_message_status(status)
                        
    except Exception as e:
        logger.error(f"Error handling webhook: {e}")

def handle_incoming_message(message):
    """Process incoming WhatsApp message"""
    try:
        message_id = message.get('id')
        from_number = message.get('from')
        timestamp = message.get('timestamp')
        message_type = message.get('type', 'text')
        
        # Store message in database
        from models import SystemSettings
        to_number = SystemSettings.get_setting('whatsapp_phone_number_id') or os.environ.get('WHATSAPP_NUMBER', 'system')
        
        whatsapp_msg = WhatsAppMessage(
            message_id=message_id,
            from_number=from_number,
            to_number=to_number,
            message_type=message_type,
            received_at=datetime.fromtimestamp(int(timestamp))
        )
        
        if message_type == 'text':
            message_body = message.get('text', {}).get('body', '').strip()
            whatsapp_msg.message_body = message_body
            
        elif message_type in ['image', 'document']:
            # Handle Twilio media format
            media_url = message.get('media_url')
            if media_url:
                whatsapp_msg.media_url = media_url
                message_body = f"[{message_type.upper()}_ATTACHMENT]"
                whatsapp_msg.message_body = message_body
            else:
                # Handle Facebook API format
                media_id = None
                if message_type == 'image':
                    media_id = message.get('image', {}).get('id')
                elif message_type == 'document':
                    media_id = message.get('document', {}).get('id')
                
                if media_id:
                    media_url = get_media_url(media_id)
                    whatsapp_msg.media_url = media_url
                    message_body = f"[{message_type.upper()}_ATTACHMENT]"
                    whatsapp_msg.message_body = message_body
        
        db.session.add(whatsapp_msg)
        
        # Find or create application record for this number
        application = get_or_create_application(from_number)
        
        # Process message based on conversation state
        if message_type == 'text':
            process_text_message(application, message_body, from_number)
        elif message_type in ['image', 'document'] and application.conversation_state == STATE_WAITING_FOR_CV:
            process_media_message(application, whatsapp_msg, from_number)
        
        whatsapp_msg.status = 'processed'
        whatsapp_msg.processed_at = datetime.utcnow()
        db.session.commit()
        
    except Exception as e:
        logger.error(f"Error handling incoming message: {e}")
        db.session.rollback()

def get_or_create_application(phone_number):
    """Get existing application or create new one for phone number"""
    # Look for existing incomplete application
    application = Application.query.filter_by(
        whatsapp_number=phone_number,
        conversation_state=STATE_COMPLETED
    ).first()
    
    if not application:
        # Look for any incomplete application
        application = Application.query.filter_by(
            whatsapp_number=phone_number
        ).filter(Application.conversation_state != STATE_COMPLETED).first()
    
    if not application:
        application = Application(
            whatsapp_number=phone_number,
            conversation_state=STATE_WAITING_FOR_APPLY,
            temp_data={}
        )
        db.session.add(application)
    
    return application

def process_text_message(application, message_body, from_number):
    """Process text message based on conversation state"""
    state = application.conversation_state
    
    if state == STATE_WAITING_FOR_APPLY:
        handle_apply_command(application, message_body, from_number)
    elif state == STATE_WAITING_FOR_NAME:
        handle_name_input(application, message_body, from_number)
    elif state == STATE_WAITING_FOR_EMAIL:
        handle_email_input(application, message_body, from_number)
    elif state == STATE_WAITING_FOR_PHONE:
        handle_phone_input(application, message_body, from_number)
    elif state == STATE_WAITING_FOR_COVER_LETTER:
        handle_cover_letter_input(application, message_body, from_number)
    elif state == STATE_WAITING_FOR_CV:
        # If they send text instead of file, remind them
        send_whatsapp_message(
            from_number,
            "📎 Please attach your **CV** as a PDF, Word document, or image file to complete your application."
        )

def handle_apply_command(application, message_body, from_number):
    """Handle APPLY command with position and secret codes"""
    parts = message_body.upper().split()
    
    if len(parts) < 3 or parts[0] != 'APPLY':
        send_whatsapp_message(
            from_number,
            "🚀 **Welcome to our Internship Application System!**\n\n📝 To apply for an internship, please send:\n**APPLY [POSITION_CODE] [SECRET_CODE]**\n\n💡 **Example:** APPLY WD001 SECRET123\n\n🔍 Make sure you have the correct codes from the job posting!"
        )
        return
    
    position_code = parts[1]
    secret_code = parts[2]
    
    # Find internship
    internship = Internship.query.filter_by(
        position_code=position_code,
        secret_code=secret_code,
        is_active=True
    ).first()
    
    if not internship:
        send_whatsapp_message(
            from_number,
            "Invalid position code or secret code. Please check your details and try again."
        )
        return
    
    if internship.is_deadline_passed():
        send_whatsapp_message(
            from_number,
            f"Sorry, the application deadline for {internship.title} has passed."
        )
        return
    
    # Check if already applied
    existing_app = Application.query.filter_by(
        internship_id=internship.id,
        whatsapp_number=from_number,
        conversation_state=STATE_COMPLETED
    ).first()
    
    if existing_app:
        send_whatsapp_message(
            from_number,
            f"You have already applied for {internship.title}. Your application status is: {existing_app.status.title()}"
        )
        return
    
    # Start application process - skip to CV upload
    application.internship_id = internship.id
    application.conversation_state = STATE_WAITING_FOR_CV
    application.temp_data = {'internship_id': internship.id}
    
    send_whatsapp_message(
        from_number,
        f"🎉 Welcome! You're applying for: **{internship.title}**\n⏰ Deadline: {internship.deadline.strftime('%B %d, %Y')}\n\n📎 **Quick Process:** Just send your CV/resume and we'll extract your details from it.\n\nPlease attach your CV as PDF, Word document, or image:"
    )

def handle_name_input(application, message_body, from_number):
    """Handle full name input"""
    if len(message_body.strip()) < 2:
        send_whatsapp_message(
            from_number,
            "Please provide your full name (at least 2 characters):"
        )
        return
    
    temp_data = application.temp_data or {}
    temp_data['full_name'] = message_body.strip()
    application.temp_data = temp_data
    application.conversation_state = STATE_WAITING_FOR_EMAIL
    
    send_whatsapp_message(
        from_number,
        f"✅ Perfect {temp_data['full_name']}! \n\n📧 Now please provide your **email address**:"
    )

def handle_email_input(application, message_body, from_number):
    """Handle email input"""
    email = message_body.strip()
    
    # Basic email validation
    if '@' not in email or '.' not in email.split('@')[1]:
        send_whatsapp_message(
            from_number,
            "Please provide a valid email address:"
        )
        return
    
    temp_data = application.temp_data or {}
    temp_data['email'] = email
    application.temp_data = temp_data
    application.conversation_state = STATE_WAITING_FOR_PHONE
    
    send_whatsapp_message(
        from_number,
        "📧 Great! Email received.\n\n📱 Now please provide your **phone number**:"
    )

def handle_phone_input(application, message_body, from_number):
    """Handle phone number input"""
    phone = message_body.strip()
    
    if len(phone) < 8:
        send_whatsapp_message(
            from_number,
            "Please provide a valid phone number:"
        )
        return
    
    temp_data = application.temp_data or {}
    temp_data['phone_number'] = phone
    application.temp_data = temp_data
    application.conversation_state = STATE_WAITING_FOR_COVER_LETTER
    
    send_whatsapp_message(
        from_number,
        "📱 Perfect! Phone number saved.\n\n💬 Now please write a short **cover letter or motivation message** (tell us why you want this internship):"
    )

def handle_cover_letter_input(application, message_body, from_number):
    """Handle cover letter input"""
    if len(message_body.strip()) < 20:
        send_whatsapp_message(
            from_number,
            "Please provide a more detailed cover letter (at least 20 characters). Tell us why you want this internship:"
        )
        return
    
    temp_data = application.temp_data or {}
    temp_data['cover_letter'] = message_body.strip()
    application.temp_data = temp_data
    application.conversation_state = STATE_WAITING_FOR_CV
    
    send_whatsapp_message(
        from_number,
        "📝 Excellent! Your motivation is noted.\n\n📎 **Final Step:** Please attach your **CV** as a PDF, Word document, or image file.\n\n💡 **Tip:** If you have a cover letter from your university or college, please include it with your CV document."
    )

def process_media_message(application, whatsapp_msg, from_number):
    """Process media attachment (CV)"""
    try:
        media_url = getattr(whatsapp_msg, 'media_url', None)
        if not media_url:
            send_whatsapp_message(
                from_number,
                "Error processing your file. Please try uploading again."
            )
            return
        
        # For now, just mark as received since we have the media URL
        filename = f"cv_{application.id}_{whatsapp_msg.message_id}.jpg"
        original_filename = "CV_attachment.jpg"
        
        # Complete the application with CV only
        temp_data = application.temp_data or {}
        
        application.full_name = 'Details in CV'
        application.email = f'cv_applicant_{application.id}@pending.com'
        application.phone_number = from_number
        application.cover_letter = 'Please see attached CV for details'
        application.cv_filename = filename
        application.cv_original_filename = original_filename
        application.conversation_state = STATE_COMPLETED
        application.applied_at = datetime.utcnow()
        
        internship = Internship.query.get(application.internship_id)
        
        send_whatsapp_message(
            from_number,
            f"🎉 **APPLICATION COMPLETE!**\n\n📋 Position: {internship.title}\n📎 CV: Received ✅\n📱 Phone: {application.phone_number}\n\n✅ Done! We'll review your CV and contact you via WhatsApp.\n\n🤞 Good luck!"
        )
        
        # Send confirmation email if possible
        try:
            from communication import send_email
            send_email(
                application.email,
                f"Application Confirmation - {internship.title}",
                f"Dear {application.full_name},\n\nYour application for {internship.title} has been successfully submitted.\n\nWe will review your application and get back to you soon.\n\nBest regards,\nThe Team"
            )
        except Exception as e:
            logger.error(f"Failed to send confirmation email: {e}")
        
    except Exception as e:
        logger.error(f"Error processing media message: {e}")
        send_whatsapp_message(
            from_number,
            "Error processing your file. Please try uploading again."
        )

def handle_message_status(status):
    """Handle message delivery status updates"""
    try:
        message_id = status.get('id')
        status_type = status.get('status')
        timestamp = status.get('timestamp')
        
        # Update message status in database
        whatsapp_msg = WhatsAppMessage.query.filter_by(message_id=message_id).first()
        if whatsapp_msg:
            whatsapp_msg.status = status_type
            db.session.commit()
            
    except Exception as e:
        logger.error(f"Error handling message status: {e}")

def get_media_url(media_id):
    """Get media URL from WhatsApp API"""
    try:
        access_token = os.environ.get('WHATSAPP_ACCESS_TOKEN')
        url = f"https://graph.facebook.com/v17.0/{media_id}"
        
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data.get('url')
            
    except Exception as e:
        logger.error(f"Error getting media URL: {e}")
    
    return None
