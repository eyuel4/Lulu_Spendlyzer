import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { BulkUploadResponse } from '@app/services/manual-transaction.service';

/**
 * Dialog component for confirming duplicate transaction handling
 * Displays flagged duplicates and allows user to accept or reject them
 */
@Component({
  selector: 'app-duplicate-confirmation',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="w-full max-w-2xl">
      <!-- Dialog Header -->
      <div class="px-6 py-4 border-b border-slate-200 dark:border-slate-700">
        <h2 class="text-lg font-semibold text-slate-900 dark:text-white">Duplicate Transactions Detected</h2>
        <p class="text-sm text-slate-600 dark:text-slate-400 mt-1">
          We found {{ duplicateCount }} potential duplicate transaction(s).
          Review and decide whether to keep them or discard them.
        </p>
      </div>

      <!-- Dialog Body -->
      <div class="px-6 py-6 max-h-96 overflow-y-auto">
        <!-- Summary Stats -->
        <div class="grid grid-cols-3 gap-4 mb-6">
          <div class="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
            <p class="text-xs text-green-600 dark:text-green-400 font-medium">Successfully Imported</p>
            <p class="text-2xl font-bold text-green-700 dark:text-green-300">{{ successfulCount }}</p>
          </div>
          <div class="p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg">
            <p class="text-xs text-amber-600 dark:text-amber-400 font-medium">Duplicates Found</p>
            <p class="text-2xl font-bold text-amber-700 dark:text-amber-300">{{ duplicateCount }}</p>
          </div>
          <div class="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
            <p class="text-xs text-red-600 dark:text-red-400 font-medium">Failed to Import</p>
            <p class="text-2xl font-bold text-red-700 dark:text-red-300">{{ failedCount }}</p>
          </div>
        </div>

        <!-- Duplicate List -->
        <div class="space-y-3">
          <h3 class="text-sm font-medium text-slate-900 dark:text-white">Duplicate Transactions:</h3>
          <div class="space-y-2 border border-slate-200 dark:border-slate-700 rounded-lg p-3 bg-slate-50 dark:bg-slate-900/50">
            <div *ngIf="duplicates && duplicates.length > 0; else noDuplicates">
              <div *ngFor="let dup of duplicates" class="pb-2 border-b border-slate-200 dark:border-slate-700 last:border-0">
                <div class="flex items-start justify-between">
                  <div class="flex-1">
                    <p class="text-sm font-medium text-slate-900 dark:text-white">
                      {{ dup.description }}
                    </p>
                    <p class="text-xs text-slate-600 dark:text-slate-400 mt-1">
                      <span class="font-semibold">Date:</span> {{ formatDate(dup.date) }} |
                      <span class="font-semibold">Amount:</span> {{ formatCurrency(dup.amount, dup.currency) }} |
                      <span class="font-semibold">Merchant:</span> {{ dup.merchant || 'N/A' }}
                    </p>
                    <p class="text-xs text-slate-600 dark:text-slate-400 mt-1">
                      <span class="inline-block px-2 py-0.5 bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300 rounded">
                        Similarity: {{ (dup.similarity_score * 100).toFixed(0) }}%
                      </span>
                    </p>
                  </div>
                  <div class="flex space-x-2">
                    <input
                      type="checkbox"
                      [(ngModel)]="selectedDuplicates[dup.id]"
                      class="mt-1"
                      title="Select to include this transaction"
                    >
                  </div>
                </div>
              </div>
            </div>
            <ng-template #noDuplicates>
              <p class="text-sm text-slate-600 dark:text-slate-400">No duplicates to display</p>
            </ng-template>
          </div>
        </div>

        <!-- User Notes -->
        <div class="mt-4">
          <label class="block text-sm font-medium text-slate-900 dark:text-white mb-2">
            Notes (Optional)
          </label>
          <textarea
            [(ngModel)]="userNotes"
            placeholder="Add notes about your decision..."
            class="w-full px-3 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            rows="3"
          ></textarea>
        </div>

        <!-- Failed Rows Info -->
        <div *ngIf="failedCount > 0" class="mt-4 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
          <p class="text-sm font-medium text-red-700 dark:text-red-300">{{ failedCount }} row(s) failed to import:</p>
          <ul class="text-xs text-red-600 dark:text-red-400 mt-2 space-y-1">
            <li *ngFor="let failed of failedRows">
              <span class="font-medium">Row {{ failed.row }}:</span> {{ failed.error }}
            </li>
          </ul>
        </div>
      </div>

      <!-- Dialog Footer -->
      <div class="px-6 py-4 border-t border-slate-200 dark:border-slate-700 flex justify-between items-center space-x-3">
        <button
          (click)="onReject()"
          class="px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-600 transition-colors"
        >
          Discard All Duplicates
        </button>
        <div class="flex space-x-3">
          <button
            (click)="onCancel()"
            class="px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
          >
            Cancel
          </button>
          <button
            (click)="onAccept()"
            class="px-4 py-2 text-sm font-medium text-white bg-amber-600 border border-transparent rounded-lg hover:bg-amber-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-500 transition-colors"
          >
            Keep Selected ({{ getSelectedCount() }})
          </button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    :host {
      display: block;
    }
  `]
})
export class DuplicateConfirmationComponent {
  duplicates: any[] = [];
  successfulCount = 0;
  failedCount = 0;
  duplicateCount = 0;
  failedRows: any[] = [];
  userNotes = '';
  selectedDuplicates: { [key: number]: boolean } = {};

  constructor(
    public dialogRef: MatDialogRef<DuplicateConfirmationComponent>,
    @Inject(MAT_DIALOG_DATA) public data: BulkUploadResponse
  ) {
    this.initialize();
  }

  private initialize(): void {
    if (this.data) {
      this.successfulCount = this.data.successful_count;
      this.failedCount = this.data.failed_count;
      this.duplicateCount = this.data.duplicate_count;
      this.failedRows = this.data.failed_rows || [];

      // Mock duplicates for now - in Phase 14, fetch from API
      this.duplicates = [
        {
          id: 1,
          date: '2025-10-15',
          description: 'Whole Foods',
          amount: 45.99,
          currency: 'USD',
          merchant: 'Whole Foods',
          similarity_score: 0.95
        }
      ];

      // Pre-select all duplicates
      this.duplicates.forEach((dup) => {
        this.selectedDuplicates[dup.id] = true;
      });
    }
  }

  getSelectedCount(): number {
    return Object.values(this.selectedDuplicates).filter(v => v).length;
  }

  formatDate(date: string): string {
    try {
      const d = new Date(date);
      return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
    } catch {
      return date;
    }
  }

  formatCurrency(amount: number, currency: string): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency
    }).format(amount);
  }

  onAccept(): void {
    const selectedIds = Object.entries(this.selectedDuplicates)
      .filter(([, selected]) => selected)
      .map(([id]) => parseInt(id));

    this.dialogRef.close({
      action: 'ACCEPT',
      duplicateIds: selectedIds,
      userNotes: this.userNotes
    });
  }

  onReject(): void {
    this.dialogRef.close({
      action: 'REJECT',
      duplicateIds: [],
      userNotes: this.userNotes
    });
  }

  onCancel(): void {
    this.dialogRef.close(null);
  }
}
