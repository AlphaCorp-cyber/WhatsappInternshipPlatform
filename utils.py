import os
import uuid
import requests
from werkzeug.utils import secure_filename
from flask import current_app

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file):
    """Save uploaded file and return filename"""
    if file and allowed_file(file.filename):
        # Generate unique filename
        filename = str(uuid.uuid4()) + '.' + file.filename.rsplit('.', 1)[1].lower()
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        return filename
    return None

def save_media_file(media_url, file_type):
    """Download and save media file from WhatsApp"""
    try:
        access_token = os.environ.get('WHATSAPP_ACCESS_TOKEN')
        
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        
        # For Twilio WhatsApp API, we need to handle authentication differently
        if 'twilio.com' in media_url:
            # Use Twilio account credentials
            from twilio.rest import Client
            twilio_sid = os.environ.get('TWILIO_ACCOUNT_SID')
            twilio_token = os.environ.get('TWILIO_AUTH_TOKEN')
            
            if twilio_sid and twilio_token:
                import base64
                credentials = base64.b64encode(f"{twilio_sid}:{twilio_token}".encode()).decode()
                headers = {
                    'Authorization': f'Basic {credentials}'
                }
        
        response = requests.get(media_url, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Failed to download media: {response.status_code}")
        
        # Determine file extension based on content type
        content_type = response.headers.get('content-type', '')
        extension = 'pdf'  # default
        
        if 'image' in content_type:
            if 'jpeg' in content_type:
                extension = 'jpg'
            elif 'png' in content_type:
                extension = 'png'
            else:
                extension = 'jpg'
        elif 'application/pdf' in content_type:
            extension = 'pdf'
        elif 'word' in content_type or 'document' in content_type:
            extension = 'docx'
        
        # Generate unique filename
        filename = str(uuid.uuid4()) + '.' + extension
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        
        with open(file_path, 'wb') as f:
            f.write(response.content)
        
        original_filename = f"cv_attachment.{extension}"
        
        return filename, original_filename
        
    except Exception as e:
        current_app.logger.error(f"Error saving media file: {e}")
        raise

def format_phone_number(phone_number):
    """Format phone number for international use"""
    # Handle different input formats
    if phone_number.startswith('whatsapp:'):
        phone_number = phone_number.replace('whatsapp:', '')
    if phone_number.startswith('whatsapp+'):
        phone_number = phone_number.replace('whatsapp+', '+')
    
    # Remove all non-digit characters except +
    cleaned = ''.join(c for c in phone_number if c.isdigit() or c == '+')
    
    # Ensure it starts with +
    if not cleaned.startswith('+'):
        # Add country code if missing (assuming Zimbabwe +263)
        if not cleaned.startswith('263') and not cleaned.startswith('1'):
            # Remove leading zero if present
            if cleaned.startswith('0'):
                cleaned = cleaned[1:]


import hashlib
from difflib import SequenceMatcher

def hash_email(email):
    """Create hash of email for duplicate detection"""
    return hashlib.sha256(email.lower().strip().encode()).hexdigest()

def calculate_name_similarity(name1, name2):
    """Calculate similarity between two names (0-1 scale)"""
    return SequenceMatcher(None, name1.lower().strip(), name2.lower().strip()).ratio()

def detect_duplicate_application(internship_id, full_name, email, whatsapp_number):
    """
    Detect if this is a duplicate application
    Returns: (is_duplicate, original_application_id, reason)
    """
    from models import Application
    
    # Check for exact email match (different phone numbers)
    email_hash = hash_email(email)
    existing_email = Application.query.filter_by(
        internship_id=internship_id,
        email_hash=email_hash,
        conversation_state='completed'
    ).first()
    
    if existing_email and existing_email.whatsapp_number != whatsapp_number:
        return True, existing_email.application_id, "Same email, different WhatsApp number"
    
    # Check for similar names with different emails/numbers
    existing_apps = Application.query.filter_by(
        internship_id=internship_id,
        conversation_state='completed'
    ).all()
    
    for app in existing_apps:
        if app.whatsapp_number != whatsapp_number:
            name_similarity = calculate_name_similarity(full_name, app.full_name)
            if name_similarity > 0.85:  # 85% similarity threshold
                return True, app.application_id, f"Similar name ({name_similarity:.2%} match)"
    
    return False, None, None

def validate_application_authenticity(full_name, email, cv_filename):
    """
    Basic validation to detect fake applications
    Returns: (is_valid, issues)
    """
    issues = []
    
    # Check for suspicious patterns
    if len(full_name.split()) < 2:
        issues.append("Name appears incomplete")
    
    if any(word in full_name.lower() for word in ['test', 'fake', 'demo', 'sample']):
        issues.append("Name contains suspicious words")
    
    if any(domain in email.lower() for domain in ['tempmail', '10minute', 'guerrilla']):
        issues.append("Temporary email address detected")
    
    # Check if CV file is too small (likely fake)
    if cv_filename:
        import os
        from flask import current_app
        cv_path = os.path.join(current_app.config['UPLOAD_FOLDER'], cv_filename)
        if os.path.exists(cv_path) and os.path.getsize(cv_path) < 10000:  # Less than 10KB
            issues.append("CV file suspiciously small")
    
    return len(issues) == 0, issues

def generate_qr_code(text):
    """Generate QR code for sharing (optional feature)"""
    try:
        import qrcode
        from io import BytesIO
        import base64
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(text)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        # Convert to base64 for embedding in HTML
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{img_base64}"
        
    except ImportError:
        current_app.logger.warning("qrcode library not installed")
        return None
    except Exception as e:
        current_app.logger.error(f"Error generating QR code: {e}")
        return None
