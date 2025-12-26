# Lulu Spendlyzer - Personal Finance App

## Quick Start

### Backend Setup
```bash
# Run the backend Python App
python -m uvicorn app.main:app --reload --port 8000

# Run in Debug Mode
python -m uvicorn app.main:app --reload --port 8000 --log-level debug

# Remove DB (if needed)
rm finance.db

# Create DB
python -m app.core.init_db

# Start Redis (for caching)
docker-compose up -d redis
```

### Frontend Setup
```bash
# Start the frontend
npm start
```

## Features Completed ✅

### Core Features
- **Redis Caching**: Implemented with Redis for improved performance
- **Family Signup**: Complete family/group account management
- **Invite-Signup**: Email-based invitation system for family members
- **Email System**: SMTP integration for notifications and invitations
- **Account & Settings**: Comprehensive user settings management
- **System Error Handling**: Smart error logging without user-facing notifications
- **Plaid Integration**: Connect bank accounts and automatically sync transactions

### Authentication & Security
- **JWT Authentication**: Secure token-based authentication
- **Google OAuth**: Social login integration
- **Password Reset**: Email-based password recovery
- **Two-Factor Authentication**: Enhanced security options
- **Session Management**: Active session tracking and management

### User Experience
- **Dark/Light Theme**: Toggleable theme system
- **Notification System**: User-friendly notification management
- **Responsive Design**: Mobile-first responsive UI
- **Loading States**: Proper loading indicators throughout
- **Bank Connections**: Secure Plaid integration for automatic transaction sync
- **Manual & Auto Sync**: Daily automatic sync + on-demand manual sync

### System Architecture
- **Database Logging**: System errors and audit events logged to database with async persistence
- **Comprehensive Audit Trail**: Full audit logging for user actions and system events
- **Frontend-Backend Integration**: Frontend errors automatically logged to backend database
- **Error Classification**: Distinguishes between user-facing and system errors
- **Database Schema**: Comprehensive SQLAlchemy models with logging tables
- **API Design**: RESTful FastAPI endpoints with logging endpoints

## System Error Handling & Logging

The application implements comprehensive error handling and logging that:

- **Database Persistence**: All system errors and audit events are logged to the database with async persistence
- **Frontend Integration**: Frontend errors are automatically sent to the backend for logging
- **Comprehensive Audit Trail**: User actions, system events, and security events are fully logged
- **Error Classification**: Distinguishes between user-facing errors and system errors
- **Hides Technical Details**: Users don't see confusing system error messages
- **Maintains Debugging**: Developers can access complete logs for troubleshooting

### Logging Features
- **System Logs**: Application errors, warnings, and info messages with full context
- **Audit Logs**: User actions, security events, and system changes with before/after data
- **Async Processing**: Background queue processing for high-performance logging
- **Rich Metadata**: IP addresses, user agents, session IDs, and request tracing
- **Filtering & Search**: API endpoints for querying logs with various filters

### Error Types Handled
- **System Errors** (logged to DB, not shown to users): Backend failures, network issues, database errors
- **User Errors** (shown to users): Validation errors, authentication failures, business logic errors
- **Audit Events** (logged to DB): Login/logout, data changes, security events, user actions

## ToDo 🚧
- [x] Fix DB Init issue after DB log have been implemented.
- [x] Validate system level logs are saved in DB.
- [x] **Plaid Integration**: Connect banks and sync transactions automatically
- [] Show pending invitation status on dashboard
- [ ] Allow users to switch from personal to family accounts
- [ ] Implement account visibility controls for family groups
- [ ] Refactor dashboard with monthly/yearly analysis graphs
- [ ] Add comprehensive transaction categorization
- [ ] Implement budget tracking and alerts
- [ ] Add export functionality for reports
- [ ] Implement data backup and recovery

## Technology Stack

- **Frontend**: Angular 17+, TypeScript, Tailwind CSS
- **Backend**: FastAPI, Python 3.10+, SQLAlchemy
- **Database**: SQLite (development), MySQL (production ready)
- **Caching**: Redis
- **Authentication**: JWT, Google OAuth
- **Email**: SMTP (Gmail)
- **Bank Integration**: Plaid (Sandbox/Production)
- **Scheduling**: APScheduler (for background jobs)
- **Deployment**: Localhost (development ready)

## Plaid Integration 🏦

The app now supports secure bank account connections through Plaid:

- **Connect Banks**: Securely link bank accounts via Plaid Link
- **Auto Sync**: Automatic daily transaction sync at 2 AM
- **Manual Sync**: On-demand sync button for each connected bank
- **Manage Banks**: View, sync, and disconnect connected accounts
- **Deduplication**: Prevents duplicate transactions
- **Last 30 Days**: Syncs recent transactions on connection

### Quick Start with Plaid

1. **Get Plaid Credentials**: Sign up at https://dashboard.plaid.com/signup
2. **Configure**: Add credentials to `.env` file
3. **Setup**: See [PLAID_QUICK_START.md](PLAID_QUICK_START.md) for detailed instructions
4. **Test**: Use sandbox credentials (user_good/pass_good)

For complete implementation details, see [PLAID_INTEGRATION_COMPLETE.md](PLAID_INTEGRATION_COMPLETE.md)