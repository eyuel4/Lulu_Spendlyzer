# SAAS Framework Prompts

A comprehensive collection of reusable prompts for building SAAS applications with authentication, social login, password reset, theme system, notifications, and user management.

## Table of Contents

1. [FastAPI Authentication Backend Foundation](#fastapi-authentication-backend-foundation)
2. [Angular Authentication Service](#angular-authentication-service)
3. [Google OAuth Integration](#google-oauth-integration)
4. [Password Reset System](#password-reset-system)
5. [Theme System](#theme-system)
6. [Header Component with User Menu](#header-component-with-user-menu)
7. [Notification System](#notification-system)
8. [Database and Email Setup](#database-and-email-setup)

---

## FastAPI Authentication Backend Foundation

### Database Models Setup
```
Create a FastAPI authentication system with SQLAlchemy models. Start by creating the User model with these exact fields: id (primary key), first_name, last_name, username (unique), email (unique), password_hash, is_primary (boolean), family_group_id (foreign key, nullable), auth_provider (string), provider_id (string, nullable), is_verified (boolean), created_at (datetime). 

Also create a UserPreferences model with user_id (foreign key), account_type, primary_goal (JSON), financial_focus (JSON), experience_level, created_at, updated_at.

Use declarative base pattern and include proper imports for SQLAlchemy, datetime, and timezone handling.
```

### Authentication Routes with JWT
```
Implement FastAPI authentication routes in app/routes/auth.py. Create these endpoints:

1. POST /auth/signup - Accept UserCreate schema, check for existing username/email, hash password with bcrypt, create user, return JWT token
2. POST /auth/signin - Accept login (username or email) and password, verify credentials, return JWT token  
3. GET /auth/me - Extract token from Authorization header, decode JWT, return current user data

Use passlib for password hashing, PyJWT for token creation, and proper error handling with HTTPException. Set JWT_SECRET from environment variables and 60-minute token expiration.
```

---

## Angular Authentication Service

### Auth Service Implementation
```
Create an Angular authentication service (src/app/services/auth.service.ts) with these features:

1. User interface with id, username, email, first_name, last_name, is_primary, family_group_id, created_at
2. BehaviorSubject for current user management
3. Methods: signup(), signin(), logout(), getToken(), fetchCurrentUser()
4. JWT token storage in localStorage
5. HTTP headers with Authorization Bearer token
6. Error handling for 401 responses with auto-logout
7. User data persistence and loading from localStorage

Use HttpClient for API calls, RxJS observables, and proper TypeScript interfaces.
```

### HTTP Interceptor Setup
```
Create an Angular HTTP interceptor (src/app/interceptors/auth.interceptor.ts) that:

1. Injects AuthService and Router
2. Adds Authorization header with Bearer token to all requests
3. Catches 401 errors and automatically logs out user
4. Redirects to signin page on authentication failures
5. Uses proper error handling with throwError

Register the interceptor in app.config.ts with provideHttpClient and withInterceptors.
```

---

## Google OAuth Integration

### Backend OAuth Setup
```
Implement Google OAuth2 in FastAPI auth routes:

1. Add /auth/google/login endpoint that redirects to Google OAuth
2. Add /auth/google/callback endpoint that handles OAuth response
3. Extract user info from Google token (email, name, given_name, family_name, sub)
4. Check if user exists by email, if not create new user with auth_provider='google'
5. Set provider_id to Google user ID and is_verified=True
6. Generate JWT token and redirect to frontend with token in URL
7. Handle existing user login with Google

Use authlib for OAuth integration and proper error handling for token parsing failures.
```

### Frontend OAuth Handling
```
Create Angular social login component that:

1. Extracts token from URL query parameters
2. Stores token in localStorage
3. Fetches current user data
4. Handles new vs existing user flows
5. Shows loading states during authentication
6. Redirects to dashboard or questionnaire based on user status
7. Provides error handling for failed OAuth attempts

Use ActivatedRoute for URL parameter extraction and proper navigation handling.
```

---

## Password Reset System

### Backend Password Reset
```
Add password reset functionality to FastAPI auth routes:

1. POST /auth/forgot-password - Accept email, generate reset token, send email
2. POST /auth/reset-password - Accept token and new password, validate and update
3. Create reset token with 30-minute expiration
4. Use background tasks for email sending
5. Always return success message (security through obscurity)
6. Proper token validation and error handling

Use SMTP with Gmail, EmailMessage for email composition, and secrets for token generation.
```

### Frontend Password Reset
```
Create Angular password reset components:

1. Forgot password component with email form
2. Reset password component with token extraction from URL
3. Reactive forms with validation (required fields, password confirmation)
4. Success/error message handling
5. Loading states during API calls
6. Proper navigation after successful reset

Use ReactiveFormsModule, FormBuilder, and proper form validation patterns.
```

---

## Theme System

### Theme Service
```
Create Angular theme service (src/app/services/theme.service.ts) with:

1. Theme enum: 'light' | 'dark'
2. BehaviorSubject for current theme
3. localStorage persistence
4. System preference detection
5. Theme toggle method
6. Automatic initialization

Use platform detection for SSR compatibility and proper TypeScript typing.
```

### Theme Integration
```
Integrate theme system across components:

1. Add theme toggle button with sun/moon icons
2. Apply theme classes to root elements
3. Use Tailwind dark: variants for styling
4. Add smooth transitions (duration-200)
5. Ensure consistent color palette across components

Use ngClass for dynamic theme class application and proper CSS transitions.
```

---

## Header Component with User Menu

### Header Structure
```
Create Angular header component with:

1. Logo and app title
2. Theme toggle button with conditional icons
3. User avatar with initials (first letter of first and last name)
4. User name and email display
5. Responsive design (hidden on mobile)
6. Loading states for user data
7. Mobile menu toggle button

Use Tailwind CSS for responsive design and proper flexbox layout.
```

### User Dropdown Menu
```
Implement user dropdown functionality:

1. Clickable user name with dropdown arrow
2. Dropdown menu with items: Profile, Account & Settings, Billing & Subscription, Help & Support, Feature Tour, Request a Feature, Sign out
3. Click outside to close functionality using HostListener
4. Hover effects and smooth transitions
5. Proper z-index layering
6. Mobile responsive menu items
7. Icon integration for each menu item

Use relative/absolute positioning, event handling, and proper state management.
```

---

## Notification System

### Enhanced Notification Service
```
Create Angular notification service (src/app/services/notification.service.ts) with:

1. Notification interface: id, title, message, type, isRead, createdAt, actionUrl, isSystem
2. BehaviorSubject for notifications array
3. Unread count observable (excludes system notifications)
4. Methods: markAsRead(), markAllAsRead(), addNotification(), logSystemError()
5. Mock data for testing with different notification types
6. Proper TypeScript typing and error handling
7. System error logging without user-facing notifications

Use RxJS operators for data transformation and proper state management.
```

### System Error Handling
```
Implement intelligent error handling that distinguishes between:

1. User-facing errors: Show notifications for validation errors, auth failures, business logic errors
2. System errors: Log to console and store for debugging without showing to users

Key features:
- logSystemError() method for system-level error logging
- isSystem property to mark system notifications
- Filter system notifications from UI display
- Maintain comprehensive error logging for debugging
- Console logging for immediate debugging access

Error types handled:
- System errors (logged, not shown): Backend failures, network issues, database errors
- User errors (shown): Invalid input, authentication failures, business logic errors
```

### Notification UI
```
Create notification UI components:

1. Notification bell icon with badge showing unread count
2. Dropdown showing top 10 notifications
3. Color-coded notification types (blue=info, green=success, yellow=warning, red=error)
4. Read/unread visual indicators (background color and font weight)
5. "Mark all read" button when unread notifications exist
6. Click to mark individual notifications as read
7. Custom scrollbar styling for dark theme
8. Mobile responsive design

Use ngClass for conditional styling and proper event handling.
```

### Custom Scrollbar Styling
```
Add custom scrollbar styles for notification dropdown:

1. Thin scrollbar (6px width) for modern browsers
2. Light theme: slate gray colors matching the design
3. Dark theme: darker slate colors blending with background
4. Hover effects for better interactivity
5. Cross-browser support (Webkit and Firefox)
6. Transparent track for clean appearance

Use CSS scrollbar properties and proper color matching with Tailwind palette.
```

---

## Database and Email Setup

### Database Configuration
```
Set up SQLAlchemy database with:

1. Async database session management
2. Proper model relationships and foreign keys
3. Database initialization scripts
4. Migration handling
5. Connection pooling and error handling

Use async SQLAlchemy patterns and proper session lifecycle management.
```

### Email Configuration
```
Configure email system with:

1. SMTP settings for Gmail
2. Email templates for invitations and password reset
3. Background task processing
4. Error handling and logging
5. Environment variable configuration
6. Rate limiting considerations

Use proper email formatting and error handling for delivery failures.
```

---

## Implementation Strategy

### Phase 1: Foundation (Backend)
1. Database models and relationships
2. Basic authentication routes (signup, signin, me)
3. JWT token implementation
4. Database configuration

### Phase 2: Frontend Auth
1. Authentication service
2. HTTP interceptor
3. Signup/signin components
4. Route guards and navigation

### Phase 3: Advanced Auth
1. Google OAuth integration
2. Password reset system
3. Email functionality
4. Social login handling

### Phase 4: UI/UX
1. Theme system implementation
2. Header component with user menu
3. Notification system
4. Responsive design

### Phase 5: Polish
1. Error handling improvements
2. Loading states
3. Custom styling
4. Testing and validation

---

## Environment Variables Required

### Backend (.env)
```
JWT_SECRET=your-secret-key-here
EMAIL_FROM=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
DB_URL=sqlite:///./finance.db
```

### Frontend (environment.ts)
```typescript
export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000'
};
```

---

## Dependencies

### Backend (requirements.txt)
```
fastapi
uvicorn
sqlalchemy
asyncpg
passlib[bcrypt]
python-jose[cryptography]
python-multipart
authlib
emails
```

### Frontend (package.json)
```json
{
  "dependencies": {
    "@angular/core": "^17.0.0",
    "@angular/common": "^17.0.0",
    "@angular/router": "^17.0.0",
    "@angular/forms": "^17.0.0",
    "rxjs": "^7.8.0"
  }
}
```

---

## Notes

- All prompts are designed to work with Angular 17+ and FastAPI
- Use Tailwind CSS for styling consistency
- Implement proper error handling throughout
- Follow TypeScript best practices
- Use reactive forms for all user inputs
- Implement proper loading states
- Ensure mobile responsiveness
- Use proper security practices (JWT, password hashing, etc.)

---

*This framework provides a solid foundation for building SAAS applications with modern authentication, user management, and UI/UX patterns.* 