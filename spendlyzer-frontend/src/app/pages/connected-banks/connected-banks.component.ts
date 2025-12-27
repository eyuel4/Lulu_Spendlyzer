import { Component, OnInit, OnDestroy, Inject, PLATFORM_ID } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { PlaidService, PlaidAccount, PlaidSyncResponse } from '../../services/plaid.service';
import { BankConnectionModalComponent } from '../bank-connection-modal/bank-connection-modal.component';
import { ThemeService } from '../../services/theme.service';
import { AuthService } from '../../services/auth.service';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

interface BankWithStatus extends PlaidAccount {
  isSyncing?: boolean;
  syncError?: string;
}

interface BankGroup {
  bankName: string;
  cards: BankWithStatus[];
  lastSyncDate?: string; // Most recent sync date among all cards
}

@Component({
  selector: 'app-connected-banks',
  standalone: true,
  imports: [CommonModule, BankConnectionModalComponent, RouterModule],
  templateUrl: './connected-banks.component.html',
  styleUrls: ['./connected-banks.component.scss']
})
export class ConnectedBanksComponent implements OnInit, OnDestroy {
  banks: BankWithStatus[] = [];
  bankGroups: BankGroup[] = [];
  isLoading = false;
  error: string | null = null;
  showConnectionModal = false;
  showDisconnectConfirm = false;
  bankToDisconnect: BankWithStatus | null = null;
  successMessage: string | null = null;
  connectedBanksCount = 0;
  currentTheme: 'light' | 'dark' = 'light';
  private destroy$ = new Subject<void>();

  constructor(
    private plaidService: PlaidService,
    private themeService: ThemeService,
    private authService: AuthService,
    public router: Router,
    @Inject(PLATFORM_ID) private platformId: Object
  ) {}

  ngOnInit() {
    // Only load in browser to avoid SSR issues
    if (isPlatformBrowser(this.platformId)) {
      // Verify user is authenticated before loading
      this.verifyAuthentication();
    }
  }

  /**
   * Verify user authentication before loading data
   */
  verifyAuthentication() {
    const token = this.authService.getToken();
    if (!token) {
      console.warn('No token found, redirecting to signin');
      this.router.navigate(['/signin']);
      return;
    }

    // Verify token is valid by fetching current user
    this.authService.fetchCurrentUser()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          // User is authenticated, proceed with loading
          // Subscribe to theme changes
          this.themeService.currentTheme$
            .pipe(takeUntil(this.destroy$))
            .subscribe(theme => {
              this.currentTheme = theme;
            });
          
          this.loadConnectedBanks();
        },
        error: (err) => {
          console.error('Authentication verification failed:', err);
          // If auth fails, redirect will be handled by interceptor
          // But we can also redirect here as a fallback
          if (err.status === 401) {
            this.router.navigate(['/signin']);
          }
        }
      });
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }

  /**
   * Load all connected bank accounts
   */
  loadConnectedBanks() {
    // Double-check token before making API call
    const token = this.authService.getToken();
    if (!token) {
      console.warn('No token in loadConnectedBanks, redirecting to signin');
      this.router.navigate(['/signin']);
      return;
    }

    console.log('Loading connected banks with token');

    this.isLoading = true;
    this.error = null;

    this.plaidService.getConnectedAccounts()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (accounts) => {
          console.log('Connected banks loaded successfully:', accounts.length);
          this.banks = accounts.map(account => ({
            ...account,
            isSyncing: false,
            syncError: undefined
          }));
          this.connectedBanksCount = accounts.length;
          this.bankGroups = this.groupBanksByBankName(this.banks);
          this.isLoading = false;
        },
        error: (err) => {
          console.error('Error loading banks:', err);
          console.error('Error status:', err.status);
          // Don't redirect here - let the interceptor handle 401 errors
          // Only show error message for other errors
          if (err.status !== 401) {
            this.error = 'Failed to load connected banks. Please try again.';
          } else {
            console.warn('401 error - interceptor will handle redirect');
          }
          this.isLoading = false;
        }
      });
  }

  /**
   * Group banks by bank name
   */
  groupBanksByBankName(banks: BankWithStatus[]): BankGroup[] {
    const groupsMap = new Map<string, BankWithStatus[]>();
    
    // Group cards by bank name
    banks.forEach(bank => {
      const bankName = bank.bank_name;
      if (!groupsMap.has(bankName)) {
        groupsMap.set(bankName, []);
      }
      groupsMap.get(bankName)!.push(bank);
    });
    
    // Convert map to array and calculate last sync date for each group
    const groups: BankGroup[] = Array.from(groupsMap.entries()).map(([bankName, cards]) => {
      // Find the most recent sync date among all cards
      const syncDates = cards
        .map(card => card.last_sync_date)
        .filter(date => date !== undefined && date !== null) as string[];
      
      let lastSyncDate: string | undefined;
      if (syncDates.length > 0) {
        // Sort dates and get the most recent
        syncDates.sort((a, b) => new Date(b).getTime() - new Date(a).getTime());
        lastSyncDate = syncDates[0];
      }
      
      return {
        bankName,
        cards,
        lastSyncDate
      };
    });
    
    // Sort groups by bank name
    groups.sort((a, b) => a.bankName.localeCompare(b.bankName));
    
    return groups;
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
   * Toggle sync enabled status for a bank
   */
  toggleSync(bank: BankWithStatus) {
    const newStatus = !bank.sync_enabled;
    bank.isSyncing = true;

    this.plaidService.toggleSync(bank.id, newStatus)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (updatedAccount) => {
          bank.sync_enabled = updatedAccount.sync_enabled;
          bank.isSyncing = false;
          // Regroup banks to update the display
          this.bankGroups = this.groupBanksByBankName(this.banks);
          this.showSuccessMessage(
            `Auto-sync ${updatedAccount.sync_enabled ? 'enabled' : 'disabled'} for ${bank.bank_name}`
          );
        },
        error: (err) => {
          console.error('Error toggling sync:', err);
          bank.isSyncing = false;
          this.showErrorMessage('Failed to update sync status. Please try again.');
        }
      });
  }

  /**
   * Sync transactions for a specific bank (manual sync)
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
          // Regroup banks to update the display with new sync date
          this.bankGroups = this.groupBanksByBankName(this.banks);
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

