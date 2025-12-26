import { Component, OnInit, OnDestroy, Inject, PLATFORM_ID } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { PlaidService, PlaidAccount, PlaidSyncResponse } from '../../services/plaid.service';
import { BankConnectionModalComponent } from '../bank-connection-modal/bank-connection-modal.component';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

interface BankWithStatus extends PlaidAccount {
  isSyncing?: boolean;
  syncError?: string;
}

@Component({
  selector: 'app-connected-banks',
  standalone: true,
  imports: [CommonModule, BankConnectionModalComponent],
  templateUrl: './connected-banks.component.html',
  styleUrls: ['./connected-banks.component.scss']
})
export class ConnectedBanksComponent implements OnInit, OnDestroy {
  banks: BankWithStatus[] = [];
  isLoading = false;
  error: string | null = null;
  showConnectionModal = false;
  showDisconnectConfirm = false;
  bankToDisconnect: BankWithStatus | null = null;
  successMessage: string | null = null;
  private destroy$ = new Subject<void>();

  constructor(
    private plaidService: PlaidService,
    @Inject(PLATFORM_ID) private platformId: Object
  ) {}

  ngOnInit() {
    // Only load in browser to avoid SSR issues
    if (isPlatformBrowser(this.platformId)) {
      this.loadConnectedBanks();
    }
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }

  /**
   * Load all connected bank accounts
   */
  loadConnectedBanks() {
    this.isLoading = true;
    this.error = null;

    this.plaidService.getConnectedAccounts()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (accounts) => {
          this.banks = accounts.map(account => ({
            ...account,
            isSyncing: false,
            syncError: undefined
          }));
          this.isLoading = false;
        },
        error: (err) => {
          console.error('Error loading banks:', err);
          this.error = 'Failed to load connected banks. Please try again.';
          this.isLoading = false;
        }
      });
  }

  /**
   * Open bank connection modal
   */
  openConnectionModal() {
    this.showConnectionModal = true;
  }

  /**
   * Close bank connection modal
   */
  closeConnectionModal() {
    this.showConnectionModal = false;
  }

  /**
   * Handle successful bank connection
   */
  handleConnectionSuccess(result: any) {
    this.showConnectionModal = false;
    this.showSuccessMessage(`Successfully connected ${result.card.bank_name}!`);
    this.loadConnectedBanks();
  }

  /**
   * Sync transactions for a specific bank
   */
  syncBank(bank: BankWithStatus) {
    bank.isSyncing = true;
    bank.syncError = undefined;

    this.plaidService.syncTransactions(bank.id)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response: PlaidSyncResponse) => {
          bank.isSyncing = false;
          bank.last_sync_date = response.sync_date;
          this.showSuccessMessage(
            `Synced ${response.transactions_added} new transaction${response.transactions_added !== 1 ? 's' : ''}`
          );
        },
        error: (err) => {
          console.error('Error syncing bank:', err);
          bank.isSyncing = false;
          bank.syncError = 'Sync failed';
          this.showErrorMessage('Failed to sync transactions. Please try again.');
        }
      });
  }

  /**
   * Show disconnect confirmation
   */
  confirmDisconnect(bank: BankWithStatus) {
    this.bankToDisconnect = bank;
    this.showDisconnectConfirm = true;
  }

  /**
   * Cancel disconnect
   */
  cancelDisconnect() {
    this.bankToDisconnect = null;
    this.showDisconnectConfirm = false;
  }

  /**
   * Disconnect a bank account
   */
  disconnectBank() {
    if (!this.bankToDisconnect) return;

    const bank = this.bankToDisconnect;
    this.showDisconnectConfirm = false;

    this.plaidService.disconnectAccount(bank.id)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.showSuccessMessage(`${bank.bank_name} disconnected successfully`);
          this.loadConnectedBanks();
          this.bankToDisconnect = null;
        },
        error: (err) => {
          console.error('Error disconnecting bank:', err);
          this.showErrorMessage('Failed to disconnect bank. Please try again.');
          this.bankToDisconnect = null;
        }
      });
  }

  /**
   * Format date for display
   */
  formatDate(dateString: string | undefined): string {
    if (!dateString) return 'Never';
    
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min${diffMins !== 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
    
    return date.toLocaleDateString();
  }

  /**
   * Show success message
   */
  showSuccessMessage(message: string) {
    this.successMessage = message;
    setTimeout(() => {
      this.successMessage = null;
    }, 5000);
  }

  /**
   * Show error message
   */
  showErrorMessage(message: string) {
    this.error = message;
    setTimeout(() => {
      this.error = null;
    }, 5000);
  }

  /**
   * Get bank icon based on name
   */
  getBankIcon(bankName: string): string {
    // Return appropriate icon based on bank name
    // For now, return a generic bank icon
    return '🏦';
  }
}

