import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, BehaviorSubject, of } from 'rxjs';
import { tap, catchError } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import { AuthService } from './auth.service';

export interface SecuritySettings {
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
}

export interface NotificationSettings {
  emailNotifications: boolean;
  pushNotifications: boolean;
  transactionAlerts: boolean;
  budgetAlerts: boolean;
  familyUpdates: boolean;
  marketingEmails: boolean;
}

export interface PrivacySettings {
  profileVisibility: 'private' | 'family' | 'public';
  dataSharing: boolean;
  analyticsSharing: boolean;
  allowFamilyAccess: boolean;
}

export interface FamilyMember {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  role: string;
  status: 'active' | 'pending' | 'invited';
  joined_at?: string;
}

export interface Invitation {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  status: 'pending' | 'accepted' | 'expired' | 'cancelled';
  sent_at: string;
  expires_at: string;
}

export interface InvitationRequest {
  email: string;
  first_name?: string;
  last_name?: string;
  role: 'member' | 'admin';
}

export interface AccountType {
  type: 'personal' | 'family';
  familyGroupId?: number;
}

export interface Session {
  id: string;
  device_info?: string;
  ip_address?: string;
  user_agent?: string;
  last_active_at?: string;
  is_current?: boolean;
}

export interface TwoFactorSettings {
  enabled: boolean;
  method: 'sms' | 'email' | 'authenticator';
  phoneNumber?: string;
  backupCodes: string[];
}

@Injectable({
  providedIn: 'root'
})
export class AccountSettingsService {
  private apiUrl = environment.apiUrl;
  private familyMembersSubject = new BehaviorSubject<FamilyMember[]>([]);
  private invitationsSubject = new BehaviorSubject<Invitation[]>([]);
  private accountTypeSubject = new BehaviorSubject<AccountType>({ type: 'personal' });

  public familyMembers$ = this.familyMembersSubject.asObservable();
  public invitations$ = this.invitationsSubject.asObservable();
  public accountType$ = this.accountTypeSubject.asObservable();

  constructor(private http: HttpClient, private authService: AuthService) {}

  // Security Settings
  sendPasswordResetEmail(): Observable<any> {
    const user = this.authService.currentUserValue;
    const email = user?.email;
    if (!email) return of({ error: 'No email found' });
    const url = `${this.apiUrl}/auth/forgot-password`;
    return this.http.post(url, { email }).pipe(
      tap(() => console.log('Password reset email sent successfully')),
      catchError(this.handleError)
    );
  }

  updateEmail(newEmail: string): Observable<any> {
    const user = this.authService.currentUserValue;
    const userId = user?.id;
    const token = this.authService.getToken();
    if (!userId || !token) return of({ error: 'Not authenticated' });
    const headers = { 'Authorization': `Bearer ${token}` };
    const url = `${this.apiUrl}/users/${userId}`;
    return this.http.put(url, { email: newEmail }, { headers }).pipe(
      tap(() => console.log('Email updated successfully')),
      catchError(this.handleError)
    );
  }

  // Session Management
  getActiveSessions(): Observable<Session[]> {
    const url = `${this.apiUrl}/users/sessions`;
    return this.http.get<any[]>(url).pipe(
      // Map backend fields to UI fields
      tap(sessions => {
        sessions.forEach(session => {
          session.device = session.device_info || session.user_agent || 'Unknown Device';
          session.location = session.ip_address || 'Unknown Location';
          session.lastActive = session.last_active_at;
          session.isCurrent = session.is_current;
          session.ipAddress = session.ip_address;
        });
      }),
      catchError(this.handleError)
    );
  }

  logoutFromSession(sessionId: string): Observable<any> {
    const url = `${this.apiUrl}/users/sessions/${sessionId}`;
    return this.http.delete(url).pipe(
      tap(() => console.log('Session logged out successfully')),
      catchError(this.handleError)
    );
  }

  logoutFromAllSessions(): Observable<any> {
    const url = `${this.apiUrl}/users/sessions`;
    return this.http.delete(url).pipe(
      tap(() => console.log('All sessions logged out successfully')),
      catchError(this.handleError)
    );
  }

  // Two-Factor Authentication
  getTwoFactorSettings(): Observable<TwoFactorSettings> {
    const url = `${this.apiUrl}/users/2fa/settings`;
    return this.http.get<TwoFactorSettings>(url).pipe(
      catchError(this.handleError)
    );
  }

  enableTwoFactor(method: 'sms' | 'email' | 'authenticator', phoneNumber?: string): Observable<any> {
    const url = `${this.apiUrl}/users/2fa/enable`;
    return this.http.post(url, { method, phoneNumber }).pipe(
      tap(() => console.log('Two-factor authentication enabled')),
      catchError(this.handleError)
    );
  }

  disableTwoFactor(): Observable<any> {
    const url = `${this.apiUrl}/users/2fa/disable`;
    return this.http.post(url, {}).pipe(
      tap(() => console.log('Two-factor authentication disabled')),
      catchError(this.handleError)
    );
  }

  // Notification Settings
  getNotificationSettings(): Observable<NotificationSettings> {
    const url = `${this.apiUrl}/users/notification-settings`;
    return this.http.get<NotificationSettings>(url).pipe(
      catchError(this.handleError)
    );
  }

  updateNotificationSettings(settings: NotificationSettings): Observable<any> {
    const url = `${this.apiUrl}/users/notification-settings`;
    return this.http.put(url, settings).pipe(
      tap(() => console.log('Notification settings updated successfully')),
      catchError(this.handleError)
    );
  }

  // Privacy Settings
  getPrivacySettings(): Observable<PrivacySettings> {
    const url = `${this.apiUrl}/users/privacy-settings`;
    return this.http.get<PrivacySettings>(url).pipe(
      catchError(this.handleError)
    );
  }

  updatePrivacySettings(settings: PrivacySettings): Observable<any> {
    const url = `${this.apiUrl}/users/privacy-settings`;
    return this.http.put(url, settings).pipe(
      tap(() => console.log('Privacy settings updated successfully')),
      catchError(this.handleError)
    );
  }

  // Family Management
  getAccountType(): Observable<AccountType> {
    const url = `${this.apiUrl}/users/account-type`;
    return this.http.get<AccountType>(url).pipe(
      tap(accountType => this.accountTypeSubject.next(accountType)),
      catchError(this.handleError)
    );
  }

  convertToFamilyAccount(): Observable<any> {
    const url = `${this.apiUrl}/users/convert-to-family`;
    return this.http.post(url, {}).pipe(
      tap(() => {
        this.accountTypeSubject.next({ type: 'family' });
        console.log('Account converted to family successfully');
      }),
      catchError(this.handleError)
    );
  }

  getFamilyMembers(): Observable<FamilyMember[]> {
    const url = `${this.apiUrl}/family/members`;
    return this.http.get<FamilyMember[]>(url).pipe(
      tap(members => this.familyMembersSubject.next(members)),
      catchError(this.handleError)
    );
  }

  getInvitations(): Observable<Invitation[]> {
    const url = `${this.apiUrl}/family/invitations`;
    return this.http.get<Invitation[]>(url).pipe(
      tap(invitations => this.invitationsSubject.next(invitations)),
      catchError(this.handleError)
    );
  }

  sendInvitation(invitation: InvitationRequest): Observable<any> {
    const url = `${this.apiUrl}/family/invitations`;
    return this.http.post(url, invitation).pipe(
      tap(() => {
        console.log('Invitation sent successfully');
        // Refresh invitations list
        this.getInvitations().subscribe();
      }),
      catchError(this.handleError)
    );
  }

  resendInvitation(invitationId: number): Observable<any> {
    const url = `${this.apiUrl}/family/invitations/${invitationId}/resend`;
    return this.http.post(url, {}).pipe(
      tap(() => console.log('Invitation resent successfully')),
      catchError(this.handleError)
    );
  }

  cancelInvitation(invitationId: number): Observable<any> {
    const url = `${this.apiUrl}/family/invitations/${invitationId}`;
    return this.http.delete(url).pipe(
      tap(() => {
        console.log('Invitation cancelled successfully');
        // Refresh invitations list
        this.getInvitations().subscribe();
      }),
      catchError(this.handleError)
    );
  }

  removeFamilyMember(memberId: number): Observable<any> {
    const url = `${this.apiUrl}/family/members/${memberId}`;
    return this.http.delete(url).pipe(
      tap(() => {
        console.log('Family member removed successfully');
        // Refresh family members list
        this.getFamilyMembers().subscribe();
      }),
      catchError(this.handleError)
    );
  }

  updateFamilyMemberRole(memberId: number, role: string): Observable<any> {
    const url = `${this.apiUrl}/family/members/${memberId}/role`;
    return this.http.put(url, { role }).pipe(
      tap(() => {
        console.log('Family member role updated successfully');
        // Refresh family members list
        this.getFamilyMembers().subscribe();
      }),
      catchError(this.handleError)
    );
  }

  // Utility methods
  refreshFamilyData(): void {
    this.getFamilyMembers().subscribe();
    this.getInvitations().subscribe();
  }

  private handleError(error: any): Observable<never> {
    console.error('Account settings service error:', error);
    throw error;
  }

  // Mock data methods for development
  getMockFamilyMembers(): FamilyMember[] {
    return [
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
  }

  getMockInvitations(): Invitation[] {
    return [
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
  }

  // Development mode methods
  getMockNotificationSettings(): NotificationSettings {
    return {
      emailNotifications: true,
      pushNotifications: true,
      transactionAlerts: true,
      budgetAlerts: true,
      familyUpdates: true,
      marketingEmails: false
    };
  }

  getMockPrivacySettings(): PrivacySettings {
    return {
      profileVisibility: 'private',
      dataSharing: false,
      analyticsSharing: true,
      allowFamilyAccess: true
    };
  }
} 