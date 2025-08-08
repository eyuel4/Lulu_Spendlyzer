import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule, FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { ThemeService, Theme } from '../../services/theme.service';
import { AccountSettingsService, FamilyMember, Invitation, InvitationRequest, Session, TwoFactorSettings } from '../../services/account-settings.service';
import { NotificationService } from '../../services/notification.service';
import { TrustedDevicesComponent } from './trusted-devices.component';

@Component({
  selector: 'app-account-settings',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, FormsModule, TrustedDevicesComponent],
  templateUrl: './account-settings.component.html',
  styleUrls: ['./account-settings.component.scss']
})
export class AccountSettingsComponent implements OnInit {
  currentTheme: Theme = 'light';
  loading = true;
  activeTab = 'security';
  
  // User authentication info
  isSocialLogin = false;
  currentUser: any = null;
  
  // Form groups
  emailChangeForm: FormGroup;
  notificationForm: FormGroup;
  privacyForm: FormGroup;
  
  // Family management
  accountType: 'personal' | 'family' = 'personal';
  familyMembers: FamilyMember[] = [];
  invitations: Invitation[] = [];
  showInviteModal = false;
  showConversionWarning = false;
  
  // Security management
  activeSessions: Session[] = [];
  twoFactorSettings: TwoFactorSettings | null = null;
  showTwoFactorModal = false;
  showSessionModal = false;
  showQRCodeModalFlag = false;
  qrCodeData: { qrCodeUrl: string; secretKey: string; backupCodes: string[] } | null = null;
  selected2FAMethod: 'authenticator' | 'sms' | 'email' | null = null;
  phoneNumber = '';
  
  // 2FA verification flow properties
  showVerificationModal = false;
  verificationCode = '';
  isVerifying = false;
  pending2FAMethod: 'sms' | 'email' | null = null;
  pendingPhoneNumber = '';


  constructor(
    private fb: FormBuilder,
    private router: Router,
    private authService: AuthService,
    private themeService: ThemeService,
    private accountSettingsService: AccountSettingsService,
    private notificationService: NotificationService
  ) {
    this.emailChangeForm = this.fb.group({
      newEmail: ['', [Validators.required, Validators.email]],
      confirmEmail: ['', [Validators.required, Validators.email]]
    }, { validators: this.emailMatchValidator });
    
    this.notificationForm = this.fb.group({
      emailNotifications: [true],
      pushNotifications: [true],
      transactionAlerts: [true],
      budgetAlerts: [true],
      familyUpdates: [true],
      marketingEmails: [false]
    });
    
    this.privacyForm = this.fb.group({
      profileVisibility: ['private'],
      dataSharing: [false],
      analyticsSharing: [true],
      allowFamilyAccess: [true]
    });
  }

  ngOnInit(): void {
    this.loadUserData();
    this.loadFamilyData();
    this.loadSettings();
    this.loadActiveSessions();
    this.loadTwoFactorSettings();
    
    // Subscribe to theme changes
    this.themeService.currentTheme$.subscribe(theme => {
      this.currentTheme = theme;
    });
  }

  private loadUserData(): void {
    this.authService.fetchCurrentUser().subscribe({
      next: (user) => {
        this.currentUser = user;
        // Check if user is social login (Google)
        this.isSocialLogin = user.auth_provider === 'google';
        // Determine account type based on user data
        this.accountType = user.family_group_id ? 'family' : 'personal';
        this.loading = false;
      },
      error: (error) => {
        console.error('Error loading user data:', error);
        this.loading = false;
      }
    });
  }

  private loadFamilyData(): void {
    // Load family members and invitations using service
    this.accountSettingsService.getFamilyMembers().subscribe({
      next: (members) => {
        this.familyMembers = members;
      },
      error: (error) => {
        console.error('Error loading family members:', error);
        this.familyMembers = [];
      }
    });

    this.accountSettingsService.getInvitations().subscribe({
      next: (invitations) => {
        this.invitations = invitations;
      },
      error: (error) => {
        console.error('Error loading invitations:', error);
        this.invitations = [];
      }
    });
  }

  private loadSettings(): void {
    // Load notification and privacy settings
    this.accountSettingsService.getNotificationSettings().subscribe({
      next: (settings) => {
        this.notificationForm.patchValue(settings);
      },
      error: (error) => {
        console.error('Error loading notification settings:', error);
        // Use default values
      }
    });

    this.accountSettingsService.getPrivacySettings().subscribe({
      next: (settings) => {
        this.privacyForm.patchValue(settings);
      },
      error: (error) => {
        console.error('Error loading privacy settings:', error);
        // Use default values
      }
    });
  }

  private emailMatchValidator(form: FormGroup): {[key: string]: any} | null {
    const newEmail = form.get('newEmail');
    const confirmEmail = form.get('confirmEmail');
    
    if (newEmail && confirmEmail && newEmail.value !== confirmEmail.value) {
      return { emailMismatch: true };
    }
    return null;
  }

  // Navigation
  goBack(): void {
    this.router.navigate(['/dashboard']);
  }

  // Tab navigation
  setActiveTab(tab: string): void {
    this.activeTab = tab;
  }

  // Security settings
  resetPassword(): void {
    this.accountSettingsService.sendPasswordResetEmail().subscribe({
      next: (res) => {
        if (res?.error) {
          this.notificationService.addNotification({
            title: 'Password Reset Failed',
            message: res.error,
            type: 'error',
            isRead: false
          });
        } else {
          this.notificationService.addNotification({
            title: 'Password Reset Email Sent',
            message: 'Check your email for password reset instructions.',
            type: 'success',
            isRead: false
          });
        }
      },
      error: (error) => {
        if (error.status === 401) {
          this.authService.logout();
          this.router.navigate(['/signin']);
        }
        this.notificationService.logSystemError('Password Reset Failed', 'Failed to send password reset email', error);
      }
    });
  }

  updateEmail(): void {
    if (this.emailChangeForm.valid) {
      this.accountSettingsService.updateEmail(this.emailChangeForm.value.newEmail).subscribe({
        next: (res) => {
          if (res?.error) {
            this.notificationService.addNotification({
              title: 'Email Update Failed',
              message: res.error,
              type: 'error',
              isRead: false
            });
          } else {
            this.emailChangeForm.reset();
            this.notificationService.addNotification({
              title: 'Email Updated',
              message: 'Your email address has been successfully updated.',
              type: 'success',
              isRead: false
            });
          }
        },
        error: (error) => {
          if (error.status === 401) {
            this.authService.logout();
            this.router.navigate(['/signin']);
          }
          this.notificationService.logSystemError('Email Update Failed', 'Failed to update email address', error);
        }
      });
    }
  }

  // Session Management
  loadActiveSessions(): void {
    console.log('Loading active sessions...');
    console.log('Current user:', this.currentUser);
    console.log('Is authenticated:', this.authService.isAuthenticated());
    
    this.accountSettingsService.getActiveSessions().subscribe({
      next: (sessions) => {
        console.log('Received sessions in component:', sessions);
        this.activeSessions = sessions || [];
        if (this.activeSessions.length === 0) {
          console.log('No active sessions found');
        }
      },
      error: (error) => {
        console.error('Error loading sessions:', error);
        this.activeSessions = [];
      }
    });
  }

  logoutFromSession(session: Session): void {
    console.log('Logging out session:', session);
    this.accountSettingsService.logoutFromSession(session.id.toString()).subscribe({
      next: (response) => {
        console.log('Logout response:', response);
        
        // Check if this was the current session
        if (session.isCurrent) {
          this.notificationService.addNotification({
            title: 'Current Session Logged Out',
            message: 'You have been logged out from this device. Redirecting to login.',
            type: 'info',
            isRead: false
          });
          // Clear local storage and redirect to login
          this.authService.logout();
          this.router.navigate(['/signin']);
        } else {
          this.notificationService.addNotification({
            title: 'Session Logged Out',
            message: `Successfully logged out from ${session.device || 'Unknown Device'}.`,
            type: 'success',
            isRead: false
          });
          this.loadActiveSessions();
        }
      },
      error: (error) => {
        console.error('Error logging out from session:', error);
        this.notificationService.logSystemError('Logout Failed', 'Failed to logout from session', error);
      }
    });
  }

  logoutFromAllSessions(): void {
    console.log('Logging out from all sessions');
    this.accountSettingsService.logoutFromAllSessions().subscribe({
      next: (response) => {
        console.log('Logout all response:', response);
        this.notificationService.addNotification({
          title: 'All Sessions Logged Out',
          message: 'Successfully logged out from all devices. You will be redirected to login.',
          type: 'success',
          isRead: false
        });
        
        // Clear local storage and redirect to login
        this.authService.logout();
        this.router.navigate(['/signin']);
      },
      error: (error) => {
        console.error('Error logging out from all sessions:', error);
        this.notificationService.logSystemError('Logout Failed', 'Failed to logout from all sessions', error);
      }
    });
  }

  // Two-Factor Authentication
  loadTwoFactorSettings(): void {
    this.accountSettingsService.getTwoFactorSettings().subscribe({
      next: (settings) => {
        this.twoFactorSettings = settings;
      },
      error: (error) => {
        console.error('Error loading 2FA settings:', error);
        this.twoFactorSettings = null;
      }
    });
  }

  enableTwoFactor(method: 'sms' | 'email' | 'authenticator', phoneNumber?: string): void {
    this.accountSettingsService.enableTwoFactor(method, phoneNumber).subscribe({
      next: (response) => {
        this.notificationService.addNotification({
          title: 'Two-Factor Enabled',
          message: `Two-factor authentication has been enabled using ${method}.`,
          type: 'success',
          isRead: false
        });
        
        // Handle different 2FA methods
        if (method === 'authenticator' && response.qr_code_url) {
          // Show QR code modal
          this.showQRCodeModal(response.qr_code_url, response.secret_key, response.backup_codes);
        } else if (method === 'sms') {
          // Show SMS setup confirmation
          this.notificationService.addNotification({
            title: 'SMS 2FA Setup',
            message: `SMS 2FA has been enabled for ${phoneNumber}. You will receive a verification code when logging in.`,
            type: 'info',
            isRead: false
          });
        } else if (method === 'email') {
          // Show email setup confirmation
          this.notificationService.addNotification({
            title: 'Email 2FA Setup',
            message: 'Email 2FA has been enabled. You will receive a verification code when logging in.',
            type: 'info',
            isRead: false
          });
        }
        
        this.loadTwoFactorSettings();
        this.showTwoFactorModal = false;
      },
      error: (error) => {
        console.error('Error enabling 2FA:', error);
        this.notificationService.logSystemError('2FA Setup Failed', 'Failed to enable two-factor authentication', error);
      }
    });
  }

  showQRCodeModal(qrCodeUrl: string, secretKey: string, backupCodes: string[]): void {
    // Store QR code data for modal display
    this.qrCodeData = {
      qrCodeUrl,
      secretKey,
      backupCodes
    };
    this.showQRCodeModalFlag = true;
  }

  closeQRCodeModal(): void {
    this.showQRCodeModalFlag = false;
    this.qrCodeData = null;
  }

  copyToClipboard(text: string): void {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text).then(() => {
        this.notificationService.addNotification({
          title: 'Copied!',
          message: 'Secret key copied to clipboard.',
          type: 'success',
          isRead: false
        });
      });
    } else {
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = text;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      
      this.notificationService.addNotification({
        title: 'Copied!',
        message: 'Secret key copied to clipboard.',
        type: 'success',
        isRead: false
      });
    }
  }

  downloadBackupCodes(): void {
    if (!this.qrCodeData?.backupCodes) return;

    const content = `Spendlyzer Backup Codes\n\n` +
      `Generated on: ${new Date().toLocaleDateString()}\n\n` +
      `IMPORTANT: Keep these codes in a secure location. You can use them to access your account if you lose your authenticator device.\n\n` +
      `Backup Codes:\n` +
      this.qrCodeData.backupCodes.map((code, index) => `${index + 1}. ${code}`).join('\n') +
      `\n\nNote: Each code can only be used once.`;

    const blob = new Blob([content], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'spendlyzer-backup-codes.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);

    this.notificationService.addNotification({
      title: 'Downloaded!',
      message: 'Backup codes have been downloaded.',
      type: 'success',
      isRead: false
    });
  }

  select2FAMethod(method: 'authenticator' | 'sms' | 'email'): void {
    this.selected2FAMethod = method;
  }

  enableSelected2FA(): void {
    if (!this.selected2FAMethod) return;

    if (this.selected2FAMethod === 'sms' && !this.phoneNumber) {
      this.notificationService.addNotification({
        title: 'Phone Number Required',
        message: 'Please enter your phone number for SMS 2FA.',
        type: 'error',
        isRead: false
      });
      return;
    }

    // For SMS and Email, we need to verify first
    if (this.selected2FAMethod === 'sms' || this.selected2FAMethod === 'email') {
      this.pending2FAMethod = this.selected2FAMethod;
      this.pendingPhoneNumber = this.phoneNumber;
      this.sendVerificationCode();
    } else {
      // For authenticator, enable directly
      this.enableTwoFactor(this.selected2FAMethod, this.phoneNumber || undefined);
    }
  }

  sendVerificationCode(): void {
    if (!this.pending2FAMethod) return;

    this.accountSettingsService.sendSetupVerificationCode(
      this.pending2FAMethod,
      this.pending2FAMethod === 'sms' ? this.pendingPhoneNumber : undefined
    ).subscribe({
      next: (response) => {
        this.showVerificationModal = true;
        this.notificationService.addNotification({
          title: 'Verification Code Sent',
          message: `A verification code has been sent to your ${this.pending2FAMethod === 'sms' ? 'phone' : 'email'}.`,
          type: 'success',
          isRead: false
        });
      },
      error: (error) => {
        console.error('Error sending verification code:', error);
        this.notificationService.addNotification({
          title: 'Error',
          message: 'Failed to send verification code. Please try again.',
          type: 'error',
          isRead: false
        });
      }
    });
  }

  verifyAndEnable2FA(): void {
    if (!this.verificationCode || !this.pending2FAMethod) return;

    this.isVerifying = true;
    
    // First verify the code
    this.accountSettingsService.verify2FACode(this.verificationCode).subscribe({
      next: () => {
        // If verification successful, enable 2FA
        this.enableTwoFactor(this.pending2FAMethod!, this.pending2FAMethod === 'sms' ? this.pendingPhoneNumber : undefined);
        this.closeVerificationModal();
      },
      error: (error) => {
        this.isVerifying = false;
        console.error('Verification failed:', error);
        this.notificationService.addNotification({
          title: 'Verification Failed',
          message: 'Invalid verification code. Please try again.',
          type: 'error',
          isRead: false
        });
      }
    });
  }

  closeVerificationModal(): void {
    this.showVerificationModal = false;
    this.verificationCode = '';
    this.isVerifying = false;
    this.pending2FAMethod = null;
    this.pendingPhoneNumber = '';
  }

  resendVerificationCode(): void {
    this.sendVerificationCode();
  }

  cancel2FASetup(): void {
    this.selected2FAMethod = null;
    this.phoneNumber = '';
    this.showTwoFactorModal = false;
  }

  disableTwoFactor(): void {
    this.accountSettingsService.disableTwoFactor().subscribe({
      next: () => {
        this.notificationService.addNotification({
          title: 'Two-Factor Disabled',
          message: 'Two-factor authentication has been disabled.',
          type: 'success',
          isRead: false
        });
        this.loadTwoFactorSettings();
      },
      error: (error) => {
        console.error('Error disabling 2FA:', error);
        this.notificationService.logSystemError('2FA Disable Failed', 'Failed to disable two-factor authentication', error);
      }
    });
  }

  // Notification settings
  updateNotificationSettings(): void {
    if (this.notificationForm.valid) {
      this.accountSettingsService.updateNotificationSettings(this.notificationForm.value).subscribe({
        next: () => {
          console.log('Notification settings updated successfully');
          this.notificationService.addNotification({
            title: 'Settings Updated',
            message: 'Your notification preferences have been saved.',
            type: 'success',
            isRead: false
          });
        },
        error: (error) => {
          console.error('Error updating notification settings:', error);
          this.notificationService.logSystemError('Settings Update Failed', 'Failed to update notification settings', error);
        }
      });
    }
  }

  // Privacy settings
  updatePrivacySettings(): void {
    if (this.privacyForm.valid) {
      this.accountSettingsService.updatePrivacySettings(this.privacyForm.value).subscribe({
        next: () => {
          console.log('Privacy settings updated successfully');
          this.notificationService.addNotification({
            title: 'Privacy Settings Updated',
            message: 'Your privacy preferences have been saved.',
            type: 'success',
            isRead: false
          });
        },
        error: (error) => {
          console.error('Error updating privacy settings:', error);
          this.notificationService.logSystemError('Privacy Update Failed', 'Failed to update privacy settings', error);
        }
      });
    }
  }

  // Family management
  showInviteForm(): void {
    if (this.accountType === 'personal') {
      this.showConversionWarning = true;
    } else {
      this.showInviteModal = true;
    }
  }

  confirmAccountConversion(): void {
    this.accountSettingsService.convertToFamilyAccount().subscribe({
      next: () => {
        this.showConversionWarning = false;
        this.accountType = 'family';
        this.showInviteModal = true;
        this.notificationService.addNotification({
          title: 'Account Converted',
          message: 'Your account has been successfully converted to a family account.',
          type: 'success',
          isRead: false
        });
      },
      error: (error) => {
        console.error('Error converting account:', error);
        this.notificationService.logSystemError('Conversion Failed', 'Failed to convert account', error);
      }
    });
  }

  cancelAccountConversion(): void {
    this.showConversionWarning = false;
  }

  sendInvitation(invitationData: InvitationRequest): void {
    this.accountSettingsService.sendInvitation(invitationData).subscribe({
      next: () => {
        console.log('Invitation sent successfully');
        this.showInviteModal = false;
        this.notificationService.addNotification({
          title: 'Invitation Sent',
          message: `Invitation sent to ${invitationData.email} successfully.`,
          type: 'success',
          isRead: false
        });
      },
      error: (error) => {
        console.error('Error sending invitation:', error);
        this.notificationService.logSystemError('Invitation Failed', 'Failed to send invitation', error);
      }
    });
  }

  resendInvitation(invitation: Invitation): void {
    this.accountSettingsService.resendInvitation(invitation.id).subscribe({
      next: () => {
        console.log('Invitation resent successfully');
        this.notificationService.addNotification({
          title: 'Invitation Resent',
          message: `Invitation resent to ${invitation.email} successfully.`,
          type: 'success',
          isRead: false
        });
      },
      error: (error) => {
        console.error('Error resending invitation:', error);
        this.notificationService.logSystemError('Resend Failed', 'Failed to resend invitation', error);
      }
    });
  }

  cancelInvitation(invitation: Invitation): void {
    this.accountSettingsService.cancelInvitation(invitation.id).subscribe({
      next: () => {
        console.log('Invitation cancelled successfully');
        this.notificationService.addNotification({
          title: 'Invitation Cancelled',
          message: `Invitation to ${invitation.email} has been cancelled.`,
          type: 'success',
          isRead: false
        });
      },
      error: (error) => {
        console.error('Error cancelling invitation:', error);
        this.notificationService.logSystemError('Cancellation Failed', 'Failed to cancel invitation', error);
      }
    });
  }

  removeFamilyMember(member: FamilyMember): void {
    this.accountSettingsService.removeFamilyMember(member.id).subscribe({
      next: () => {
        console.log('Family member removed successfully');
        this.notificationService.addNotification({
          title: 'Member Removed',
          message: `${member.first_name} ${member.last_name} has been removed from your family group.`,
          type: 'success',
          isRead: false
        });
      },
      error: (error) => {
        console.error('Error removing family member:', error);
        this.notificationService.logSystemError('Removal Failed', 'Failed to remove family member', error);
      }
    });
  }

  // Utility methods
  getInvitationStatusColor(status: string): string {
    switch (status) {
      case 'pending': return 'text-yellow-600 bg-yellow-50 dark:text-yellow-400 dark:bg-yellow-900/20';
      case 'accepted': return 'text-green-600 bg-green-50 dark:text-green-400 dark:bg-green-900/20';
      case 'expired': return 'text-red-600 bg-red-50 dark:text-red-400 dark:bg-red-900/20';
      case 'cancelled': return 'text-gray-600 bg-gray-50 dark:text-gray-400 dark:bg-gray-900/20';
      default: return 'text-gray-600 bg-gray-50 dark:text-gray-400 dark:bg-gray-900/20';
    }
  }

  getMemberStatusColor(status: string): string {
    switch (status) {
      case 'active': return 'text-green-600 bg-green-50 dark:text-green-400 dark:bg-green-900/20';
      case 'pending': return 'text-yellow-600 bg-yellow-50 dark:text-yellow-400 dark:bg-yellow-900/20';
      case 'invited': return 'text-blue-600 bg-blue-50 dark:text-blue-400 dark:bg-blue-900/20';
      default: return 'text-gray-600 bg-gray-50 dark:text-gray-400 dark:bg-gray-900/20';
    }
  }

  formatDate(dateString: string): string {
    return new Date(dateString).toLocaleDateString();
  }

  getDaysUntilExpiry(expiresAt: string): number {
    const expiryDate = new Date(expiresAt);
    const now = new Date();
    const diffTime = expiryDate.getTime() - now.getTime();
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  }

  // Mock data methods for development

} 