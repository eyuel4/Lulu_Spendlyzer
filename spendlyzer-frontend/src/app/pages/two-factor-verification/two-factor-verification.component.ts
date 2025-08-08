import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { Router, ActivatedRoute } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { AccountSettingsService, ResendCodeResponse, TwoFactorCodeResponse } from '../../services/account-settings.service';
import { NotificationService } from '../../services/notification.service';
import { TrustedDeviceService } from '../../services/trusted-device.service';

@Component({
  selector: 'app-two-factor-verification',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  template: `
    <div class="min-h-screen bg-gradient-to-br from-indigo-50 to-blue-100 dark:from-slate-900 dark:to-slate-800 flex items-center justify-center p-4">
      <div class="max-w-md w-full bg-white dark:bg-slate-800 rounded-xl shadow-lg p-8">
        <div class="text-center mb-8">
          <div class="w-16 h-16 bg-indigo-100 dark:bg-indigo-900 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg class="w-8 h-8 text-indigo-600 dark:text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path>
            </svg>
          </div>
          <h2 class="text-2xl font-bold text-slate-900 dark:text-white">Two-Factor Authentication</h2>
          <p class="text-slate-600 dark:text-slate-400 mt-2">
            Please enter the verification code from your {{ twoFAMethod }}.
          </p>
          <p *ngIf="expirationMessage" class="text-sm text-amber-600 dark:text-amber-400 mt-2 font-medium">
            {{ expirationMessage }}
          </p>
        </div>

        <form [formGroup]="verificationForm" (ngSubmit)="verifyCode()" class="space-y-6">
          <div>
            <label for="code" class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
              Verification Code
            </label>
            <input
              id="code"
              type="text"
              formControlName="code"
              placeholder="Enter 6-digit code"
              class="w-full px-4 py-3 border border-slate-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400 focus:border-transparent bg-white dark:bg-slate-700 text-slate-900 dark:text-white placeholder-slate-500 dark:placeholder-slate-400"
              maxlength="6"
            >
          </div>

          <!-- Remember Device Checkbox -->
          <div class="flex items-center">
            <input
              id="rememberDevice"
              type="checkbox"
              formControlName="rememberDevice"
              class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-slate-300 rounded"
            >
            <label for="rememberDevice" class="ml-2 block text-sm text-slate-700 dark:text-slate-300">
              Remember this device for 7 days
            </label>
          </div>

          <button
            type="submit"
            [disabled]="verificationForm.invalid || loading"
            class="w-full bg-indigo-600 dark:bg-indigo-500 text-white py-3 px-4 rounded-lg hover:bg-indigo-700 dark:hover:bg-indigo-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 dark:focus:ring-offset-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
          >
            <span *ngIf="loading" class="flex items-center justify-center">
              <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Verifying...
            </span>
            <span *ngIf="!loading">Verify</span>
          </button>
        </form>

        <!-- Only show resend button for SMS and Email methods -->
        <div *ngIf="canResendCode" class="mt-6 text-center">
          <button
            (click)="resendCode()"
            [disabled]="resendLoading"
            class="text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
          >
            <span *ngIf="resendLoading">Sending...</span>
            <span *ngIf="!resendLoading">Resend Code</span>
          </button>
        </div>

        <div class="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg">
          <h3 class="text-sm font-medium text-blue-800 dark:text-blue-200 mb-2">Need help?</h3>
          <p class="text-sm text-blue-700 dark:text-blue-300">
            If you're having trouble with two-factor authentication, you can use a backup code or contact support.
          </p>
        </div>
      </div>
    </div>
  `,
  styleUrls: ['./two-factor-verification.component.scss']
})
export class TwoFactorVerificationComponent implements OnInit {
  verificationForm: FormGroup;
  loading = false;
  resendLoading = false;
  twoFAMethod = 'authenticator';
  expirationMessage = '';
  canResendCode = false;
  codeExpiresAt = '';

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private route: ActivatedRoute,
    private authService: AuthService,
    private accountSettingsService: AccountSettingsService,
    private notificationService: NotificationService,
    private trustedDeviceService: TrustedDeviceService
  ) {
    this.verificationForm = this.fb.group({
      code: ['', [Validators.required, Validators.minLength(6), Validators.maxLength(6)]],
      rememberDevice: [false]
    });
  }

  ngOnInit(): void {
    // Check for temp_token and method in URL parameters (from Google OAuth)
    this.route.queryParams.subscribe(params => {
      const tempToken = params['temp_token'];
      const method = params['method'];
      
      if (tempToken && typeof window !== 'undefined') {
        localStorage.setItem('temp_2fa_token', tempToken);
      }
      
      if (method && typeof window !== 'undefined') {
        localStorage.setItem('2fa_method', method);
      }
    });

    // Check if 2FA is required
    if (!this.authService.is2FARequired()) {
      this.router.navigate(['/signin']);
      return;
    }

    // Get 2FA method from localStorage (set during signin or from URL)
    const method = (typeof window !== 'undefined' ? localStorage.getItem('2fa_method') : null) || 'authenticator';
    this.twoFAMethod = method;
    
    // Set whether resend is available based on method
    this.canResendCode = this.accountSettingsService.canResendCode(method as 'sms' | 'email' | 'authenticator');
    
    // If it's SMS or Email, get the initial code with expiration
    if (this.canResendCode) {
      this.sendInitialCode();
    }
  }

  private sendInitialCode(): void {
    if (this.twoFAMethod === 'sms' || this.twoFAMethod === 'email') {
      this.accountSettingsService.sendLoginVerificationCode(
        this.twoFAMethod as 'sms' | 'email'
      ).subscribe({
        next: (response) => {
          if (response.expiresAt) {
            this.codeExpiresAt = response.expiresAt;
            this.updateExpirationMessage();
            // Start countdown timer
            this.startExpirationTimer();
          }
        },
        error: (error) => {
          console.error('Failed to send initial code:', error);
        }
      });
    }
  }

  private updateExpirationMessage(): void {
    if (this.codeExpiresAt) {
      this.expirationMessage = this.accountSettingsService.getExpirationMessage(this.codeExpiresAt);
    }
  }

  private startExpirationTimer(): void {
    // Update expiration message every minute
    setInterval(() => {
      this.updateExpirationMessage();
    }, 60000); // 60 seconds
  }

  verifyCode(): void {
    if (this.verificationForm.invalid) return;

    this.loading = true;
    const code = this.verificationForm.get('code')?.value;
    const rememberDevice = this.verificationForm.get('rememberDevice')?.value;

    this.authService.verify2FA(code, rememberDevice).subscribe({
      next: (response) => {
        this.loading = false;
        this.notificationService.addNotification({
          title: 'Login Successful',
          message: 'Two-factor authentication verified successfully.',
          type: 'success',
          isRead: false
        });
        this.router.navigate(['/dashboard']);
      },
      error: (error) => {
        this.loading = false;
        console.error('2FA verification error:', error);
        this.notificationService.addNotification({
          title: 'Verification Failed',
          message: 'Invalid verification code. Please try again.',
          type: 'error',
          isRead: false
        });
      }
    });
  }

  resendCode(): void {
    if (!this.canResendCode) {
      this.notificationService.addNotification({
        title: 'Not Available',
        message: 'Resend is not available for authenticator apps.',
        type: 'warning',
        isRead: false
      });
      return;
    }

    this.resendLoading = true;

    this.accountSettingsService.sendLoginVerificationCode(
      this.twoFAMethod as 'sms' | 'email'
    ).subscribe({
      next: (response: TwoFactorCodeResponse) => {
        this.resendLoading = false;
        
        if (response.success) {
          this.codeExpiresAt = response.expiresAt || '';
          this.updateExpirationMessage();
          
          const methodText = this.twoFAMethod === 'sms' ? 'SMS' : 'Email';
          this.notificationService.addNotification({
            title: 'Code Sent',
            message: `${methodText} verification code has been resent. ${this.expirationMessage}`,
            type: 'success',
            isRead: false
          });
        } else {
          this.notificationService.addNotification({
            title: 'Error',
            message: response.message || 'Failed to resend code. Please try again.',
            type: 'error',
            isRead: false
          });
        }
      },
      error: (error) => {
        this.resendLoading = false;
        console.error('Resend code error:', error);
        
        let errorMessage = 'Failed to resend code. Please try again.';
        if (error.error?.detail) {
          errorMessage = error.error.detail;
        }
        
        this.notificationService.addNotification({
          title: 'Error',
          message: errorMessage,
          type: 'error',
          isRead: false
        });
      }
    });
  }
} 