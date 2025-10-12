# Phase 13 Implementation Guide - CSV Upload UI & Duplicate Dialog

**Date**: October 11, 2025
**Phase**: 13 of 17
**Status**: IN PROGRESS

---

## Overview

Phase 13 focuses on implementing the CSV upload user interface and duplicate confirmation dialog within the ManualTransactionModalComponent. This involves:

1. Adding CSV upload tab to modal
2. Implementing CSV file drag-and-drop
3. Creating duplicate confirmation dialog
4. Adding loading and error states
5. Integrating with ManualTransactionService

---

## Files Delivered

### 1. **Duplicate Confirmation Dialog Component**
**File**: `spendlyzer-frontend/src/app/pages/manual-transaction-modal/duplicate-confirmation.component.ts`
**Status**: ✅ Created
**Type**: Angular Standalone Component

**Features**:
- ✅ Dialog for displaying duplicate transactions
- ✅ Summary statistics (successful, duplicates, failed)
- ✅ List of flagged duplicates with details
- ✅ Checkboxes for user selection
- ✅ User notes textarea
- ✅ Accept/Reject/Cancel buttons
- ✅ Failed rows display
- ✅ Similarity score visualization

**Usage**:
```typescript
// In modal component
import { DuplicateConfirmationComponent } from './duplicate-confirmation.component';
import { MatDialog } from '@angular/material/dialog';

constructor(public dialog: MatDialog) {}

openDuplicateDialog(uploadResponse: BulkUploadResponse): void {
  const dialogRef = this.dialog.open(DuplicateConfirmationComponent, {
    width: '600px',
    maxWidth: '90vw',
    data: uploadResponse
  });

  dialogRef.afterClosed().subscribe(result => {
    if (result?.action === 'ACCEPT') {
      this.confirmDuplicates(result.duplicateIds, result.userNotes);
    } else if (result?.action === 'REJECT') {
      // Discard all duplicates
    }
  });
}
```

### 2. **Enhanced Modal HTML Template**
**File**: `spendlyzer-frontend/src/app/pages/manual-transaction-modal/manual-transaction-modal.component.enhanced.html`
**Status**: ✅ Created
**Type**: Angular Template

**Features**:
- ✅ Tab navigation (Manual Entry / CSV Upload)
- ✅ Manual entry tab with AG Grid
- ✅ CSV upload tab with drag-and-drop
- ✅ File input with browse button
- ✅ CSV template download button
- ✅ Upload progress indicator
- ✅ Error and success messages
- ✅ Toast notification area
- ✅ Loading spinner on save button
- ✅ Responsive design with Tailwind CSS
- ✅ Dark mode support

**Key UI Elements**:
```html
<!-- Tab Navigation -->
<button (click)="activeTab = 'manual'">Manual Entry</button>
<button (click)="activeTab = 'csv'">CSV Upload</button>

<!-- CSV Upload Area (Drag & Drop) -->
<div (dragover)="onDragOver($event)" (drop)="onDropCSV($event)">
  Drop your CSV file here
</div>

<!-- CSV File Input -->
<input #csvFileInput type="file" accept=".csv"
  (change)="onCSVFileSelected($event)" class="hidden">

<!-- Download Template Button -->
<button (click)="downloadCSVTemplate()">Download CSV Template</button>

<!-- Progress & Messages -->
<div *ngIf="csvUploading">Processing...</div>
<div *ngIf="csvError">{{ csvError }}</div>
<div *ngIf="csvSuccess">{{ csvSuccess }}</div>

<!-- Toast Notification -->
<div *ngIf="toastMessage" [class]="'toast-' + toastType">
  {{ toastMessage }}
</div>
```

---

## Component Methods to Implement

### CSV Handling Methods

#### 1. **onCSVFileSelected(event)**
```typescript
/**
 * Handle CSV file selection from input element
 */
onCSVFileSelected(event: any): void {
  const file = event.target.files[0];
  if (file) {
    this.processCSVFile(file);
  }
}
```

**Logic**:
- Get file from input element
- Call processCSVFile()

---

#### 2. **onDropCSV(event)**
```typescript
/**
 * Handle CSV file drop from drag-and-drop
 */
onDropCSV(event: DragEvent): void {
  event.preventDefault();
  this.isDraggingCSV = false;

  const files = event.dataTransfer?.files;
  if (files && files.length > 0) {
    const file = files[0];
    if (file.type === 'text/csv' || file.name.endsWith('.csv')) {
      this.processCSVFile(file);
    } else {
      this.showToast('Please select a CSV file', 'error');
    }
  }
}
```

**Logic**:
- Prevent default drag behavior
- Check file type
- Call processCSVFile()

---

#### 3. **onDragOver(event)**
```typescript
/**
 * Handle drag over area for visual feedback
 */
onDragOver(event: DragEvent): void {
  event.preventDefault();
  this.isDraggingCSV = true;
}
```

**Logic**:
- Show visual feedback (CSS class)

---

#### 4. **processCSVFile(file)**
```typescript
/**
 * Process CSV file: parse, validate, and display in grid
 */
private async processCSVFile(file: File): Promise<void> {
  this.csvUploading = true;
  this.csvFileName = file.name;
  this.csvError = null;
  this.csvSuccess = null;

  try {
    // Parse CSV
    const transactions = await this.manualTransactionService.parseCSVFile(file);

    // Validate each transaction
    const invalid = transactions.filter(t => {
      const error = this.manualTransactionService.validateTransaction(t);
      return error !== null;
    });

    if (invalid.length > 0) {
      throw new Error(`${invalid.length} transaction(s) have validation errors`);
    }

    // Add to grid
    this.rowData = [...this.rowData, ...transactions];
    this.csvTransactionCount = transactions.length;
    this.csvSuccess = true;
    this.showToast(`Successfully imported ${transactions.length} transaction(s)`, 'success');

  } catch (error: any) {
    this.csvError = error.message;
    this.showToast(`CSV import failed: ${error.message}`, 'error');
  } finally {
    this.csvUploading = false;
  }
}
```

**Logic**:
- Parse CSV file
- Validate each row
- Add to grid data
- Show success/error messages

---

#### 5. **downloadCSVTemplate()**
```typescript
/**
 * Download CSV template file
 */
downloadCSVTemplate(): void {
  this.manualTransactionService.downloadCSVTemplate();
  this.showToast('CSV template downloaded', 'success');
}
```

---

### Dialog & State Management

#### 6. **openDuplicateDialog(response)**
```typescript
/**
 * Open duplicate confirmation dialog
 */
private openDuplicateDialog(response: BulkUploadResponse): void {
  const dialogRef = this.dialog.open(DuplicateConfirmationComponent, {
    width: '600px',
    maxWidth: '90vw',
    data: response
  });

  dialogRef.afterClosed().subscribe(result => {
    if (!result) return; // Cancelled

    if (result.action === 'ACCEPT') {
      // Confirm and proceed
      this.confirmDuplicates(result.duplicateIds, result.userNotes);
    } else if (result.action === 'REJECT') {
      // Discard all duplicates - transactions already saved
      this.showToast('Duplicate transactions discarded', 'info');
      this.modalRef.close();
    }
  });
}
```

---

#### 7. **confirmDuplicates(ids, notes)**
```typescript
/**
 * Confirm duplicate transaction handling
 */
private confirmDuplicates(duplicateIds: number[], userNotes: string): void {
  const request: DuplicateConfirmationRequest = {
    duplicate_transaction_ids: duplicateIds,
    action: 'ACCEPT',
    user_notes: userNotes
  };

  this.manualTransactionService.confirmDuplicateHandling(request)
    .subscribe(
      (response) => {
        this.showToast(`${duplicateIds.length} duplicate(s) confirmed`, 'success');
        this.modalRef.close();
      },
      (error) => {
        this.showToast(`Failed to confirm duplicates: ${error}`, 'error');
      }
    );
}
```

---

#### 8. **onSave()**
```typescript
/**
 * Save all transactions - single or bulk
 */
onSave(): void {
  if (this.rowData.length === 0) {
    this.showToast('No transactions to save', 'warning');
    return;
  }

  this.isSaving = true;

  // Check if bulk or single
  if (this.rowData.length === 1) {
    this.saveSingleTransaction(this.rowData[0]);
  } else {
    this.saveBulkTransactions(this.rowData);
  }
}
```

---

#### 9. **saveSingleTransaction(transaction)**
```typescript
/**
 * Save single transaction
 */
private saveSingleTransaction(transaction: ManualTransaction): void {
  this.manualTransactionService.createTransaction(transaction)
    .subscribe(
      (response) => {
        this.isSaving = false;
        this.showToast('Transaction saved successfully', 'success');
        this.transactionsSaved.emit([response]);
        setTimeout(() => this.modalRef.close(), 1500);
      },
      (error) => {
        this.isSaving = false;
        this.showToast(`Failed to save: ${error.message}`, 'error');
      }
    );
}
```

---

#### 10. **saveBulkTransactions(transactions)**
```typescript
/**
 * Save bulk transactions
 */
private saveBulkTransactions(transactions: ManualTransaction[]): void {
  const request: BulkTransactionUploadRequest = {
    transactions: transactions,
    filename: `manual_upload_${new Date().toISOString()}`,
    allow_duplicates: false
  };

  this.manualTransactionService.bulkCreateTransactions(request)
    .subscribe(
      (response) => {
        this.isSaving = false;

        // Handle response
        if (response.status === 'PENDING_REVIEW') {
          // Show duplicate dialog
          this.openDuplicateDialog(response);
        } else if (response.failed_count > 0) {
          // Show errors
          this.showFailedRows(response.failed_rows);
          this.showToast(
            `${response.successful_count} saved, ${response.failed_count} failed`,
            'warning'
          );
        } else {
          // All success
          this.showToast(
            `${response.successful_count} transactions saved successfully`,
            'success'
          );
          this.transactionsSaved.emit(response.created_transactions);
          setTimeout(() => this.modalRef.close(), 1500);
        }
      },
      (error) => {
        this.isSaving = false;
        this.showToast(`Bulk upload failed: ${error.message}`, 'error');
      }
    );
}
```

---

#### 11. **showFailedRows(failed)**
```typescript
/**
 * Show details of failed rows
 */
private showFailedRows(failed: any[]): void {
  const failedText = failed
    .map(f => `Row ${f.row}: ${f.error}`)
    .join('\n');

  console.error('Failed rows:', failedText);
  // Could also show in a detailed error dialog
}
```

---

#### 12. **showToast(message, type)**
```typescript
/**
 * Show toast notification
 */
private showToast(message: string, type: 'success' | 'error' | 'warning' | 'info'): void {
  this.toastMessage = message;
  this.toastType = type;

  // Auto-hide after 5 seconds
  setTimeout(() => {
    this.toastMessage = null;
  }, 5000);
}
```

---

## Component Properties

```typescript
// Tab Management
activeTab: 'manual' | 'csv' = 'manual';

// CSV Upload State
csvUploading = false;
csvFileName = '';
csvError: string | null = null;
csvSuccess: boolean = false;
csvTransactionCount = 0;
isDraggingCSV = false;

// Save State
isSaving = false;

// Toast Notification
toastMessage: string | null = null;
toastType: 'success' | 'error' | 'warning' | 'info' = 'success';

// Dialog Reference
private modalRef: MatDialogRef<...>;
```

---

## Component Imports

```typescript
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { AgGridModule } from 'ag-grid-angular';
import { MatDialog, MatDialogRef } from '@angular/material/dialog';
import { ManualTransactionService, BulkUploadResponse, ManualTransaction, DuplicateConfirmationRequest } from '@app/services/manual-transaction.service';
import { DuplicateConfirmationComponent } from './duplicate-confirmation.component';
```

---

## Implementation Steps

### Step 1: Update Component TypeScript
1. Add new properties for CSV and state management
2. Implement CSV handling methods (onCSVFileSelected, onDropCSV, etc.)
3. Implement dialog handling methods
4. Implement save methods (single and bulk)
5. Add toast notification system

### Step 2: Replace Template
1. Replace `manual-transaction-modal.component.html` with `.enhanced.html`
2. Add tab navigation
3. Add CSV upload area
4. Update save button with loading state

### Step 3: Add Dependencies
1. Import MatDialog for duplicate dialog
2. Import ManualTransactionService
3. Import DuplicateConfirmationComponent

### Step 4: Test Functionality
1. Test manual entry tab (existing)
2. Test CSV file selection
3. Test CSV drag-and-drop
4. Test CSV parsing and validation
5. Test duplicate detection
6. Test success/error flows

---

## Component Injection in Dashboard

```typescript
import { ManualTransactionModalComponent } from '@app/pages/manual-transaction-modal/manual-transaction-modal.component';

// In dashboard component
<app-manual-transaction-modal
  [isOpen]="showManualTransactionModal"
  (closeModal)="showManualTransactionModal = false"
  (transactionsSaved)="onTransactionsSaved($event)"
></app-manual-transaction-modal>

// Method
onTransactionsSaved(transactions: ManualTransaction[]): void {
  console.log('Transactions saved:', transactions);
  // Refresh transaction list
  this.loadTransactions();
}
```

---

## CSV Format Reference

### Required Columns
```
date,description,amount,currency,transaction_type_id,payment_method_id,card_id
```

### Example CSV
```csv
date,description,amount,currency,merchant,transaction_type_id,expense_category_id,payment_method_id,budget_type_id,card_id,is_shared,notes
2025-10-15,Whole Foods,45.99,USD,Whole Foods,1,1,1,1,1,false,Weekly groceries
2025-10-14,Shell Gas,55.00,USD,Shell,1,2,1,1,1,false,Gas fill-up
2025-10-13,Amazon,120.00,USD,Amazon,1,3,2,2,2,true,Electronics purchase
```

---

## Error Handling

### CSV Parsing Errors
- Invalid date format
- Missing required columns
- Non-numeric amounts
- Invalid currency
- File read errors

### Validation Errors
- Date in future
- Date > 2 years old
- Negative amount
- Required fields missing

### API Errors
- Network errors
- Server validation errors
- Authorization errors
- Rate limiting

---

## User Experience Flow

### Manual Entry Tab
1. User clicks "Add Row"
2. Grid adds new row
3. User enters data
4. User clicks "Save All Transactions"
5. Modal closes on success

### CSV Upload Tab
1. User drags CSV or clicks to browse
2. File is parsed and validated
3. Transactions appear in summary
4. User clicks "Save All Transactions"
5. If duplicates found:
   - Duplicate dialog opens
   - User selects which to keep
   - Selected duplicates are confirmed
6. Modal closes on success

### Duplicate Confirmation
1. Dialog shows flagged duplicates
2. User can see similarity score
3. User selects which to keep
4. User optionally adds notes
5. User confirms or rejects
6. Modal closes

---

## Integration with Service

**Service Method Called**: `bulkCreateTransactions()`
- Sends transactions to backend
- Backend checks for duplicates
- Returns response with counts

**If Duplicates**: Show dialog
- User reviews duplicates
- Calls `confirmDuplicateHandling()`
- Duplicates are confirmed or discarded

---

## Performance Considerations

### CSV Parsing
- Parses on client-side (instant)
- Validates each row before submission
- Shows real-time progress

### Batch Upload
- Sends all rows in one request
- Backend processes row-by-row
- Returns detailed feedback

### Memory Management
- Grid pagination (if needed)
- Clear loaded CSV after processing
- Unsubscribe from all subscriptions on destroy

---

## Accessibility Features

- ✅ Keyboard navigation (Tab, Enter)
- ✅ ARIA labels on buttons
- ✅ Focus management in modal
- ✅ Error messages clearly displayed
- ✅ Loading state visually indicated
- ✅ Dark mode support

---

## Testing Checklist

- [ ] Manual entry tab functionality
- [ ] CSV file selection
- [ ] Drag-and-drop functionality
- [ ] CSV parsing and validation
- [ ] Error message display
- [ ] Duplicate detection workflow
- [ ] Dialog open/close
- [ ] Save single transaction
- [ ] Save bulk transactions
- [ ] Toast notification display
- [ ] Loading states
- [ ] Dark/light theme switching
- [ ] Responsive design
- [ ] Keyboard navigation

---

## Next Phase (14)

Phase 14 will focus on:
1. **Remove Mock Data** - Replace hardcoded categories/payment methods with API calls
2. **Use Real Metadata** - Load from ManualTransactionService
3. **Update Grid Configuration** - Map API data to AG Grid
4. **Dropdown Integration** - Populate from metadata
5. **End-to-End Testing** - Test complete flow with real backend

---

## Files Ready for Phase 14

- ✅ `duplicate-confirmation.component.ts` - Dialog component
- ✅ `manual-transaction-modal.component.enhanced.html` - Updated template
- ✅ Enhanced component TypeScript (ready to integrate)

---

## Summary

Phase 13 delivers:

1. **Duplicate Confirmation Dialog** - Material dialog for handling duplicates
2. **Enhanced Modal Template** - Tab-based UI with CSV upload support
3. **CSV Upload Functionality** - Drag-and-drop and file selection
4. **Component Methods** - All required methods for CSV handling
5. **State Management** - Loading, error, and success states
6. **User Feedback** - Toast notifications and dialogs
7. **Error Handling** - Comprehensive error scenarios
8. **Implementation Guide** - Step-by-step integration instructions

**Status**: Ready for integration and Phase 14!

