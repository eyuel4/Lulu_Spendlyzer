# Manual Transaction Implementation Documentation

**Date**: October 11, 2025
**Status**: Backend Implementation Completed, Frontend Implementation Required
**Author**: Senior Software Engineer

---

## Overview

This document describes the complete implementation of the manual transaction functionality for the Spendlyzer personal finance application. The system allows users to manually enter individual transactions or bulk import transactions via CSV upload, with built-in duplicate detection and audit logging.

---

## Architecture Overview

### Database Models

All new models follow the existing SQLAlchemy/SQLite pattern with async support.

#### 1. **TransactionType** (`app/models/transaction_type.py`)
- **Purpose**: Defines transaction types (Income, Expense, Transfer, Cash, Check Withdrawn, Wire)
- **System-wide**: Yes, shared across all users
- **Fields**: name, description, icon, color, is_active
- **Table**: `transaction_types`

#### 2. **ExpenseCategory** (`app/models/expense_category.py`)
- **Purpose**: Main expense categories (Food & Dining, Transportation, Shopping, etc.)
- **System-wide**: Yes, shared across all users
- **Fields**: name, description, icon, color, bg_color, display_order, is_active
- **Table**: `expense_categories`

#### 3. **ExpenseSubcategory** (`app/models/expense_subcategory.py`)
- **Purpose**: Detailed subcategories under main categories (Groceries, Restaurants, Gas, etc.)
- **System-wide**: Yes, shared across all users
- **Fields**: name, expense_category_id, icon, is_active, display_order
- **Table**: `expense_subcategories`

#### 4. **PaymentMethod** (`app/models/payment_method.py`)
- **Purpose**: Payment methods (Credit Card, Debit Card, Cash, Check, Bank Transfer, Wire, Mobile Payment)
- **System-wide**: Yes, shared across all users
- **Fields**: name, description, icon, color, display_order, is_active
- **Table**: `payment_methods`

#### 5. **BudgetType** (`app/models/budget_type.py`)
- **Purpose**: Budget classifications (Essential, Discretionary, Investment, Emergency)
- **System-wide**: Yes, shared across all users
- **Fields**: name, description, icon, color, display_order, is_active
- **Table**: `budget_types`

#### 6. **BulkUpload** (`app/models/bulk_upload.py`)
- **Purpose**: Tracks bulk transaction uploads for audit trail
- **User-specific**: Yes, per user
- **Fields**: user_id, filename, total_rows, successful_count, failed_count, duplicate_count, status, error_message, metadata, timestamps
- **Table**: `bulk_uploads`
- **Status values**: PENDING, PROCESSING, COMPLETED, PARTIAL_FAILURE, PENDING_REVIEW

#### 7. **DuplicateTransaction** (`app/models/duplicate_transaction.py`)
- **Purpose**: Tracks potential duplicates identified during bulk uploads
- **User-specific**: Yes, per user
- **Fields**: bulk_upload_id, existing_transaction_id, date, amount, category, payment_method, card_id, description, merchant, similarity_score, matching_fields, user_action, user_notes
- **Table**: `duplicate_transactions`

#### 8. **TransactionUpload** (`app/models/transaction_upload.py`)
- **Purpose**: Links transactions to their source bulk upload for traceability
- **User-specific**: Yes, per user
- **Fields**: transaction_id, bulk_upload_id, row_number, csv_row_data
- **Table**: `transaction_uploads`

#### 9. **Transaction** (Enhanced)
- **Modified**: Added new fields to support manual transactions
- **New fields**:
  - `transaction_type_id`: Links to TransactionType
  - `expense_category_id`: Links to ExpenseCategory
  - `expense_subcategory_id`: Links to ExpenseSubcategory
  - `payment_method_id`: Links to PaymentMethod
  - `budget_type_id`: Links to BudgetType
  - `is_manual`: Boolean flag (true for manually entered)
  - `currency`: USD or CAD
  - `is_shared`: Visible to family group members
  - `notes`: Additional notes
  - `plaid_transaction_id`: Made nullable for manual transactions
- **New indexes**:
  - `idx_transaction_user_date`
  - `idx_transaction_user_month`
  - `idx_transaction_is_manual_user`
  - `idx_transaction_is_shared_user`

---

## Database Schema Changes

### Migration Script

Run the following to initialize all tables and metadata:

```bash
python scripts/init_transaction_metadata.py
```

This script:
1. Creates all new tables
2. Inserts 6 transaction types
3. Inserts 11 expense categories
4. Inserts 51 expense subcategories
5. Inserts 7 payment methods
6. Inserts 4 budget types

All operations are idempotent - safe to run multiple times.

---

## API Schemas

Located in `app/schemas/manual_transaction.py`

### Request Schemas

#### `ManualTransactionCreate`
```json
{
  "date": "2025-10-15",
  "amount": 45.99,
  "currency": "USD",
  "description": "Groceries",
  "merchant": "Whole Foods",
  "notes": "Weekly grocery run",
  "transaction_type_id": 1,
  "expense_category_id": 1,
  "expense_subcategory_id": 1,
  "payment_method_id": 1,
  "budget_type_id": 1,
  "card_id": 1,
  "is_shared": false
}
```

**Validations**:
- Date cannot be in the future
- Date cannot be more than 2 years old
- Amount must be positive
- Currency must be USD or CAD

#### `BulkTransactionCreateRequest`
```json
{
  "transactions": [ /* array of ManualTransactionCreate */ ],
  "filename": "transactions.csv",
  "allow_duplicates": false
}
```

**Constraints**:
- Max 1000 transactions per request
- Min 1 transaction per request

### Response Schemas

#### `ManualTransactionResponse`
Includes all fields from request plus:
- `id`: Transaction ID
- `user_id`: User ID
- `month_id`: Auto-calculated from date
- `is_manual`: Always true
- `created_at`: Timestamp
- `updated_at`: Timestamp
- Relationship data for categories, payment methods, etc.

#### `BulkUploadResponse`
```json
{
  "bulk_upload_id": 123,
  "total_rows": 50,
  "successful_count": 48,
  "failed_count": 1,
  "duplicate_count": 1,
  "status": "PENDING_REVIEW",
  "created_transactions": [ /* array */ ],
  "failed_rows": [
    {
      "row": 15,
      "error": "Invalid card ID"
    }
  ]
}
```

---

## API Endpoints

All endpoints require JWT authentication via `Authorization: Bearer <token>` header.

### Manual Transaction Endpoints

**Base Path**: `/transactions/manual`

#### 1. Create Single Transaction
```
POST /transactions/manual
Content-Type: application/json

{ManualTransactionCreate}
```

**Response**: `ManualTransactionResponse` (201 Created)

**Errors**:
- 401: Unauthorized
- 422: Validation error (invalid date, amount, etc.)
- 400: Server error

**Audit Log**: CREATE event for resource_type=TRANSACTION

---

#### 2. Bulk Create Transactions
```
POST /transactions/manual/bulk
Content-Type: application/json

{BulkTransactionCreateRequest}
```

**Response**: `BulkUploadResponse` (201 Created)

**Duplicate Handling**:
- Duplicates are identified by: same date, same card, same amount (±$0.01), same category
- If `allow_duplicates=false` and duplicates found, status = PENDING_REVIEW
- Duplicates flagged for user confirmation

**Audit Log**: BULK_CREATE event with counts

---

#### 3. Update Transaction
```
PUT /transactions/manual/{transaction_id}
Content-Type: application/json

{ManualTransactionUpdate}  // All fields optional
```

**Response**: `ManualTransactionResponse` (200 OK)

**Errors**:
- 401: Unauthorized
- 404: Transaction not found
- 400: Server error

**Audit Log**: UPDATE event with before/after changes

---

#### 4. Delete Transaction
```
DELETE /transactions/manual/{transaction_id}
```

**Response**:
```json
{
  "message": "Transaction deleted successfully"
}
```

**Errors**:
- 401: Unauthorized
- 404: Transaction not found
- 400: Server error

**Audit Log**: DELETE event

---

#### 5. Get Transaction Metadata
```
GET /transactions/manual/metadata
```

**Response**: `TransactionMetadataResponse` (200 OK)

**Caching**: Results cached for 1 hour via Redis

**Response Structure**:
```json
{
  "transaction_types": [ /* with id, name, icon, color */ ],
  "expense_categories": [ /* with id, name, icon, color, bg_color */ ],
  "payment_methods": [ /* with id, name, icon, color */ ],
  "budget_types": [ /* with id, name, description, icon, color */ ]
}
```

---

#### 6. Get Bulk Upload Status
```
GET /transactions/manual/bulk/{bulk_upload_id}
```

**Response**:
```json
{
  "bulk_upload_id": 123,
  "filename": "transactions.csv",
  "total_rows": 50,
  "successful_count": 48,
  "failed_count": 1,
  "duplicate_count": 1,
  "status": "PENDING_REVIEW",
  "uploaded_at": "2025-10-11T15:30:00Z",
  "processed_at": "2025-10-11T15:31:00Z"
}
```

---

#### 7. Confirm Duplicate Handling
```
POST /transactions/manual/duplicates/confirm
Content-Type: application/json

{
  "duplicate_transaction_ids": [15, 16, 17],
  "action": "ACCEPT",
  "user_notes": "These are legitimate purchases"
}
```

**Response**:
```json
{
  "status": "confirmed",
  "action": "ACCEPT",
  "duplicates_processed": 3
}
```

---

## Service Layer

Located in `app/services/manual_transaction_service.py`

### ManualTransactionService Class

#### Methods

1. **`create_manual_transaction()`**
   - Creates a single transaction
   - Auto-calculates month_id from date
   - Generates unique plaid_transaction_id for manual transactions
   - Logs audit event
   - Invalidates Redis caches

2. **`create_bulk_transactions()`**
   - Processes array of transactions
   - Performs duplicate detection for each transaction
   - Handles failures gracefully (partial success)
   - Creates bulk upload record for tracking
   - Links transactions to bulk upload via TransactionUpload model
   - Returns detailed report with counts and any failures
   - Supports skipping duplicate checks with `allow_duplicates=true`

3. **`_find_duplicates()`**
   - Identifies potential duplicates by:
     - Same user
     - Same card
     - Same transaction date
     - Same amount (±$0.01 variance)
     - Same expense category (if provided)
   - Returns list of matching transactions

4. **`update_transaction()`**
   - Updates specified fields only
   - Tracks changes for audit log
   - Invalidates caches
   - User ownership validation

5. **`delete_transaction()`**
   - Deletes transaction and related TransactionUpload records
   - Logs audit event
   - Invalidates caches
   - User ownership validation

6. **`get_bulk_upload_status()`**
   - Retrieves bulk upload record with related data
   - User ownership validation

---

## Audit Logging

All transaction operations are logged via `logging_service.audit_log()`:

### Logged Events

| Event | Resource | Action |
|-------|----------|--------|
| CREATE | TRANSACTION | Create manual transaction |
| UPDATE | TRANSACTION | Update transaction with field changes |
| DELETE | TRANSACTION | Delete transaction |
| BULK_CREATE | TRANSACTION | Bulk upload with success/failure counts |

### Audit Log Fields

- `event_type`: CREATE, UPDATE, DELETE, BULK_CREATE
- `resource_type`: TRANSACTION
- `resource_id`: Transaction ID
- `user_id`: User performing action
- `action`: Human-readable description
- `is_successful`: SUCCESS, FAILURE, PARTIAL
- `changes`: Before/after for updates
- `meta`: Additional metadata (bulk upload counts, etc.)
- `created_at`: Timestamp

---

## Redis Caching

### Cached Items

1. **Transaction Metadata** (1 hour expiry)
   - Cache key: `transaction_metadata:all`
   - Contents: All transaction types, categories, subcategories, payment methods, budget types

2. **Transaction Lookups** (automatically invalidated)
   - Cache key: `transactions:{user_id}:*`
   - Pattern: Invalidated on any user transaction change

3. **Summary Caches** (automatically invalidated)
   - Cache key: `transaction_summary:{user_id}:*`
   - Pattern: Invalidated on any user transaction change

---

## Data Validation Rules

### Date Validation
- ✓ Cannot be in the future
- ✓ Cannot be more than 2 years in the past
- ✓ Format: YYYY-MM-DD

### Amount Validation
- ✓ Must be positive (> 0)
- ✓ Variance for duplicates: ±$0.01

### Currency Validation
- ✓ USD or CAD only

### Card Validation
- ✓ Must exist and belong to user

### Duplicate Threshold
- ✓ Similarity score: 85% match
- ✓ Matching on: date, amount, category, card

---

## Error Handling

### Validation Errors (422)
```json
{
  "detail": [
    {
      "loc": ["body", "date"],
      "msg": "Transaction date cannot be in the future",
      "type": "value_error"
    }
  ]
}
```

### Not Found Errors (404)
```json
{
  "detail": "Transaction not found"
}
```

### Server Errors (400)
```json
{
  "detail": "Failed to create transaction: [error description]"
}
```

---

## CSV Bulk Upload Format

**Expected CSV Columns** (order-independent):
```
date,amount,currency,description,merchant,transaction_type_id,expense_category_id,expense_subcategory_id,payment_method_id,budget_type_id,card_id,is_shared,notes
```

**Example CSV**:
```csv
date,description,amount,currency,merchant,transaction_type_id,expense_category_id,payment_method_id,card_id
2025-10-15,Whole Foods,45.99,USD,Whole Foods,1,1,1,1
2025-10-14,Gas,55.00,USD,Shell,1,2,1,1
2025-10-14,Amazon,120.00,USD,Amazon,1,3,1,2
```

**Constraints**:
- Max 1000 rows per upload
- Header row required
- All required fields must be present
- Invalid rows reported in failed_rows array

---

## Duplicate Detection Algorithm

### Process

1. **Extract Transaction Data**
   - Date, Amount, Category ID, Card ID

2. **Query Database**
   - Find existing transactions where:
     - user_id = current user
     - card_id = transaction card
     - date = transaction date
     - amount within ±$0.01
     - category_id = transaction category (if provided)

3. **Create Duplicate Record**
   - If match found, create DuplicateTransaction record
   - Calculate similarity_score (0-1, default 0.95 for high match)
   - Flag matching_fields

4. **Return to User**
   - If `allow_duplicates=false`, skip insertion
   - Add to duplicate_count in BulkUploadResponse
   - Set bulk_upload status = PENDING_REVIEW

5. **User Confirmation** (Future Implementation)
   - User reviews flagged duplicates via frontend
   - Can ACCEPT or REJECT each duplicate
   - Confirmed duplicates are inserted on ACCEPT

---

## Testing Requirements

### Unit Tests (Backend)

**ManualTransactionService Tests**:
- [ ] create_manual_transaction() - valid transaction
- [ ] create_manual_transaction() - invalid date (future)
- [ ] create_manual_transaction() - invalid date (too old)
- [ ] create_manual_transaction() - invalid card
- [ ] create_bulk_transactions() - valid bulk upload
- [ ] create_bulk_transactions() - with duplicates (allow_duplicates=false)
- [ ] create_bulk_transactions() - partial failure
- [ ] _find_duplicates() - finds exact match
- [ ] _find_duplicates() - amount variance ±$0.01
- [ ] update_transaction() - valid update
- [ ] update_transaction() - invalid transaction ID
- [ ] delete_transaction() - successful delete
- [ ] delete_transaction() - invalid transaction ID

**Schema Validation Tests**:
- [ ] ManualTransactionCreate - valid data
- [ ] ManualTransactionCreate - invalid date (future)
- [ ] ManualTransactionCreate - invalid currency
- [ ] ManualTransactionCreate - negative amount

**Route Tests**:
- [ ] POST /transactions/manual - 201 Created
- [ ] POST /transactions/manual/bulk - 201 Created
- [ ] PUT /transactions/manual/{id} - 200 OK
- [ ] DELETE /transactions/manual/{id} - 200 OK
- [ ] GET /transactions/manual/metadata - 200 OK with cached data
- [ ] GET /transactions/manual/bulk/{id} - 200 OK
- [ ] POST /transactions/manual/duplicates/confirm - 200 OK

**Authentication Tests**:
- [ ] Missing Authorization header - 401
- [ ] Invalid token - 401
- [ ] Expired token - 401
- [ ] Different user accessing transaction - 404

### Integration Tests

- [ ] Create transaction → Verify in database
- [ ] Bulk upload → Verify all transactions created
- [ ] Bulk upload with duplicates → Verify flagged for review
- [ ] Update transaction → Verify audit log created
- [ ] Delete transaction → Verify removed + related records cleaned up
- [ ] Metadata cache → Verify cached after first request

---

## Frontend Implementation (Next Phase)

### Components Needed

1. **TransactionService** (Angular Service)
   - Methods for CRUD operations
   - Metadata fetching with caching
   - CSV parsing and bulk upload

2. **ManualTransactionModalComponent** (Updates)
   - Replace mock data with API calls
   - Add CSV upload UI
   - Implement duplicate confirmation dialog
   - Handle loading/error states

3. **DuplicateConfirmationDialog** (New)
   - Display flagged duplicates
   - Accept/Reject UI
   - Confirm and retry upload

### API Integration Points

- Fetch metadata on component init
- Submit transactions on form submit
- Handle bulk upload responses
- Show duplicate confirmation when needed
- Update grid with confirmed transactions

---

## Known Limitations

1. **Duplicate Confirmation** (Phase 2)
   - Currently accepts duplicates from frontend
   - Final confirmation endpoint not implemented
   - Need to handle ACCEPT/REJECT actions

2. **CSV Parsing** (Frontend)
   - Need to implement CSV parser in Angular
   - Currently schema expects array of objects
   - Frontend needs to convert CSV rows to JSON

3. **Family Group Sharing** (Phase 2)
   - is_shared field set but not enforced
   - Need to implement visibility logic
   - Query modification for family access

4. **Month ID Format**
   - Currently auto-calculated as YYYY-MM
   - Should be configurable per user preferences

---

## Deployment Checklist

- [ ] Run `python scripts/init_transaction_metadata.py`
- [ ] Verify all new tables created
- [ ] Verify metadata populated (11 categories, 51 subcategories, etc.)
- [ ] Test API endpoints with Postman/Insomnia
- [ ] Verify Redis caching working
- [ ] Check audit logs in system_logs table
- [ ] Update frontend to consume new APIs
- [ ] Test end-to-end flow
- [ ] Performance test bulk uploads (1000 rows)

---

## Performance Considerations

1. **Bulk Upload (1000 rows)**
   - Expected time: 5-15 seconds depending on duplicate detection
   - Batch processing: Row-by-row for granular error handling
   - Could optimize with batch inserts (trade-off with error tracking)

2. **Duplicate Detection**
   - Query per transaction in bulk upload
   - Could pre-load user transactions for batch comparison
   - Consider caching for high-volume uploads

3. **Cache Invalidation**
   - Pattern-based deletion on transaction changes
   - Consider implementing more fine-grained cache keys

---

## File Structure

```
app/
├── models/
│   ├── transaction_type.py          # New
│   ├── expense_category.py          # New
│   ├── expense_subcategory.py       # New
│   ├── payment_method.py            # New
│   ├── budget_type.py               # New
│   ├── bulk_upload.py               # New
│   ├── duplicate_transaction.py     # New
│   ├── transaction_upload.py        # New
│   └── transaction.py               # Enhanced
├── schemas/
│   └── manual_transaction.py        # New
├── services/
│   └── manual_transaction_service.py # New
├── routes/
│   └── manual_transaction.py        # New
└── main.py                          # Updated

scripts/
└── init_transaction_metadata.py     # New (migration/initialization)
```

---

## References

- SQLAlchemy Async: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- Pydantic Validation: https://docs.pydantic.dev/latest/
- FastAPI: https://fastapi.tiangolo.com/
- Redis Caching: https://redis.io/commands/

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-10-11 | Initial backend implementation |

---

**Questions or Issues**: Contact the development team.
