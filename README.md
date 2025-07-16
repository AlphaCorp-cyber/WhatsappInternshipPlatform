# WhatsApp Internship Application System

A modern SaaS platform that enables candidates to apply for internships directly through WhatsApp conversations, with a powerful admin dashboard for managing applications.

## Quick Start

### 1. Environment Setup
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your actual values
nano .env
```

### 2. Database Setup
```bash
# Run the setup script to create tables and default admin
python3 create_sample_data.py
```

### 3. Start Application
```bash
# Install dependencies (if needed)
pip install -r requirements.txt

# Start the server
python3 main.py
```

### 4. Access Admin Dashboard
- **URL**: http://localhost:5000
- **Username**: `admin`
- **Password**: `admin123`
- **⚠️ IMPORTANT**: Change password after first login!

## Default Configuration

The setup script creates:

### Default Admin Account
- **Username**: admin
- **Email**: admin@company.com
- **Password**: admin123 (change immediately!)
- **Role**: Full admin access

### Sample Internship
- **Title**: Web Developer Internship
- **Position Code**: Auto-generated (e.g., WD001)
- **Secret Code**: Auto-generated (e.g., SECRET123)
- **Deadline**: 30 days from creation

### Test WhatsApp Application
Send this message to your WhatsApp number:
```
APPLY [POSITION_CODE] [SECRET_CODE]
```

## Environment Variables Required

### Essential (.env file)
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:port/dbname

# Security
SESSION_SECRET=your-secure-random-string

# Twilio WhatsApp
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=+1234567890
TWILIO_WHATSAPP_NUMBER=whatsapp:+1234567890
```

### Generate Secure Session Secret
```bash
python3 -c "import secrets; print('SESSION_SECRET=' + secrets.token_urlsafe(32))"
```

## Features

### For Candidates
- Apply via WhatsApp with just name, email, and CV
- Real-time application feedback
- Automatic confirmation messages
- PDF document upload support

### For Administrators
- Complete internship management
- Application review with CV viewing
- Bulk messaging to shortlisted candidates
- Export functionality (CSV/ZIP)
- Real-time statistics dashboard

## Documentation

- **[DOCUMENTATION.md](DOCUMENTATION.md)** - Complete system guide
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Self-hosting instructions

## Security Notes

1. **Change default admin password immediately**
2. **Keep .env file secure** (never commit to version control)
3. **Use strong SESSION_SECRET** (32+ random characters)
4. **Configure firewall** for production deployment
5. **Regular backups** of database and uploaded files

## Support

- Check logs for troubleshooting
- Review documentation for detailed setup
- Test WhatsApp bot with sample internship codes

---

🚀 **Ready to use!** The system is fully configured with sample data for immediate testing.