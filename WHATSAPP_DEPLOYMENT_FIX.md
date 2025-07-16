# WhatsApp Bot Deployment Fix Guide

## Current Issue: WhatsApp Bot Not Responding in Deployed Environment

### Quick Diagnosis
Your WhatsApp bot works locally but not in production. This is typically a webhook configuration issue.

## Step 1: Find Your Deployed URL
Your Replit app should be accessible at:
- `https://YOUR-REPL-NAME.USERNAME.replit.app`
- Or check the "Webview" tab in Replit for the correct URL

## Step 2: Update Twilio Webhook Configuration

### In Twilio Console (https://console.twilio.com/):

1. **Go to Messaging → Try it out → Send a WhatsApp message**
2. **Click "Sandbox Settings"**
3. **Update the webhook URL to:**
   ```
   https://YOUR-REPL-NAME.USERNAME.replit.app/webhook/whatsapp
   ```
4. **Set HTTP method to: POST**
5. **Save the configuration**

## Step 3: Test the Webhook

### Test webhook accessibility:
```bash
curl -X POST https://YOUR-DEPLOYED-URL/webhook/whatsapp \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "From=whatsapp%3A%2B1234567890&Body=test&MessageSid=test123"
```

Should return status 200.

## Step 4: Verify Environment Variables

Ensure these secrets are set in your deployed Replit:
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN` 
- `TWILIO_WHATSAPP_NUMBER`
- `DATABASE_URL`
- `SESSION_SECRET`

## Step 5: Check Logs

In your deployed Replit, check the console logs for:
- Webhook receiving messages: "TWILIO WHATSAPP WEBHOOK RECEIVED"
- Any error messages
- Database connection issues

## Common Issues & Solutions

### Issue 1: Wrong Webhook URL
**Problem:** Twilio is sending to old localhost URL
**Solution:** Update webhook URL in Twilio console to your deployed URL

### Issue 2: HTTPS Required
**Problem:** Twilio requires HTTPS webhooks
**Solution:** Replit provides HTTPS by default, ensure URL starts with `https://`

### Issue 3: Environment Variables Missing
**Problem:** Secrets not configured in deployed environment
**Solution:** Add all required secrets in Replit's "Secrets" tab

### Issue 4: Port Binding
**Problem:** App not accessible on deployed port
**Solution:** Ensure app binds to `0.0.0.0:5000` (already configured)

## Emergency Test Method

If webhook still doesn't work, use the "Test Bot Response" feature:
1. Login to admin dashboard
2. Go to Settings
3. Use "Test WhatsApp Bot" form
4. This bypasses Twilio and tests the bot logic directly

## Current Working Configuration

✅ **Local webhook**: Working properly
✅ **Bot logic**: All conversation flows working
✅ **Database**: Applications saving correctly
✅ **CV handling**: Fixed and working

❌ **Production webhook**: Needs Twilio URL update

The fix is simply updating the webhook URL in your Twilio console to point to your deployed Replit URL instead of localhost.