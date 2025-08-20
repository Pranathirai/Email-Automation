# 🔑 SMTP Setup Guide for MailerPro

## 📧 Gmail OAuth Setup

### Step 1: Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create new project or select existing one
3. Enable Gmail API:
   - Go to "APIs & Services" → "Library"
   - Search "Gmail API" and enable it

### Step 2: Create OAuth Credentials
1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth 2.0 Client IDs"
3. Set Application type: "Web application"
4. Add these redirect URIs:
   ```
   http://localhost:3000/auth/gmail/callback
   https://your-domain.com/auth/gmail/callback
   ```
5. Save Client ID and Client Secret

### Step 3: Configure in MailerPro
```json
{
  "provider": "gmail",
  "client_id": "your-gmail-client-id",
  "client_secret": "your-gmail-client-secret",
  "daily_limit": 500
}
```

---

## 📮 Outlook OAuth Setup

### Step 1: Register Azure App
1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to "Azure Active Directory" → "App registrations"
3. Click "New registration"
4. Set redirect URI: `https://your-domain.com/auth/outlook/callback`

### Step 2: Configure Permissions
1. Go to "API permissions"
2. Add Microsoft Graph permissions:
   - `Mail.Send` (Application)
   - `Mail.ReadWrite` (Delegated)
3. Grant admin consent

### Step 3: Get Credentials
1. Go to "Certificates & secrets"
2. Create new client secret
3. Copy Application (client) ID and Client secret

### Step 4: Configure in MailerPro
```json
{
  "provider": "outlook",
  "client_id": "your-outlook-client-id", 
  "client_secret": "your-outlook-client-secret",
  "daily_limit": 300
}
```

---

## 🔧 Custom SMTP Providers

### 📧 SendGrid SMTP
```json
{
  "provider": "custom",
  "name": "SendGrid",
  "smtp_host": "smtp.sendgrid.net",
  "smtp_port": 587,
  "username": "apikey",
  "password": "your-sendgrid-api-key",
  "daily_limit": 1000
}
```

**Get SendGrid API Key:**
1. Sign up at [SendGrid](https://sendgrid.com)
2. Go to Settings → API Keys
3. Create new API key with "Mail Send" permissions

### 🎯 Mailgun SMTP
```json
{
  "provider": "custom",
  "name": "Mailgun",
  "smtp_host": "smtp.mailgun.org",
  "smtp_port": 587,
  "username": "postmaster@your-domain.mailgun.org",
  "password": "your-mailgun-password",
  "daily_limit": 800
}
```

**Get Mailgun Credentials:**
1. Sign up at [Mailgun](https://mailgun.com)
2. Add and verify your domain
3. Get SMTP credentials from Domains → Domain Settings

### ☁️ Amazon SES SMTP
```json
{
  "provider": "custom",
  "name": "Amazon SES",
  "smtp_host": "email-smtp.us-east-1.amazonaws.com",
  "smtp_port": 587,
  "username": "your-ses-smtp-username",
  "password": "your-ses-smtp-password",
  "daily_limit": 2000
}
```

**Get SES SMTP Credentials:**
1. Go to [AWS SES Console](https://console.aws.amazon.com/ses)
2. Create SMTP credentials in "SMTP Settings"
3. Request production access (remove sandbox mode)

### 🌟 ColdSend.pro (Recommended)
```json
{
  "provider": "custom",
  "name": "ColdSend.pro",
  "smtp_host": "smtp.coldsend.pro",
  "smtp_port": 587,
  "username": "your-coldsend-username",
  "password": "your-coldsend-password",
  "daily_limit": 500
}
```

**Get ColdSend Credentials:**
1. Sign up at [ColdSend.pro](https://coldsend.pro)
2. Choose plan (100 inboxes for $50/month)
3. Get SMTP credentials from dashboard

---

## 🔒 Gmail App Password Setup (Alternative)

If you prefer Gmail App Passwords instead of OAuth:

1. Enable 2-Factor Authentication on your Gmail
2. Go to Google Account Settings → Security
3. Generate App Password for "Mail"
4. Use this configuration:

```json
{
  "provider": "custom",
  "name": "Gmail App Password",
  "smtp_host": "smtp.gmail.com",
  "smtp_port": 587,
  "username": "your-gmail@gmail.com",
  "password": "your-16-digit-app-password",
  "daily_limit": 500
}
```

---

## 🚨 Important Notes

### Daily Limits by Provider:
- **Gmail**: 500 emails/day (free), 2000/day (Google Workspace)
- **Outlook**: 300 emails/day (free), 10,000/day (Office 365)
- **SendGrid**: Based on your plan (100/day free)
- **Mailgun**: Based on your plan (5,000/month free)
- **Amazon SES**: No daily limits, pay per email
- **ColdSend.pro**: Up to 10,000/month based on plan

### Best Practices:
1. **Start Small**: Begin with 50-100 emails/day
2. **Warm Up**: Gradually increase sending volume
3. **Multiple Accounts**: Use 3-5 different SMTP accounts
4. **Monitor Bounces**: Keep bounce rate under 5%
5. **Authentication**: Set up SPF, DKIM, DMARC records

### Security:
- Never share SMTP credentials
- Use environment variables for production
- Rotate passwords regularly
- Monitor sending activity

---

## 🔥 Quick Start Recommendations

**For Beginners:**
1. Start with Gmail App Password (easiest)
2. Add SendGrid free tier
3. Test with 50 emails/day

**For Professionals:**
1. ColdSend.pro (best deliverability)
2. Amazon SES (cost-effective)
3. Multiple Gmail/Outlook accounts

**For Enterprise:**
1. Dedicated SendGrid plan
2. Amazon SES with dedicated IPs  
3. Multiple ColdSend.pro accounts