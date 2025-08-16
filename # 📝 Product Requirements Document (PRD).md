# 📝 Product Requirements Document (PRD)

**Project Name:** Lulu_Spendlyzer  
**Author:** Eyuel Taddese  
**Date:** June 18, 2025  
**Version:** 1.4

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

## ✅ Completed Features & Tasks

### Manual Transaction Management System
**Status:** ✅ **COMPLETED** (with mock data)

**Implemented Features:**
1. **AG Grid v33+ Integration**
   - ✅ Updated to AG Grid v33+ Theming API
   - ✅ Removed legacy CSS imports
   - ✅ Fixed dark theme compatibility
   - ✅ Added proper TypeScript typing with GridOptions

2. **Enhanced Transaction Grid**
   - ✅ Category column with icons and color coding
   - ✅ Bank Type column with bank icons
   - ✅ Cards column with card selection (including Cash option)
   - ✅ Subcategory dropdown (dependent on category selection)
   - ✅ Budget Type classification
   - ✅ Date, Amount, Description, Merchant fields
   - ✅ Actions column with delete functionality

3. **Data Models & Interfaces**
   - ✅ Category interface with icon, color, and background color
   - ✅ BankType interface with icon support
   - ✅ Card interface with bank association and last 4 digits
   - ✅ ManualTransaction interface with all required fields
   - ✅ BudgetType and Subcategory interfaces

4. **Mock Data Implementation**
   - ✅ 6 categories with icons and colors (Food & Dining, Transportation, Shopping, Entertainment, Healthcare, Utilities)
   - ✅ 15 subcategories mapped to categories
   - ✅ 4 budget types (Essential, Discretionary, Investment, Emergency)
   - ✅ 5 bank types (Chase, Bank of America, Wells Fargo, Citibank, Cash)
   - ✅ 5 sample cards with bank associations

5. **UI/UX Features**
   - ✅ Dark theme support with proper AG Grid styling
   - ✅ Responsive modal design
   - ✅ Add/Delete row functionality
   - ✅ Form validation and data filtering
   - ✅ Professional styling with Tailwind CSS
   - ✅ Accessibility features and keyboard navigation

6. **Technical Implementation**
   - ✅ Theme service integration for dark/light mode
   - ✅ Grid event handling and data management
   - ✅ Cell editors for different data types
   - ✅ Custom cell renderers for icons and formatting
   - ✅ Data validation and error handling

**Files Modified:**
- `spendlyzer-frontend/src/app/pages/manual-transaction-modal/manual-transaction-modal.component.ts`
- `spendlyzer-frontend/src/app/pages/manual-transaction-modal/manual-transaction-modal.component.html`
- `spendlyzer-frontend/src/app/pages/manual-transaction-modal/manual-transaction-modal.component.scss`
- `spendlyzer-frontend/src/styles.scss`
- `spendlyzer-frontend/src/app/pages/dashboard/dashboard.component.ts`
- `spendlyzer-frontend/src/app/pages/dashboard/dashboard.component.html`

---

## 🔄 Pending Features & Tasks

### Manual Transaction Management System
**Status:** 🔄 **PENDING**

**Remaining Tasks:**
1. **Backend Integration**
   - 🔄 Create FastAPI endpoints for transaction CRUD operations
   - 🔄 Implement transaction service with database operations
   - 🔄 Add validation and business logic
   - 🔄 Connect frontend to backend APIs

2. **Data Persistence**
   - 🔄 Database schema for transactions, categories, bank types, cards
   - 🔄 SQLAlchemy models for all entities
   - 🔄 Migration scripts for new tables and relationships

3. **Real Data Sources**
   - 🔄 Replace mock data with database queries
   - 🔄 Implement category management service
   - 🔄 Add bank type and card management
   - 🔄 User-specific data filtering

4. **Enhanced Features**
   - 🔄 Bulk import/export functionality
   - 🔄 Transaction templates
   - 🔄 Recurring transaction setup
   - 🔄 Transaction search and filtering
   - 🔄 Transaction history and audit trail

5. **Integration Features**
   - 🔄 Connect with existing dashboard
   - 🔄 Update transaction reports and analytics
   - 🔄 Family account support for shared transactions
   - 🔄 Notification system for transaction alerts

6. **Advanced Functionality**
   - 🔄 Transaction categorization AI/ML
   - 🔄 Duplicate transaction detection
   - 🔄 Transaction reconciliation
   - 🔄 Budget tracking and alerts
   - 🔄 Financial goal tracking

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
| **Data Grid** | **AG Grid v33+ (Theming API)** |

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

### `Transaction` (New - Pending Implementation)

```python
id: int (PK)
user_id: int (FK → User.id)
date: datetime
amount: decimal
description: str
merchant: str
category_id: int (FK → Category.id)
subcategory_id: int (nullable FK → Subcategory.id)
budget_type_id: int (nullable FK → BudgetType.id)
bank_type_id: int (nullable FK → BankType.id)
card_id: int (nullable FK → Card.id)
created_at: datetime
updated_at: datetime
```

### `Category` (New - Pending Implementation)

```python
id: int (PK)
name: str
icon: str
color: str
bg_color: str
user_id: int (nullable FK → User.id)  # null for system categories
family_group_id: int (nullable FK → FamilyGroup.id)
created_at: datetime
```

### `BankType` (New - Pending Implementation)

```python
id: int (PK)
name: str
icon: str
user_id: int (FK → User.id)
created_at: datetime
```

### `Card` (New - Pending Implementation)

```python
id: int (PK)
name: str
bank_type_id: int (FK → BankType.id)
last_four_digits: str
user_id: int (FK → User.id)
is_active: bool
created_at: datetime
```

---

## 🔐 Feature Implementation Prompts

### Manual Transaction Management System

**Prompt:** "Implement a comprehensive manual transaction management system with the following requirements:

1. **Frontend AG Grid Integration**:
   - Use AG Grid v33+ with Theming API (no legacy CSS)
   - Support dark/light theme switching
   - Implement editable cells with proper validation
   - Add custom cell renderers for icons and formatting
   - Support bulk operations (add, edit, delete rows)

2. **Transaction Data Model**:
   - Date, amount, description, merchant fields
   - Category and subcategory selection with icons
   - Bank type and card selection (including Cash option)
   - Budget type classification
   - User and family group associations

3. **Backend API Endpoints**:
   - CRUD operations for transactions
   - Category, bank type, and card management
   - Bulk transaction import/export
   - Transaction validation and business rules
   - Family account support for shared transactions

4. **Database Schema**:
   - Transaction table with all required fields
   - Category, BankType, Card, BudgetType tables
   - Proper foreign key relationships
   - Indexes for performance optimization
   - Audit trail for transaction changes

5. **Advanced Features**:
   - Transaction templates and recurring transactions
   - Duplicate detection and reconciliation
   - AI-powered categorization
   - Budget tracking and alerts
   - Transaction search and filtering

**Technical Requirements:**
- Frontend: Angular components with AG Grid integration
- Backend: FastAPI with SQLAlchemy ORM
- Database: SQLite with proper schema design
- Authentication: User-specific data access
- Performance: Efficient queries and caching

**Success Criteria:**
- Users can add/edit/delete transactions in a spreadsheet-like interface
- All transaction data is properly categorized and stored
- System supports both individual and family accounts
- Performance is optimized for large transaction datasets
- UI is responsive and accessible across devices"

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

---

## 📊 Project Status Summary

| Feature Area | Status | Progress | Notes |
|--------------|--------|----------|-------|
| **Manual Transaction Management** | 🔄 In Progress | 60% | Frontend complete with mock data, backend pending |
| **AG Grid Integration** | ✅ Complete | 100% | v33+ Theming API implemented |
| **Dark Theme Support** | ✅ Complete | 100% | Full dark mode compatibility |
| **Data Models (Frontend)** | ✅ Complete | 100% | All interfaces and mock data implemented |
| **Backend API** | 🔄 Pending | 0% | Need to implement transaction endpoints |
| **Database Schema** | 🔄 Pending | 0% | Need to create transaction tables |
| **Two-Factor Authentication** | 🔄 Pending | 0% | Not started |
| **Account Settings** | 🔄 Pending | 0% | Not started |
| **Trusted Device Management** | 🔄 Pending | 0% | Not started |
| **Email Integration** | 🔄 Pending | 0% | Not started |

**Next Priority:** Implement backend API and database schema for manual transaction management system.
