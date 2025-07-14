from datetime import datetime, timedelta
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import string

class Admin(UserMixin, db.Model):
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='admin')  # admin, view_only
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<Admin {self.username}>'

class Internship(db.Model):
    __tablename__ = 'internships'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text, nullable=False)
    position_code = db.Column(db.String(10), unique=True, nullable=False)
    secret_code = db.Column(db.String(20), nullable=False)
    deadline = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    admin = db.relationship('Admin', backref='internships')
    applications = db.relationship('Application', backref='internship', lazy='dynamic')
    
    @staticmethod
    def generate_position_code():
        """Generate a unique position code"""
        while True:
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
            if not Internship.query.filter_by(position_code=code).first():
                return code
    
    @staticmethod
    def generate_secret_code():
        """Generate a secret code"""
        return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
    
    def regenerate_secret_code(self):
        """Regenerate the secret code"""
        self.secret_code = self.generate_secret_code()
        db.session.commit()
    
    def get_share_message(self, whatsapp_number):
        """Generate share message for the internship"""
        # Create WhatsApp link with pre-filled message
        apply_message = f"APPLY {self.position_code} {self.secret_code}"
        whatsapp_link = f"https://wa.me/{whatsapp_number.replace('+', '')}?text={apply_message.replace(' ', '%20')}"
        
        return f"""🎯 **{self.title}** - Apply Now!

📝 **Description:** {self.description[:100]}...

✅ **Requirements:** {self.requirements[:100]}...

📅 **Deadline:** {self.deadline.strftime('%B %d, %Y')}

🚀 **Apply via WhatsApp:**
{whatsapp_link}

Or send manually: APPLY {self.position_code} {self.secret_code}
To: {whatsapp_number}

#internship #jobs #opportunity"""
    
    def is_deadline_passed(self):
        return datetime.utcnow() > self.deadline
    
    def __repr__(self):
        return f'<Internship {self.title} ({self.position_code})>'

class Application(db.Model):
    __tablename__ = 'applications'
    
    id = db.Column(db.Integer, primary_key=True)
    internship_id = db.Column(db.Integer, db.ForeignKey('internships.id'), nullable=True)  # Allow null during conversation
    full_name = db.Column(db.String(200), nullable=True)  # Allow null during conversation
    email = db.Column(db.String(120), nullable=True)  # Allow null during conversation  
    phone_number = db.Column(db.String(20), nullable=True)  # Allow null during conversation
    whatsapp_number = db.Column(db.String(20), nullable=False)  # Always required
    cover_letter = db.Column(db.Text, nullable=True)  # Allow null during conversation
    cv_filename = db.Column(db.String(255))
    cv_original_filename = db.Column(db.String(255))
    status = db.Column(db.String(20), default='pending')  # pending, shortlisted, selected, rejected
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # WhatsApp conversation state
    conversation_state = db.Column(db.String(50), default='waiting_for_apply')
    temp_data = db.Column(db.JSON)  # Store temporary data during application process
    
    def __repr__(self):
        return f'<Application {self.full_name} for {self.internship.title}>'

class WhatsAppMessage(db.Model):
    __tablename__ = 'whatsapp_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.String(100), unique=True, nullable=False)
    from_number = db.Column(db.String(20), nullable=False)
    to_number = db.Column(db.String(20), nullable=False)
    message_body = db.Column(db.Text)
    message_type = db.Column(db.String(20), default='text')  # text, image, document
    media_url = db.Column(db.String(500))
    media_content_type = db.Column(db.String(100))  # MIME type for media files
    status = db.Column(db.String(20), default='received')  # received, processed, failed
    received_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<WhatsAppMessage {self.message_id} from {self.from_number}>'

class NotificationLog(db.Model):
    __tablename__ = 'notification_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'))
    channel = db.Column(db.String(20), nullable=False)  # whatsapp, email, sms
    recipient = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, sent, failed
    sent_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    application = db.relationship('Application', backref='notifications')
    
    def __repr__(self):
        return f'<NotificationLog {self.channel} to {self.recipient}>'

class SystemSettings(db.Model):
    __tablename__ = 'system_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), default='general')  # general, whatsapp, email, sms
    is_encrypted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @staticmethod
    def get_setting(key, default=None):
        """Get a setting value by key"""
        setting = SystemSettings.query.filter_by(key=key).first()
        return setting.value if setting else default
    
    @staticmethod
    def set_setting(key, value, description=None, category='general', is_encrypted=False):
        """Set a setting value"""
        setting = SystemSettings.query.filter_by(key=key).first()
        if setting:
            setting.value = value
            setting.updated_at = datetime.utcnow()
            if description:
                setting.description = description
        else:
            setting = SystemSettings(
                key=key,
                value=value,
                description=description,
                category=category,
                is_encrypted=is_encrypted
            )
            db.session.add(setting)
        db.session.commit()
        return setting
    
    def __repr__(self):
        return f'<SystemSettings {self.key}>'
