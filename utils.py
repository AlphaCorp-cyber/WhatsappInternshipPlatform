import os
import uuid
import requests
from werkzeug.utils import secure_filename
from flask import current_app

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'png', 'jpg', 'jpeg', 'gif'}

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
    # Remove all non-digit characters
    cleaned = ''.join(filter(str.isdigit, phone_number))
    
    # Add country code if missing (assuming Zimbabwe +263)
    if not cleaned.startswith('263') and not cleaned.startswith('1'):
        # Remove leading zero if present
        if cleaned.startswith('0'):
            cleaned = cleaned[1:]
        cleaned = '263' + cleaned
    
    return '+' + cleaned

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
