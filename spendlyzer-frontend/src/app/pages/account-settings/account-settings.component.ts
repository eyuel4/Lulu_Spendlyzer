import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { ThemeService, Theme } from '../../services/theme.service';
import { AccountSettingsService, FamilyMember, Invitation, InvitationRequest, Session, TwoFactorSettings } from '../../services/account-settings.service';
import { NotificationService } from '../../services/notification.service';

@Component({
  selector: 'app-account-settings',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './account-settings.component.html',
  styleUrls: ['./account-settings.component.scss']
})
export class AccountSettingsComponent implements OnInit {
  currentTheme: Theme = 'light';
  loading = true;
  activeTab = 'security';
  
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
  
  // Mock data for demonstration
  mockFamilyMembers: FamilyMember[] = [
    {
      id: 1,
      first_name: 'John',
      last_name: 'Doe',
      email: 'john.doe@example.com',
      role: 'Member',
      status: 'active',
      joined_at: '2024-01-15'
    },
    {
      id: 2,
      first_name: 'Jane',
      last_name: 'Smith',
      email: 'jane.smith@example.com',
      role: 'Member',
      status: 'pending'
    }
  ];
  
  mockInvitations: Invitation[] = [
    {
      id: 1,
      email: 'partner@example.com',
      first_name: 'Partner',
      last_name: 'Name',
      role: 'Member',
      status: 'pending',
      sent_at: '2024-01-20T10:00:00Z',
      expires_at: '2024-01-27T10:00:00Z'
    }
  ];

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
        // Fallback to mock data for development
        this.familyMembers = this.mockFamilyMembers;
      }
    });

    this.accountSettingsService.getInvitations().subscribe({
      next: (invitations) => {
        this.invitations = invitations;
      },
      error: (error) => {
        console.error('Error loading invitations:', error);
        // Fallback to mock data for development
        this.invitations = this.mockInvitations;
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
    this.accountSettingsService.getActiveSessions().subscribe({
      next: (sessions) => {
        this.activeSessions = sessions;
      },
      error: (error) => {
        console.error('Error loading sessions:', error);
        // Do not load mock data; show empty or error state only
        this.activeSessions = [];
      }
    });
  }

  logoutFromSession(session: Session): void {
    this.accountSettingsService.logoutFromSession(session.id).subscribe({
      next: () => {
        this.notificationService.addNotification({
          title: 'Session Logged Out',
          message: `Successfully logged out from ${session.device_info || session.user_agent || 'Unknown Device'}.`,
          type: 'success',
          isRead: false
        });
        this.loadActiveSessions();
      },
      error: (error) => {
        console.error('Error logging out from session:', error);
        this.notificationService.logSystemError('Logout Failed', 'Failed to logout from session', error);
      }
    });
  }

  logoutFromAllSessions(): void {
    this.accountSettingsService.logoutFromAllSessions().subscribe({
      next: () => {
        this.notificationService.addNotification({
          title: 'All Sessions Logged Out',
          message: 'Successfully logged out from all devices.',
          type: 'success',
          isRead: false
        });
        this.loadActiveSessions();
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
        // Load mock data for development
        this.twoFactorSettings = this.getMockTwoFactorSettings();
      }
    });
  }

  enableTwoFactor(method: 'sms' | 'email' | 'authenticator', phoneNumber?: string): void {
    this.accountSettingsService.enableTwoFactor(method, phoneNumber).subscribe({
      next: () => {
        this.notificationService.addNotification({
          title: 'Two-Factor Enabled',
          message: `Two-factor authentication has been enabled using ${method}.`,
          type: 'success',
          isRead: false
        });
        this.loadTwoFactorSettings();
        this.showTwoFactorModal = false;
      },
      error: (error) => {
        console.error('Error enabling 2FA:', error);
        this.notificationService.logSystemError('2FA Setup Failed', 'Failed to enable two-factor authentication', error);
      }
    });
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
  getMockTwoFactorSettings(): TwoFactorSettings {
    return {
      enabled: false,
      method: 'authenticator',
      backupCodes: ['123456', '234567', '345678', '456789', '567890']
    };
  }
} 