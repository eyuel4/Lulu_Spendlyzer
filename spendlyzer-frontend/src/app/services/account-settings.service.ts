import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, BehaviorSubject, of } from 'rxjs';
import { tap, catchError, map } from 'rxjs/operators';
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
  id: number;
  user_id?: number;
  token_jti?: string;
  device_info?: string;
  ip_address?: string;
  user_agent?: string;
  created_at?: string;
  last_active_at?: string;
  is_current?: boolean;
  // UI-specific fields
  device?: string;
  location?: string;
  lastActive?: string;
  isCurrent?: boolean;
  ipAddress?: string;
}

export interface TwoFactorSettings {
  enabled: boolean;
  method: 'sms' | 'email' | 'authenticator';
  phoneNumber?: string;
  backupCodes: string[];
}

export interface TwoFactorCodeResponse {
  success: boolean;
  message: string;
  expiresAt?: string;
  method: 'sms' | 'email' | 'authenticator';
}

export interface ResendCodeResponse {
  success: boolean;
  message: string;
  expiresAt: string;
  method: 'sms' | 'email';
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
    const url = `${this.apiUrl}/sessions`;
    const token = this.authService.getToken();
    console.log('Fetching sessions from:', url);
    console.log('Token available:', !!token);
    
    if (!token) {
      console.error('No authentication token available');
      return of([]);
    }
    
    return this.http.get<any[]>(url).pipe(
      // Map backend fields to UI fields
      map((sessions: any[]) => {
        console.log('Raw sessions from API:', sessions);
        if (!sessions || sessions.length === 0) {
          console.log('No sessions found in database');
          return [];
        }
        return sessions.map((session: any) => ({
          ...session,
          device: session.device_info || session.user_agent || 'Unknown Device',
          location: session.ip_address || 'Unknown Location',
          lastActive: session.last_active_at,
          isCurrent: session.is_current,
          ipAddress: session.ip_address
        }));
      }),
      tap((mappedSessions: Session[]) => {
        console.log('Processed sessions:', mappedSessions);
      }),
      catchError((error) => {
        console.error('Session API error:', error);
        console.error('Error details:', error.status, error.message);
        // Return empty array instead of throwing error to show "No active sessions"
        return of([]);
      })
    );
  }

  logoutFromSession(sessionId: string): Observable<any> {
    const url = `${this.apiUrl}/sessions/${sessionId}`;
    return this.http.delete(url).pipe(
      tap((response: any) => {
        console.log('Session logged out successfully');
        // If logout is required, clear local storage
        if (response.logout_required) {
          this.authService.logout();
        }
      }),
      catchError(this.handleError)
    );
  }

  logoutFromAllSessions(): Observable<any> {
    const url = `${this.apiUrl}/sessions`;
    return this.http.delete(url).pipe(
      tap((response: any) => {
        console.log('All sessions logged out successfully');
        // If logout is required, clear local storage and redirect
        if (response.logout_required) {
          this.authService.logout();
        }
      }),
      catchError(this.handleError)
    );
  }

  // Two-Factor Authentication
  getTwoFactorSettings(): Observable<TwoFactorSettings> {
    const url = `${this.apiUrl}/users/2fa/settings`;
    return this.http.get<TwoFactorSettings>(url).pipe(
      catchError(() => of({ enabled: false, method: 'authenticator' as const, backupCodes: [] }))
    );
  }

  enableTwoFactor(method: 'sms' | 'email' | 'authenticator', phoneNumber?: string): Observable<any> {
    const url = `${this.apiUrl}/users/2fa/enable`;
    const payload: any = { method };
    if (phoneNumber) {
      payload.phone_number = phoneNumber;
    }
    return this.http.post(url, payload).pipe(
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

  // Send 2FA code with expiration (for SMS and Email)
  sendTwoFactorCode(method: 'sms' | 'email', phoneNumber?: string): Observable<TwoFactorCodeResponse> {
    const url = `${this.apiUrl}/users/2fa/send-code`;
    const payload: any = { method };
    if (method === 'sms' && phoneNumber) {
      payload.phone_number = phoneNumber;
    }
    
    // Get token (regular or temporary for 2FA flow)
    const token = this.authService.getToken() || (typeof window !== 'undefined' ? localStorage.getItem('temp_2fa_token') : null);
    let headers = new HttpHeaders();
    if (token) {
      headers = headers.set('Authorization', `Bearer ${token}`);
    }
    
    return this.http.post<TwoFactorCodeResponse>(url, payload, { headers }).pipe(
      tap((response) => {
        console.log(`${method.toUpperCase()} verification code sent successfully`);
        if (response.expiresAt) {
          console.log(`Code expires at: ${response.expiresAt}`);
        }
      }),
      catchError(this.handleError)
    );
  }

  // Send 2FA setup verification code (for SMS and Email during setup)
  sendSetupVerificationCode(method: 'sms' | 'email', phoneNumber?: string): Observable<TwoFactorCodeResponse> {
    const url = `${this.apiUrl}/users/2fa/send-setup-code`;
    const payload: any = { method };
    if (method === 'sms' && phoneNumber) {
      payload.phone_number = phoneNumber;
    }
    
    // Get token (regular or temporary for 2FA flow)
    const token = this.authService.getToken() || (typeof window !== 'undefined' ? localStorage.getItem('temp_2fa_token') : null);
    let headers = new HttpHeaders();
    if (token) {
      headers = headers.set('Authorization', `Bearer ${token}`);
    }
    
    return this.http.post<TwoFactorCodeResponse>(url, payload, { headers }).pipe(
      tap((response) => {
        console.log(`${method.toUpperCase()} setup verification code sent successfully`);
        if (response.expiresAt) {
          console.log(`Code expires at: ${response.expiresAt}`);
        }
      }),
      catchError(this.handleError)
    );
  }

  // Send 2FA login verification code (for SMS and Email during login)
  sendLoginVerificationCode(method: 'sms' | 'email', phoneNumber?: string): Observable<TwoFactorCodeResponse> {
    const url = `${this.apiUrl}/users/2fa/send-login-code`;
    const payload: any = { method };
    if (method === 'sms' && phoneNumber) {
      payload.phone_number = phoneNumber;
    }
    
    // Get temporary token for login flow
    const token = (typeof window !== 'undefined' ? localStorage.getItem('temp_2fa_token') : null) || this.authService.getToken();
    let headers = new HttpHeaders();
    if (token) {
      headers = headers.set('Authorization', `Bearer ${token}`);
    }
    
    return this.http.post<TwoFactorCodeResponse>(url, payload, { headers }).pipe(
      tap((response) => {
        console.log(`${method.toUpperCase()} login verification code sent successfully`);
        if (response.expiresAt) {
          console.log(`Code expires at: ${response.expiresAt}`);
        }
      }),
      catchError(this.handleError)
    );
  }

  // Resend 2FA code (only for SMS and Email, not for authenticator apps)
  resendTwoFactorCode(method: 'sms' | 'email'): Observable<ResendCodeResponse> {
    const url = `${this.apiUrl}/users/2fa/resend-code`;
    const payload = { method };
    
    // Get token (regular or temporary for 2FA flow)
    const token = this.authService.getToken() || (typeof window !== 'undefined' ? localStorage.getItem('temp_2fa_token') : null);
    let headers = new HttpHeaders();
    if (token) {
      headers = headers.set('Authorization', `Bearer ${token}`);
    }
    
    return this.http.post<ResendCodeResponse>(url, payload, { headers }).pipe(
      tap((response) => {
        console.log(`${method.toUpperCase()} verification code resent successfully`);
        console.log(`Code expires at: ${response.expiresAt}`);
      }),
      catchError(this.handleError)
    );
  }

  // Verify 2FA code during setup
  verify2FACode(code: string): Observable<any> {
    const url = `${this.apiUrl}/users/2fa/verify-setup`;
    const payload = { code };
    
    // Get token (regular or temporary for 2FA flow)
    const token = this.authService.getToken() || (typeof window !== 'undefined' ? localStorage.getItem('temp_2fa_token') : null);
    let headers = new HttpHeaders();
    if (token) {
      headers = headers.set('Authorization', `Bearer ${token}`);
    }
    
    return this.http.post(url, payload, { headers }).pipe(
      tap(() => console.log('2FA setup verification successful')),
      catchError(this.handleError)
    );
  }

  // Check if resend is available for the given 2FA method
  canResendCode(method: 'sms' | 'email' | 'authenticator'): boolean {
    return method === 'sms' || method === 'email';
  }

  // Get expiration message for display
  getExpirationMessage(expiresAt: string): string {
    const expiryDate = new Date(expiresAt);
    const now = new Date();
    const diffInMinutes = Math.ceil((expiryDate.getTime() - now.getTime()) / (1000 * 60));
    
    if (diffInMinutes <= 0) {
      return 'Code has expired. Please request a new one.';
    } else if (diffInMinutes === 1) {
      return 'Code expires in 1 minute.';
    } else {
      return `Code expires in ${diffInMinutes} minutes.`;
    }
  }

  // Notification Settings
  getNotificationSettings(): Observable<NotificationSettings> {
    const url = `${this.apiUrl}/users/notification-settings`;
    const token = this.authService.getToken();
    const headers = new HttpHeaders().set('Authorization', `Bearer ${token}`);
    return this.http.get<NotificationSettings>(url, { headers }).pipe(
      catchError(this.handleError)
    );
  }

  updateNotificationSettings(settings: NotificationSettings): Observable<any> {
    const url = `${this.apiUrl}/users/notification-settings`;
    const token = this.authService.getToken();
    const headers = new HttpHeaders().set('Authorization', `Bearer ${token}`);
    return this.http.put(url, settings, { headers }).pipe(
      tap(() => console.log('Notification settings updated successfully')),
      catchError(this.handleError)
    );
  }

  // Privacy Settings
  getPrivacySettings(): Observable<PrivacySettings> {
    const url = `${this.apiUrl}/users/privacy-settings`;
    const token = this.authService.getToken();
    const headers = new HttpHeaders().set('Authorization', `Bearer ${token}`);
    return this.http.get<PrivacySettings>(url, { headers }).pipe(
      catchError(this.handleError)
    );
  }

  updatePrivacySettings(settings: PrivacySettings): Observable<any> {
    const url = `${this.apiUrl}/users/privacy-settings`;
    const token = this.authService.getToken();
    const headers = new HttpHeaders().set('Authorization', `Bearer ${token}`);
    return this.http.put(url, settings, { headers }).pipe(
      tap(() => console.log('Privacy settings updated successfully')),
      catchError(this.handleError)
    );
  }

  // Family Management
  getAccountType(): Observable<AccountType> {
    const url = `${this.apiUrl}/users/account-type`;
    const token = this.authService.getToken();
    const headers = new HttpHeaders().set('Authorization', `Bearer ${token}`);
    return this.http.get<AccountType>(url, { headers }).pipe(
      tap(accountType => this.accountTypeSubject.next(accountType)),
      catchError(this.handleError)
    );
  }

  convertToFamilyAccount(): Observable<any> {
    const url = `${this.apiUrl}/users/convert-to-family`;
    const token = this.authService.getToken();
    const headers = new HttpHeaders().set('Authorization', `Bearer ${token}`);
    return this.http.post(url, {}, { headers }).pipe(
      tap(() => {
        this.accountTypeSubject.next({ type: 'family' });
        console.log('Account converted to family successfully');
      }),
      catchError(this.handleError)
    );
  }

  getFamilyMembers(): Observable<FamilyMember[]> {
    const url = `${this.apiUrl}/family/members`;
    const token = this.authService.getToken();
    const headers = new HttpHeaders().set('Authorization', `Bearer ${token}`);
    return this.http.get<FamilyMember[]>(url, { headers }).pipe(
      tap(members => this.familyMembersSubject.next(members)),
      catchError(this.handleError)
    );
  }

  getInvitations(): Observable<Invitation[]> {
    const url = `${this.apiUrl}/family/invitations`;
    const token = this.authService.getToken();
    const headers = new HttpHeaders().set('Authorization', `Bearer ${token}`);
    return this.http.get<Invitation[]>(url, { headers }).pipe(
      tap(invitations => this.invitationsSubject.next(invitations)),
      catchError(this.handleError)
    );
  }

  sendInvitation(invitation: InvitationRequest): Observable<any> {
    const url = `${this.apiUrl}/family/invitations`;
    const token = this.authService.getToken();
    const headers = new HttpHeaders().set('Authorization', `Bearer ${token}`);
    return this.http.post(url, invitation, { headers }).pipe(
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
    const token = this.authService.getToken();
    const headers = new HttpHeaders().set('Authorization', `Bearer ${token}`);
    return this.http.post(url, {}, { headers }).pipe(
      tap(() => console.log('Invitation resent successfully')),
      catchError(this.handleError)
    );
  }

  cancelInvitation(invitationId: number): Observable<any> {
    const url = `${this.apiUrl}/family/invitations/${invitationId}`;
    const token = this.authService.getToken();
    const headers = new HttpHeaders().set('Authorization', `Bearer ${token}`);
    return this.http.delete(url, { headers }).pipe(
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



} 