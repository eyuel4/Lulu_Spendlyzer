# Error Handling & Logging Guide

## Overview

The Lulu Spendlyzer application implements an intelligent error handling system that provides a clean user experience while maintaining comprehensive debugging capabilities. This guide explains how the system works and how to use it effectively.

## Error Classification

### User-Facing Errors (Shown to Users)
These errors are displayed to users because they can take action to resolve them:

- **Input Validation Errors**: Invalid email format, password requirements not met
- **Authentication Failures**: Wrong credentials, expired tokens, insufficient permissions
- **Business Logic Errors**: Invalid operations, data conflicts, business rule violations
- **Network Issues**: Connection problems that users can retry

### System Errors (Logged Only)
These errors are logged for debugging but not shown to users:

- **Backend Operation Failures**: Database errors, service failures, internal exceptions
- **External API Failures**: Plaid API errors, email service failures, third-party service issues
- **Infrastructure Issues**: Timeouts, connection drops, server errors
- **Database Issues**: Constraint violations, connection problems, query failures
- **Session Management**: Token validation failures, session cleanup errors

## Implementation

### Frontend Implementation

#### Notification Service Enhancement

The notification service has been enhanced to support system error logging:

```typescript
// Enhanced Notification Interface
interface Notification {
  id: string;
  title: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
  isRead: boolean;
  createdAt: Date;
  actionUrl?: string;
  isSystem?: boolean; // New property to distinguish system notifications
}
```

#### System Error Logging Method

```typescript
// New method for logging system errors
logSystemError(title: string, message: string, error?: any): void {
  // Log to console for immediate debugging
  console.error(`System Error - ${title}:`, message, error);
  
  // Create system notification (not shown to users)
  const systemNotification: Notification = {
    id: this.generateId(),
    title,
    message,
    type: 'error',
    isRead: true, // Mark as read so it doesn't show in unread count
    createdAt: new Date(),
    isSystem: true // Mark as system notification
  };
  
  // Add to notifications but filter from UI
  const currentNotifications = this.notificationsSubject.value;
  this.notificationsSubject.next([systemNotification, ...currentNotifications]);
}
```

#### UI Filtering

The dashboard component filters out system notifications from the UI:

```typescript
private loadNotifications(): void {
  this.notificationService.getNotifications().subscribe(notifications => {
    // Filter out system notifications from the UI
    this.notifications = notifications.filter(notification => !notification.isSystem);
  });
}
```

### Usage Examples

#### Logging System Errors

Instead of showing error notifications to users, log them:

```typescript
// Before (shows error to user)
this.notificationService.addNotification({
  title: 'Password Reset Failed',
  message: 'Failed to send password reset email. Please try again.',
  type: 'error',
  isRead: false
});

// After (logs for debugging only)
this.notificationService.logSystemError('Password Reset Failed', 'Failed to send password reset email', error);
```

#### Showing User Errors

Continue showing user-facing errors normally:

```typescript
// User validation error (show to user)
this.notificationService.addNotification({
  title: 'Invalid Email',
  message: 'Please enter a valid email address.',
  type: 'error',
  isRead: false
});
```

## Error Types Handled

### System Errors (Logged, Not Shown)
- Password reset email failures
- Email address update failures
- Session logout failures
- Two-factor authentication setup/disable failures
- Settings update failures
- Account conversion failures
- Invitation send/resend/cancel failures
- Family member removal failures
- Database operation failures
- External API failures

### User Errors (Shown to Users)
- Invalid email format
- Password requirements not met
- Authentication failures
- Permission denied errors
- Business logic validation errors
- Network connectivity issues (with retry guidance)

## Debugging and Monitoring

### Console Logging
All system errors are logged to the browser console with structured information:

```
System Error - Password Reset Failed: Failed to send password reset email
Error: SMTP connection failed
    at EmailService.sendEmail (email.service.ts:45)
    at AccountSettingsService.sendPasswordResetEmail (account-settings.service.ts:123)
```

### System Notification Access
System notifications are stored and can be accessed for debugging:

```typescript
// Get system notifications (admin/debugging use)
this.notificationService.getSystemNotifications().subscribe(systemErrors => {
  console.log('System errors:', systemErrors);
});

// Clear system notifications
this.notificationService.clearSystemNotifications();
```

### Future Enhancements
- Backend database logging for persistent error tracking
- Error aggregation and analytics dashboard
- Automated alerting for critical system failures
- Integration with external monitoring services (Sentry, LogRocket, etc.)

## Best Practices

### When to Use logSystemError()
- Backend operation failures
- External service failures
- Database errors
- Network infrastructure issues
- Session management failures
- Any error that users cannot resolve

### When to Use addNotification()
- Input validation errors
- Authentication failures
- Business logic errors that users can fix
- Success messages
- Information messages
- Warning messages

### Error Message Guidelines
- **System Errors**: Technical details for debugging
- **User Errors**: Clear, actionable guidance
- **Success Messages**: Confirmation of completed actions
- **Info Messages**: Helpful information about features or status

## Configuration

### Environment Variables
No additional configuration is required for the error handling system. It works with the existing notification service configuration.

### Customization
To customize error handling behavior:

1. **Modify logSystemError()**: Add additional logging destinations
2. **Extend Notification Interface**: Add more properties for categorization
3. **Custom Filtering**: Implement custom logic for what constitutes a system error
4. **External Integration**: Add integration with external logging services

## Troubleshooting

### Common Issues

**System errors still showing in UI**
- Check that `isSystem: true` is set on the notification
- Verify that the dashboard component is filtering system notifications
- Ensure the notification service is properly configured

**Missing error logs**
- Check browser console for console.error messages
- Verify that logSystemError() is being called
- Check that error objects are being passed correctly

**User errors not showing**
- Verify that addNotification() is being used (not logSystemError())
- Check that isSystem is not set to true
- Ensure the notification service is properly injected

### Debug Commands

```typescript
// Check all notifications (including system ones)
this.notificationService.getNotifications().subscribe(all => {
  console.log('All notifications:', all);
});

// Check only system notifications
this.notificationService.getSystemNotifications().subscribe(system => {
  console.log('System notifications:', system);
});

// Check unread count (should exclude system notifications)
this.notificationService.getUnreadCount().subscribe(count => {
  console.log('Unread count:', count);
});
```

## Conclusion

This error handling system provides a balance between user experience and debugging capabilities. Users see only relevant, actionable error messages while developers have comprehensive logging for troubleshooting and system monitoring.

The system is designed to be extensible, allowing for future enhancements such as backend logging, error analytics, and integration with external monitoring services. 