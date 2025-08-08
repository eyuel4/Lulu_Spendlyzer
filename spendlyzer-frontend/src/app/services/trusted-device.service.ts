import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { AuthService } from './auth.service';

export interface TrustedDevice {
  id: number;
  user_id: number;
  device_name: string;
  location: string;
  country_code: string;
  is_active: boolean;
  created_at: string;
  expires_at: string;
  last_used_at: string;
}

export interface TrustedDeviceList {
  devices: TrustedDevice[];
  total_count: number;
}

export interface TrustedDeviceCreate {
  remember_device: boolean;
  expiration_days: number;
}

export interface TrustedDeviceVerify {
  token: string;
  device_hash: string;
}

export interface TrustedDeviceCheck {
  is_trusted: boolean;
  reason?: string;
  device_name?: string;
  location?: string;
  expires_at?: string;
}

@Injectable({
  providedIn: 'root'
})
export class TrustedDeviceService {
  private apiUrl = `${environment.apiUrl}/auth`;

  constructor(
    private http: HttpClient,
    private authService: AuthService
  ) { }

  private getHeaders(): HttpHeaders {
    const token = this.authService.getToken();
    return new HttpHeaders({
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    });
  }

  /**
   * Create a new trusted device
   */
  createTrustedDevice(deviceData: TrustedDeviceCreate): Observable<TrustedDevice> {
    return this.http.post<TrustedDevice>(
      `${this.apiUrl}/trust-device`,
      deviceData,
      { headers: this.getHeaders() }
    );
  }

  /**
   * Get all trusted devices for the current user
   */
  getTrustedDevices(): Observable<TrustedDeviceList> {
    return this.http.get<TrustedDeviceList>(
      `${this.apiUrl}/trusted-devices`,
      { headers: this.getHeaders() }
    );
  }

  /**
   * Revoke a specific trusted device
   */
  revokeTrustedDevice(deviceId: number): Observable<any> {
    return this.http.delete(
      `${this.apiUrl}/trust-device/${deviceId}`,
      { headers: this.getHeaders() }
    );
  }

  /**
   * Revoke all trusted devices
   */
  revokeAllTrustedDevices(): Observable<any> {
    return this.http.delete(
      `${this.apiUrl}/trusted-devices/all`,
      { headers: this.getHeaders() }
    );
  }

  /**
   * Check if current request is from a trusted device
   */
  checkTrustedDevice(): Observable<TrustedDeviceCheck> {
    return this.http.get<TrustedDeviceCheck>(
      `${this.apiUrl}/trusted-devices/check`,
      { headers: this.getHeaders() }
    );
  }

  /**
   * Verify a trusted device token
   */
  verifyTrustedDevice(verifyData: TrustedDeviceVerify): Observable<any> {
    return this.http.post(
      `${this.apiUrl}/verify-trusted-device`,
      verifyData,
      { headers: this.getHeaders() }
    );
  }

  /**
   * Get trusted device token from cookies
   */
  getTrustedDeviceToken(): string | null {
    return this.getCookie('trusted_device_token');
  }

  /**
   * Set trusted device token in cookies
   */
  setTrustedDeviceToken(token: string, expiresInDays: number): void {
    const expires = new Date();
    expires.setDate(expires.getDate() + expiresInDays);
    
    document.cookie = `trusted_device_token=${token}; expires=${expires.toUTCString()}; path=/; secure; samesite=strict`;
  }

  /**
   * Remove trusted device token from cookies
   */
  removeTrustedDeviceToken(): void {
    document.cookie = 'trusted_device_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
  }

  /**
   * Generate device fingerprint
   */
  generateDeviceFingerprint(): string {
    const fingerprint = {
      userAgent: navigator.userAgent,
      screenResolution: `${screen.width}x${screen.height}`,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      language: navigator.language,
      platform: navigator.platform,
      cookieEnabled: navigator.cookieEnabled,
      doNotTrack: navigator.doNotTrack,
      hardwareConcurrency: navigator.hardwareConcurrency,
      maxTouchPoints: navigator.maxTouchPoints
    };

    // Create a simple hash of the fingerprint
    const fingerprintString = JSON.stringify(fingerprint);
    let hash = 0;
    for (let i = 0; i < fingerprintString.length; i++) {
      const char = fingerprintString.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32-bit integer
    }
    return Math.abs(hash).toString(36);
  }

  /**
   * Get device name for display
   */
  getDeviceName(): string {
    const userAgent = navigator.userAgent;
    
    // Detect device type
    let deviceType = 'Desktop';
    if (/Mobile|Android|iPhone|iPad/.test(userAgent)) {
      deviceType = 'Mobile';
    } else if (/iPad/.test(userAgent)) {
      deviceType = 'Tablet';
    }
    
    // Detect OS
    let os = 'Unknown OS';
    if (/Windows/.test(userAgent)) {
      os = 'Windows';
    } else if (/Mac/.test(userAgent)) {
      os = 'macOS';
    } else if (/Linux/.test(userAgent)) {
      os = 'Linux';
    } else if (/Android/.test(userAgent)) {
      os = 'Android';
    } else if (/iPhone|iPad/.test(userAgent)) {
      os = 'iOS';
    }
    
    // Detect browser
    let browser = 'Unknown Browser';
    if (/Chrome/.test(userAgent)) {
      browser = 'Chrome';
    } else if (/Firefox/.test(userAgent)) {
      browser = 'Firefox';
    } else if (/Safari/.test(userAgent)) {
      browser = 'Safari';
    } else if (/Edge/.test(userAgent)) {
      browser = 'Edge';
    }
    
    return `${deviceType} - ${os} - ${browser}`;
  }

  /**
   * Format date for display
   */
  formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
  }

  /**
   * Check if device is expired
   */
  isDeviceExpired(expiresAt: string): boolean {
    return new Date(expiresAt) < new Date();
  }

  /**
   * Get days until expiration
   */
  getDaysUntilExpiration(expiresAt: string): number {
    const now = new Date();
    const expires = new Date(expiresAt);
    const diffTime = expires.getTime() - now.getTime();
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  }

  /**
   * Helper method to get cookie value
   */
  private getCookie(name: string): string | null {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
      return parts.pop()?.split(';').shift() || null;
    }
    return null;
  }
} 