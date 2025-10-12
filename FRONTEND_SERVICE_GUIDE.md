# Frontend Manual Transaction Service Guide

**File Location**: `spendlyzer-frontend/src/app/services/manual-transaction.service.ts`

**Test File**: `spendlyzer-frontend/src/app/services/manual-transaction.service.spec.ts`

---

## Overview

The `ManualTransactionService` is an Angular service that provides a complete interface for managing manual transactions with the backend API. It handles:

- Single transaction creation
- Bulk CSV transaction uploads
- Transaction updates and deletion
- CSV file parsing and validation
- Transaction metadata caching
- Error handling and user feedback

---

## Injection & Setup

### Basic Setup in Component

```typescript
import { Component, OnInit } from '@angular/core';
import { ManualTransactionService, ManualTransaction } from '@app/services/manual-transaction.service';

@Component({
  selector: 'app-manual-transaction-modal',
  templateUrl: './manual-transaction-modal.component.html',
  styleUrls: ['./manual-transaction-modal.component.scss']
})
export class ManualTransactionModalComponent implements OnInit {
  constructor(
    private transactionService: ManualTransactionService
  ) {}

  ngOnInit(): void {
    // Service automatically loads metadata on initialization
    this.loadMetadata();
  }

  private loadMetadata(): void {
    this.transactionService.metadata$.subscribe(
      (metadata) => {
        if (metadata) {
          // Use metadata in component
          console.log('Categories:', metadata.expense_categories);
          console.log('Payment Methods:', metadata.payment_methods);
        }
      }
    );
  }
}
```

---

## API Methods

### 1. Get Transaction Metadata

**Method**: `getTransactionMetadata(): Observable<TransactionMetadata>`

**Purpose**: Fetch all categories, payment methods, transaction types, and budget types.

**Usage**:
```typescript
this.transactionService.getTransactionMetadata().subscribe(
  (metadata) => {
    console.log('Transaction Types:', metadata.transaction_types);
    console.log('Categories:', metadata.expense_categories);
    console.log('Payment Methods:', metadata.payment_methods);
    console.log('Budget Types:', metadata.budget_types);
  },
  (error) => {
    console.error('Failed to load metadata:', error);
  }
);
```

**Caching**: Results are cached for 1 hour automatically.

**Returns**:
```typescript
{
  transaction_types: MetadataItem[],
  expense_categories: MetadataItem[],
  payment_methods: MetadataItem[],
  budget_types: MetadataItem[]
}
```

---

### 2. Create Single Transaction

**Method**: `createTransaction(transaction: ManualTransaction): Observable<ManualTransaction>`

**Purpose**: Create a single manual transaction.

**Usage**:
```typescript
const newTransaction: ManualTransaction = {
  date: '2025-10-15',
  amount: 45.99,
  currency: 'USD',
  description: 'Whole Foods groceries',
  merchant: 'Whole Foods',
  notes: 'Weekly grocery shopping',
  transaction_type_id: 1,
  expense_category_id: 1,
  expense_subcategory_id: 1,
  payment_method_id: 1,
  budget_type_id: 1,
  card_id: 1,
  is_shared: false
};

this.transactionService.createTransaction(newTransaction).subscribe(
  (response) => {
    console.log('Transaction created:', response);
    console.log('Transaction ID:', response.id);
  },
  (error) => {
    console.error('Failed to create transaction:', error);
    this.showErrorNotification(error.message);
  }
);
```

**Validation**: Performed by backend. Common errors:
- Date in future
- Date more than 2 years old
- Invalid amount (≤ 0)
- Invalid currency (not USD or CAD)
- Card not found

---

### 3. Bulk Create Transactions

**Method**: `bulkCreateTransactions(request: BulkTransactionUploadRequest): Observable<BulkUploadResponse>`

**Purpose**: Create multiple transactions at once, with duplicate detection.

**Usage**:
```typescript
const bulkRequest: BulkTransactionUploadRequest = {
  transactions: [
    {
      date: '2025-10-15',
      amount: 45.99,
      currency: 'USD',
      description: 'Groceries',
      merchant: 'Whole Foods',
      transaction_type_id: 1,
      expense_category_id: 1,
      payment_method_id: 1,
      card_id: 1,
      is_shared: false
    },
    // ... more transactions
  ],
  filename: 'transactions.csv',
  allow_duplicates: false
};

this.transactionService.bulkCreateTransactions(bulkRequest).subscribe(
  (response) => {
    console.log('Bulk upload complete:');
    console.log(`Success: ${response.successful_count}`);
    console.log(`Failed: ${response.failed_count}`);
    console.log(`Duplicates: ${response.duplicate_count}`);
    console.log(`Status: ${response.status}`);

    if (response.status === 'PENDING_REVIEW') {
      // Show duplicate confirmation dialog
      this.showDuplicateConfirmation(response);
    } else if (response.failed_count > 0) {
      // Show failed rows
      this.showFailedRows(response.failed_rows);
    }
  },
  (error) => {
    console.error('Bulk upload failed:', error);
  }
);
```

**Response**:
```typescript
{
  bulk_upload_id: number,
  total_rows: number,
  successful_count: number,
  failed_count: number,
  duplicate_count: number,
  status: 'COMPLETED' | 'PARTIAL_FAILURE' | 'PENDING_REVIEW' | 'FAILED',
  error_message?: string,
  created_transactions: ManualTransaction[],
  failed_rows?: Array<{
    row: number,
    error: string,
    data?: any
  }>
}
```

---

### 4. Update Transaction

**Method**: `updateTransaction(transactionId: number, updateData: ManualTransactionUpdateRequest): Observable<ManualTransaction>`

**Purpose**: Update specific fields of an existing transaction.

**Usage**:
```typescript
const updates: ManualTransactionUpdateRequest = {
  amount: 50.00,
  merchant: 'Trader Joe\'s',
  notes: 'Updated merchant'
};

this.transactionService.updateTransaction(123, updates).subscribe(
  (response) => {
    console.log('Transaction updated:', response);
    this.showSuccessNotification('Transaction updated successfully');
  },
  (error) => {
    console.error('Failed to update transaction:', error);
  }
);
```

**Note**: All fields are optional. Only provided fields will be updated.

---

### 5. Delete Transaction

**Method**: `deleteTransaction(transactionId: number): Observable<{ message: string }>`

**Purpose**: Delete a manual transaction permanently.

**Usage**:
```typescript
this.transactionService.deleteTransaction(123).subscribe(
  (response) => {
    console.log(response.message); // "Transaction deleted successfully"
    this.showSuccessNotification('Transaction deleted');
  },
  (error) => {
    console.error('Failed to delete transaction:', error);
  }
);
```

---

### 6. Get Bulk Upload Status

**Method**: `getBulkUploadStatus(bulkUploadId: number): Observable<BulkUploadStatus>`

**Purpose**: Check the status of a bulk upload operation.

**Usage**:
```typescript
this.transactionService.getBulkUploadStatus(1).subscribe(
  (status) => {
    console.log('Upload status:', status.status);
    console.log('Processed:', status.processed_at);
  },
  (error) => {
    console.error('Failed to fetch status:', error);
  }
);
```

---

### 7. Confirm Duplicate Handling

**Method**: `confirmDuplicateHandling(confirmation: DuplicateConfirmationRequest): Observable<DuplicateConfirmationResponse>`

**Purpose**: Accept or reject flagged duplicate transactions.

**Usage**:
```typescript
const confirmation: DuplicateConfirmationRequest = {
  duplicate_transaction_ids: [15, 16, 17],
  action: 'ACCEPT', // or 'REJECT'
  user_notes: 'These are legitimate separate purchases'
};

this.transactionService.confirmDuplicateHandling(confirmation).subscribe(
  (response) => {
    console.log(`${response.action}: ${response.duplicates_processed} duplicates`);
  },
  (error) => {
    console.error('Failed to confirm duplicates:', error);
  }
);
```

---

## CSV File Operations

### 1. Parse CSV File

**Method**: `parseCSVFile(file: File, delimiter: string = ','): Promise<ManualTransaction[]>`

**Purpose**: Parse CSV file into transaction objects for validation and submission.

**Usage**:
```typescript
// In file input change handler
onFileSelected(event: any): void {
  const file: File = event.target.files[0];

  this.transactionService.parseCSVFile(file)
    .then((transactions) => {
      console.log(`Parsed ${transactions.length} transactions`);
      // Validate before submission
      const invalidTransactions = transactions.filter(t => {
        const error = this.transactionService.validateTransaction(t);
        return error !== null;
      });

      if (invalidTransactions.length > 0) {
        this.showErrorNotification('Some transactions have validation errors');
        return;
      }

      // Submit valid transactions
      this.submitTransactions(transactions);
    })
    .catch((error) => {
      console.error('Failed to parse CSV:', error);
      this.showErrorNotification(error.message);
    });
}

private submitTransactions(transactions: ManualTransaction[]): void {
  const request: BulkTransactionUploadRequest = {
    transactions: transactions,
    filename: 'upload.csv',
    allow_duplicates: false
  };

  this.transactionService.bulkCreateTransactions(request).subscribe(
    (response) => {
      this.handleUploadResponse(response);
    }
  );
}
```

**CSV Format Requirements**:
```
date,description,amount,currency,merchant,transaction_type_id,expense_category_id,expense_subcategory_id,payment_method_id,budget_type_id,card_id,is_shared,notes
```

**Required Columns**:
- date (YYYY-MM-DD)
- amount
- currency (USD or CAD)
- description
- transaction_type_id
- payment_method_id
- card_id

**Optional Columns**:
- merchant
- notes
- expense_category_id
- expense_subcategory_id
- budget_type_id
- is_shared

---

### 2. Validate Transaction

**Method**: `validateTransaction(transaction: ManualTransaction): string | null`

**Purpose**: Validate transaction data according to business rules.

**Usage**:
```typescript
const validationError = this.transactionService.validateTransaction(transaction);

if (validationError) {
  console.error('Validation error:', validationError);
  // Show error message to user
} else {
  console.log('Transaction is valid');
  // Proceed with submission
}
```

**Validations**:
- Date cannot be in future
- Date cannot be > 2 years old
- Amount must be positive
- Currency must be USD or CAD
- All required fields present
- Transaction type, payment method, and card must be provided

---

### 3. Generate CSV Template

**Method**: `generateCSVTemplate(): string`

**Purpose**: Generate a CSV template string with example rows.

**Usage**:
```typescript
const csvTemplate = this.transactionService.generateCSVTemplate();
// Use to display example or pre-fill form
```

**Output**:
```csv
date,description,amount,currency,merchant,transaction_type_id,expense_category_id,expense_subcategory_id,payment_method_id,budget_type_id,card_id,is_shared,notes
2025-10-15,Whole Foods,45.99,USD,Whole Foods,1,1,1,1,1,1,false,Weekly groceries
2025-10-14,Shell Gas Station,55.00,USD,Shell,1,2,4,1,1,1,false,Gas fill-up
2025-10-13,Amazon Purchase,120.00,USD,Amazon,1,3,8,2,2,2,true,Electronics purchase
```

---

### 4. Download CSV Template

**Method**: `downloadCSVTemplate(): void`

**Purpose**: Trigger download of CSV template file.

**Usage**:
```html
<button (click)="transactionService.downloadCSVTemplate()">
  Download CSV Template
</button>
```

---

## Utility Methods

### 1. Get Category by ID

**Method**: `getCategoryById(categoryId: number): MetadataItem | null`

**Usage**:
```typescript
const category = this.transactionService.getCategoryById(1);
if (category) {
  console.log(`Category: ${category.name}, Color: ${category.color}`);
}
```

---

### 2. Get Payment Method by ID

**Method**: `getPaymentMethodById(methodId: number): MetadataItem | null`

**Usage**:
```typescript
const method = this.transactionService.getPaymentMethodById(1);
console.log(`Payment Method: ${method?.name}`);
```

---

### 3. Get Subcategories for Category

**Method**: `getSubcategoriesForCategory(categoryId: number): MetadataItem[]`

**Usage**:
```typescript
const subcategories = this.transactionService.getSubcategoriesForCategory(1);
console.log(`Subcategories for category 1:`, subcategories);
```

---

### 4. Format Date

**Method**: `formatDate(date: string): string`

**Usage**:
```typescript
const formatted = this.transactionService.formatDate('2025-10-15');
console.log(formatted); // "Oct 15, 2025"
```

---

### 5. Format Currency

**Method**: `formatCurrency(amount: number, currency: string = 'USD'): string`

**Usage**:
```typescript
const formatted = this.transactionService.formatCurrency(45.99, 'USD');
console.log(formatted); // "$45.99"
```

---

## Error Handling

### Common Error Scenarios

#### 1. Validation Error (422)
```typescript
this.transactionService.createTransaction(transaction).subscribe(
  (response) => { /* success */ },
  (error) => {
    // error.message contains validation details
    // e.g., "Transaction date cannot be in the future"
  }
);
```

#### 2. Not Found (404)
```typescript
this.transactionService.updateTransaction(999, updates).subscribe(
  (response) => { /* success */ },
  (error) => {
    // error.message: "Transaction not found"
  }
);
```

#### 3. Server Error (400)
```typescript
this.transactionService.bulkCreateTransactions(request).subscribe(
  (response) => { /* success */ },
  (error) => {
    // error.message contains server error details
  }
);
```

---

## Component Integration Example

```typescript
import { Component, OnInit } from '@angular/core';
import { ManualTransactionService, ManualTransaction, BulkUploadResponse } from '@app/services/manual-transaction.service';

@Component({
  selector: 'app-manual-transaction-modal',
  templateUrl: './manual-transaction-modal.component.html',
  styleUrls: ['./manual-transaction-modal.component.scss']
})
export class ManualTransactionModalComponent implements OnInit {
  loading = false;
  error: string | null = null;
  successMessage: string | null = null;

  metadata$ = this.transactionService.metadata$;

  constructor(
    private transactionService: ManualTransactionService
  ) {}

  ngOnInit(): void {
    // Metadata loads automatically
  }

  // Single transaction form submission
  submitTransaction(formData: any): void {
    this.loading = true;
    this.error = null;

    const transaction: ManualTransaction = {
      date: formData.date,
      amount: formData.amount,
      currency: formData.currency,
      description: formData.description,
      merchant: formData.merchant,
      notes: formData.notes,
      transaction_type_id: formData.transactionTypeId,
      expense_category_id: formData.categoryId,
      expense_subcategory_id: formData.subcategoryId,
      payment_method_id: formData.paymentMethodId,
      budget_type_id: formData.budgetTypeId,
      card_id: formData.cardId,
      is_shared: formData.isShared || false
    };

    // Validate
    const validationError = this.transactionService.validateTransaction(transaction);
    if (validationError) {
      this.error = validationError;
      this.loading = false;
      return;
    }

    // Submit
    this.transactionService.createTransaction(transaction).subscribe(
      (response) => {
        this.loading = false;
        this.successMessage = 'Transaction created successfully';
        // Reset form or close modal
      },
      (error) => {
        this.loading = false;
        this.error = error.message;
      }
    );
  }

  // CSV upload handler
  onCSVSelected(event: any): void {
    const file: File = event.target.files[0];

    this.loading = true;
    this.error = null;

    this.transactionService.parseCSVFile(file)
      .then((transactions) => {
        const request = {
          transactions: transactions,
          filename: file.name,
          allow_duplicates: false
        };

        return this.transactionService.bulkCreateTransactions(request).toPromise();
      })
      .then((response) => {
        this.loading = false;

        if (response?.status === 'PENDING_REVIEW') {
          // Show duplicate confirmation dialog
          this.showDuplicateDialog(response);
        } else {
          this.successMessage = `${response?.successful_count} transactions imported successfully`;
        }
      })
      .catch((error) => {
        this.loading = false;
        this.error = error.message;
      });
  }

  private showDuplicateDialog(response: BulkUploadResponse): void {
    // Implementation depends on your modal/dialog system
    console.log(`${response.duplicate_count} duplicates found`);
  }

  downloadTemplate(): void {
    this.transactionService.downloadCSVTemplate();
  }
}
```

---

## Testing

### Run Unit Tests

```bash
ng test --include='**/manual-transaction.service.spec.ts'
```

### Test Coverage

- Service initialization
- Metadata fetching and caching
- Transaction CRUD operations
- Bulk upload with duplicate handling
- CSV parsing and validation
- Error handling
- Caching behavior

---

## Best Practices

1. **Always validate before submission**
   ```typescript
   const error = this.transactionService.validateTransaction(transaction);
   if (error) { /* show error */ }
   ```

2. **Handle duplicate scenarios gracefully**
   ```typescript
   if (response.status === 'PENDING_REVIEW') {
     // Show duplicate confirmation dialog
   }
   ```

3. **Provide user feedback**
   - Show loading indicator during submission
   - Display success/error messages
   - Handle specific error cases

4. **Use metadata subscription**
   ```typescript
   this.transactionService.metadata$.subscribe(metadata => {
     // Populate dropdowns with metadata
   });
   ```

5. **Cache CSV parsing results**
   - Parse once, submit multiple times if needed
   - Don't re-parse on every keystroke

---

## Troubleshooting

### Issue: Metadata not loading
**Solution**: Check that you have valid JWT token in localStorage. Service requires `access_token`.

### Issue: CSV parsing fails
**Solution**: Ensure CSV has all required columns and proper date format (YYYY-MM-DD).

### Issue: Transaction not created
**Solution**: Check validation errors - date range, amount, required fields, card existence.

### Issue: Duplicates always flagged
**Solution**: Check if `allow_duplicates` is set to false. Set to true to skip duplicate checking.

---

## API Response Examples

### Success Response
```json
{
  "id": 123,
  "user_id": 1,
  "date": "2025-10-15",
  "amount": 45.99,
  "currency": "USD",
  "description": "Groceries",
  "merchant": "Whole Foods",
  "transaction_type_id": 1,
  "is_manual": true,
  "created_at": "2025-10-11T15:30:00Z"
}
```

### Error Response
```json
{
  "detail": "Transaction date cannot be in the future"
}
```

### Bulk Upload Response
```json
{
  "bulk_upload_id": 1,
  "total_rows": 50,
  "successful_count": 48,
  "failed_count": 1,
  "duplicate_count": 1,
  "status": "PENDING_REVIEW",
  "created_transactions": [ /* array */ ],
  "failed_rows": [
    {
      "row": 25,
      "error": "Invalid card ID"
    }
  ]
}
```

---

## Next Steps (Phase 13-14)

1. Update ManualTransactionModalComponent to use this service
2. Implement CSV upload UI with file input
3. Create duplicate confirmation dialog
4. Remove mock data and use real API responses
5. Add loading and error state handling

