import os
import csv
import zipfile
from io import StringIO
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, jsonify, send_file, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from app import app, db
from models import Admin, Internship, Application, NotificationLog, SystemSettings
from utils import allowed_file, save_uploaded_file
from communication import send_whatsapp_message, send_email, send_sms
import whatsapp_handler

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        admin = Admin.query.filter_by(username=username).first()
        
        if admin and admin.check_password(password) and admin.is_active:
            login_user(admin, remember=True)
            next_page = request.args.get('next')
            flash('Logged in successfully!', 'success')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

# Dashboard routes
@app.route('/')
@login_required
def dashboard():
    total_internships = Internship.query.filter_by(is_active=True).count()
    total_applications = Application.query.count()
    pending_applications = Application.query.filter_by(status='pending').count()
    recent_applications = Application.query.order_by(Application.applied_at.desc()).limit(5).all()
    
    return render_template('dashboard.html',
                         total_internships=total_internships,
                         total_applications=total_applications,
                         pending_applications=pending_applications,
                         recent_applications=recent_applications)

# Internship management routes
@app.route('/internships')
@login_required
def internships():
    page = request.args.get('page', 1, type=int)
    internships = Internship.query.filter_by(is_active=True).order_by(
        Internship.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False)
    
    return render_template('internships.html', internships=internships)

@app.route('/internships/create', methods=['GET', 'POST'])
@login_required
def create_internship():
    if request.method == 'POST':
        try:
            internship = Internship(
                title=request.form['title'],
                description=request.form['description'],
                requirements=request.form['requirements'],
                position_code=Internship.generate_position_code(),
                secret_code=Internship.generate_secret_code(),
                deadline=datetime.strptime(request.form['deadline'], '%Y-%m-%dT%H:%M'),
                created_by=current_user.id
            )
            
            db.session.add(internship)
            db.session.commit()
            
            flash(f'Internship created successfully! Position Code: {internship.position_code}', 'success')
            return redirect(url_for('internships'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating internship: {str(e)}', 'danger')
    
    return render_template('create_internship.html')

@app.route('/internships/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_internship(id):
    internship = Internship.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            internship.title = request.form['title']
            internship.description = request.form['description']
            internship.requirements = request.form['requirements']
            internship.deadline = datetime.strptime(request.form['deadline'], '%Y-%m-%dT%H:%M')
            internship.updated_at = datetime.utcnow()
            
            db.session.commit()
            flash('Internship updated successfully!', 'success')
            return redirect(url_for('internships'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating internship: {str(e)}', 'danger')
    
    return render_template('edit_internship.html', internship=internship)

@app.route('/internships/<int:id>/regenerate_secret')
@login_required
def regenerate_secret(id):
    internship = Internship.query.get_or_404(id)
    internship.regenerate_secret_code()
    flash(f'New secret code generated: {internship.secret_code}', 'success')
    return redirect(url_for('internships'))

@app.route('/internships/<int:id>/deactivate')
@login_required
def deactivate_internship(id):
    internship = Internship.query.get_or_404(id)
    internship.is_active = False
    db.session.commit()
    flash('Internship deactivated successfully!', 'success')
    return redirect(url_for('internships'))

@app.route('/internships/<int:id>/share')
@login_required
def get_share_message(id):
    internship = Internship.query.get_or_404(id)
    whatsapp_number = os.environ.get('WHATSAPP_NUMBER', '+1234567890')
    share_message = internship.get_share_message(whatsapp_number)
    
    return jsonify({'message': share_message})

# Application management routes
@app.route('/applications')
@login_required
def applications():
    page = request.args.get('page', 1, type=int)
    internship_id = request.args.get('internship_id', type=int)
    status = request.args.get('status')
    search = request.args.get('search', '')
    
    query = Application.query
    
    if internship_id:
        query = query.filter_by(internship_id=internship_id)
    
    if status:
        query = query.filter_by(status=status)
    
    if search:
        query = query.filter(
            db.or_(
                Application.full_name.contains(search),
                Application.email.contains(search),
                Application.phone_number.contains(search)
            )
        )
    
    applications = query.order_by(Application.applied_at.desc()).paginate(
        page=page, per_page=20, error_out=False)
    
    internships = Internship.query.filter_by(is_active=True).all()
    
    return render_template('applications.html', 
                         applications=applications,
                         internships=internships,
                         current_internship_id=internship_id,
                         current_status=status,
                         search=search)

@app.route('/applications/<int:id>')
@login_required
def application_detail(id):
    application = Application.query.get_or_404(id)
    return render_template('application_detail.html', application=application)

@app.route('/applications/<int:id>/update_status', methods=['POST'])
@login_required
def update_application_status(id):
    application = Application.query.get_or_404(id)
    new_status = request.form['status']
    send_notification = request.form.get('send_notification') == 'on'
    
    old_status = application.status
    application.status = new_status
    application.updated_at = datetime.utcnow()
    
    try:
        db.session.commit()
        
        if send_notification and new_status != old_status:
            # Send notification to applicant
            message = f"Your application for {application.internship.title} has been updated to: {new_status.title()}"
            
            # Send WhatsApp notification
            try:
                send_whatsapp_message(application.whatsapp_number, message)
            except Exception as e:
                current_app.logger.error(f"Failed to send WhatsApp notification: {e}")
            
            # Send email notification
            try:
                send_email(
                    application.email,
                    f"Application Status Update - {application.internship.title}",
                    message
                )
            except Exception as e:
                current_app.logger.error(f"Failed to send email notification: {e}")
        
        flash('Application status updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating application status: {str(e)}', 'danger')
    
    return redirect(url_for('application_detail', id=id))

@app.route('/applications/export')
@login_required
def export_applications():
    internship_id = request.args.get('internship_id', type=int)
    status = request.args.get('status')
    format_type = request.args.get('format', 'csv')
    
    query = Application.query
    
    if internship_id:
        query = query.filter_by(internship_id=internship_id)
    
    if status:
        query = query.filter_by(status=status)
    
    applications = query.order_by(Application.applied_at.desc()).all()
    
    if format_type == 'csv':
        return export_applications_csv(applications)
    elif format_type == 'zip':
        return export_applications_zip(applications)
    
    flash('Invalid export format', 'danger')
    return redirect(url_for('applications'))

def export_applications_csv(applications):
    import tempfile
    import os
    
    # Create temporary file for CSV export
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as tmp_file:
        writer = csv.writer(tmp_file)
        
        # Write header
        writer.writerow([
            'ID', 'Internship', 'Full Name', 'Email', 'Phone', 'WhatsApp',
            'Status', 'Applied At', 'CV Filename'
        ])
        
        # Write data
        for app in applications:
            writer.writerow([
                app.id,
                app.internship.title,
                app.full_name,
                app.email,
                app.phone_number,
                app.whatsapp_number,
                app.status,
                app.applied_at.strftime('%Y-%m-%d %H:%M:%S'),
                app.cv_original_filename or 'N/A'
            ])
        
        tmp_file_path = tmp_file.name
    
    # Send the file and clean up after
    def remove_file(response):
        try:
            os.remove(tmp_file_path)
        except OSError:
            pass
        return response
    
    return send_file(
        tmp_file_path,
        mimetype='text/csv',
        as_attachment=True,
        download_name='applications.csv'
    )

def export_applications_zip(applications):
    import tempfile
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
        with zipfile.ZipFile(tmp_file.name, 'w') as zip_file:
            # Add CSV file
            csv_content = StringIO()
            writer = csv.writer(csv_content)
            writer.writerow([
                'ID', 'Internship', 'Full Name', 'Email', 'Phone', 'WhatsApp',
                'Status', 'Applied At', 'CV Filename'
            ])
            
            for app in applications:
                writer.writerow([
                    app.id,
                    app.internship.title,
                    app.full_name,
                    app.email,
                    app.phone_number,
                    app.whatsapp_number,
                    app.status,
                    app.applied_at.strftime('%Y-%m-%d %H:%M:%S'),
                    app.cv_original_filename or 'N/A'
                ])
            
            zip_file.writestr('applications.csv', csv_content.getvalue())
            
            # Add CV files
            for app in applications:
                if app.cv_filename:
                    cv_path = os.path.join(current_app.config['UPLOAD_FOLDER'], app.cv_filename)
                    if os.path.exists(cv_path):
                        zip_file.write(cv_path, f"cvs/{app.cv_original_filename}")
        
        return send_file(
            tmp_file.name,
            mimetype='application/zip',
            as_attachment=True,
            download_name='applications.zip'
        )

# WhatsApp webhook
@app.route('/webhook/whatsapp', methods=['GET', 'POST'])
def whatsapp_webhook():
    if request.method == 'GET':
        # Webhook verification
        verify_token = os.environ.get('WHATSAPP_VERIFY_TOKEN', 'your_verify_token')
        
        if request.args.get('hub.verify_token') == verify_token:
            return request.args.get('hub.challenge')
        return 'Invalid verification token', 403
    
    elif request.method == 'POST':
        # Handle incoming messages
        try:
            data = request.get_json()
            whatsapp_handler.handle_webhook(data)
            return 'OK', 200
        except Exception as e:
            current_app.logger.error(f"Error processing WhatsApp webhook: {e}")
            return 'Error', 500

# Settings management routes
@app.route('/settings')
@login_required
def settings():
    # Get all settings grouped by category
    settings = {}
    all_settings = SystemSettings.query.order_by(SystemSettings.category, SystemSettings.key).all()
    
    for setting in all_settings:
        if setting.category not in settings:
            settings[setting.category] = []
        settings[setting.category].append(setting)
    
    return render_template('settings.html', settings=settings)

@app.route('/settings/update', methods=['POST'])
@login_required
def update_settings():
    try:
        # Get form data
        for key, value in request.form.items():
            if key.startswith('setting_'):
                setting_key = key.replace('setting_', '')
                
                # Determine category based on key prefix
                category = 'general'
                if setting_key.startswith('twilio_'):
                    category = 'sms'
                elif setting_key.startswith('whatsapp_'):
                    category = 'whatsapp'
                elif setting_key.startswith('email_') or setting_key.startswith('smtp_'):
                    category = 'email'
                
                # Set the setting
                SystemSettings.set_setting(
                    key=setting_key,
                    value=value,
                    category=category,
                    is_encrypted=setting_key.endswith('_token') or setting_key.endswith('_password')
                )
        
        flash('Settings updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating settings: {str(e)}', 'danger')
    
    return redirect(url_for('settings'))

@app.route('/settings/test/<channel>')
@login_required
def test_communication(channel):
    """Test communication channels"""
    try:
        test_message = "Test message from WhatsApp Internship System"
        
        if channel == 'sms':
            # Test SMS using Twilio
            account_sid = SystemSettings.get_setting('twilio_account_sid')
            auth_token = SystemSettings.get_setting('twilio_auth_token')
            from_number = SystemSettings.get_setting('twilio_phone_number')
            test_number = SystemSettings.get_setting('test_phone_number', '+1234567890')
            
            if not all([account_sid, auth_token, from_number]):
                return jsonify({'success': False, 'message': 'Twilio credentials not configured'})
            
            # Test SMS sending
            success = send_sms(test_number, test_message)
            return jsonify({
                'success': success,
                'message': 'SMS test message sent successfully!' if success else 'SMS test failed'
            })
            
        elif channel == 'whatsapp':
            # Test WhatsApp
            access_token = SystemSettings.get_setting('whatsapp_access_token')
            phone_number_id = SystemSettings.get_setting('whatsapp_phone_number_id')
            test_number = SystemSettings.get_setting('test_whatsapp_number', '+1234567890')
            
            if not all([access_token, phone_number_id]):
                return jsonify({'success': False, 'message': 'WhatsApp credentials not configured'})
            
            success = send_whatsapp_message(test_number, test_message)
            return jsonify({
                'success': success,
                'message': 'WhatsApp test message sent successfully!' if success else 'WhatsApp test failed'
            })
            
        elif channel == 'email':
            # Test Email
            smtp_server = SystemSettings.get_setting('smtp_server')
            smtp_username = SystemSettings.get_setting('smtp_username')
            smtp_password = SystemSettings.get_setting('smtp_password')
            test_email = SystemSettings.get_setting('test_email', 'test@example.com')
            
            if not all([smtp_server, smtp_username, smtp_password]):
                return jsonify({'success': False, 'message': 'Email credentials not configured'})
            
            success = send_email(test_email, 'Test Email', test_message)
            return jsonify({
                'success': success,
                'message': 'Test email sent successfully!' if success else 'Email test failed'
            })
        
        return jsonify({'success': False, 'message': 'Invalid channel'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Test failed: {str(e)}'})

# File upload route
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        try:
            filename = save_uploaded_file(file)
            return jsonify({'filename': filename, 'original_filename': file.filename})
        except RequestEntityTooLarge:
            return jsonify({'error': 'File too large'}), 413
        except Exception as e:
            current_app.logger.error(f"File upload error: {e}")
            return jsonify({'error': 'Upload failed'}), 500
    
    return jsonify({'error': 'Invalid file type'}), 400

# Create default admin user if none exists
def create_default_admin():
    if not Admin.query.first():
        admin = Admin(
            username='admin',
            email='admin@example.com',
            role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("Default admin user created: username=admin, password=admin123")

# Admin account management routes
@app.route('/account')
@login_required
def account_settings():
    """Show admin account settings page"""
    return render_template('account_settings.html', admin=current_user)

@app.route('/account/update', methods=['POST'])
@login_required
def update_account():
    """Update admin account details"""
    try:
        # Update basic info
        if 'username' in request.form:
            new_username = request.form['username'].strip()
            if new_username != current_user.username:
                # Check if username is already taken
                existing_admin = Admin.query.filter_by(username=new_username).first()
                if existing_admin and existing_admin.id != current_user.id:
                    flash('Username already exists', 'danger')
                    return redirect(url_for('account_settings'))
                current_user.username = new_username
        
        if 'email' in request.form:
            new_email = request.form['email'].strip().lower()
            if new_email != current_user.email:
                # Check if email is already taken
                existing_admin = Admin.query.filter_by(email=new_email).first()
                if existing_admin and existing_admin.id != current_user.id:
                    flash('Email already exists', 'danger')
                    return redirect(url_for('account_settings'))
                current_user.email = new_email
        
        db.session.commit()
        flash('Account details updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating account: {str(e)}', 'danger')
    
    return redirect(url_for('account_settings'))

@app.route('/account/change-password', methods=['POST'])
@login_required
def change_password():
    """Change admin password"""
    try:
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        # Verify current password
        if not current_user.check_password(current_password):
            flash('Current password is incorrect', 'danger')
            return redirect(url_for('account_settings'))
        
        # Check if new passwords match
        if new_password != confirm_password:
            flash('New passwords do not match', 'danger')
            return redirect(url_for('account_settings'))
        
        # Check password length
        if len(new_password) < 6:
            flash('Password must be at least 6 characters long', 'danger')
            return redirect(url_for('account_settings'))
        
        # Update password
        current_user.set_password(new_password)
        db.session.commit()
        
        flash('Password changed successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error changing password: {str(e)}', 'danger')
    
    return redirect(url_for('account_settings'))

# Call the function when the module is loaded
with app.app_context():
    try:
        create_default_admin()
    except Exception as e:
        print(f"Error creating default admin: {e}")
