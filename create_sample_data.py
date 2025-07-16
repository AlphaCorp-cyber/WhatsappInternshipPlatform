#!/usr/bin/env python3
"""
Create sample database with tables and default admin user
Run this script to set up the database for development or production
"""

from app import app, db
from models import Admin, Internship, Application, SystemSettings
from datetime import datetime, timedelta
import os

def create_sample_data():
    """Create sample database with default admin and sample internship"""
    
    with app.app_context():
        # Create all database tables
        print("Creating database tables...")
        db.create_all()
        
        # Check if admin already exists
        existing_admin = Admin.query.filter_by(username='admin').first()
        if not existing_admin:
            # Create default admin user
            admin = Admin(
                username='admin',
                email='admin@company.com',
                role='admin',
                is_active=True
            )
            admin.set_password('admin123')  # Default password - CHANGE IN PRODUCTION
            db.session.add(admin)
            print("✅ Created default admin user:")
            print("   Username: admin")
            print("   Password: admin123")
            print("   ⚠️  IMPORTANT: Change this password after first login!")
        else:
            print("✅ Admin user already exists")
            admin = existing_admin
        
        # Create sample internship if none exist
        existing_internship = Internship.query.first()
        if not existing_internship:
            internship = Internship(
                title='Web Developer Internship',
                description='''We are looking for a motivated Web Developer Intern to join our dynamic team. 
                
This is an excellent opportunity to gain hands-on experience in modern web development technologies and work on real projects that impact our business.

**What you'll do:**
- Develop and maintain web applications using modern frameworks
- Collaborate with senior developers on exciting projects
- Learn industry best practices and coding standards
- Participate in code reviews and team meetings
- Contribute to both frontend and backend development

**Duration:** 3-6 months with possibility of full-time offer
**Location:** Remote/Hybrid options available
**Compensation:** Competitive stipend provided''',
                requirements='''**Required Skills:**
- Basic knowledge of HTML, CSS, and JavaScript
- Familiarity with at least one programming language (Python, JavaScript, Java, etc.)
- Understanding of version control (Git)
- Strong problem-solving abilities
- Excellent communication skills

**Preferred Skills:**
- Experience with React, Vue.js, or Angular
- Knowledge of backend frameworks (Flask, Django, Node.js)
- Database experience (SQL, NoSQL)
- Understanding of web APIs and RESTful services
- Portfolio of personal or academic projects

**Education:**
- Currently pursuing Computer Science, Web Development, or related field
- Recent graduates are also welcome to apply

**Personal Qualities:**
- Eager to learn and grow
- Team player with collaborative mindset
- Attention to detail
- Ability to work independently
- Passion for technology and innovation''',
                deadline=datetime.utcnow() + timedelta(days=30),  # 30 days from now
                created_by=admin.id,
                is_active=True,
                accepting_applications=True
            )
            db.session.add(internship)
            print("✅ Created sample internship:")
            print(f"   Title: {internship.title}")
            print(f"   Position Code: {internship.position_code}")
            print(f"   Secret Code: {internship.secret_code}")
            print(f"   Deadline: {internship.deadline.strftime('%Y-%m-%d %H:%M')}")
        else:
            print("✅ Sample internship already exists")
        
        # Create system settings
        default_settings = [
            ('whatsapp_webhook_url', '/webhook/whatsapp', 'WhatsApp webhook endpoint', 'whatsapp'),
            ('application_retention_days', '90', 'Days to keep completed applications', 'general'),
            ('max_file_size_mb', '16', 'Maximum CV file size in MB', 'files'),
            ('allowed_file_types', 'pdf', 'Allowed CV file types (comma-separated)', 'files'),
            ('email_notifications_enabled', 'true', 'Enable email notifications', 'email'),
            ('sms_notifications_enabled', 'false', 'Enable SMS notifications', 'sms'),
        ]
        
        for key, value, description, category in default_settings:
            existing_setting = SystemSettings.query.filter_by(key=key).first()
            if not existing_setting:
                setting = SystemSettings(
                    key=key,
                    value=value,
                    description=description,
                    category=category
                )
                db.session.add(setting)
        
        # Commit all changes
        try:
            db.session.commit()
            print("✅ Database setup completed successfully!")
            
            # Print summary
            print("\n" + "="*50)
            print("DATABASE SETUP SUMMARY")
            print("="*50)
            print("📊 Tables created: admins, internships, applications, whatsapp_messages, notification_logs, system_settings")
            print("👤 Default admin created - Login at: http://localhost:5000")
            print("   Username: admin")
            print("   Password: admin123")
            print("💼 Sample internship created with codes for testing")
            print("⚙️  System settings configured with defaults")
            print("\n🔐 SECURITY NOTE: Change the admin password immediately after first login!")
            print("📱 WhatsApp Bot: Send 'APPLY [POSITION_CODE] [SECRET_CODE]' to test")
            
            # Show internship details
            internship = Internship.query.first()
            if internship:
                print(f"\n📋 Test Application Command:")
                print(f"   APPLY {internship.position_code} {internship.secret_code}")
            
        except Exception as e:
            print(f"❌ Error setting up database: {e}")
            db.session.rollback()
            return False
    
    return True

if __name__ == '__main__':
    print("🚀 Setting up WhatsApp Internship Application System database...")
    print("📂 Using database:", os.environ.get('DATABASE_URL', 'Not configured'))
    
    success = create_sample_data()
    if success:
        print("\n✅ Setup complete! You can now start the application.")
    else:
        print("\n❌ Setup failed. Please check the error messages above.")