import { Injectable, Inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { AuthService } from './auth.service';

export interface LinkTokenResponse {
  link_token: string;
  expiration: string;
}

export interface PublicTokenExchange {
  public_token: string;
  institution_id?: string;
  institution_name?: string;
  accounts?: any[];
}

export interface PlaidAccount {
  id: number;
  bank_name: string;
  card_name: string;
  last4: string;
  plaid_item_id?: string;
  plaid_institution_id?: string;
  last_sync_date?: string;
  sync_enabled?: boolean;
  created_at: string;
  updated_at: string;
}

export interface PlaidSyncResponse {
  success: boolean;
  message: string;
  transactions_added: number;
  transactions_updated: number;
  card_id: number;
  sync_date: string;
}

export interface PlaidDisconnectResponse {
  success: boolean;
  message: string;
  card_id: number;
}

@Injectable({
  providedIn: 'root'
})
export class PlaidService {
  private apiUrl = `${environment.apiUrl}/plaid`;

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
   * Create a Plaid Link token
   */
  createLinkToken(): Observable<LinkTokenResponse> {
    const url = `${this.apiUrl}/create-link-token`;
    console.log('PlaidService: Creating link token, URL:', url);
    console.log('PlaidService: Headers:', this.getHeaders().keys());
    
    return this.http.post<LinkTokenResponse>(
      url,
      {},
      { headers: this.getHeaders() }
    );
  }

  /**
   * Exchange public token for access token and sync initial transactions
   */
  exchangePublicToken(exchangeData: PublicTokenExchange): Observable<any> {
    return this.http.post(
      `${this.apiUrl}/exchange-token`,
      exchangeData,
      { headers: this.getHeaders() }
    );
  }

  /**
   * Get all connected bank accounts
   */
  getConnectedAccounts(): Observable<PlaidAccount[]> {
    return this.http.get<PlaidAccount[]>(
      `${this.apiUrl}/accounts`,
      { headers: this.getHeaders() }
    );
  }

  /**
   * Manually sync transactions for a specific card
   */
  syncTransactions(cardId: number): Observable<PlaidSyncResponse> {
    return this.http.post<PlaidSyncResponse>(
      `${this.apiUrl}/sync-transactions/${cardId}`,
      {},
      { headers: this.getHeaders() }
    );
  }

  /**
   * Toggle sync enabled status for a bank account
   */
  toggleSync(cardId: number, enabled: boolean): Observable<PlaidAccount> {
    return this.http.put<PlaidAccount>(
      `${this.apiUrl}/toggle-sync/${cardId}?enabled=${enabled}`,
      {},
      { headers: this.getHeaders() }
    );
  }

  /**
   * Disconnect a bank account
   */
  disconnectAccount(cardId: number): Observable<PlaidDisconnectResponse> {
    return this.http.delete<PlaidDisconnectResponse>(
      `${this.apiUrl}/disconnect/${cardId}`,
      { headers: this.getHeaders() }
    );
  }
}

