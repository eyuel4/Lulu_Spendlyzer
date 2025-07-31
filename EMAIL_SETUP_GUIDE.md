# Email Setup Guide for Spendlyzer

## Problem
You're getting this error when sending emails:
```
Error sending invitation email: (535, b'5.7.8 Username and Password not accepted')
```

## Solution: Use Gmail App Passwords

### Step 1: Enable 2-Factor Authentication
1. Go to your Google Account: https://myaccount.google.com/
2. Navigate to **Security** → **2-Step Verification**
3. Enable 2-Step Verification if not already enabled

### Step 2: Generate an App Password
1. Go to: https://myaccount.google.com/apppasswords
2. Select **"Mail"** as the app
3. Select **"Other"** as the device (name it "Spendlyzer")
4. Click **"Generate"**
5. Copy the 16-character password (format: `abcd efgh ijkl mnop`)
byai ykcu hlny nmbm (Spendlyzer)

### Step 3: Update Your Environment Variables
Create or update your `.env` file in the project root:

```env
# Database Configuration
DB_URL=sqlite+aiosqlite:///finance.db

# JWT Configuration
JWT_SECRET=your-super-secret-jwt-key-here

# Email Configuration (Gmail)
EMAIL_FROM=your-email@gmail.com
EMAIL_PASSWORD=your-16-character-app-password-here
EMAIL_TO=your-email@gmail.com

# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

### Step 4: Restart Your Application
After updating the `.env` file:
```bash
# Stop the current server (Ctrl+C)
# Then restart:
python -m uvicorn app.main:app --reload --port 8000
```

## Important Notes
- **Never use your regular Gmail password** - it won't work
- **Always use the App Password** - it's specifically for applications
- **Keep your App Password secure** - it's like a special key for your app
- **The App Password is 16 characters** with spaces (remove spaces when using)

## Testing
After setup, test by creating a family group with invitees. You should see:
```
Invitation email sent successfully to user@example.com
```

## Troubleshooting
If you still get errors:
1. Make sure 2-Factor Authentication is enabled
2. Verify you're using the App Password (not regular password)
3. Check that your Gmail account allows "less secure apps" (though App Passwords are preferred)
4. Ensure your `.env` file is in the correct location (project root) 