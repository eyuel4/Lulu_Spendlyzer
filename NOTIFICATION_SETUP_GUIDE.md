# Notification Service Setup Guide

This guide explains how to configure the production-ready SMS and Email notification services for 2FA.

## Environment Variables

Add the following environment variables to your `.env` file:

### Email Configuration (SMTP)
```env
# SMTP Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@spendlyzer.com
```

### SMS Configuration (Twilio)
```env
# Twilio Configuration
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_PHONE_NUMBER=+1234567890
```

### Redis Configuration (for rate limiting and code storage)
```env
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

## Email Setup

### Gmail Setup
1. Enable 2-Factor Authentication on your Gmail account
2. Generate an App Password:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate a new app password for "Mail"
3. Use the generated password as `SMTP_PASSWORD`

### Other Email Providers
- **Outlook/Hotmail**: Use `smtp-mail.outlook.com` with port 587
- **Yahoo**: Use `smtp.mail.yahoo.com` with port 587
- **Custom SMTP**: Use your provider's SMTP settings

## SMS Setup (Twilio)

### Twilio Account Setup
1. Create a Twilio account at [twilio.com](https://www.twilio.com)
2. Get your Account SID and Auth Token from the Twilio Console
3. Purchase a phone number for SMS sending
4. Add the credentials to your environment variables

### Alternative SMS Providers
You can modify the `NotificationService` class to use other SMS providers:
- **AWS SNS**: Use AWS Simple Notification Service
- **SendGrid**: Use SendGrid's SMS API
- **Vonage**: Use Vonage (formerly Nexmo)

## Rate Limiting

The service includes built-in rate limiting:
- **SMS**: 5 messages per hour per phone number
- **Email**: 10 emails per hour per email address
- **Verification codes**: 5-minute expiry, 3 attempts maximum

## Security Features

### Code Generation
- 6-digit numeric codes
- Cryptographically secure random generation
- Stored in Redis with expiry
- Attempt tracking to prevent brute force

### Rate Limiting
- Per-user rate limiting
- Redis-based tracking
- Configurable limits

### Code Verification
- One-time use codes
- Automatic cleanup after verification
- Attempt counting to prevent abuse

## Testing

### Development Mode
For development/testing, you can use:
- **Email**: Gmail with app passwords
- **SMS**: Twilio trial account (limited messages)

### Production Mode
For production:
- Use dedicated email service (SendGrid, Mailgun, etc.)
- Use paid Twilio account for SMS
- Ensure Redis is properly configured for persistence

## Monitoring

### Logs
The service logs all operations:
- Successful sends
- Failed sends
- Rate limit violations
- Verification attempts

### Metrics to Monitor
- Send success rates
- Rate limit violations
- Verification success rates
- Redis connection status

## Troubleshooting

### Common Issues

1. **Email not sending**:
   - Check SMTP credentials
   - Verify app password for Gmail
   - Check firewall/network settings

2. **SMS not sending**:
   - Verify Twilio credentials
   - Check phone number format
   - Ensure sufficient Twilio credits

3. **Rate limiting issues**:
   - Check Redis connection
   - Verify rate limit settings
   - Monitor Redis memory usage

### Debug Mode
Enable debug logging by setting:
```env
LOG_LEVEL=DEBUG
```

## Production Checklist

- [ ] Configure production email service
- [ ] Set up Twilio production account
- [ ] Configure Redis with persistence
- [ ] Set up monitoring and alerting
- [ ] Test rate limiting
- [ ] Verify code expiry settings
- [ ] Set up backup notification methods
- [ ] Configure error handling and retries
- [ ] Set up logging and monitoring
- [ ] Test all 2FA flows end-to-end 