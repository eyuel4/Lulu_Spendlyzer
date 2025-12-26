import { Component, EventEmitter, Input, Output, OnInit, OnDestroy, Inject, PLATFORM_ID } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { PlaidService, LinkTokenResponse } from '../../services/plaid.service';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

declare const Plaid: any;

@Component({
  selector: 'app-bank-connection-modal',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './bank-connection-modal.component.html',
  styleUrls: ['./bank-connection-modal.component.scss']
})
export class BankConnectionModalComponent implements OnInit, OnDestroy {
  @Input() isOpen = false;
  @Output() closeModal = new EventEmitter<void>();
  @Output() connectionSuccess = new EventEmitter<any>();

  isLoading = false;
  error: string | null = null;
  linkToken: string | null = null;
  plaidHandler: any = null;
  private destroy$ = new Subject<void>();

  constructor(
    private plaidService: PlaidService,
    @Inject(PLATFORM_ID) private platformId: Object
  ) {}

  ngOnInit() {
    // Only initialize Plaid in browser environment
    if (this.isOpen && isPlatformBrowser(this.platformId)) {
      this.initializePlaid();
    }
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
    if (this.plaidHandler) {
      this.plaidHandler.destroy();
    }
  }

  ngOnChanges() {
    // Only initialize Plaid in browser environment
    if (this.isOpen && !this.linkToken && isPlatformBrowser(this.platformId)) {
      this.initializePlaid();
    }
  }

  /**
   * Initialize Plaid Link
   */
  initializePlaid() {
    this.isLoading = true;
    this.error = null;

    this.plaidService.createLinkToken()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response: LinkTokenResponse) => {
          this.linkToken = response.link_token;
          this.createPlaidLink();
          this.isLoading = false;
        },
        error: (err) => {
          console.error('Error creating link token:', err);
          this.error = 'Failed to initialize bank connection. Please try again.';
          this.isLoading = false;
        }
      });
  }

  /**
   * Create Plaid Link handler
   */
  createPlaidLink() {
    // Only run in browser
    if (!isPlatformBrowser(this.platformId)) {
      return;
    }
    
    if (!this.linkToken || typeof Plaid === 'undefined') {
      this.error = 'Plaid is not loaded. Please refresh the page.';
      return;
    }

    this.plaidHandler = Plaid.create({
      token: this.linkToken,
      onSuccess: (public_token: string, metadata: any) => {
        this.handlePlaidSuccess(public_token, metadata);
      },
      onExit: (err: any, metadata: any) => {
        this.handlePlaidExit(err, metadata);
      },
      onEvent: (eventName: string, metadata: any) => {
        console.log('Plaid event:', eventName, metadata);
      }
    });

    // Auto-open Plaid Link
    this.plaidHandler.open();
  }

  /**
   * Handle successful Plaid connection
   */
  handlePlaidSuccess(publicToken: string, metadata: any) {
    this.isLoading = true;
    this.error = null;

    const exchangeData = {
      public_token: publicToken,
      institution_id: metadata.institution?.institution_id,
      institution_name: metadata.institution?.name,
      accounts: metadata.accounts
    };

    this.plaidService.exchangePublicToken(exchangeData)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          this.isLoading = false;
          this.connectionSuccess.emit(response);
          this.close();
        },
        error: (err) => {
          console.error('Error exchanging token:', err);
          this.error = 'Failed to connect bank account. Please try again.';
          this.isLoading = false;
        }
      });
  }

  /**
   * Handle Plaid Link exit
   */
  handlePlaidExit(err: any, metadata: any) {
    if (err) {
      console.error('Plaid error:', err);
      this.error = 'Bank connection was cancelled or failed.';
    }
    // User cancelled, just close
    this.close();
  }

  /**
   * Retry connection
   */
  retry() {
    this.error = null;
    this.linkToken = null;
    this.initializePlaid();
  }

  /**
   * Close modal
   */
  close() {
    this.closeModal.emit();
  }
}

