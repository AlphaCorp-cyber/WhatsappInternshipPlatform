# WhatsApp Internship Application System

## Overview

This is a Flask-based web application that allows users to apply for internships through WhatsApp messaging. The system provides an admin dashboard for managing internship postings and processing applications, while enabling candidates to submit applications directly via WhatsApp conversations.

## System Architecture

### Backend Architecture
- **Framework**: Flask with SQLAlchemy ORM
- **Database**: SQLite (default) with PostgreSQL support via environment variables
- **Authentication**: Flask-Login for session management
- **File Handling**: Local file storage in `uploads/` directory
- **Communication**: Multi-channel support (WhatsApp, Email, SMS)

### Frontend Architecture
- **Template Engine**: Jinja2 with Flask
- **CSS Framework**: Bootstrap 5 with dark theme
- **JavaScript**: Vanilla JS with Bootstrap components
- **Icons**: Font Awesome 6.4.0

## Key Components

### 1. Models (`models.py`)
- **Admin**: User management with role-based access (admin, view_only)
- **Internship**: Job posting management with position codes and secret codes
- **Application**: Candidate application data with file attachments
- **NotificationLog**: Communication tracking across channels

### 2. WhatsApp Integration (`whatsapp_handler.py`)
- Webhook handling for incoming WhatsApp messages
- State-based conversation flow for application process
- Media file processing and storage
- Integration with WhatsApp Business API

### 3. Communication System (`communication.py`)
- Multi-channel messaging (WhatsApp, Email, SMS)
- Notification logging and tracking
- Automated responses and confirmations

### 4. Admin Dashboard (`routes.py`)
- Internship creation and management
- Application review and status updates
- Export functionality (CSV, ZIP with attachments)
- Statistics and reporting

## Data Flow

### Application Process
1. Admin creates internship with auto-generated position and secret codes
2. Candidate sends WhatsApp message with codes to start application
3. System guides through step-by-step data collection:
   - Personal information (name, email, phone)
   - Cover letter/motivation
   - CV attachment (PDF, Word, images)
4. Application stored in database with file attachments
5. Confirmation sent to candidate via WhatsApp

### Admin Workflow
1. Login to dashboard with Flask-Login authentication
2. Create/manage internship postings
3. Review applications with filtering and search
4. Update application status with automated notifications
5. Export application data and attachments

## External Dependencies

### Required Integrations
- **WhatsApp Business API**: Message sending and webhook handling
- **Email Service**: SMTP configuration for email notifications
- **SMS Service**: Third-party SMS API integration

### Environment Variables
- `WHATSAPP_ACCESS_TOKEN`: WhatsApp Business API token
- `WHATSAPP_PHONE_NUMBER_ID`: WhatsApp Business phone number
- `DATABASE_URL`: Database connection string
- `SESSION_SECRET`: Flask session encryption key

## Deployment Strategy

### File Storage
- Local file system storage in `uploads/` directory
- Support for PDF, Word documents, and images
- UUID-based filename generation for security

### Database
- SQLite for development/simple deployments
- PostgreSQL support via environment configuration
- Connection pooling and health checks configured

### Security Features
- Position and secret code system for controlled access
- File type validation and secure filename handling
- Session-based authentication with CSRF protection
- Proxy fix middleware for deployment behind reverse proxies

## User Preferences

Preferred communication style: Simple, everyday language.

## WhatsApp Bot Status

### ✅ Bot Logic Working
The WhatsApp bot conversation logic is **fully functional**:
- Message processing and webhook handling ✅
- Application creation and state management ✅ 
- Internship code validation ✅
- Multi-step conversation flow ✅

### 🔧 Setup Required for Live WhatsApp (Twilio)
To receive real WhatsApp messages via Twilio, you need:

1. **Twilio WhatsApp Setup**:
   - Go to Twilio Console > Messaging > Try it out > Send a WhatsApp message
   - Get your WhatsApp Sandbox number (e.g., +14155238886)
   - Configure credentials in environment variables

2. **Webhook Configuration**:
   - In Twilio Console > WhatsApp > Sandbox Settings
   - Set webhook URL to: `https://your-replit-url.replit.app/webhook/whatsapp`
   - HTTP POST method

3. **Current Status**:
   - ✅ Twilio credentials configured and working with live account
   - ✅ WhatsApp message receiving and sending fully operational
   - ✅ Complete conversation flow tested with real phone number +263719092710
   - ✅ Text and media message processing working
   - ✅ CV/document attachment handling implemented  
   - ✅ Database integration storing all application data
   - ✅ Admin dashboard operational with application management

### 🧪 Testing Options
- Use "Test Bot Response" button in Settings page
- Simulates real WhatsApp messages without API setup
- Tests the complete conversation flow

## Changelog

- July 14, 2025: PDF-only document system with in-browser viewing
- July 14, 2025: Streamlined application process - name, email + CV upload for speed
- July 14, 2025: Enhanced WhatsApp bot messages with emojis, welcome screen, and position details
- July 14, 2025: Document upload hint added for university/college cover letters
- July 14, 2025: WhatsApp bot logic completed and tested
- July 14, 2025: Settings management system added  
- July 14, 2025: Multi-channel communication system implemented
- June 30, 2025: Initial setup