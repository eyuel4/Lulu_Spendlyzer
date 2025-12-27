import { Injectable, Inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { AuthService } from './auth.service';

export interface TransactionFilters {
  skip?: number;
  limit?: number;
  month?: string;
  card_id?: number;
  bank_name?: string;
  merchant_name?: string;
  expense_category_id?: number;
  custom_category?: string;
  start_date?: string;
  end_date?: string;
  currency?: string;
}

export interface Transaction {
  id: number;
  user_id: number;
  card_id: number;
  name: string;
  merchant_name?: string;
  date: string;
  amount: number;
  plaid_category?: string;
  custom_category?: string;
  budget_type?: string;
  month_id: string;
  plaid_transaction_id: string;
  currency: string;
  created_at: string;
  bank_name?: string;
  card_name?: string;
  expense_category_name?: string;
  expense_category_id?: number;
}

export interface DropdownMetadata {
  merchants: string[];
  banks: Array<{ id: number; name: string }>;
  cards: Array<{ id: number; name: string; bank_name: string; last4: string }>;
  expense_categories: Array<{ id: number; name: string; description?: string }>;
  custom_categories: string[];
}

export interface TransactionUpdate {
  name?: string;
  merchant_name?: string;
  date?: string;
  amount?: number;
  plaid_category?: string;
  custom_category?: string;
  budget_type?: string;
  month_id?: string;
  card_id?: number;
  expense_category_id?: number;
}

@Injectable({
  providedIn: 'root'
})
export class TransactionService {
  private apiUrl = `${environment.apiUrl}/transactions`;

  constructor(
    private http: HttpClient,
    private authService: AuthService,
    @Inject(PLATFORM_ID) private platformId: Object
  ) {}

  private getHeaders(): HttpHeaders {
    const token = this.authService.getToken() || '';
    
    return new HttpHeaders({
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    });
  }

  /**
   * Get transactions with optional filters
   */
  getTransactions(filters: TransactionFilters = {}): Observable<Transaction[]> {
    let params = new HttpParams();
    
    if (filters.skip !== undefined) params = params.set('skip', filters.skip.toString());
    if (filters.limit !== undefined) params = params.set('limit', filters.limit.toString());
    if (filters.month) params = params.set('month', filters.month);
    if (filters.card_id !== undefined) params = params.set('card_id', filters.card_id.toString());
    if (filters.bank_name) params = params.set('bank_name', filters.bank_name);
    if (filters.merchant_name) params = params.set('merchant_name', filters.merchant_name);
    if (filters.expense_category_id !== undefined) params = params.set('expense_category_id', filters.expense_category_id.toString());
    if (filters.custom_category) params = params.set('custom_category', filters.custom_category);
    if (filters.start_date) params = params.set('start_date', filters.start_date);
    if (filters.end_date) params = params.set('end_date', filters.end_date);
    if (filters.currency) params = params.set('currency', filters.currency);

    return this.http.get<Transaction[]>(this.apiUrl, {
      headers: this.getHeaders(),
      params
    });
  }

  /**
   * Get a single transaction by ID
   */
  getTransaction(id: number): Observable<Transaction> {
    return this.http.get<Transaction>(`${this.apiUrl}/${id}`, {
      headers: this.getHeaders()
    });
  }

  /**
   * Get dropdown metadata for transaction editing
   */
  getDropdownMetadata(): Observable<DropdownMetadata> {
    return this.http.get<DropdownMetadata>(`${this.apiUrl}/dropdown-metadata/`, {
      headers: this.getHeaders()
    });
  }

  /**
   * Update a transaction
   */
  updateTransaction(id: number, updates: TransactionUpdate): Observable<Transaction> {
    return this.http.put<Transaction>(`${this.apiUrl}/${id}`, updates, {
      headers: this.getHeaders()
    });
  }
}

