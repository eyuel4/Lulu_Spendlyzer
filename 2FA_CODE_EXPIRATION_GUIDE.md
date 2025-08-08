# 2FA Code Expiration Guide

## Overview
This guide explains the new two-factor authentication (2FA) code expiration functionality that has been implemented for SMS and Email verification methods.

## Key Features

### 1. Conditional Resend Functionality
- **Authenticator Apps (Google Authenticator, etc.)**: No resend button is shown
- **SMS/Email Methods**: Resend button is available with 10-minute expiration

### 2. Code Expiration
- All SMS and Email verification codes expire after **10 minutes**
- Users see a countdown message showing when the code will expire
- Expired codes are automatically rejected during verification

### 3. User Experience Improvements
- Clear expiration messages: "Code expires in X minutes"
- Automatic countdown timer updates every minute
- Success notifications include expiration information

## Implementation Details

### Frontend Changes

#### Account Settings Service (`account-settings.service.ts`)
- Added `sendTwoFactorCode()` method for initial code sending
- Added `resendTwoFactorCode()` method for code resending
- Added `canResendCode()` utility method
- Added `getExpirationMessage()` for user-friendly expiration display

#### Two-Factor Verification Component
- Conditional resend button display based on 2FA method
- Real-time expiration countdown
- Enhanced error handling and user feedback

### Backend Changes

#### New API Endpoints
- `POST /users/2fa/send-code` - Send initial verification code
- `POST /users/2fa/resend-code` - Resend verification code

#### Database Schema Updates
- Added `temp_code` field to store temporary verification codes
- Added `temp_code_expires_at` field to track expiration times
- Database changes are automatically handled through `/app/core/init_db.py` and `/app/core/database.py`

#### Enhanced Verification Logic
- SMS/Email codes are validated against stored temporary codes
- Expiration times are checked during verification
- Temporary codes are cleared after successful verification

## Usage Examples

### For SMS 2FA
1. User enables SMS 2FA
2. System sends 6-digit code via SMS
3. User sees: "Code expires in 10 minutes"
4. If code expires, user can click "Resend Code"
5. New code is sent with fresh 10-minute expiration

### For Email 2FA
1. User enables Email 2FA
2. System sends 6-digit code via email
3. User sees: "Code expires in 10 minutes"
4. If code expires, user can click "Resend Code"
5. New code is sent with fresh 10-minute expiration

### For Authenticator Apps
1. User enables Authenticator 2FA
2. No resend functionality is available
3. User must use the authenticator app to generate codes

## Database Setup

The database schema is automatically managed through the core database files:

- **`/app/core/database.py`**: Contains database connection and initialization logic
- **`/app/core/init_db.py`**: Handles table creation and schema updates

When you start the application, SQLAlchemy will automatically create any missing tables or columns based on the model definitions.

To initialize the database:

```bash
python app/core/init_db.py
```

## Security Considerations

1. **Code Storage**: Temporary codes are stored in the database with expiration times
2. **Automatic Cleanup**: Codes are cleared after successful verification
3. **Expiration Enforcement**: Server-side validation ensures expired codes are rejected
4. **Rate Limiting**: Consider implementing rate limiting for code sending/resending

## Future Enhancements

1. **Redis Integration**: Store temporary codes in Redis for better performance
2. **Rate Limiting**: Implement rate limiting for code sending
3. **SMS/Email Service Integration**: Connect to actual SMS/Email services
4. **Audit Logging**: Log all code sending and verification attempts

## Testing

To test the functionality:

1. Enable 2FA with SMS or Email method
2. Check that resend button appears only for SMS/Email
3. Verify expiration countdown works correctly
4. Test that expired codes are rejected
5. Confirm resend functionality works as expected

## Database Schema Management

All database changes (adding columns, renaming columns, adding tables) should be handled by:

1. **Updating the model files** in `/app/models/` with the new schema
2. **Ensuring the models are imported** in `/app/core/database.py`
3. **Running the initialization script** to apply changes

This approach ensures consistency and avoids the need for separate migration scripts. 