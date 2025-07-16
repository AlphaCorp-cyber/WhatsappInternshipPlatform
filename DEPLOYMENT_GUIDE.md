# Self-Hosting Deployment Guide

## Environment Variables Setup

When hosting on your own server, you'll need to configure these environment variables. Here are the different methods:

### 1. Environment File (.env)

Create a `.env` file in your project root:

```bash
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/internship_db

# Flask Security
SESSION_SECRET=your-super-secure-random-string-here

# Twilio WhatsApp Configuration
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_PHONE_NUMBER=+1234567890
TWILIO_WHATSAPP_NUMBER=whatsapp:+1234567890

# Optional: Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password

# Optional: Additional SMS Configuration
SMS_SERVICE_API_KEY=your-sms-api-key
```

**Important**: Add `.env` to your `.gitignore` file to prevent committing secrets to version control.

### 2. System Environment Variables

For production servers, set environment variables in your system:

#### Linux/Ubuntu (systemd service)
```bash
# Create environment file
sudo nano /etc/environment

# Add variables:
DATABASE_URL="postgresql://username:password@localhost:5432/internship_db"
SESSION_SECRET="your-super-secure-random-string"
TWILIO_ACCOUNT_SID="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
TWILIO_AUTH_TOKEN="your-twilio-auth-token"
TWILIO_PHONE_NUMBER="+1234567890"
TWILIO_WHATSAPP_NUMBER="whatsapp:+1234567890"

# Reload environment
source /etc/environment
```

#### Docker Environment
```dockerfile
# In docker-compose.yml
version: '3.8'
services:
  app:
    build: .
    environment:
      - DATABASE_URL=postgresql://username:password@db:5432/internship_db
      - SESSION_SECRET=your-super-secure-random-string
      - TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
      - TWILIO_AUTH_TOKEN=your-twilio-auth-token
      - TWILIO_PHONE_NUMBER=+1234567890
      - TWILIO_WHATSAPP_NUMBER=whatsapp:+1234567890
    ports:
      - "5000:5000"
```

### 3. Cloud Provider Secrets Management

#### AWS (using AWS Secrets Manager)
```python
# Add to app.py for AWS deployment
import boto3
import json

def get_aws_secret(secret_name):
    session = boto3.session.Session()
    client = session.client('secretsmanager', region_name='us-east-1')
    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        return json.loads(get_secret_value_response['SecretString'])
    except Exception as e:
        print(f"Error retrieving secret: {e}")
        return None

# Use in app configuration
if os.environ.get('AWS_SECRET_NAME'):
    secrets = get_aws_secret(os.environ['AWS_SECRET_NAME'])
    os.environ.update(secrets)
```

#### DigitalOcean App Platform
```yaml
# In .do/app.yaml
name: internship-app
services:
- name: web
  source_dir: /
  github:
    repo: your-username/your-repo
    branch: main
  run_command: gunicorn --bind 0.0.0.0:$PORT main:app
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  envs:
  - key: DATABASE_URL
    value: ${db.DATABASE_URL}
  - key: SESSION_SECRET
    value: ${APP_SECRET}
    type: SECRET
  - key: TWILIO_ACCOUNT_SID
    value: ${TWILIO_SID}
    type: SECRET
  - key: TWILIO_AUTH_TOKEN
    value: ${TWILIO_TOKEN}
    type: SECRET
```

#### Heroku
```bash
# Set via Heroku CLI
heroku config:set DATABASE_URL="postgresql://..." --app your-app-name
heroku config:set SESSION_SECRET="your-secret" --app your-app-name
heroku config:set TWILIO_ACCOUNT_SID="ACxxx" --app your-app-name
heroku config:set TWILIO_AUTH_TOKEN="your-token" --app your-app-name
```

## Required Secrets Breakdown

### 1. Database Configuration
```bash
# PostgreSQL (recommended for production)
DATABASE_URL=postgresql://username:password@host:port/database

# SQLite (development only)
DATABASE_URL=sqlite:///internship.db
```

### 2. Flask Security
```bash
# Generate a secure random string
SESSION_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
```

### 3. Twilio WhatsApp Setup
```bash
# From Twilio Console (https://console.twilio.com/)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx  # Account SID
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx     # Auth Token
TWILIO_PHONE_NUMBER=+1234567890                         # Your Twilio phone number
TWILIO_WHATSAPP_NUMBER=whatsapp:+1234567890             # WhatsApp-enabled number
```

### 4. Optional Email Configuration
```bash
# Gmail SMTP
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-specific-password  # Not your regular password

# SendGrid
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USER=apikey
EMAIL_PASSWORD=your-sendgrid-api-key
```

## Security Best Practices

### 1. Secret Generation
```bash
# Generate secure SESSION_SECRET
python3 -c "import secrets; print('SESSION_SECRET=' + secrets.token_urlsafe(32))"

# Generate secure database password
python3 -c "import secrets, string; chars = string.ascii_letters + string.digits; print(''.join(secrets.choice(chars) for _ in range(20)))"
```

### 2. File Permissions
```bash
# Secure .env file permissions
chmod 600 .env
chown your-app-user:your-app-group .env

# Secure upload directory
chmod 755 uploads/
chown your-app-user:your-app-group uploads/
```

### 3. Firewall Configuration
```bash
# Allow only necessary ports
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw allow 5432  # PostgreSQL (if external access needed)
sudo ufw enable
```

## Server Setup Examples

### 1. Ubuntu/Debian Server Setup
```bash
# Install dependencies
sudo apt update
sudo apt install python3 python3-pip python3-venv postgresql nginx

# Create application user
sudo useradd -m -s /bin/bash internship-app
sudo usermod -aG www-data internship-app

# Setup application directory
sudo mkdir -p /opt/internship-app
sudo chown internship-app:internship-app /opt/internship-app

# Clone and setup application
cd /opt/internship-app
git clone your-repo-url .
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create environment file
sudo nano /opt/internship-app/.env
# Add your environment variables here

# Setup systemd service
sudo nano /etc/systemd/system/internship-app.service
```

### 2. Systemd Service Configuration
```ini
[Unit]
Description=Internship Application System
After=network.target postgresql.service

[Service]
Type=notify
User=internship-app
Group=internship-app
WorkingDirectory=/opt/internship-app
Environment=PATH=/opt/internship-app/venv/bin
EnvironmentFile=/opt/internship-app/.env
ExecStart=/opt/internship-app/venv/bin/gunicorn --bind unix:/tmp/internship-app.sock --workers 3 main:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 3. Nginx Configuration
```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    location / {
        proxy_pass http://unix:/tmp/internship-app.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /opt/internship-app/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location /uploads {
        alias /opt/internship-app/uploads;
        expires 1d;
        add_header Cache-Control "private";
    }
}
```

## Environment Variables Loading

The application automatically loads environment variables in this order:

1. **System environment variables** (highest priority)
2. **`.env` file** in project root
3. **Default values** (if any)

### Loading .env File
If you want to use a `.env` file, install python-dotenv:

```bash
pip install python-dotenv
```

Then add to the top of `app.py`:
```python
from dotenv import load_dotenv
load_dotenv()  # Load .env file
```

## Webhook Configuration

For your own server, you'll need to configure the Twilio webhook URL:

1. **Get your server's public URL**:
   - Domain: `https://yourdomain.com`
   - IP with SSL: `https://your-ip-address`

2. **Set webhook in Twilio Console**:
   - URL: `https://yourdomain.com/webhook/whatsapp`
   - Method: `POST`
   - Content-Type: `application/x-www-form-urlencoded`

3. **Test webhook**:
   ```bash
   curl -X POST https://yourdomain.com/webhook/whatsapp \
     -d "From=whatsapp:+1234567890&Body=test&MessageSid=test123"
   ```

## Monitoring and Logging

### 1. Application Logs
```bash
# View systemd service logs
sudo journalctl -u internship-app.service -f

# Application-specific logs
tail -f /opt/internship-app/app.log
```

### 2. Database Monitoring
```bash
# PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-*.log

# Database connections
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity;"
```

### 3. Nginx Logs
```bash
# Access logs
sudo tail -f /var/log/nginx/access.log

# Error logs
sudo tail -f /var/log/nginx/error.log
```

## Backup Strategy

### 1. Database Backup
```bash
# Create backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump internship_db > /backups/internship_db_$DATE.sql
find /backups -name "internship_db_*.sql" -mtime +7 -delete
```

### 2. File Backup
```bash
# Backup uploads directory
rsync -av /opt/internship-app/uploads/ /backups/uploads/
```

### 3. Environment Backup
```bash
# Securely backup environment file
cp /opt/internship-app/.env /secure-backups/.env.backup
chmod 600 /secure-backups/.env.backup
```

## Troubleshooting

### Common Issues

1. **Permission Denied Errors**:
   ```bash
   sudo chown -R internship-app:internship-app /opt/internship-app
   sudo chmod 755 /opt/internship-app
   sudo chmod 600 /opt/internship-app/.env
   ```

2. **Database Connection Issues**:
   ```bash
   # Test PostgreSQL connection
   psql -h localhost -U username -d internship_db -c "SELECT 1;"
   ```

3. **Webhook Not Receiving Messages**:
   - Check firewall allows port 80/443
   - Verify SSL certificate is valid
   - Test webhook URL accessibility
   - Check Twilio webhook logs

4. **File Upload Issues**:
   ```bash
   # Ensure uploads directory exists and is writable
   mkdir -p /opt/internship-app/uploads
   chown internship-app:internship-app /opt/internship-app/uploads
   chmod 755 /opt/internship-app/uploads
   ```

This guide covers all aspects of self-hosting the WhatsApp Internship Application System on your own server with proper secrets management.