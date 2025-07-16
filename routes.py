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
import os
from models import Admin, Internship, Application, NotificationLog, SystemSettings
from utils import allowed_file, save_uploaded_file
from communication import send_whatsapp_message, send_email, send_sms
import whatsapp_handler

def auto_deactivate_expired_internships():
    """Automatically stop accepting applications for internships that have passed their deadline"""
    try:
        from datetime import datetime
        
        # Find all active internships that have passed their deadline but are still accepting applications
        expired_internships = Internship.query.filter(
            Internship.is_active == True,
            Internship.accepting_applications == True,
            Internship.deadline < datetime.utcnow()
        ).all()
        
        if expired_internships:
            for internship in expired_internships:
                internship.accepting_applications = False
                current_app.logger.info(f"Auto-stopped applications for expired internship: {internship.title} (ID: {internship.id})")
            
            db.session.commit()
            current_app.logger.info(f"Auto-stopped applications for {len(expired_internships)} expired internships")
            
    except Exception as e:
        current_app.logger.error(f"Error auto-stopping applications for expired internships: {e}")
        db.session.rollback()

def cleanup_incomplete_applications():
    """Remove incomplete applications from database to keep admin dashboard clean"""
    try:
        # Delete applications that are not completed (incomplete conversation state)
        incomplete_apps = Application.query.filter(
            Application.conversation_state != 'completed'
        ).all()
        
        if incomplete_apps:
            for app in incomplete_apps:
                db.session.delete(app)
            
            db.session.commit()
            current_app.logger.info(f"Cleaned up {len(incomplete_apps)} incomplete applications")
            
    except Exception as e:
        current_app.logger.error(f"Error cleaning up incomplete applications: {e}")
        db.session.rollback()

# Authentication routes
@app.route('/health')
def health_check():
    """Health check endpoint for deployment verification"""
    try:
        # Test database connection
        admin_count = Admin.query.count()
        internship_count = Internship.query.count()
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'admins': admin_count,
            'internships': internship_count,
            'version': '1.0.0',
            'webhook_url': f"{request.url_root}webhook/whatsapp"
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

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
    # Auto-deactivate expired internships
    auto_deactivate_expired_internships()
    
    # Clean up incomplete applications
    cleanup_incomplete_applications()
    
    total_internships = Internship.query.filter_by(is_active=True).count()
    total_applications = Application.query.filter_by(conversation_state='completed').count()
    pending_applications = Application.query.filter_by(status='pending', conversation_state='completed').count()
    recent_applications = Application.query.filter_by(conversation_state='completed').order_by(Application.applied_at.desc()).limit(5).all()
    
    return render_template('dashboard.html',
                         total_internships=total_internships,
                         total_applications=total_applications,
                         pending_applications=pending_applications,
                         recent_applications=recent_applications)

# Internship management routes
@app.route('/internships')
@login_required
def internships():
    # Auto-stop applications for expired internships (but keep them visible)
    auto_deactivate_expired_internships()
    
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'all')
    
    query = Internship.query.filter_by(is_active=True)
    
    if status_filter == 'accepting':
        query = query.filter_by(accepting_applications=True)
    elif status_filter == 'closed':
        query = query.filter_by(accepting_applications=False)
    
    internships = query.order_by(Internship.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False)
    
    return render_template('internships.html', internships=internships, status_filter=status_filter)

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

@app.route('/internships/<int:id>/toggle-applications')
@login_required
def toggle_applications(id):
    internship = Internship.query.get_or_404(id)
    internship.accepting_applications = not internship.accepting_applications
    
    action = "opened" if internship.accepting_applications else "closed"
    db.session.commit()
    
    flash(f'Applications for "{internship.title}" have been {action}', 'success')
    return redirect(url_for('internships'))

@app.route('/internships/<int:id>/share')
@login_required
def get_share_message(id):
    internship = Internship.query.get_or_404(id)
    # Use live WhatsApp number from system settings
    whatsapp_number = SystemSettings.get_setting('twilio_whatsapp_number', '+16056050396')
    share_message = internship.get_share_message(whatsapp_number)
    
    return jsonify({'message': share_message})

# Application management routes
@app.route('/shortlisted')
@login_required
def shortlisted_dashboard():
    """Shortlisted applicants dashboard with bulk messaging"""
    internship_id = request.args.get('internship_id', type=int)
    
    # Get shortlisted applications
    query = Application.query.filter_by(status='shortlisted')
    
    if internship_id:
        query = query.filter_by(internship_id=internship_id)
    
    shortlisted_applications = query.order_by(Application.applied_at.desc()).all()
    internships = Internship.query.filter_by(is_active=True).all()
    
    return render_template('shortlisted_dashboard.html', 
                         applications=shortlisted_applications,
                         internships=internships,
                         current_internship_id=internship_id)

@app.route('/shortlisted/bulk-message', methods=['POST'])
@login_required
def send_bulk_message():
    """Send bulk WhatsApp message to shortlisted applicants"""
    try:
        application_ids = request.form.getlist('application_ids')
        message_template = request.form.get('message_template')
        interview_date = request.form.get('interview_date')
        interview_time = request.form.get('interview_time')
        interview_location = request.form.get('interview_location')
        
        if not application_ids or not message_template:
            flash('Please select applicants and provide a message template.', 'warning')
            return redirect(url_for('shortlisted_dashboard'))
        
        sent_count = 0
        failed_count = 0
        
        for app_id in application_ids:
            application = Application.query.get(app_id)
            if not application or application.status != 'shortlisted':
                continue
                
            # Personalize the message
            personalized_message = message_template.format(
                name=application.full_name,
                position=application.internship.title,
                interview_date=interview_date or "[Date to be confirmed]",
                interview_time=interview_time or "[Time to be confirmed]", 
                interview_location=interview_location or "[Location to be confirmed]"
            )
            
            try:
                from communication import send_whatsapp_message
                send_whatsapp_message(application.whatsapp_number, personalized_message)
                sent_count += 1
                
                # Log the notification
                from communication import log_notification
                log_notification(
                    application.id,
                    'whatsapp',
                    application.whatsapp_number,
                    personalized_message,
                    'sent'
                )
                
            except Exception as e:
                failed_count += 1
                current_app.logger.error(f"Failed to send message to {application.whatsapp_number}: {e}")
                
                # Log the failed notification
                from communication import log_notification
                log_notification(
                    application.id,
                    'whatsapp',
                    application.whatsapp_number,
                    personalized_message,
                    'failed',
                    str(e)
                )
        
        if sent_count > 0:
            flash(f'✅ Successfully sent messages to {sent_count} applicants!', 'success')
        if failed_count > 0:
            flash(f'⚠️ Failed to send {failed_count} messages. Check logs for details.', 'warning')
            
        return redirect(url_for('shortlisted_dashboard'))
        
    except Exception as e:
        flash(f'Error sending bulk messages: {str(e)}', 'danger')
        return redirect(url_for('shortlisted_dashboard'))

@app.route('/applications')
@login_required
def applications():
    page = request.args.get('page', 1, type=int)
    internship_id = request.args.get('internship_id', type=int)
    status = request.args.get('status')
    search = request.args.get('search', '')
    
    # Clean up incomplete applications first
    cleanup_incomplete_applications()
    
    # Build query for applications - ONLY show completed applications
    query = Application.query.filter_by(conversation_state='completed')
    
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

@app.route('/applications/<int:id>/cv')
@login_required
def view_cv(id):
    """View application CV document"""
    application = Application.query.get_or_404(id)
    if not application.cv_filename:
        flash('No CV file found for this application', 'warning')
        return redirect(url_for('application_detail', id=id))
    
    cv_path = os.path.join(app.config.get('UPLOAD_FOLDER', 'uploads'), application.cv_filename)
    if not os.path.exists(cv_path):
        flash('CV file not found on disk', 'error')
        return redirect(url_for('application_detail', id=id))
    
    # Check if download is requested
    download = request.args.get('download') == '1'
    return send_file(cv_path, as_attachment=download, download_name=application.cv_original_filename or 'cv.pdf')

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
            # Send personalized notification to applicant with emojis
            if new_status == 'selected':
                message = f"🎉 **CONGRATULATIONS {application.full_name}!** 🎉\n\n✨ We are delighted to inform you that you have been **SELECTED** for the {application.internship.title} position!\n\n🚀 This is an amazing achievement and we're excited to have you join our team!\n\n📧 Please check your email for next steps and onboarding details.\n\n🎊 Welcome aboard! 🎊"
            elif new_status == 'rejected':
                message = f"📧 Dear {application.full_name},\n\n😔 We regret to inform you that your application for {application.internship.title} was not successful this time.\n\n💪 Please don't be discouraged! This doesn't reflect your abilities or potential.\n\n🌟 We encourage you to:\n• Keep developing your skills\n• Apply for future opportunities with us\n• Stay connected for upcoming positions\n\n🙏 Thank you for your interest in our company. We wish you all the best in your career journey!\n\n💼 Keep pushing forward - your perfect opportunity is coming!"
            elif new_status == 'shortlisted':
                message = f"🎯 **Great News {application.full_name}!** 🎯\n\n✅ You have been **SHORTLISTED** for the {application.internship.title} position!\n\n📋 You've made it to the next round! This means your application stood out among many candidates.\n\n📞 **Next Steps:**\n• Keep your phone available for contact\n• Check your email regularly\n• Prepare for potential interviews\n\n🤞 Best of luck! We'll be in touch soon."
            else:  # pending or other status
                message = f"📋 Hello {application.full_name},\n\n📄 Your application status for **{application.internship.title}** has been updated to: **{new_status.title()}**\n\n🔍 We'll keep you informed of any changes.\n\n📧 Thank you for your patience!"
            
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


@app.route('/applications/duplicates')
@login_required
def view_duplicates():
    """View and manage duplicate applications"""
    duplicates = Application.query.filter_by(is_duplicate=True).order_by(Application.applied_at.desc()).all()
    return render_template('duplicates.html', duplicates=duplicates)

@app.route('/applications/<int:id>/mark-duplicate', methods=['POST'])
@login_required
def mark_as_duplicate(id):
    """Mark application as duplicate"""
    application = Application.query.get_or_404(id)
    original_id = request.form.get('original_application_id')
    
    application.is_duplicate = True
    application.original_application_id = original_id
    application.status = 'rejected'
    
    db.session.commit()
    flash('Application marked as duplicate', 'success')
    return redirect(url_for('applications'))

@app.route('/applications/validate-batch', methods=['POST'])
@login_required
def validate_batch_applications():
    """Batch validate applications for duplicates"""
    from utils import detect_duplicate_application
    
    validated = 0
    duplicates_found = 0
    
    applications = Application.query.filter_by(conversation_state='completed', is_duplicate=False).all()
    
    for app in applications:
        is_duplicate, original_app_id, reason = detect_duplicate_application(
            app.internship_id, app.full_name, app.email, app.whatsapp_number
        )
        
        if is_duplicate:
            app.is_duplicate = True
            app.original_application_id = original_app_id
            duplicates_found += 1
        
        validated += 1
    
    db.session.commit()
    flash(f'Validated {validated} applications. Found {duplicates_found} duplicates.', 'info')
    return redirect(url_for('applications'))

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

# WhatsApp webhook (Twilio format)
@app.route('/webhook/whatsapp', methods=['GET', 'POST'])
def whatsapp_webhook():
    if request.method == 'GET':
        # For Twilio, this is typically not used, but keep for compatibility
        return 'Webhook endpoint ready', 200, {'Content-Type': 'text/plain'}
    
    elif request.method == 'POST':
        # Handle incoming Twilio WhatsApp messages
        try:
            # Twilio sends form data, not JSON
            data = request.form.to_dict()
            current_app.logger.info(f"=== TWILIO WHATSAPP WEBHOOK RECEIVED ===")
            current_app.logger.info(f"Form data: {data}")
            current_app.logger.info(f"Request headers: {dict(request.headers)}")
            
            # Convert Twilio format to our internal format
            if 'From' in data:
                # Extract phone number and format properly
                from utils import format_phone_number
                from_number = format_phone_number(data['From'])
                message_sid = data.get('MessageSid', 'unknown')
                
                # Check if it's a media message
                num_media = int(data.get('NumMedia', 0))
                
                if num_media > 0:
                    # Handle media message (image, document, etc.)
                    media_url = data.get('MediaUrl0', '')
                    media_content_type = data.get('MediaContentType0', '')
                    
                    converted_data = {
                        'entry': [{
                            'changes': [{
                                'field': 'messages',
                                'value': {
                                    'messages': [{
                                        'id': message_sid,
                                        'from': from_number,
                                        'timestamp': str(int(datetime.now().timestamp())),
                                        'type': 'image' if 'image' in media_content_type else 'document',
                                        'image': {
                                            'id': message_sid,
                                            'mime_type': media_content_type,
                                        } if 'image' in media_content_type else None,
                                        'document': {
                                            'id': message_sid,
                                            'mime_type': media_content_type,
                                        } if 'document' in media_content_type else None,
                                        'media_url': media_url,
                                        'media_content_type': media_content_type
                                    }]
                                }
                            }]
                        }]
                    }
                else:
                    # Handle text message
                    message_body = data.get('Body', '')
                    converted_data = {
                        'entry': [{
                            'changes': [{
                                'field': 'messages',
                                'value': {
                                    'messages': [{
                                        'id': message_sid,
                                        'from': from_number,
                                        'timestamp': str(int(datetime.now().timestamp())),
                                        'type': 'text',
                                        'text': {
                                            'body': message_body
                                        }
                                    }]
                                }
                            }]
                        }]
                    }
                
                # Import and process
                from whatsapp_handler import handle_webhook
                handle_webhook(converted_data)
            
            # Return empty response for WhatsApp webhooks (no TwiML needed)
            return '', 200, {'Content-Type': 'text/plain'}
        except Exception as e:
            current_app.logger.error(f"Error processing Twilio WhatsApp webhook: {e}")
            import traceback
            current_app.logger.error(f"Traceback: {traceback.format_exc()}")
            return 'Error', 500, {'Content-Type': 'text/plain'}

@app.route('/test-whatsapp', methods=['POST'])
@login_required
def test_whatsapp_bot():
    """Test WhatsApp bot functionality with simulated message"""
    try:
        # Get test data from form
        from_number = request.form.get('from_number', '+1234567890')
        message_text = request.form.get('message_text', 'APPLY HLEB0H PXEI8387')
        
        # Create simulated webhook data
        simulated_data = {
            'entry': [{
                'changes': [{
                    'field': 'messages',
                    'value': {
                        'messages': [{
                            'id': f'test_msg_{datetime.now().timestamp()}',
                            'from': from_number,
                            'timestamp': str(int(datetime.now().timestamp())),
                            'type': 'text',
                            'text': {
                                'body': message_text
                            }
                        }]
                    }
                }]
            }]
        }
        
        current_app.logger.info(f"Testing WhatsApp bot with simulated data: {simulated_data}")
        
        # Import and process
        from whatsapp_handler import handle_webhook
        handle_webhook(simulated_data)
        
        flash(f'Test message processed: "{message_text}" from {from_number}', 'success')
        
    except Exception as e:
        current_app.logger.error(f"Error in WhatsApp test: {e}")
        import traceback
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        flash(f'Error testing WhatsApp bot: {str(e)}', 'danger')
    
    return redirect(url_for('settings'))

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
