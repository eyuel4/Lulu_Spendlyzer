# 📝 Product Requirements Document (PRD)

**Project Name:** Lulu_Spendlyzer  
**Author:** Eyuel Taddese  
**Date:** June 18, 2025  
**Version:** 1.3

---

## 📌 Project Overview

**Spendlyzer** is a personal finance dashboard and automation app that:
- Connects to multiple banks using **Plaid**
- Pulls transactions per card and per month
- Categorizes spending using both **Plaid categories** and **custom categories**
- Generates monthly reports with insights
- Supports **individual** and **family/group** accounts
- Runs fully on **localhost** using Angular + FastAPI + SQLite (or MySQL)

---

## ⚙️ Technology Stack

| Layer       | Stack                      |
|-------------|----------------------------|
| Frontend    | Angular 17+                |
| Backend     | Python 3.10+ with FastAPI  |
| API Client  | Plaid Python SDK           |
| Database    | SQLite (or optional MySQL) |
| ORM         | SQLAlchemy (async)         |
| Email (optional)| SMTP (for invite flows)|
| Deployment  | Localhost only             |

---

## 👥 User Account Modes

### 1. Individual Account
- Single user, links multiple banks/cards
- Sees only their own transactions and reports

### 2. Family/Group Account
- Primary account owner
- Can invite additional members (spouse, partner, children)
- All users share a **FamilyGroup**
- Each user may link their own bank accounts
- Shared view of total household spending

---

## 🗃️ Data Model (SQLAlchemy ORM)

### `User`

```python
id: int (PK)
first_name: str
last_name: str
email: str
password_hash: str
is_primary: bool  # True if the main account holder
family_group_id: int (nullable FK → FamilyGroup.id)
created_at: datetime
```

---

## 🔐 Feature Implementation Prompts

### Two-Factor Authentication (2FA) System

**Prompt:** "Implement a comprehensive two-factor authentication system with the following requirements:

1. **Multiple 2FA Methods**: Support Authenticator App (TOTP), SMS, and Email verification
2. **Code Expiration**: SMS and Email codes expire after 10 minutes
3. **Conditional UI**: Hide resend button for Authenticator App, show for SMS/Email
4. **Pre-Enablement Verification**: For SMS/Email 2FA, require code verification before enabling
5. **Dynamic Method Display**: UI should show correct method (SMS/Email/Authenticator) based on user's setup
6. **Security Best Practices**: 
   - Don't log sensitive codes
   - Use actual email sending for verification
   - Store temporary codes in database with expiration
   - Clear codes after verification attempts

**Technical Requirements:**
- Frontend: Angular components for 2FA setup and verification
- Backend: FastAPI endpoints for code sending, verification, and 2FA management
- Database: Add temp_code and temp_code_expires_at fields to TwoFactorAuth model
- Email Integration: Reuse existing SMTP configuration for 2FA emails
- Token Management: Handle temporary tokens for 2FA flow vs regular JWT tokens

**User Flow:**
1. User enables 2FA in account settings
2. For SMS/Email: Send verification code → User enters code → Enable 2FA
3. For Authenticator: Generate QR code → User scans → Enable 2FA
4. During login: User enters 2FA code → Complete authentication"

### Account Settings & User Preferences

**Prompt:** "Implement a comprehensive account settings system with the following features:

1. **Security Settings**:
   - Password reset (disabled for social login users)
   - Email change functionality
   - Two-factor authentication management
   - Active session management

2. **Notification Preferences**:
   - Email notifications toggle
   - Push notifications toggle
   - Transaction alerts
   - Budget alerts
   - Family updates
   - Marketing emails

3. **Privacy Settings**:
   - Profile visibility (private/family/public)
   - Data sharing preferences
   - Analytics sharing
   - Family access permissions

4. **Family Management**:
   - Convert personal account to family account
   - Invite family members
   - Manage family member roles
   - View pending invitations
   - Remove family members

**Technical Requirements:**
- Frontend: Angular components with tabbed interface (Security, Notifications, Family, Privacy)
- Backend: FastAPI endpoints for all settings management
- Database: User preferences and notification settings storage
- Authentication: Proper authorization for all settings endpoints
- Social Login Integration: Detect and handle Google OAuth users appropriately

**UI/UX Requirements:**
- Modern, accessible design with dark mode support
- Form validation and error handling
- Success/error notifications
- Loading states and optimistic updates
- Responsive design for mobile and desktop"

### Database Schema Management

**Prompt:** "Implement database schema management with the following requirements:

1. **No Migration Scripts**: Handle all database changes directly in core files
2. **Automatic Schema Updates**: Use SQLAlchemy's declarative base for automatic schema updates
3. **Schema Location**: All schema changes go in `/app/core/init_db.py` and `database.py`
4. **Field Management**: Support adding columns, renaming columns, and adding tables
5. **Data Integrity**: Ensure existing data is preserved during schema updates

**Technical Requirements:**
- Use SQLAlchemy's create_all() for automatic schema generation
- Handle new fields with proper defaults and nullable settings
- Support both SQLite and MySQL databases
- Maintain backward compatibility where possible
- Document schema changes in code comments"

### Email Integration for User Flows

**Prompt:** "Implement email integration for user authentication and notification flows:

1. **Email Configuration**: SMTP setup with Gmail or other providers
2. **Email Templates**: Professional HTML and text templates
3. **Email Flows**:
   - User invitations for family accounts
   - Password reset emails
   - Two-factor authentication codes
   - Account verification emails
4. **Security**: Don't log sensitive information in email content
5. **Error Handling**: Graceful fallbacks when email sending fails

**Technical Requirements:**
- Reusable email service with template system
- Environment variable configuration for SMTP settings
- Rate limiting for email sending
- Email queue system for reliability
- HTML and text email support
- Email tracking and delivery confirmation"

### Enhanced Trusted Device Management for Financial App

**Prompt:** "Implement a comprehensive "Remember Device" system for a personal finance application that handles sensitive financial data, bank connections, and transaction uploads. The system must balance security with user convenience while meeting financial industry security standards.

**Requirements:**

1. **Database Schema & Models**:
   - Create TrustedDevice model with fields: id, user_id, device_hash, token_hash, created_at, expires_at, last_used_at, user_agent, ip_address, location, is_active
   - Add trusted_device_id field to UserSession model for tracking
   - Implement automatic cleanup of expired trusted device records

2. **Backend API Endpoints**:
   - POST /auth/trust-device - Create trusted device token after successful 2FA
   - DELETE /auth/trust-device/{device_id} - Revoke specific trusted device
   - GET /auth/trusted-devices - List user's trusted devices
   - POST /auth/verify-trusted-device - Validate trusted device token
   - Modify existing login endpoints to check for valid trusted devices

3. **Device Fingerprinting**:
   - Implement device fingerprinting using: browser, OS, screen resolution, timezone, language, plugins
   - Create unique device hash from fingerprint data
   - Validate device fingerprint on each request with trusted token
   - Store fingerprint data securely (hashed)

4. **Security Features**:
   - Generate cryptographically secure random tokens (32+ characters)
   - Hash tokens before database storage
   - Implement 7-day expiration for trusted devices
   - Add geographic restrictions (block new countries/regions)
   - Implement IP change monitoring and alerts
   - Add rate limiting for trusted device operations

5. **Risk-Based Authentication**:
   - Skip 2FA for: same device + same location + recent activity (< 24 hours)
   - Require 2FA for: new device, new location, unusual transaction patterns
   - Enhanced verification for: bank account connections, large transactions, account changes
   - Implement suspicious activity detection

6. **Frontend Components**:
   - Add "Remember this device" checkbox on 2FA verification screen
   - Create trusted devices management page in account settings
   - Display device list with: device name, location, last used, actions (revoke)
   - Add security notifications for suspicious activity

7. **Audit & Monitoring**:
   - Log all trusted device operations (create, use, revoke)
   - Track device usage patterns and locations
   - Implement fraud detection for unusual patterns
   - Add admin dashboard for security monitoring

8. **User Experience**:
   - Clear messaging about security implications
   - Graceful handling of expired/invalid trusted devices
   - Emergency access recovery options
   - Security education tooltips and help content

9. **Compliance & Best Practices**:
   - Ensure compliance with financial data protection regulations
   - Implement comprehensive audit trails
   - Add data encryption for sensitive device information
   - Provide user controls for privacy and security preferences

10. **Testing & Validation**:
    - Unit tests for all trusted device operations
    - Integration tests for device fingerprinting
    - Security testing for token generation and validation
    - Performance testing for device validation overhead

**Technical Specifications:**
- Use secure HTTP-only cookies for trusted device tokens
- Implement proper CSRF protection
- Add comprehensive error handling and logging
- Ensure mobile responsiveness for device management UI
- Follow OWASP security guidelines for implementation

**Success Criteria:**
- Users can opt to remember devices for 7 days
- System maintains security while reducing 2FA friction
- Comprehensive audit trail of all device activities
- Users can manage and revoke trusted devices
- System detects and responds to suspicious activity
- Performance impact is minimal (< 100ms additional latency)"

---

## 🐛 Bug Fix Guidelines

**Note:** Bug fixes should focus on:
- Identifying root cause of issues
- Implementing targeted fixes
- Testing the specific functionality
- Not updating requirements document unless it's a feature enhancement

**Common Bug Fix Areas:**
- Authentication token handling
- API endpoint errors (400, 401, 422, 405)
- Frontend-backend data synchronization
- Database connection issues
- CORS and routing problems
