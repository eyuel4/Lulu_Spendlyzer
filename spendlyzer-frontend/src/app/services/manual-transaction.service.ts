import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, BehaviorSubject, throwError } from 'rxjs';
import { tap, catchError, map } from 'rxjs/operators';
import { CacheService } from './cache.service';

/**
 * Manual Transaction Models and Interfaces
 */

export interface ManualTransaction {
  id?: number;
  user_id?: number;
  date: string; // YYYY-MM-DD format
  amount: number;
  currency: 'USD' | 'CAD';
  description: string;
  merchant?: string;
  notes?: string;
  transaction_type_id: number;
  expense_category_id?: number;
  expense_subcategory_id?: number;
  payment_method_id: number;
  budget_type_id?: number;
  card_id: number;
  is_shared: boolean;
  month_id?: string;
  is_manual?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface MetadataItem {
  id: number;
  name: string;
  description?: string;
  icon?: string;
  color?: string;
  bg_color?: string;
  display_order?: number;
}

export interface TransactionMetadata {
  transaction_types: MetadataItem[];
  expense_categories: MetadataItem[];
  payment_methods: MetadataItem[];
  budget_types: MetadataItem[];
}

export interface ManualTransactionUpdateRequest {
  date?: string;
  amount?: number;
  currency?: 'USD' | 'CAD';
  description?: string;
  merchant?: string;
  notes?: string;
  transaction_type_id?: number;
  expense_category_id?: number;
  expense_subcategory_id?: number;
  payment_method_id?: number;
  budget_type_id?: number;
  is_shared?: boolean;
}

export interface BulkTransactionUploadRequest {
  transactions: ManualTransaction[];
  filename?: string;
  allow_duplicates?: boolean;
}

export interface BulkUploadResponse {
  bulk_upload_id: number;
  total_rows: number;
  successful_count: number;
  failed_count: number;
  duplicate_count: number;
  status: 'COMPLETED' | 'PARTIAL_FAILURE' | 'PENDING_REVIEW' | 'FAILED';
  error_message?: string;
  created_transactions: ManualTransaction[];
  failed_rows?: Array<{
    row: number;
    error: string;
    data?: any;
  }>;
}

export interface BulkUploadStatus {
  bulk_upload_id: number;
  filename: string;
  total_rows: number;
  successful_count: number;
  failed_count: number;
  duplicate_count: number;
  status: string;
  uploaded_at: string;
  processed_at?: string;
}

export interface DuplicateConfirmationRequest {
  duplicate_transaction_ids: number[];
  action: 'ACCEPT' | 'REJECT';
  user_notes?: string;
}

export interface DuplicateConfirmationResponse {
  status: string;
  action: string;
  duplicates_processed: number;
}

@Injectable({
  providedIn: 'root'
})
export class ManualTransactionService {
  private apiUrl = 'http://localhost:8000/transactions/manual';
  private metadataSubject = new BehaviorSubject<TransactionMetadata | null>(null);
  public metadata$ = this.metadataSubject.asObservable();

  private httpHeaders = new HttpHeaders({
    'Content-Type': 'application/json'
  });

  constructor(
    private http: HttpClient,
    private cacheService: CacheService
  ) {
    this.loadMetadata();
  }

  /**
   * Get Authorization headers with JWT token
   */
  private getAuthHeaders(): HttpHeaders {
    const token = this.getToken();
    if (token) {
      return this.httpHeaders.set('Authorization', `Bearer ${token}`);
    }
    return this.httpHeaders;
  }

  /**
   * Get JWT token from localStorage
   */
  private getToken(): string | null {
    if (typeof window !== 'undefined' && window.localStorage) {
      return localStorage.getItem('access_token');
    }
    return null;
  }

  /**
   * Load transaction metadata (categories, payment methods, etc.)
   * Caches results locally for performance
   */
  private loadMetadata(): void {
    const cacheKey = 'transaction_metadata';
    const cached = this.cacheService.get(cacheKey);

    if (cached) {
      this.metadataSubject.next(cached);
    } else {
      this.getTransactionMetadata().subscribe(
        (metadata) => {
          this.cacheService.set(cacheKey, metadata, 3600000); // Cache for 1 hour
          this.metadataSubject.next(metadata);
        },
        (error) => {
          console.error('Failed to load transaction metadata:', error);
        }
      );
    }
  }

  /**
   * Get all transaction metadata
   * @returns Observable of TransactionMetadata
   */
  public getTransactionMetadata(): Observable<TransactionMetadata> {
    return this.http.get<TransactionMetadata>(
      `${this.apiUrl}/metadata`,
      { headers: this.getAuthHeaders() }
    ).pipe(
      tap((metadata) => {
        this.metadataSubject.next(metadata);
      }),
      catchError((error) => {
        console.error('Error fetching transaction metadata:', error);
        return throwError(() => new Error('Failed to fetch transaction metadata'));
      })
    );
  }

  /**
   * Create a single manual transaction
   * @param transaction Transaction data to create
   * @returns Observable of created transaction
   */
  public createTransaction(transaction: ManualTransaction): Observable<ManualTransaction> {
    return this.http.post<ManualTransaction>(
      `${this.apiUrl}/`,
      transaction,
      { headers: this.getAuthHeaders() }
    ).pipe(
      tap((response) => {
        // Invalidate cache on new transaction
        this.invalidateTransactionCaches();
      }),
      catchError((error) => {
        console.error('Error creating transaction:', error);
        return throwError(() => new Error(error.error?.detail || 'Failed to create transaction'));
      })
    );
  }

  /**
   * Bulk upload transactions from array
   * Handles duplicate detection and returns detailed report
   * @param request Bulk upload request with transactions array
   * @returns Observable of bulk upload response
   */
  public bulkCreateTransactions(request: BulkTransactionUploadRequest): Observable<BulkUploadResponse> {
    return this.http.post<BulkUploadResponse>(
      `${this.apiUrl}/bulk`,
      request,
      { headers: this.getAuthHeaders() }
    ).pipe(
      tap((response) => {
        // Invalidate cache on bulk create
        this.invalidateTransactionCaches();
      }),
      catchError((error) => {
        console.error('Error bulk uploading transactions:', error);
        return throwError(() => new Error(error.error?.detail || 'Failed to bulk upload transactions'));
      })
    );
  }

  /**
   * Update an existing manual transaction
   * @param transactionId ID of transaction to update
   * @param updateData Updated transaction fields
   * @returns Observable of updated transaction
   */
  public updateTransaction(
    transactionId: number,
    updateData: ManualTransactionUpdateRequest
  ): Observable<ManualTransaction> {
    return this.http.put<ManualTransaction>(
      `${this.apiUrl}/${transactionId}`,
      updateData,
      { headers: this.getAuthHeaders() }
    ).pipe(
      tap((response) => {
        // Invalidate cache on update
        this.invalidateTransactionCaches();
      }),
      catchError((error) => {
        console.error('Error updating transaction:', error);
        return throwError(() => new Error(error.error?.detail || 'Failed to update transaction'));
      })
    );
  }

  /**
   * Delete a manual transaction
   * @param transactionId ID of transaction to delete
   * @returns Observable of delete response
   */
  public deleteTransaction(transactionId: number): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(
      `${this.apiUrl}/${transactionId}`,
      { headers: this.getAuthHeaders() }
    ).pipe(
      tap((response) => {
        // Invalidate cache on delete
        this.invalidateTransactionCaches();
      }),
      catchError((error) => {
        console.error('Error deleting transaction:', error);
        return throwError(() => new Error(error.error?.detail || 'Failed to delete transaction'));
      })
    );
  }

  /**
   * Get status of a bulk upload
   * @param bulkUploadId ID of bulk upload to check
   * @returns Observable of bulk upload status
   */
  public getBulkUploadStatus(bulkUploadId: number): Observable<BulkUploadStatus> {
    return this.http.get<BulkUploadStatus>(
      `${this.apiUrl}/bulk/${bulkUploadId}`,
      { headers: this.getAuthHeaders() }
    ).pipe(
      catchError((error) => {
        console.error('Error fetching bulk upload status:', error);
        return throwError(() => new Error(error.error?.detail || 'Failed to fetch bulk upload status'));
      })
    );
  }

  /**
   * Confirm handling of duplicate transactions
   * @param confirmation Confirmation request (ACCEPT or REJECT)
   * @returns Observable of confirmation response
   */
  public confirmDuplicateHandling(
    confirmation: DuplicateConfirmationRequest
  ): Observable<DuplicateConfirmationResponse> {
    return this.http.post<DuplicateConfirmationResponse>(
      `${this.apiUrl}/duplicates/confirm`,
      confirmation,
      { headers: this.getAuthHeaders() }
    ).pipe(
      tap((response) => {
        // Invalidate cache on confirmation
        this.invalidateTransactionCaches();
      }),
      catchError((error) => {
        console.error('Error confirming duplicate handling:', error);
        return throwError(() => new Error(error.error?.detail || 'Failed to confirm duplicate handling'));
      })
    );
  }

  /**
   * Parse CSV file and convert to transaction objects
   * @param file CSV file to parse
   * @param delimiter CSV delimiter (default: comma)
   * @returns Array of parsed transactions
   */
  public parseCSVFile(file: File, delimiter: string = ','): Promise<ManualTransaction[]> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();

      reader.onload = (event: any) => {
        try {
          const csv = event.target.result;
          const lines = csv.split('\n').filter((line: string) => line.trim().length > 0);

          if (lines.length < 2) {
            reject(new Error('CSV file must contain at least a header row and one data row'));
            return;
          }

          // Parse header
          const headers = lines[0].split(delimiter).map((h: string) => h.trim().toLowerCase());

          // Validate required headers
          const requiredHeaders = [
            'date', 'amount', 'currency', 'description',
            'transaction_type_id', 'payment_method_id', 'card_id'
          ];

          const missingHeaders = requiredHeaders.filter(h => !headers.includes(h));
          if (missingHeaders.length > 0) {
            reject(new Error(`Missing required CSV columns: ${missingHeaders.join(', ')}`));
            return;
          }

          // Parse data rows
          const transactions: ManualTransaction[] = [];

          for (let i = 1; i < lines.length; i++) {
            const values = lines[i].split(delimiter).map((v: string) => v.trim());

            // Create transaction object
            const transaction: ManualTransaction = {
              date: values[headers.indexOf('date')],
              amount: parseFloat(values[headers.indexOf('amount')]),
              currency: (values[headers.indexOf('currency')] || 'USD') as 'USD' | 'CAD',
              description: values[headers.indexOf('description')],
              merchant: values[headers.indexOf('merchant')] || undefined,
              notes: values[headers.indexOf('notes')] || undefined,
              transaction_type_id: parseInt(values[headers.indexOf('transaction_type_id')]),
              expense_category_id: values[headers.indexOf('expense_category_id')]
                ? parseInt(values[headers.indexOf('expense_category_id')])
                : undefined,
              expense_subcategory_id: values[headers.indexOf('expense_subcategory_id')]
                ? parseInt(values[headers.indexOf('expense_subcategory_id')])
                : undefined,
              payment_method_id: parseInt(values[headers.indexOf('payment_method_id')]),
              budget_type_id: values[headers.indexOf('budget_type_id')]
                ? parseInt(values[headers.indexOf('budget_type_id')])
                : undefined,
              card_id: parseInt(values[headers.indexOf('card_id')]),
              is_shared: (values[headers.indexOf('is_shared')] || 'false').toLowerCase() === 'true'
            };

            // Validate parsed transaction
            const validationError = this.validateTransaction(transaction);
            if (validationError) {
              reject(new Error(`Row ${i + 1} validation error: ${validationError}`));
              return;
            }

            transactions.push(transaction);
          }

          resolve(transactions);
        } catch (error: any) {
          reject(new Error(`CSV parsing error: ${error.message}`));
        }
      };

      reader.onerror = () => {
        reject(new Error('Failed to read CSV file'));
      };

      reader.readAsText(file);
    });
  }

  /**
   * Validate transaction data
   * @param transaction Transaction to validate
   * @returns Error message if validation fails, null otherwise
   */
  public validateTransaction(transaction: ManualTransaction): string | null {
    // Validate date
    if (!transaction.date || !/^\d{4}-\d{2}-\d{2}$/.test(transaction.date)) {
      return 'Invalid date format. Use YYYY-MM-DD.';
    }

    const transactionDate = new Date(transaction.date);
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    if (transactionDate > today) {
      return 'Transaction date cannot be in the future.';
    }

    const twoYearsAgo = new Date();
    twoYearsAgo.setFullYear(twoYearsAgo.getFullYear() - 2);

    if (transactionDate < twoYearsAgo) {
      return 'Transaction date cannot be more than 2 years old.';
    }

    // Validate amount
    if (!transaction.amount || transaction.amount <= 0) {
      return 'Amount must be a positive number.';
    }

    // Validate currency
    if (!['USD', 'CAD'].includes(transaction.currency)) {
      return 'Currency must be USD or CAD.';
    }

    // Validate required fields
    if (!transaction.description || transaction.description.trim().length === 0) {
      return 'Description is required.';
    }

    if (!transaction.transaction_type_id) {
      return 'Transaction type is required.';
    }

    if (!transaction.payment_method_id) {
      return 'Payment method is required.';
    }

    if (!transaction.card_id) {
      return 'Card is required.';
    }

    return null;
  }

  /**
   * Generate CSV template for bulk upload
   * @returns CSV template string
   */
  public generateCSVTemplate(): string {
    const headers = [
      'date',
      'description',
      'amount',
      'currency',
      'merchant',
      'transaction_type_id',
      'expense_category_id',
      'expense_subcategory_id',
      'payment_method_id',
      'budget_type_id',
      'card_id',
      'is_shared',
      'notes'
    ];

    const exampleRows = [
      ['2025-10-15', 'Whole Foods', '45.99', 'USD', 'Whole Foods', '1', '1', '1', '1', '1', '1', 'false', 'Weekly groceries'],
      ['2025-10-14', 'Shell Gas Station', '55.00', 'USD', 'Shell', '1', '2', '4', '1', '1', '1', 'false', 'Gas fill-up'],
      ['2025-10-13', 'Amazon Purchase', '120.00', 'USD', 'Amazon', '1', '3', '8', '2', '2', '2', 'true', 'Electronics purchase']
    ];

    const allRows = [headers, ...exampleRows];
    return allRows.map(row => row.join(',')).join('\n');
  }

  /**
   * Download CSV template
   */
  public downloadCSVTemplate(): void {
    const csv = this.generateCSVTemplate();
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);

    link.setAttribute('href', url);
    link.setAttribute('download', 'transaction_template.csv');
    link.style.visibility = 'hidden';

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  /**
   * Invalidate transaction-related caches
   */
  private invalidateTransactionCaches(): void {
    // Invalidate metadata and any transaction lists
    this.cacheService.remove('transaction_metadata');
    // Additional cache invalidation can be added here
  }

  /**
   * Get category by ID from metadata
   * @param categoryId Category ID
   * @returns Category item or null
   */
  public getCategoryById(categoryId: number): MetadataItem | null {
    const metadata = this.metadataSubject.value;
    if (!metadata) return null;

    return metadata.expense_categories.find(cat => cat.id === categoryId) || null;
  }

  /**
   * Get subcategories for a category
   * @param categoryId Category ID
   * @returns Array of subcategories
   */
  public getSubcategoriesForCategory(categoryId: number): MetadataItem[] {
    const metadata = this.metadataSubject.value;
    if (!metadata) return [];

    // Note: This is a frontend-side filter. Backend subcategories have expense_category_id
    // For now, return all subcategories - backend filtering would be more efficient
    return metadata.expense_categories; // Placeholder - actual implementation depends on API response structure
  }

  /**
   * Get payment method by ID
   * @param methodId Payment method ID
   * @returns Payment method item or null
   */
  public getPaymentMethodById(methodId: number): MetadataItem | null {
    const metadata = this.metadataSubject.value;
    if (!metadata) return null;

    return metadata.payment_methods.find(m => m.id === methodId) || null;
  }

  /**
   * Format date for display
   * @param date Date string (YYYY-MM-DD)
   * @returns Formatted date string
   */
  public formatDate(date: string): string {
    try {
      const d = new Date(date);
      return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
    } catch {
      return date;
    }
  }

  /**
   * Format currency for display
   * @param amount Amount to format
   * @param currency Currency code
   * @returns Formatted currency string
   */
  public formatCurrency(amount: number, currency: string = 'USD'): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency
    }).format(amount);
  }
}
